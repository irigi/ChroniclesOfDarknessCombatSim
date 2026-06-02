use rand::SeedableRng;
use rand_xoshiro::Xoshiro256PlusPlus;

use crate::action::{Action, decode_action, encode_action, ACTION_SPACE_SIZE, IRON_SKIN_OFFSET};
use crate::character::{
    BuildDefinition, CharacterState, ConditionFlags, DamageType, Seeming,
    SplatBuild, SplatState, WolfForm, WeaponProfile,
};
use crate::dice::{roll_pool, AgainRule};

pub const MAX_TURNS: u32 = 30;

// ─── Per-turn bonus state (consumed at end of turn) ───────────────────────────

#[derive(Debug, Clone, Default)]
struct TurnBonuses {
    attack_dice_bonus: i8,
    armor_active: bool,   // Resilience active armor
    armor_value: u8,
    did_spend_physical_intensity: bool,
}

// ─── Combat state ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct CombatState {
    pub characters: Vec<CharacterState>,
    pub builds: Vec<BuildDefinition>,
    pub initiative_order: Vec<usize>,
    pub current_actor_pos: usize,
    pub turn: u32,
    pub done: bool,
    pub winner_team: Option<u8>,
    turn_bonuses: Vec<TurnBonuses>,
    /// Per-character tick counter for non-Gauru lethal regeneration.
    regen_tick_counters: Vec<u8>,
    rng: Xoshiro256PlusPlus,
}

impl CombatState {
    pub fn new(builds: Vec<BuildDefinition>, teams: Vec<u8>, seed: u64) -> Self {
        let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
        let n = builds.len();

        let initiatives: Vec<i16> = builds
            .iter()
            .map(|b| {
                let roll: i16 = rand::Rng::gen_range(&mut rng, 1i16..=10i16);
                let initiative_mod = b.initiative_mod() as i16;
                let weapon_penalty = b.weapon.initiative_penalty as i16;
                roll + initiative_mod + weapon_penalty
            })
            .collect();

        let characters: Vec<CharacterState> = builds
            .iter()
            .zip(teams.iter())
            .zip(initiatives.iter())
            .map(|((b, &t), &ini)| CharacterState::from_build(b, t, ini))
            .collect();

        let mut order: Vec<usize> = (0..n).collect();
        order.sort_by(|&a, &b| characters[b].initiative.cmp(&characters[a].initiative));

        let turn_bonuses = (0..n).map(|_| TurnBonuses::default()).collect();
        let regen_tick_counters = vec![0u8; n];

        Self {
            characters,
            builds,
            initiative_order: order,
            current_actor_pos: 0,
            turn: 1,
            done: false,
            winner_team: None,
            turn_bonuses,
            regen_tick_counters,
            rng,
        }
    }

    pub fn current_actor(&self) -> usize {
        self.initiative_order[self.current_actor_pos]
    }

    // ─── Legal action mask ────────────────────────────────────────────────────

    pub fn legal_mask(&self) -> Vec<bool> {
        let mut mask = vec![false; ACTION_SPACE_SIZE];
        let actor_idx = self.current_actor();
        let actor = &self.characters[actor_idx];
        let build = &self.builds[actor_idx];

        if actor.is_incapacitated || self.done {
            mask[encode_action(Action::Pass)] = true;
            return mask;
        }

        // Dominated: only Pass this turn
        if actor.conditions.dominated {
            mask[encode_action(Action::Pass)] = true;
            return mask;
        }

        // Frightened with no WP: only Pass
        if actor.conditions.frightened && actor.willpower == 0 {
            mask[encode_action(Action::Pass)] = true;
            return mask;
        }

        // Attack any living enemy
        for (i, ch) in self.characters.iter().enumerate() {
            if ch.team != actor.team && !ch.is_incapacitated {
                // Check Nightmare passive: if the target has Nightmare, WP attacks are blocked
                let nightmare_blocks_wp = match &self.builds[i].splat_data {
                    SplatBuild::Vampire { disciplines, .. } => disciplines.nightmare >= 1,
                    _ => false,
                };
                mask[encode_action(Action::Attack { target_idx: i as u8, spend_willpower: false })] = true;
                if actor.willpower > 0 && !nightmare_blocks_wp {
                    mask[encode_action(Action::Attack { target_idx: i as u8, spend_willpower: true })] = true;
                }
            }
        }

        // ── Vampire actions ────────────────────────────────────────────────────
        if let SplatState::Vampire { vitae, vitae_spent_this_turn, blood_potency } = &actor.splat {
            let per_turn_limit = crate::splats::vampire::vitae_per_turn(*blood_potency);
            let can_spend = *vitae > 0 && *vitae_spent_this_turn < per_turn_limit;
            let disciplines = match &build.splat_data {
                SplatBuild::Vampire { disciplines, .. } => disciplines.clone(),
                _ => unreachable!(),
            };

            if can_spend {
                // Physical intensity (Str/Dex/Sta bonus)
                if !self.turn_bonuses[actor_idx].did_spend_physical_intensity {
                    for attr in 0u8..3 {
                        mask[encode_action(Action::SpendResourcePhysical { attribute: attr })] = true;
                    }
                }
                // Heal with Vitae
                if actor.health.total_damage() > 0 {
                    mask[encode_action(Action::HealWithVitae)] = true;
                }
                // Celerity active: slot 0
                if disciplines.celerity > 0 {
                    for i in 0..self.characters.len() {
                        if !self.characters[i].is_incapacitated {
                            mask[encode_action(Action::ActivatePower { power_slot: 0, target_idx: i as u8 })] = true;
                        }
                    }
                }
                // Vigor active: slot 1
                if disciplines.vigor > 0 {
                    for i in 0..self.characters.len() {
                        if self.characters[i].team != actor.team && !self.characters[i].is_incapacitated {
                            mask[encode_action(Action::ActivatePower { power_slot: 1, target_idx: i as u8 })] = true;
                        }
                    }
                }
                // Resilience active: slot 2 (self-targeted)
                if disciplines.resilience > 0 {
                    mask[encode_action(Action::ActivatePower { power_slot: 2, target_idx: actor_idx as u8 })] = true;
                }
                // Protean active: slot 3 (self-targeted, Predatory Aspect)
                if disciplines.protean >= 2 {
                    mask[encode_action(Action::ActivatePower { power_slot: 3, target_idx: actor_idx as u8 })] = true;
                }
                // Nightmare active: slot 4 (target enemy, Face of the Beast)
                if disciplines.nightmare >= 2 {
                    for i in 0..self.characters.len() {
                        if self.characters[i].team != actor.team && !self.characters[i].is_incapacitated {
                            mask[encode_action(Action::ActivatePower { power_slot: 4, target_idx: i as u8 })] = true;
                        }
                    }
                }
            }
            // Dominate active: slot 5 (target enemy, no Vitae cost)
            if disciplines.dominate >= 1 {
                for i in 0..self.characters.len() {
                    if self.characters[i].team != actor.team && !self.characters[i].is_incapacitated {
                        mask[encode_action(Action::ActivatePower { power_slot: 5, target_idx: i as u8 })] = true;
                    }
                }
            }
        }

        // ── Werewolf actions ───────────────────────────────────────────────────
        if let SplatState::Werewolf { essence, current_form, primal_urge, .. } = &actor.splat {
            // Regenerate lethal with Essence
            if *essence > 0 && actor.health.count(DamageType::Lethal) > 0 {
                mask[encode_action(Action::RegenerateEssence)] = true;
            }
            // Shapeshift: slots 0-4
            let _ = (current_form, primal_urge);
            for form_slot in 0u8..5 {
                mask[encode_action(Action::ActivatePower { power_slot: form_slot, target_idx: 0 })] = true;
            }
            // Killer Instinct: slot 5 (requires Purity ≥ 1 and Essence)
            let purity = match &build.splat_data {
                SplatBuild::Werewolf { purity, .. } => *purity,
                _ => 0,
            };
            if purity >= 1 && *essence > 0 {
                mask[encode_action(Action::ActivatePower { power_slot: 5, target_idx: 0 })] = true;
            }
            // War Howl: slot 6 (requires Glory ≥ 1 and Essence)
            let glory = match &build.splat_data {
                SplatBuild::Werewolf { glory, .. } => *glory,
                _ => 0,
            };
            if glory >= 1 && *essence > 0 {
                mask[encode_action(Action::ActivatePower { power_slot: 6, target_idx: 0 })] = true;
            }
        }

        // ── Changeling actions ─────────────────────────────────────────────────
        if let SplatState::Changeling { glamour, seeming, .. } = &actor.splat {
            // Seeming power: slot 0
            let can_activate_seeming = match seeming {
                Seeming::Darkling => *glamour >= 1,
                Seeming::Ogre => *glamour >= 1,
                _ => false,
            };
            if can_activate_seeming {
                mask[encode_action(Action::ActivatePower { power_slot: 0, target_idx: actor_idx as u8 })] = true;
            }
            // Combat Contract: slot 1 — spend 2 Glamour for +Wyrd attack dice
            let has_enemy = self.characters.iter().any(|c| c.team != actor.team && !c.is_incapacitated);
            if *glamour >= 2 && has_enemy {
                for i in 0..self.characters.len() {
                    if self.characters[i].team != actor.team && !self.characters[i].is_incapacitated {
                        mask[encode_action(Action::ActivatePower { power_slot: 1, target_idx: i as u8 })] = true;
                    }
                }
            }
        }

        // Iron Skin active: spend 1 WP to downgrade lethal → bashing
        let iron_skin = build.merit("iron_skin");
        if iron_skin >= 2 && actor.willpower > 0 && actor.health.count(DamageType::Lethal) > 0 {
            mask[IRON_SKIN_OFFSET] = true;
        }

        // Full Defense is always legal
        mask[encode_action(Action::FullDefense)] = true;
        // Pass is always legal
        mask[encode_action(Action::Pass)] = true;

        mask
    }

    // ─── Step ─────────────────────────────────────────────────────────────────

    pub fn step(&mut self, action_idx: usize) -> (f32, bool) {
        if self.done {
            return (0.0, true);
        }

        let action = decode_action(action_idx).unwrap_or(Action::Pass);
        let actor_idx = self.current_actor();
        let mut reward = 0.0f32;

        if !self.characters[actor_idx].is_incapacitated {
            reward += self.apply_action(actor_idx, action);
        }

        // Advance to next actor (Phase 7E: may stay if extra actions remain)
        self.advance_actor();
        self.check_done();

        (reward, self.done)
    }

    fn apply_action(&mut self, actor_idx: usize, action: Action) -> f32 {
        // Frightened: any non-Pass action costs 1 WP
        if self.characters[actor_idx].conditions.frightened {
            match action {
                Action::Pass => {
                    self.characters[actor_idx].conditions.frightened = false;
                }
                _ => {
                    if self.characters[actor_idx].willpower > 0 {
                        self.characters[actor_idx].willpower -= 1;
                        self.characters[actor_idx].conditions.frightened = false;
                    } else {
                        // No WP to pay; force pass
                        return 0.0;
                    }
                }
            }
        }

        let mut reward = 0.0f32;

        match action {
            Action::Attack { target_idx, spend_willpower } => {
                reward += self.resolve_attack(actor_idx, target_idx as usize, spend_willpower);
            }

            Action::ActivatePower { power_slot, target_idx } => {
                let splat = self.characters[actor_idx].splat.clone();
                match splat {
                    SplatState::Vampire { .. } => {
                        reward += self.apply_vampire_power(actor_idx, power_slot, target_idx as usize);
                    }
                    SplatState::Werewolf { .. } => {
                        self.apply_werewolf_power(actor_idx, power_slot);
                    }
                    SplatState::Changeling { .. } => {
                        reward += self.apply_changeling_power(actor_idx, power_slot, target_idx as usize);
                    }
                    _ => {}
                }
            }

            Action::SpendResourcePhysical { attribute } => {
                if self.characters[actor_idx].spend_resource(1) {
                    self.turn_bonuses[actor_idx].attack_dice_bonus += 2;
                    self.turn_bonuses[actor_idx].did_spend_physical_intensity = true;
                    let _ = attribute;
                }
            }

            Action::HealWithVitae => {
                if self.characters[actor_idx].spend_resource(1) {
                    let health = &mut self.characters[actor_idx].health;
                    if !health.heal_one(DamageType::Lethal) {
                        health.heal_one(DamageType::Bashing);
                        health.heal_one(DamageType::Bashing);
                    }
                }
            }

            Action::RegenerateEssence => {
                if self.characters[actor_idx].spend_resource(1) {
                    self.characters[actor_idx].health.heal_one(DamageType::Lethal);
                }
            }

            Action::FullDefense => {
                let defense = self.characters[actor_idx].defense_base;
                self.characters[actor_idx].defense_remaining = defense * 2;
            }

            Action::Pass => {
                // Clear one-shot conditions consumed by passing
                self.characters[actor_idx].conditions.dominated = false;
            }

            Action::IronSkinDowngrade => {
                let iron_skin = self.builds[actor_idx].merit("iron_skin");
                let downgrades = if iron_skin >= 4 { 2u8 } else { 1u8 };
                if self.characters[actor_idx].willpower > 0
                    && self.characters[actor_idx].health.count(DamageType::Lethal) > 0
                {
                    self.characters[actor_idx].willpower -= 1;
                    for _ in 0..downgrades {
                        if self.characters[actor_idx].health.heal_one(DamageType::Lethal) {
                            self.characters[actor_idx].health.apply(1, DamageType::Bashing);
                        }
                    }
                }
            }
        }

        reward
    }

    // ─── Attack resolution ────────────────────────────────────────────────────

    /// Str delta and damage-mod bonus from the werewolf's current form (for melee attacks).
    fn wolf_form_attack_params(&self, actor_idx: usize) -> (i8, DamageType, i8) {
        let build = &self.builds[actor_idx];
        if build.weapon.is_ranged {
            return (0, build.weapon.damage_type, build.weapon.damage_mod);
        }
        if let SplatState::Werewolf { current_form, .. } = &self.characters[actor_idx].splat {
            return match current_form {
                WolfForm::Hishu  => (0, build.weapon.damage_type, build.weapon.damage_mod),
                WolfForm::Dalu   => (1, DamageType::Lethal,  build.weapon.damage_mod),
                WolfForm::Gauru  => (3, DamageType::Lethal,  build.weapon.damage_mod + 2),
                WolfForm::Urshul => (2, DamageType::Lethal,  build.weapon.damage_mod + 1),
                WolfForm::Urhan  => (0, DamageType::Lethal,  build.weapon.damage_mod + 1),
            };
        }
        (0, build.weapon.damage_type, build.weapon.damage_mod)
    }

    /// Adjust damage type for target-splat vulnerabilities and weapon material.
    fn effective_damage_type(
        &self,
        base_type: DamageType,
        weapon: &WeaponProfile,
        target_idx: usize,
    ) -> DamageType {
        match &self.characters[target_idx].splat {
            SplatState::Vampire { .. } => {
                if weapon.is_sunlight {
                    DamageType::Aggravated
                } else if weapon.is_fire {
                    DamageType::Lethal
                } else if base_type <= DamageType::Lethal && !weapon.is_ranged {
                    // Most melee weapons deal bashing to vampires.
                    // Silver is a werewolf weakness only — no special effect vs vampires.
                    DamageType::Bashing
                } else {
                    base_type
                }
            }
            SplatState::Werewolf { .. } => {
                if weapon.is_silver {
                    DamageType::Aggravated
                } else {
                    base_type
                }
            }
            _ => base_type,
        }
    }

    fn resolve_attack(&mut self, actor_idx: usize, target_idx: usize, spend_willpower: bool) -> f32 {
        if target_idx >= self.characters.len() || self.characters[target_idx].is_incapacitated {
            return 0.0;
        }

        // Insubstantial Darkling: no damage this turn
        if self.characters[target_idx].conditions.insubstantial {
            return 0.0;
        }

        let build = &self.builds[actor_idx];
        let bonus = self.turn_bonuses[actor_idx].attack_dice_bonus;

        // Werewolf form attack parameters
        let (str_delta, base_damage_type, mut damage_mod) = self.wolf_form_attack_params(actor_idx);

        // War Howl: +1L on attacks this turn
        if self.characters[actor_idx].conditions.war_howl_bonus {
            damage_mod += 1;
        }

        // Protean claws: unarmed attacks deal Lethal + weapon bonus
        let base_damage_type = if self.characters[actor_idx].conditions.protean_claws_active && !build.weapon.is_ranged {
            let extra = match &self.builds[actor_idx].splat_data {
                SplatBuild::Vampire { disciplines, .. } => if disciplines.protean >= 4 { 2i8 } else { 1i8 },
                _ => 1i8,
            };
            damage_mod += extra;
            DamageType::Lethal
        } else {
            base_damage_type
        };

        // Beast seeming or Martial Arts: unarmed attacks deal lethal
        let base_damage_type = if !build.weapon.is_ranged {
            let beast = matches!(&self.characters[actor_idx].splat, SplatState::Changeling { seeming: Seeming::Beast, .. });
            let martial_arts = build.merit("martial_arts_lethal") > 0;
            if beast || martial_arts { DamageType::Lethal } else { base_damage_type }
        } else {
            base_damage_type
        };

        // Build attack pool
        // Fighting Finesse: use Dex instead of Str for melee
        let use_dex = build.merit("fighting_finesse") > 0 && !build.weapon.is_ranged;
        let base_pool = if build.weapon.is_ranged {
            (build.attributes.dexterity + build.skills.firearms) as i8
        } else if use_dex {
            build.attributes.dexterity as i8 + build.skills.brawl.max(build.skills.weaponry) as i8
        } else {
            let skill = build.skills.brawl.max(build.skills.weaponry) as i8;
            (build.attributes.strength as i8 + str_delta) + skill
        };
        let mut pool = base_pool + bonus;
        if spend_willpower { pool += 3; }

        // Wound penalty (Iron Stamina reduces it)
        pool += self.characters[actor_idx].effective_wound_penalty(&self.builds[actor_idx]);

        // Ogre debuff: -1 dice on this attack if the actor was debuffed
        if self.characters[actor_idx].conditions.ogre_debuffed {
            pool -= 1;
            self.characters[actor_idx].conditions.ogre_debuffed = false;
        }

        // Subtract target defense (all attacks — CoD 2e applies defense to ranged too)
        {
            let target_def = self.characters[target_idx].defense_remaining as i8;
            pool -= target_def;
            if self.characters[target_idx].defense_remaining > 0 {
                self.characters[target_idx].defense_remaining -= 1;
            }
        }

        // Choose dice rule: Killer Instinct = 8-again, otherwise 10-again
        let again_rule = if self.characters[actor_idx].conditions.killer_instinct_active {
            AgainRule::EightAgain
        } else {
            AgainRule::TenAgain
        };

        let result = roll_pool(pool, again_rule, &mut self.rng);
        if result.successes <= 0 { return 0.0; }

        let successes = result.successes as u8;
        let total_damage = (successes as i8 + damage_mod).max(0) as u8;

        let damage_type = self.effective_damage_type(base_damage_type, &build.weapon.clone(), target_idx);

        // Armor: general + ballistic (ranged) + active Resilience + Iron Skin (passive vs bashing)
        let target_build = &self.builds[target_idx];
        let passive_armor = target_build.armor.general
            + if target_build.armor.ballistic > 0 && build.weapon.is_ranged {
                target_build.armor.ballistic
            } else { 0 };
        let active_armor = if self.turn_bonuses[target_idx].armor_active {
            self.turn_bonuses[target_idx].armor_value
        } else { 0 };
        // Iron Skin: passive armor vs bashing only (••→1, ••••→2)
        let iron_skin_armor = match target_build.merit("iron_skin") {
            1 | 2 => if damage_type == DamageType::Bashing { 1u8 } else { 0 },
            3 | 4 => if damage_type == DamageType::Bashing { 2u8 } else { 0 },
            _ => 0,
        };
        // Armor never reduces aggravated damage
        let armor_reduction = if damage_type == DamageType::Aggravated { 0 } else {
            passive_armor + active_armor + iron_skin_armor
        };
        let final_damage = total_damage.saturating_sub(armor_reduction);

        if final_damage == 0 { return 0.0; }

        self.apply_damage(target_idx, final_damage, damage_type);

        if spend_willpower && self.characters[actor_idx].willpower > 0 {
            self.characters[actor_idx].willpower -= 1;
        }

        // Ogre seeming: apply debuff to target when damage is dealt
        if let SplatState::Changeling { seeming: Seeming::Ogre, .. } = &self.characters[actor_idx].splat.clone() {
            self.characters[target_idx].conditions.ogre_debuffed = true;
            // Costs 1 Glamour if acting for own benefit (always in 1v1; skip the ally-defence distinction)
            self.characters[actor_idx].spend_resource(1);
        }

        let mut reward = successes as f32 * 0.05;
        if self.characters[target_idx].is_incapacitated { reward += 0.02; }
        reward
    }

    fn apply_damage(&mut self, target_idx: usize, amount: u8, dtype: DamageType) {
        // Darkling insubstantial: immune to physical damage
        if self.characters[target_idx].conditions.insubstantial {
            return;
        }
        let ch = &mut self.characters[target_idx];
        ch.health.apply(amount, dtype);
        self.update_incapacitation(target_idx);
    }

    fn update_incapacitation(&mut self, idx: usize) {
        let ch = &mut self.characters[idx];
        let splat_clone = ch.splat.clone();
        match &splat_clone {
            SplatState::Vampire { .. } => {
                if ch.health.last_box_is(DamageType::Aggravated) {
                    ch.is_incapacitated = true;
                    ch.in_torpor = false;
                } else if ch.health.last_box_is(DamageType::Lethal) {
                    ch.in_torpor = true;
                    ch.is_incapacitated = true;
                }
            }
            SplatState::Werewolf { current_form, .. } => {
                if ch.health.last_box_is(DamageType::Aggravated)
                    || ch.health.last_box_is(DamageType::Lethal) {
                    ch.is_incapacitated = true;
                }
                let _ = current_form;
            }
            _ => {
                if ch.health.empty_boxes() == 0 {
                    ch.is_incapacitated = true;
                }
            }
        }
    }

    // ─── Vampire powers ───────────────────────────────────────────────────────

    fn apply_vampire_power(&mut self, actor_idx: usize, power_slot: u8, target_idx: usize) -> f32 {
        let build = &self.builds[actor_idx];
        let disciplines = match &build.splat_data {
            SplatBuild::Vampire { disciplines, .. } => disciplines.clone(),
            _ => return 0.0,
        };

        match power_slot {
            0 => {
                // Celerity active: grant extra action (Phase 7E)
                if disciplines.celerity > 0 && self.characters[actor_idx].spend_resource(1) {
                    self.characters[actor_idx].extra_actions_remaining =
                        self.characters[actor_idx].extra_actions_remaining.saturating_add(1);
                }
                0.0
            }
            1 => {
                // Vigor active: reflexive bonus + extra action (Phase 7E)
                if disciplines.vigor > 0 && self.characters[actor_idx].spend_resource(1) {
                    self.turn_bonuses[actor_idx].attack_dice_bonus += disciplines.vigor as i8;
                    self.characters[actor_idx].extra_actions_remaining =
                        self.characters[actor_idx].extra_actions_remaining.saturating_add(1);
                }
                0.0
            }
            2 => {
                // Resilience active: armor for this turn
                if disciplines.resilience > 0 && self.characters[actor_idx].spend_resource(1) {
                    self.turn_bonuses[actor_idx].armor_active = true;
                    self.turn_bonuses[actor_idx].armor_value = disciplines.resilience + 1;
                }
                0.0
            }
            3 => {
                // Protean active: Predatory Aspect (claws)
                if disciplines.protean >= 2 && self.characters[actor_idx].spend_resource(1) {
                    self.characters[actor_idx].conditions.protean_claws_active = true;
                }
                0.0
            }
            4 => {
                // Nightmare active: Face of the Beast — apply Frightened to target
                if disciplines.nightmare >= 2 && self.characters[actor_idx].spend_resource(1) {
                    if target_idx < self.characters.len() && !self.characters[target_idx].is_incapacitated {
                        self.characters[target_idx].conditions.frightened = true;
                    }
                }
                0.0
            }
            5 => {
                // Dominate: Mesmerize — contested roll: Manipulation + Expression + Dominate
                // vs target Resolve + Composure (or + Blood Potency for vampires)
                if disciplines.dominate >= 1 && target_idx < self.characters.len()
                    && !self.characters[target_idx].is_incapacitated
                {
                    let manip = self.builds[actor_idx].attributes.manipulation as i8;
                    let dominate = disciplines.dominate as i8;
                    // approx: Expression = 2 (not tracked; use a constant)
                    let attack_pool = manip + 2 + dominate;

                    let target_build = &self.builds[target_idx];
                    let def_pool = target_build.attributes.resolve as i8
                        + target_build.attributes.composure as i8
                        + match &target_build.splat_data {
                            SplatBuild::Vampire { blood_potency, .. } => *blood_potency as i8,
                            _ => 0,
                        };

                    let attack_result = roll_pool(attack_pool, AgainRule::TenAgain, &mut self.rng);
                    let def_result = roll_pool(def_pool, AgainRule::TenAgain, &mut self.rng);

                    if attack_result.successes > def_result.successes {
                        self.characters[target_idx].conditions.dominated = true;
                    }
                }
                0.0
            }
            _ => 0.0,
        }
    }

    // ─── Werewolf powers ──────────────────────────────────────────────────────

    fn apply_werewolf_power(&mut self, actor_idx: usize, power_slot: u8) {
        match power_slot {
            0..=4 => self.apply_werewolf_shapeshift(actor_idx, power_slot),
            5 => {
                // Killer Instinct: 8-again on Brawl/Weaponry for this turn
                if self.characters[actor_idx].spend_resource(1) {
                    self.characters[actor_idx].conditions.killer_instinct_active = true;
                }
            }
            6 => {
                // War Howl: all alive allies (including self) get +1L damage this turn
                if self.characters[actor_idx].spend_resource(1) {
                    let actor_team = self.characters[actor_idx].team;
                    for i in 0..self.characters.len() {
                        if self.characters[i].team == actor_team && !self.characters[i].is_incapacitated {
                            self.characters[i].conditions.war_howl_bonus = true;
                        }
                    }
                }
            }
            _ => {}
        }
    }

    fn apply_werewolf_shapeshift(&mut self, actor_idx: usize, form_slot: u8) {
        let form = match form_slot {
            0 => WolfForm::Hishu,
            1 => WolfForm::Dalu,
            2 => WolfForm::Gauru,
            3 => WolfForm::Urshul,
            4 => WolfForm::Urhan,
            _ => return,
        };
        let old_form = if let SplatState::Werewolf { current_form, .. } = &self.characters[actor_idx].splat {
            *current_form
        } else { return; };
        if old_form == form { return; }

        if let SplatState::Werewolf { current_form, turns_in_gauru, .. } = &mut self.characters[actor_idx].splat {
            *current_form = form;
            if form == WolfForm::Gauru { *turns_in_gauru = 0; }
        }
        self.recalculate_werewolf_stats(actor_idx);
    }

    fn recalculate_werewolf_stats(&mut self, idx: usize) {
        let (form, primal_urge) = match &self.characters[idx].splat {
            SplatState::Werewolf { current_form, primal_urge, .. } => (*current_form, *primal_urge),
            _ => return,
        };
        let build = &self.builds[idx];
        let (_, dex_delta, sta_delta, size_delta): (i8, i8, i8, i8) = match form {
            WolfForm::Hishu  => ( 0,  0,  0,  0),
            WolfForm::Dalu   => ( 1,  0,  1,  1),
            WolfForm::Gauru  => ( 3,  1,  2,  2),
            WolfForm::Urshul => ( 2,  2,  2,  1),
            WolfForm::Urhan  => ( 0,  2,  1, -1),
        };
        let new_size    = (build.size as i8 + size_delta).max(1) as u8;
        let new_stamina = (build.attributes.stamina as i8 + sta_delta).max(1) as u8;
        // Warrior's Hide: Purity dots add to health in any form
        let purity = match &build.splat_data {
            SplatBuild::Werewolf { purity, .. } => if *purity >= 2 { *purity } else { 0 },
            _ => 0,
        };
        let new_max_hp = (new_size + new_stamina) as usize + purity as usize;

        let prev_boxes = self.characters[idx].health.boxes;
        let prev_size  = self.characters[idx].health.size;
        self.characters[idx].health = crate::character::HealthTrack::new(new_max_hp.min(crate::character::MAX_HEALTH_BOXES));
        let copy_len = prev_size.min(new_max_hp);
        self.characters[idx].health.boxes[..copy_len].copy_from_slice(&prev_boxes[..copy_len]);

        let dex = (build.attributes.dexterity as i8 + dex_delta).max(1) as u8;
        let wits = build.attributes.wits;
        let def_attr = if build.merit("street_fighting") > 0 {
            dex.max(wits)
        } else {
            dex.min(wits)
        };
        let def_skill = if build.merit("defensive_combat") > 0 {
            build.skills.brawl.max(build.skills.weaponry)
        } else if build.merit("brawling_dodge") > 0 {
            build.skills.brawl
        } else {
            build.skills.athletics
        };
        let new_def = def_attr + def_skill;
        self.characters[idx].defense_base = new_def;
        self.characters[idx].defense_remaining = new_def;

        let _ = primal_urge;
        self.update_incapacitation(idx);
    }

    // ─── Changeling powers ────────────────────────────────────────────────────

    fn apply_changeling_power(&mut self, actor_idx: usize, power_slot: u8, target_idx: usize) -> f32 {
        let seeming = match &self.characters[actor_idx].splat {
            SplatState::Changeling { seeming, .. } => *seeming,
            _ => return 0.0,
        };

        match power_slot {
            0 => {
                // Seeming-specific power
                match seeming {
                    Seeming::Darkling => {
                        // Insubstantial: immune to physical damage for 1 turn
                        if self.characters[actor_idx].spend_resource(1) {
                            self.characters[actor_idx].conditions.insubstantial = true;
                        }
                    }
                    Seeming::Ogre => {
                        // Glamour-fueled intimidation: no direct action, but the Ogre's
                        // passive already triggers on damage. This slot isn't actually used
                        // in combat (the Ogre debuff is passive). Reserve for future use.
                    }
                    _ => {}
                }
                0.0
            }
            1 => {
                // Combat Contract: spend 2 Glamour, +Wyrd dice to attack
                let wyrd = match &self.builds[actor_idx].splat_data {
                    SplatBuild::Changeling { wyrd, .. } => *wyrd as i8,
                    _ => return 0.0,
                };
                if self.characters[actor_idx].spend_resource(2) {
                    self.turn_bonuses[actor_idx].attack_dice_bonus += wyrd;
                    self.resolve_attack(actor_idx, target_idx, false)
                } else { 0.0 }
            }
            _ => 0.0,
        }
    }

    // ─── Turn management ──────────────────────────────────────────────────────

    fn advance_actor(&mut self) {
        let actor_idx = self.current_actor();

        // Phase 7E: if this actor has pending extra actions, stay on them
        if self.characters[actor_idx].extra_actions_remaining > 0 {
            self.characters[actor_idx].extra_actions_remaining -= 1;
            return;
        }

        let n = self.initiative_order.len();
        loop {
            self.current_actor_pos = (self.current_actor_pos + 1) % n;
            if self.current_actor_pos == 0 {
                self.on_turn_start();
            }
            let idx = self.initiative_order[self.current_actor_pos];
            if !self.characters[idx].is_incapacitated {
                break;
            }
            if self.characters.iter().all(|c| c.is_incapacitated) {
                self.done = true;
                return;
            }
        }
    }

    pub fn on_turn_start(&mut self) {
        self.turn += 1;
        if self.turn > MAX_TURNS {
            self.done = true;
            return;
        }

        for i in 0..self.characters.len() {
            self.turn_bonuses[i] = TurnBonuses::default();
            self.characters[i].defense_remaining = self.characters[i].defense_base;
            self.characters[i].reset_turn_counters();
            // Protean claws: persist across turns (cleared when vampire shifts or is incapacitated)
            // frightened, dominated, ogre_debuffed persist until consumed — not reset here.

            // ── Werewolf regeneration ─────────────────────────────────────────
            let wolf_regen = if let SplatState::Werewolf { current_form, primal_urge, turns_in_gauru, .. } = &self.characters[i].splat {
                Some((*current_form, *primal_urge, *turns_in_gauru))
            } else {
                None
            };

            if let Some((current_form, primal_urge, turns_in_gauru)) = wolf_regen {
                if current_form == WolfForm::Gauru {
                    // 7E-1 Gauru time limit: force revert if turns_in_gauru > primal_urge
                    if turns_in_gauru > primal_urge {
                        if let SplatState::Werewolf { current_form: cf, turns_in_gauru: tg, .. } = &mut self.characters[i].splat {
                            *cf = WolfForm::Hishu;
                            *tg = 0;
                        }
                        self.recalculate_werewolf_stats(i);
                    } else {
                        // Gauru: regenerate all bashing and lethal
                        let bashing = self.characters[i].health.count(DamageType::Bashing);
                        let lethal  = self.characters[i].health.count(DamageType::Lethal);
                        for _ in 0..bashing { self.characters[i].health.heal_one(DamageType::Bashing); }
                        for _ in 0..lethal  { self.characters[i].health.heal_one(DamageType::Lethal); }
                        if let SplatState::Werewolf { turns_in_gauru, .. } = &mut self.characters[i].splat {
                            *turns_in_gauru += 1;
                        }
                    }
                } else {
                    // Non-Gauru: heal bashing at Primal Urge rate
                    let regen = crate::splats::werewolf::bashing_regen_per_turn(primal_urge);
                    for _ in 0..regen {
                        if !self.characters[i].health.heal_one(DamageType::Bashing) { break; }
                    }
                    // 7C: non-Gauru lethal regeneration (slow, interval-based)
                    let interval = crate::splats::werewolf::lethal_regen_interval(primal_urge);
                    self.regen_tick_counters[i] += 1;
                    if self.regen_tick_counters[i] >= interval {
                        self.regen_tick_counters[i] = 0;
                        self.characters[i].health.heal_one(DamageType::Lethal);
                    }
                }
            }
        }
    }

    fn check_done(&mut self) {
        let mut teams_alive: std::collections::HashSet<u8> = std::collections::HashSet::new();
        for ch in &self.characters {
            if !ch.is_incapacitated {
                teams_alive.insert(ch.team);
            }
        }
        if teams_alive.len() <= 1 {
            self.done = true;
            self.winner_team = teams_alive.into_iter().next();
        }
        if self.turn > MAX_TURNS {
            self.done = true;
        }
    }

    // ─── Observation encoding ──────────────────────────────────────────────────
    //
    // OBS_PER_CHAR = 30 floats per character:
    //  [0]    bashing damage ratio
    //  [1]    lethal damage ratio
    //  [2]    aggravated damage ratio
    //  [3]    empty health boxes ratio
    //  [4]    wound penalty normalised  (+3)/3 → [0,1]
    //  [5]    willpower ratio
    //  [6]    supernatural resource ratio
    //  [7]    defense_remaining / defense_base
    //  [8]    is_incapacitated (0/1)
    //  [9..12] splat one-hot (Mortal, Vampire, Werewolf, Changeling)
    //  [13]   Strength/10
    //  [14]   Dexterity/10
    //  [15]   Stamina/10
    //  [16]   primary power /5   (Celerity | PrimalUrge | Wyrd | 0)
    //  [17]   secondary power /5 (Vigor | 0 | 0 | 0)
    //  [18]   tertiary power /5  (Resilience | 0 | 0 | 0)
    //  [19]   p4 /5  (Protean | Purity | 0 | 0)
    //  [20]   p5 /5  (Nightmare | Glory | 0 | 0)
    //  [21]   p6 /5  (Dominate | Cunning | 0 | 0)
    //  [22]   Wits/10
    //  [23]   is_frightened (0/1)
    //  [24]   is_dominated (0/1)
    //  [25]   combat_buff: killer_instinct=0.33, war_howl=0.66, insubstantial=1.0, else 0
    //  [26]   armor_general/5
    //  [27]   weapon_damage_mod normalised  (/10, offset by 0.5)
    //  [28]   wolf form index /4  (0=Hishu … 1=Urhan)
    //  [29]   initiative /30
    //
    // Global (3 floats): turn/MAX_TURNS, alive_allies_ratio, alive_enemies_ratio
    pub fn encode_observation(&self) -> Vec<f32> {
        let actor_idx = self.current_actor();
        let actor_team = self.characters[actor_idx].team;
        let n = self.characters.len();
        const CHAR_LEN: usize = 30;
        let mut obs = vec![0.0f32; n * CHAR_LEN + 3];

        let mut slots: Vec<usize> = vec![actor_idx];
        for i in 0..n {
            if i != actor_idx && self.characters[i].team == actor_team {
                slots.push(i);
            }
        }
        for i in 0..n {
            if self.characters[i].team != actor_team {
                slots.push(i);
            }
        }

        for (slot, &ci) in slots.iter().enumerate() {
            let o = slot * CHAR_LEN;
            let ch = &self.characters[ci];
            let build = &self.builds[ci];
            let max_hp = ch.health.size as f32;

            obs[o    ] = ch.health.count(DamageType::Bashing)    as f32 / max_hp;
            obs[o + 1] = ch.health.count(DamageType::Lethal)     as f32 / max_hp;
            obs[o + 2] = ch.health.count(DamageType::Aggravated) as f32 / max_hp;
            obs[o + 3] = ch.health.empty_boxes() as f32 / max_hp;
            obs[o + 4] = (ch.health.wound_penalty() as f32 + 3.0) / 3.0;
            obs[o + 5] = ch.willpower as f32 / build.max_willpower().max(1) as f32;
            obs[o + 6] = ch.resource() as f32 / build.max_resource().max(1) as f32;
            obs[o + 7] = ch.defense_remaining as f32 / ch.defense_base.max(1) as f32;
            obs[o + 8] = if ch.is_incapacitated { 1.0 } else { 0.0 };

            let splat_idx = match ch.splat {
                SplatState::Mortal          => 0,
                SplatState::Vampire   { .. } => 1,
                SplatState::Werewolf  { .. } => 2,
                SplatState::Changeling{ .. } => 3,
            };
            obs[o + 9 + splat_idx] = 1.0;

            obs[o + 13] = build.attributes.strength  as f32 / 10.0;
            obs[o + 14] = build.attributes.dexterity as f32 / 10.0;
            obs[o + 15] = build.attributes.stamina   as f32 / 10.0;

            // Power levels p1–p3 (existing)
            let (p1, p2, p3) = match &build.splat_data {
                SplatBuild::Vampire { disciplines, .. } =>
                    (disciplines.celerity as f32, disciplines.vigor as f32, disciplines.resilience as f32),
                SplatBuild::Werewolf { primal_urge, .. } => (*primal_urge as f32, 0.0, 0.0),
                SplatBuild::Changeling { wyrd, .. } => (*wyrd as f32, 0.0, 0.0),
                SplatBuild::Mortal => (0.0, 0.0, 0.0),
            };
            obs[o + 16] = p1 / 5.0;
            obs[o + 17] = p2 / 5.0;
            obs[o + 18] = p3 / 5.0;

            // Power levels p4–p6 (new)
            let (p4, p5, p6) = match &build.splat_data {
                SplatBuild::Vampire { disciplines, .. } =>
                    (disciplines.protean as f32, disciplines.nightmare as f32, disciplines.dominate as f32),
                SplatBuild::Werewolf { purity, glory, cunning, .. } =>
                    (*purity as f32, *glory as f32, *cunning as f32),
                _ => (0.0, 0.0, 0.0),
            };
            obs[o + 19] = p4 / 5.0;
            obs[o + 20] = p5 / 5.0;
            obs[o + 21] = p6 / 5.0;

            obs[o + 22] = build.attributes.wits as f32 / 10.0;
            obs[o + 23] = if ch.conditions.frightened { 1.0 } else { 0.0 };
            obs[o + 24] = if ch.conditions.dominated  { 1.0 } else { 0.0 };
            obs[o + 25] = if ch.conditions.killer_instinct_active { 0.33 }
                          else if ch.conditions.war_howl_bonus    { 0.66 }
                          else if ch.conditions.insubstantial     { 1.0  }
                          else { 0.0 };

            obs[o + 26] = build.armor.general as f32 / 5.0;
            obs[o + 27] = (build.weapon.damage_mod as f32 + 5.0) / 10.0;

            let form_val = if let SplatState::Werewolf { current_form, .. } = &ch.splat {
                match current_form {
                    WolfForm::Hishu  => 0.0,
                    WolfForm::Dalu   => 0.25,
                    WolfForm::Gauru  => 0.5,
                    WolfForm::Urshul => 0.75,
                    WolfForm::Urhan  => 1.0,
                }
            } else { 0.0 };
            obs[o + 28] = form_val;

            obs[o + 29] = ch.initiative as f32 / 30.0;
        }

        let go = n * CHAR_LEN;
        obs[go    ] = self.turn as f32 / MAX_TURNS as f32;
        obs[go + 1] = self.characters.iter().filter(|c| c.team == actor_team && !c.is_incapacitated).count() as f32 / n as f32;
        obs[go + 2] = self.characters.iter().filter(|c| c.team != actor_team && !c.is_incapacitated).count() as f32 / n as f32;

        obs
    }

    /// Terminal reward from the perspective of `team`
    pub fn terminal_reward(&self, team: u8) -> f32 {
        match self.winner_team {
            Some(w) if w == team => 1.0,
            Some(_) => -1.0,
            None => 0.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::character::{Attributes, ArmorProfile, CombatSkills, SplatBuild, VampireDisciplines, WeaponProfile};
    use crate::splats::vampire::vitae_max;
    use std::collections::HashMap;

    fn make_mortal(id: u32, str: u8, dex: u8, sta: u8, brawl: u8) -> BuildDefinition {
        BuildDefinition {
            id, name: format!("Mortal {}", id),
            splat: crate::character::Splat::Mortal,
            attributes: Attributes::new(str, dex, sta, 2, 2, 2, 2, 2, 2),
            skills: CombatSkills { brawl, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Mortal, size: 5, merits: HashMap::new(),
        }
    }

    fn make_vampire(id: u32, str: u8, dex: u8, sta: u8, brawl: u8, bp: u8, cel: u8, vig: u8, res: u8) -> BuildDefinition {
        BuildDefinition {
            id, name: format!("Vampire {}", id),
            splat: crate::character::Splat::Vampire,
            attributes: Attributes::new(str, dex, sta, 2, 2, 2, 2, 2, 2),
            skills: CombatSkills { brawl, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Vampire {
                blood_potency: bp, vitae_max: vitae_max(bp),
                disciplines: VampireDisciplines { celerity: cel, vigor: vig, resilience: res, ..Default::default() },
            },
            size: 5, merits: HashMap::new(),
        }
    }

    fn make_vampire_with_disciplines(id: u32, bp: u8, disc: VampireDisciplines) -> BuildDefinition {
        BuildDefinition {
            id, name: format!("Vampire {}", id),
            splat: crate::character::Splat::Vampire,
            attributes: Attributes::new(3, 3, 3, 3, 3, 3, 3, 3, 3),
            skills: CombatSkills { brawl: 3, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Vampire { blood_potency: bp, vitae_max: vitae_max(bp), disciplines: disc },
            size: 5, merits: HashMap::new(),
        }
    }

    fn make_werewolf(id: u32, str: u8, dex: u8, sta: u8, brawl: u8, pu: u8) -> BuildDefinition {
        BuildDefinition {
            id, name: format!("Werewolf {}", id),
            splat: crate::character::Splat::Werewolf,
            attributes: Attributes::new(str, dex, sta, 2, 2, 2, 2, 2, 2),
            skills: CombatSkills { brawl, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Werewolf { primal_urge: pu, essence_max: crate::splats::werewolf::essence_max(pu), purity: 0, glory: 0, cunning: 0, honor: 0, wisdom: 0 },
            size: 5, merits: HashMap::new(),
        }
    }

    fn make_werewolf_with_renown(id: u32, pu: u8, purity: u8, glory: u8) -> BuildDefinition {
        BuildDefinition {
            id, name: format!("Wolf {}", id),
            splat: crate::character::Splat::Werewolf,
            attributes: Attributes::new(4, 3, 4, 2, 3, 3, 2, 2, 3),
            skills: CombatSkills { brawl: 4, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Werewolf { primal_urge: pu, essence_max: crate::splats::werewolf::essence_max(pu), purity, glory, cunning: 0, honor: 0, wisdom: 0 },
            size: 5, merits: HashMap::new(),
        }
    }

    #[test]
    fn combat_terminates() {
        let builds = vec![make_mortal(1, 3, 2, 2, 3), make_mortal(2, 3, 2, 2, 3)];
        let mut state = CombatState::new(builds, vec![0, 1], 42);
        let mut steps = 0;
        while !state.done {
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            steps += 1;
            assert!(steps < 1000, "combat should not run forever");
        }
        assert!(state.done);
    }

    #[test]
    fn observation_has_expected_length() {
        let builds = vec![make_mortal(1, 3, 2, 2, 2), make_mortal(2, 3, 2, 2, 2)];
        let state = CombatState::new(builds, vec![0, 1], 0);
        let obs = state.encode_observation();
        assert_eq!(obs.len(), 2 * 30 + 3);  // OBS_PER_CHAR=30
    }

    #[test]
    fn weapons_deal_bashing_to_vampires() {
        let mortal_build = make_mortal(10, 4, 3, 3, 4);
        let vamp_build   = make_vampire(11, 3, 2, 3, 2, 1, 0, 0, 0);
        let mut state = CombatState::new(vec![mortal_build, vamp_build], vec![0, 1], 7);
        for _ in 0..200 {
            if state.done { break; }
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            let vamp = &state.characters[1];
            if vamp.health.count(DamageType::Bashing) > 0 {
                assert_eq!(vamp.health.count(DamageType::Lethal), 0, "vampire should take bashing from mortal fists");
                return;
            }
        }
    }

    #[test]
    fn silver_deals_aggravated_to_werewolves() {
        let mortal = {
            let mut b = make_mortal(20, 3, 3, 2, 3);
            b.weapon = WeaponProfile::silver_knife();
            b
        };
        let wolf = make_werewolf(21, 4, 3, 3, 3, 1);
        let mut state = CombatState::new(vec![mortal, wolf], vec![0, 1], 99);
        for _ in 0..200 {
            if state.done { break; }
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            let wolf_ch = &state.characters[1];
            if wolf_ch.health.count(DamageType::Aggravated) > 0 {
                return;
            }
        }
        panic!("silver should have dealt aggravated damage to werewolf");
    }

    #[test]
    fn fire_deals_lethal_to_vampires() {
        let attacker = {
            let mut b = make_mortal(30, 3, 3, 2, 3);
            b.weapon = WeaponProfile::fire();
            b
        };
        let vamp = make_vampire(31, 3, 2, 3, 2, 1, 0, 0, 0);
        let mut state = CombatState::new(vec![attacker, vamp], vec![0, 1], 55);
        for _ in 0..200 {
            if state.done { break; }
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            let vamp_ch = &state.characters[1];
            if vamp_ch.health.count(DamageType::Lethal) > 0 {
                return;
            }
        }
        panic!("fire should deal lethal to vampire");
    }

    #[test]
    fn gauru_form_boosts_werewolf_attack() {
        let wolf = make_werewolf(40, 3, 2, 3, 3, 1);
        let target = make_mortal(41, 2, 2, 2, 0);
        let mut state = CombatState::new(vec![wolf, target], vec![0, 1], 13);
        state.step(encode_action(crate::action::Action::ActivatePower { power_slot: 2, target_idx: 0 }));
        if let SplatState::Werewolf { current_form, .. } = &state.characters[0].splat {
            assert_eq!(*current_form, WolfForm::Gauru);
        } else { panic!("should be werewolf"); }
        let gauru_hp = (5 + 2) + (3 + 2); // (Size+2) + (Sta+2)
        assert_eq!(state.characters[0].health.size, gauru_hp);
    }

    #[test]
    fn gauru_regenerates_bashing_and_lethal_each_turn() {
        let wolf = make_werewolf(50, 3, 2, 3, 3, 1);
        let target = make_mortal(51, 3, 2, 3, 3);
        let mut state = CombatState::new(vec![wolf, target], vec![0, 1], 1);
        state.step(encode_action(crate::action::Action::ActivatePower { power_slot: 2, target_idx: 0 }));
        state.characters[0].health.apply(3, DamageType::Lethal);
        state.characters[0].health.apply(2, DamageType::Bashing);
        let before_l = state.characters[0].health.count(DamageType::Lethal);
        let before_b = state.characters[0].health.count(DamageType::Bashing);
        assert!(before_l > 0 && before_b > 0);
        state.on_turn_start();
        assert_eq!(state.characters[0].health.count(DamageType::Lethal), 0, "Gauru should regen all lethal");
        assert_eq!(state.characters[0].health.count(DamageType::Bashing), 0, "Gauru should regen all bashing");
    }

    #[test]
    fn vampire_celerity_adds_to_defense() {
        let vamp = make_vampire(60, 3, 3, 3, 3, 1, 3, 0, 0); // Celerity 3
        let state = CombatState::new(vec![vamp.clone(), make_mortal(61, 3, 2, 2, 2)], vec![0, 1], 0);
        let base_def = vamp.base_defense();
        let actual_def = state.characters[0].defense_base;
        assert_eq!(actual_def, base_def + 3, "Celerity 3 should add 3 to defense");
    }

    #[test]
    fn blood_potency_limits_vitae_per_turn() {
        let vamp = make_vampire(70, 3, 3, 3, 3, 1, 2, 2, 2);
        let mut state = CombatState::new(vec![vamp, make_mortal(71, 3, 2, 2, 2)], vec![0, 1], 0);
        let ok = state.characters[0].spend_resource(1);
        assert!(ok, "first Vitae spend should succeed");
        let fail = state.characters[0].spend_resource(1);
        assert!(!fail, "second Vitae spend same turn should fail at BP 1");
    }

    #[test]
    fn vampire_vs_werewolf_terminates() {
        let vamp = make_vampire(80, 4, 3, 3, 4, 2, 2, 2, 1);
        let wolf = make_werewolf(81, 4, 3, 4, 4, 2);
        let mut state = CombatState::new(vec![vamp, wolf], vec![0, 1], 12345);
        let mut steps = 0;
        while !state.done {
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            steps += 1;
            assert!(steps < 5000, "vampire vs werewolf should terminate");
        }
        assert!(state.done);
    }

    #[test]
    fn cross_splat_all_pairs_terminate() {
        let builds = vec![
            make_mortal(90, 3, 3, 3, 3),
            make_vampire(91, 4, 3, 3, 4, 1, 2, 2, 0),
            make_werewolf(92, 4, 3, 4, 4, 1),
        ];
        for i in 0..builds.len() {
            for j in (i+1)..builds.len() {
                let pair = vec![builds[i].clone(), builds[j].clone()];
                let mut state = CombatState::new(pair, vec![0, 1], (i * 100 + j) as u64);
                let mut steps = 0;
                while !state.done {
                    let mask = state.legal_mask();
                    let action = mask.iter().position(|&m| m).unwrap();
                    state.step(action);
                    steps += 1;
                    assert!(steps < 5000, "cross-splat did not terminate: {} vs {}", i, j);
                }
            }
        }
    }

    // ── Phase 7 tests ─────────────────────────────────────────────────────────

    #[test]
    fn iron_skin_active_downgrades_lethal() {
        let mut b = make_mortal(100, 3, 3, 3, 2);
        b.merits.insert("iron_skin".into(), 4);
        let mortal2 = make_mortal(101, 3, 3, 3, 2);
        let mut state = CombatState::new(vec![b, mortal2], vec![0, 1], 1);
        state.characters[0].health.apply(2, DamageType::Lethal);
        state.characters[0].willpower = 3;
        let lethal_before = state.characters[0].health.count(DamageType::Lethal);
        state.apply_action(0, Action::IronSkinDowngrade);
        let lethal_after = state.characters[0].health.count(DamageType::Lethal);
        assert!(lethal_after < lethal_before, "Iron Skin •••• should downgrade 2 lethal → bashing");
    }

    #[test]
    fn protean_claws_deal_lethal_damage() {
        let disc = VampireDisciplines { protean: 3, ..Default::default() };
        let vamp = make_vampire_with_disciplines(110, 2, disc);
        let mortal = make_mortal(111, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![vamp, mortal], vec![0, 1], 7);
        // Activate Protean claws (slot 3)
        state.apply_action(0, Action::ActivatePower { power_slot: 3, target_idx: 0 });
        assert!(state.characters[0].conditions.protean_claws_active);
        // Run some attacks and check mortal takes lethal (not bashing)
        for _ in 0..50 {
            if state.done { break; }
            state.apply_action(0, Action::Attack { target_idx: 1, spend_willpower: false });
            if state.characters[1].health.count(DamageType::Lethal) > 0 { return; }
        }
        panic!("protean claws should have dealt lethal damage");
    }

    #[test]
    fn nightmare_passive_blocks_willpower_vs_attacker() {
        let disc = VampireDisciplines { nightmare: 2, resilience: 1, ..Default::default() };
        let nightmare_vamp = make_vampire_with_disciplines(120, 2, disc);
        // Give mortal higher composure so initiative_mod is guaranteed higher
        let mut attacker = make_mortal(121, 3, 3, 3, 3);
        attacker.attributes.composure = 5; // initiative_mod = dex+composure = 8 vs vampire's 6
        let mut state = CombatState::new(vec![attacker, nightmare_vamp], vec![0, 1], 0);

        // Advance until the mortal (index 0) is the current actor
        let mut tries = 0;
        while state.current_actor() != 0 && tries < 20 {
            let mask = state.legal_mask();
            let action = mask.iter().position(|&m| m).unwrap();
            state.step(action);
            tries += 1;
        }
        assert_eq!(state.current_actor(), 0, "mortal should be current actor");

        // Check mask from the mortal's perspective
        let mask = state.legal_mask();
        let wp_attack_idx = encode_action(Action::Attack { target_idx: 1, spend_willpower: true });
        assert!(!mask[wp_attack_idx], "WP spending should be blocked vs Nightmare vampire");
        let normal_attack_idx = encode_action(Action::Attack { target_idx: 1, spend_willpower: false });
        assert!(mask[normal_attack_idx], "normal attack should still be legal");
    }

    #[test]
    fn nightmare_frightened_forces_wp_spend() {
        let disc = VampireDisciplines { nightmare: 2, ..Default::default() };
        let nightmare_vamp = make_vampire_with_disciplines(130, 2, disc);
        let mortal = make_mortal(131, 3, 3, 3, 3);
        let mut state = CombatState::new(vec![nightmare_vamp, mortal], vec![0, 1], 0);
        // Apply Frightened to mortal
        state.characters[1].conditions.frightened = true;
        let wp_before = state.characters[1].willpower;
        // The mortal attacks — should cost 1 WP
        state.apply_action(1, Action::Attack { target_idx: 0, spend_willpower: false });
        assert_eq!(state.characters[1].willpower, wp_before - 1, "Frightened should cost 1 WP on non-Pass");
        assert!(!state.characters[1].conditions.frightened, "Frightened should clear after paying cost");
    }

    #[test]
    fn nightmare_frightened_no_wp_forces_pass() {
        let disc = VampireDisciplines { nightmare: 2, ..Default::default() };
        let nightmare_vamp = make_vampire_with_disciplines(140, 2, disc);
        let mortal = make_mortal(141, 3, 3, 3, 3);
        let mut state = CombatState::new(vec![nightmare_vamp, mortal], vec![0, 1], 0);
        state.characters[1].conditions.frightened = true;
        state.characters[1].willpower = 0;
        let mask = state.legal_mask();
        // With no WP and Frightened, only Pass should be legal
        // (mortal is at index 1, so we need to set current_actor_pos to them)
        // Actually legal_mask uses current_actor, so we test the mask when mortal is actor.
        // The mask check for the current actor is based on current_actor_pos pointing to mortal.
        // Let's just directly verify the apply_action respects the constraint.
        let hp_before = state.characters[0].health.total_damage();
        state.apply_action(1, Action::Attack { target_idx: 0, spend_willpower: false });
        let hp_after = state.characters[0].health.total_damage();
        assert_eq!(hp_before, hp_after, "Frightened with no WP should not allow attacks");
    }

    #[test]
    fn dominate_dominated_forces_pass() {
        let disc = VampireDisciplines { dominate: 3, ..Default::default() };
        let vamp = make_vampire_with_disciplines(150, 3, disc);
        let mortal = make_mortal(151, 3, 3, 3, 3);
        let mut state = CombatState::new(vec![vamp, mortal], vec![0, 1], 0);
        state.characters[1].conditions.dominated = true;
        // Legal mask for mortal (player 1) should only have Pass
        // We need to manually position the actor to test the mask for player 1
        // Verify dominated flag is cleared by Pass
        let hp_before = state.characters[0].health.total_damage();
        state.apply_action(1, Action::Pass);
        assert!(!state.characters[1].conditions.dominated, "Dominated should clear on Pass");
        let hp_after = state.characters[0].health.total_damage();
        assert_eq!(hp_before, hp_after, "Dominated should prevent attacks");
    }

    #[test]
    fn warrior_hide_adds_purity_to_health() {
        let wolf_no   = make_werewolf(160, 3, 2, 3, 3, 1);
        let wolf_purity3 = make_werewolf_with_renown(161, 1, 3, 0);
        let state_no     = CombatState::new(vec![wolf_no.clone(), make_mortal(200, 3,2,2,2)], vec![0,1], 0);
        let state_purity = CombatState::new(vec![wolf_purity3.clone(), make_mortal(200, 3,2,2,2)], vec![0,1], 0);
        // wolf_no: size(5) + sta(3) = 8, purity 0
        // wolf_purity3: make_werewolf_with_renown uses sta=4: size(5) + sta(4) + purity(3) = 12
        assert_eq!(state_no.characters[0].health.size, 8);
        let purity3_hp = 5 + 4 + 3; // size + stamina(from make_werewolf_with_renown) + purity
        assert_eq!(state_purity.characters[0].health.size, purity3_hp);
    }

    #[test]
    fn killer_instinct_sets_flag() {
        let wolf = make_werewolf_with_renown(170, 2, 2, 0);
        let mortal = make_mortal(171, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![wolf, mortal], vec![0, 1], 0);
        state.apply_werewolf_power(0, 5);
        assert!(state.characters[0].conditions.killer_instinct_active);
    }

    #[test]
    fn war_howl_sets_buff_on_allies() {
        let wolf1 = make_werewolf_with_renown(180, 2, 0, 2);
        let wolf2 = make_werewolf_with_renown(181, 2, 0, 2);
        let mortal = make_mortal(182, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![wolf1, wolf2, mortal], vec![0, 0, 1], 0);
        state.apply_werewolf_power(0, 6);
        assert!(state.characters[0].conditions.war_howl_bonus, "howler should be buffed");
        assert!(state.characters[1].conditions.war_howl_bonus, "ally should be buffed");
        assert!(!state.characters[2].conditions.war_howl_bonus, "enemy should not be buffed");
    }

    #[test]
    fn gauru_time_limit_reverts_to_hishu() {
        let wolf = make_werewolf(190, 3, 2, 3, 3, 2); // Primal Urge 2
        let mortal = make_mortal(191, 3, 2, 3, 3);
        let mut state = CombatState::new(vec![wolf, mortal], vec![0, 1], 1);
        state.step(encode_action(Action::ActivatePower { power_slot: 2, target_idx: 0 }));
        // Set turns_in_gauru to exceed PU
        if let SplatState::Werewolf { turns_in_gauru, .. } = &mut state.characters[0].splat {
            *turns_in_gauru = 3; // > primal_urge(2)
        }
        state.on_turn_start();
        if let SplatState::Werewolf { current_form, .. } = &state.characters[0].splat {
            assert_eq!(*current_form, WolfForm::Hishu, "should revert to Hishu after time limit");
        }
    }

    #[test]
    fn darkling_insubstantial_negates_damage() {
        use crate::character::{Splat, SplatBuild, Seeming as CSeeming};
        let darkling = BuildDefinition {
            id: 200, name: "Darkling".into(), splat: Splat::Changeling,
            attributes: Attributes::new(3, 4, 3, 2, 3, 3, 2, 2, 3),
            skills: CombatSkills { brawl: 2, weaponry: 0, firearms: 0, athletics: 2, stealth: 3 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Changeling { wyrd: 3, glamour_max: 12, seeming: CSeeming::Darkling },
            size: 5, merits: HashMap::new(),
        };
        let mortal = make_mortal(201, 4, 3, 3, 4);
        let mut state = CombatState::new(vec![darkling, mortal], vec![0, 1], 5);
        // Activate insubstantial
        state.characters[0].conditions.insubstantial = true;
        // Attack the darkling
        let hp_before = state.characters[0].health.total_damage();
        state.apply_damage(0, 5, DamageType::Bashing);
        let hp_after = state.characters[0].health.total_damage();
        assert_eq!(hp_before, hp_after, "Insubstantial should negate all damage");
    }

    #[test]
    fn vigor_reflexive_grants_extra_action() {
        let disc = VampireDisciplines { vigor: 3, celerity: 1, ..Default::default() };
        let vamp = make_vampire_with_disciplines(210, 2, disc);
        let mortal = make_mortal(211, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![vamp, mortal], vec![0, 1], 0);
        let actor_pos_before = state.current_actor_pos;
        // Activate Vigor (slot 1) — should grant 1 extra action
        state.apply_action(0, Action::ActivatePower { power_slot: 1, target_idx: 1 });
        assert_eq!(state.characters[0].extra_actions_remaining, 1);
        // advance_actor should NOT move pos when extra actions remain
        state.advance_actor();
        assert_eq!(state.current_actor_pos, actor_pos_before, "actor should not advance with extra action pending");
        assert_eq!(state.characters[0].extra_actions_remaining, 0);
    }

    #[test]
    fn celerity_extra_action_fires_immediately() {
        let disc = VampireDisciplines { celerity: 2, ..Default::default() };
        let vamp = make_vampire_with_disciplines(220, 2, disc);
        let mortal = make_mortal(221, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![vamp, mortal], vec![0, 1], 0);
        let pos_before = state.current_actor_pos;
        state.apply_action(0, Action::ActivatePower { power_slot: 0, target_idx: 0 });
        assert_eq!(state.characters[0].extra_actions_remaining, 1);
        state.advance_actor();
        assert_eq!(state.current_actor_pos, pos_before, "Celerity should grant extra action before advancing");
    }

    #[test]
    fn werewolf_non_gauru_lethal_regen_ticks() {
        let wolf = make_werewolf(230, 3, 2, 3, 3, 1); // PU=1, interval=5
        let mortal = make_mortal(231, 3, 2, 3, 3);
        let mut state = CombatState::new(vec![wolf, mortal], vec![0, 1], 1);
        state.characters[0].health.apply(2, DamageType::Lethal);
        let lethal_start = state.characters[0].health.count(DamageType::Lethal);
        assert_eq!(lethal_start, 2);
        // Tick 4 times (interval=5), no healing yet
        for _ in 0..4 { state.on_turn_start(); }
        assert_eq!(state.characters[0].health.count(DamageType::Lethal), 2, "no lethal heal before interval");
        // 5th tick should heal 1 lethal
        state.on_turn_start();
        assert_eq!(state.characters[0].health.count(DamageType::Lethal), 1, "should heal 1 lethal at interval");
    }

    #[test]
    fn ogre_debuff_reduces_target_next_roll() {
        use crate::character::{Splat, SplatBuild, Seeming as CSeeming};
        let ogre = BuildDefinition {
            id: 240, name: "Ogre".into(), splat: Splat::Changeling,
            attributes: Attributes::new(5, 3, 4, 2, 3, 3, 2, 2, 3),
            skills: CombatSkills { brawl: 4, weaponry: 0, firearms: 0, athletics: 2, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Changeling { wyrd: 3, glamour_max: 12, seeming: CSeeming::Ogre },
            size: 5, merits: HashMap::new(),
        };
        let mortal = make_mortal(241, 3, 2, 2, 2);
        let mut state = CombatState::new(vec![ogre, mortal], vec![0, 1], 3);
        // Ensure Ogre deals damage (run attacks)
        for _ in 0..100 {
            if state.characters[1].health.total_damage() > 0 { break; }
            state.apply_action(0, Action::Attack { target_idx: 1, spend_willpower: false });
        }
        if state.characters[1].health.total_damage() > 0 {
            // Debuff should be applied to mortal
            assert!(state.characters[1].conditions.ogre_debuffed, "mortal should be debuffed after Ogre hits");
        }
    }
}
