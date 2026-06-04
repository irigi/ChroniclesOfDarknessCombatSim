use std::collections::HashMap;
use serde::{Deserialize, Serialize};

// ─── Damage type ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum DamageType {
    None = 0,
    Bashing = 1,
    Lethal = 2,
    Aggravated = 3,
}

// ─── Splat ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Splat {
    Mortal,
    Vampire,
    Werewolf,
    Changeling,
}

// ─── Build definition (immutable) ────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Attributes {
    pub strength: u8,
    pub dexterity: u8,
    pub stamina: u8,
    pub intelligence: u8,
    pub wits: u8,
    pub resolve: u8,
    pub presence: u8,
    pub manipulation: u8,
    pub composure: u8,
}

impl Attributes {
    pub fn new(
        strength: u8, dexterity: u8, stamina: u8,
        intelligence: u8, wits: u8, resolve: u8,
        presence: u8, manipulation: u8, composure: u8,
    ) -> Self {
        Self { strength, dexterity, stamina, intelligence, wits, resolve, presence, manipulation, composure }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CombatSkills {
    pub brawl: u8,
    pub weaponry: u8,
    pub firearms: u8,
    pub athletics: u8,
    pub stealth: u8,
}

impl Default for CombatSkills {
    fn default() -> Self {
        Self { brawl: 0, weaponry: 0, firearms: 0, athletics: 0, stealth: 0 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeaponProfile {
    pub damage_mod: i8,
    pub damage_type: DamageType,
    pub initiative_penalty: i8,
    pub is_ranged: bool,
    /// Silver — deals aggravated to werewolves, normal to others.
    #[serde(default)]
    pub is_silver: bool,
    /// Fire — deals lethal to vampires (ignores bashing downgrade), aggravated to mortals.
    #[serde(default)]
    pub is_fire: bool,
    /// Sunlight — deals aggravated to vampires.
    #[serde(default)]
    pub is_sunlight: bool,
}

impl WeaponProfile {
    pub fn unarmed() -> Self {
        Self { damage_mod: 0, damage_type: DamageType::Bashing, initiative_penalty: 0, is_ranged: false, is_silver: false, is_fire: false, is_sunlight: false }
    }

    pub fn silver_knife() -> Self {
        Self { damage_mod: 0, damage_type: DamageType::Lethal, initiative_penalty: 0, is_ranged: false, is_silver: true, is_fire: false, is_sunlight: false }
    }

    pub fn fire() -> Self {
        Self { damage_mod: 2, damage_type: DamageType::Lethal, initiative_penalty: 0, is_ranged: false, is_silver: false, is_fire: true, is_sunlight: false }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArmorProfile {
    pub general: u8,
    pub ballistic: u8,
}

impl ArmorProfile {
    pub fn none() -> Self {
        Self { general: 0, ballistic: 0 }
    }
}

/// Which vampire Disciplines a character has (dots, 0 = none)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct VampireDisciplines {
    pub celerity: u8,
    pub vigor: u8,
    pub resilience: u8,
    /// Protean: natural weapon form-shifting (Gangrel). Active: claws → unarmed deals Lethal + weapon bonus.
    #[serde(default)]
    pub protean: u8,
    /// Nightmare: fear aura. Passive (≥1): WP spending blocked vs attacker. Active (≥2): Frightened condition.
    #[serde(default)]
    pub nightmare: u8,
    /// Dominate: mental control. Active (≥1): Mesmerize — target must succeed roll or be Dominated next turn.
    #[serde(default)]
    pub dominate: u8,
}

/// Werewolf form (affects stat block)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WolfForm {
    Hishu,
    Dalu,
    Gauru,
    Urshul,
    Urhan,
}

impl Default for WolfForm {
    fn default() -> Self { WolfForm::Hishu }
}

/// Changeling seeming (each has a combat blessing)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Seeming {
    Beast,
    Darkling,
    Elemental,
    Fairest,
    Ogre,
    Wizened,
}

/// Splat-specific build data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SplatBuild {
    Mortal,
    Vampire {
        blood_potency: u8,
        vitae_max: u8,
        disciplines: VampireDisciplines,
    },
    Werewolf {
        primal_urge: u8,
        essence_max: u8,
        // Renown (0 = none; 1-5 is typical)
        #[serde(default)] purity: u8,
        #[serde(default)] glory: u8,
        #[serde(default)] cunning: u8,
        #[serde(default)] honor: u8,
        #[serde(default)] wisdom: u8,
    },
    Changeling {
        wyrd: u8,
        glamour_max: u8,
        seeming: Seeming,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildDefinition {
    pub id: u32,
    pub name: String,
    pub splat: Splat,
    pub attributes: Attributes,
    pub skills: CombatSkills,
    pub weapon: WeaponProfile,
    pub armor: ArmorProfile,
    pub splat_data: SplatBuild,
    /// Base size (usually 5 for adult humans)
    pub size: u8,
    /// Named combat merits and their dot ratings.
    #[serde(default)]
    pub merits: HashMap<String, u8>,
}

impl BuildDefinition {
    /// Dot rating of a named merit (0 if absent).
    pub fn merit(&self, name: &str) -> u8 {
        self.merits.get(name).copied().unwrap_or(0)
    }

    /// Max health points for this build in its default form.
    pub fn max_health(&self) -> u8 {
        let stamina_bonus = match &self.splat_data {
            SplatBuild::Vampire { disciplines, .. } => disciplines.resilience,
            _ => 0,
        };
        self.size + self.attributes.stamina + stamina_bonus
    }

    /// Max willpower
    pub fn max_willpower(&self) -> u8 {
        self.attributes.resolve + self.attributes.composure
    }

    /// Initiative modifier (before weapon and Fast Reflexes merit)
    pub fn initiative_mod(&self) -> i8 {
        (self.attributes.dexterity + self.attributes.composure) as i8
    }

    /// Defense value (before Celerity, without merit adjustments).
    pub fn base_defense(&self) -> u8 {
        let def_attr = if self.merit("street_fighting") > 0 {
            // Street Fighting: use max(Dex, Wits) instead of min
            self.attributes.dexterity.max(self.attributes.wits)
        } else {
            self.attributes.dexterity.min(self.attributes.wits)
        };
        let def_skill = if self.merit("defensive_combat") > 0 {
            // Defensive Combat: use the better of Brawl or Weaponry instead of Athletics
            self.skills.brawl.max(self.skills.weaponry)
        } else if self.merit("brawling_dodge") > 0 {
            // Brawling Dodge: use Brawl for defense
            self.skills.brawl
        } else {
            self.skills.athletics
        };
        def_attr + def_skill
    }

    /// Max supernatural resource (Vitae / Essence / Glamour)
    pub fn max_resource(&self) -> u8 {
        match &self.splat_data {
            SplatBuild::Mortal => 0,
            SplatBuild::Vampire { vitae_max, .. } => *vitae_max,
            SplatBuild::Werewolf { essence_max, .. } => *essence_max,
            SplatBuild::Changeling { glamour_max, .. } => *glamour_max,
        }
    }
}

// ─── Mutable combat state ─────────────────────────────────────────────────────

pub const MAX_HEALTH_BOXES: usize = 14;

#[derive(Debug, Clone)]
pub struct HealthTrack {
    pub boxes: [DamageType; MAX_HEALTH_BOXES],
    pub size: usize,
}

impl HealthTrack {
    pub fn new(size: usize) -> Self {
        debug_assert!(size <= MAX_HEALTH_BOXES);
        Self {
            boxes: [DamageType::None; MAX_HEALTH_BOXES],
            size,
        }
    }

    /// Count filled boxes of a given type
    pub fn count(&self, dtype: DamageType) -> u8 {
        self.boxes[..self.size].iter().filter(|&&d| d == dtype).count() as u8
    }

    /// Total damage (any type)
    pub fn total_damage(&self) -> u8 {
        self.boxes[..self.size].iter().filter(|&&d| d != DamageType::None).count() as u8
    }

    /// Empty boxes remaining
    pub fn empty_boxes(&self) -> u8 {
        self.boxes[..self.size].iter().filter(|&&d| d == DamageType::None).count() as u8
    }

    /// Is last box filled with ≥ dtype?
    pub fn last_box_is(&self, dtype: DamageType) -> bool {
        self.size > 0 && self.boxes[self.size - 1] >= dtype
    }

    /// Apply damage, returning how many points were actually applied
    pub fn apply(&mut self, amount: u8, dtype: DamageType) -> u8 {
        let mut applied = 0u8;
        for _ in 0..amount {
            if !self.apply_one(dtype) {
                break;
            }
            applied += 1;
        }
        applied
    }

    /// Apply one point of damage; returns false if all boxes are aggravated (dead)
    fn apply_one(&mut self, dtype: DamageType) -> bool {
        let insert_pos = self.boxes[..self.size]
            .iter()
            .position(|&d| d < dtype)
            .unwrap_or(self.size);

        if insert_pos >= self.size {
            if self.boxes[..self.size].iter().all(|&d| d == DamageType::Aggravated) {
                return false;
            }
            if let Some(pos) = self.boxes[..self.size].iter().position(|&d| d < DamageType::Aggravated) {
                self.boxes[pos] = match self.boxes[pos] {
                    DamageType::None => DamageType::Bashing,
                    DamageType::Bashing => DamageType::Lethal,
                    DamageType::Lethal | DamageType::Aggravated => DamageType::Aggravated,
                };
                self.sort_boxes();
            }
            return true;
        }

        for i in (insert_pos..self.size - 1).rev() {
            self.boxes[i + 1] = self.boxes[i];
        }
        self.boxes[insert_pos] = dtype;
        self.sort_boxes();
        true
    }

    /// Heal one point of the rightmost (least severe) damage of given type
    pub fn heal_one(&mut self, dtype: DamageType) -> bool {
        for i in (0..self.size).rev() {
            if self.boxes[i] == dtype {
                self.boxes[i] = DamageType::None;
                self.sort_boxes();
                return true;
            }
        }
        false
    }

    /// CoD ordering: aggravated leftmost, then lethal, then bashing, then None
    fn sort_boxes(&mut self) {
        self.boxes[..self.size].sort_by(|a, b| b.cmp(a));
    }

    /// Wound penalty: 0 / -1 / -2 / -3 based on how many boxes from right are filled
    pub fn wound_penalty(&self) -> i8 {
        let total = self.total_damage() as usize;
        if total == 0 { return 0; }
        let third_to_last = self.size.saturating_sub(3);
        let second_to_last = self.size.saturating_sub(2);
        let last = self.size.saturating_sub(1);
        if total > last { -3 }
        else if total > second_to_last { -2 }
        else if total > third_to_last { -1 }
        else { 0 }
    }
}

// ─── Per-combat condition flags ───────────────────────────────────────────────

/// Transient conditions on a character during a single combat turn.
/// All flags are reset in `on_turn_start`. One-shot conditions (frightened, dominated)
/// are also cleared when consumed in `apply_action`.
#[derive(Debug, Clone, Default)]
pub struct ConditionFlags {
    /// Nightmare: must spend 1 WP to take any non-Pass action; cleared on use or Pass.
    pub frightened: bool,
    /// Dominate: next action is forced Pass; cleared when Pass executes.
    pub dominated: bool,
    /// Protean claws are active (unarmed attacks gain weapon bonus + deal Lethal).
    pub protean_claws_active: bool,
    /// Werewolf Gift: 8-again on Brawl/Weaponry rolls this turn.
    pub killer_instinct_active: bool,
    /// Werewolf Gift: +1L on attacks this turn (received from War Howl).
    pub war_howl_bonus: bool,
    /// Darkling Changeling: no physical damage received this turn.
    pub insubstantial: bool,
    /// Ogre Changeling debuff: -1 dice on the target's next action (one-shot).
    pub ogre_debuffed: bool,
}

/// Splat-specific mutable state during combat
#[derive(Debug, Clone)]
pub enum SplatState {
    Mortal,
    Vampire {
        vitae: u8,
        vitae_spent_this_turn: u8,
        blood_potency: u8,
    },
    Werewolf {
        essence: u8,
        current_form: WolfForm,
        turns_in_gauru: u8,
        primal_urge: u8,
    },
    Changeling {
        glamour: u8,
        clarity: u8,
        seeming: Seeming,
    },
}

/// Full mutable state of one combatant during a fight
#[derive(Debug, Clone)]
pub struct CharacterState {
    pub build_id: u32,
    pub team: u8,

    pub health: HealthTrack,
    pub willpower: u8,
    pub splat: SplatState,

    pub initiative: i16,
    pub defense_remaining: u8,
    pub defense_base: u8,

    pub is_incapacitated: bool,
    pub in_torpor: bool,

    /// Active conditions that change combat rules for this character.
    pub conditions: ConditionFlags,
    /// Pending extra actions granted by Vigor/Celerity active (Phase 7E).
    pub extra_actions_remaining: u8,
}

impl CharacterState {
    pub fn from_build(build: &BuildDefinition, team: u8, initiative: i16) -> Self {
        // ── Determine base health ──────────────────────────────────────────────
        let mut max_hp = build.max_health() as usize;

        // ── Seeming passive bonuses ────────────────────────────────────────────
        let seeming_composure_bonus: u8;
        let seeming_wits_bonus: u8;
        match build.splat_data {
            SplatBuild::Changeling { seeming, .. } => {
                match seeming {
                    Seeming::Elemental => {
                        // +1 Stamina → +1 health
                        seeming_composure_bonus = 0;
                        seeming_wits_bonus = 0;
                        max_hp += 1;
                    }
                    Seeming::Fairest => {
                        // +1 Composure → +1 Willpower, +1 Initiative mod
                        seeming_composure_bonus = 1;
                        seeming_wits_bonus = 0;
                    }
                    Seeming::Wizened => {
                        // +1 Wits → better Defense (min(Dex,Wits) improves)
                        seeming_composure_bonus = 0;
                        seeming_wits_bonus = 1;
                    }
                    _ => {
                        seeming_composure_bonus = 0;
                        seeming_wits_bonus = 0;
                    }
                }
            }
            _ => {
                seeming_composure_bonus = 0;
                seeming_wits_bonus = 0;
            }
        }

        // ── Werewolf Warrior's Hide: Purity adds to health ────────────────────
        if let SplatBuild::Werewolf { purity, .. } = &build.splat_data {
            if *purity >= 2 {
                max_hp += *purity as usize;
            }
        }

        let health = HealthTrack::new(max_hp.min(MAX_HEALTH_BOXES));

        // ── Defense ───────────────────────────────────────────────────────────
        let celerity = match &build.splat_data {
            SplatBuild::Vampire { disciplines, .. } => disciplines.celerity,
            _ => 0,
        };
        // Apply Wizened seeming Wits bonus to defense calculation
        let base_def = if seeming_wits_bonus > 0 {
            // Recalculate with boosted Wits
            let boosted_wits = build.attributes.wits + seeming_wits_bonus;
            let def_attr = if build.merit("street_fighting") > 0 {
                build.attributes.dexterity.max(boosted_wits)
            } else {
                build.attributes.dexterity.min(boosted_wits)
            };
            let def_skill = if build.merit("defensive_combat") > 0 {
                build.skills.brawl.max(build.skills.weaponry)
            } else if build.merit("brawling_dodge") > 0 {
                build.skills.brawl
            } else {
                build.skills.athletics
            };
            def_attr + def_skill
        } else {
            build.base_defense()
        };
        let defense_base = base_def + celerity;

        // ── Initiative ────────────────────────────────────────────────────────
        // Apply Fast Reflexes merit (+1 per dot) and seeming bonuses
        let fast_reflexes = build.merit("fast_reflexes") as i16;
        let fairest_init_bonus = seeming_composure_bonus as i16; // Fairest +1 Composure → +1 init mod
        let beast_bonus: i16 = if let SplatBuild::Changeling { seeming: Seeming::Beast, .. } = &build.splat_data { 3 } else { 0 };
        // Firefight: Shoot First (•) — +Firearms to Initiative when ranged weapon drawn
        let firefight_bonus: i16 = if build.merit("firefight") >= 1 && build.weapon.is_ranged {
            build.skills.firearms as i16
        } else {
            0
        };
        let final_initiative = initiative + fast_reflexes + fairest_init_bonus + beast_bonus + firefight_bonus;

        // ── Willpower ─────────────────────────────────────────────────────────
        let max_wp = build.max_willpower() + seeming_composure_bonus;

        // ── SplatState ────────────────────────────────────────────────────────
        let splat = match &build.splat_data {
            SplatBuild::Mortal => SplatState::Mortal,
            SplatBuild::Vampire { vitae_max, blood_potency, .. } => SplatState::Vampire {
                vitae: *vitae_max,
                vitae_spent_this_turn: 0,
                blood_potency: *blood_potency,
            },
            SplatBuild::Werewolf { essence_max, primal_urge, .. } => SplatState::Werewolf {
                essence: *essence_max,
                current_form: WolfForm::Hishu,
                turns_in_gauru: 0,
                primal_urge: *primal_urge,
            },
            SplatBuild::Changeling { glamour_max, seeming, .. } => SplatState::Changeling {
                glamour: *glamour_max,
                clarity: 7,
                seeming: *seeming,
            },
        };

        // ── Iron Skin: passive armor vs bashing ───────────────────────────────
        // We do not modify build.armor here; it's applied at damage time in combat.rs.
        // (Iron Skin passive is checked by build.merit("iron_skin") in resolve_attack.)

        Self {
            build_id: build.id,
            team,
            health,
            willpower: max_wp,
            splat,
            initiative: final_initiative,
            defense_remaining: defense_base,
            defense_base,
            is_incapacitated: false,
            in_torpor: false,
            conditions: ConditionFlags::default(),
            extra_actions_remaining: 0,
        }
    }

    pub fn resource(&self) -> u8 {
        match &self.splat {
            SplatState::Mortal => 0,
            SplatState::Vampire { vitae, .. } => *vitae,
            SplatState::Werewolf { essence, .. } => *essence,
            SplatState::Changeling { glamour, .. } => *glamour,
        }
    }

    /// Spend supernatural resource, respecting per-turn Vitae limits for vampires.
    pub fn spend_resource(&mut self, amount: u8) -> bool {
        match &mut self.splat {
            SplatState::Mortal => false,
            SplatState::Vampire { vitae, vitae_spent_this_turn, blood_potency } => {
                let per_turn_limit = crate::splats::vampire::vitae_per_turn(*blood_potency);
                if *vitae >= amount && (*vitae_spent_this_turn + amount) <= per_turn_limit {
                    *vitae -= amount;
                    *vitae_spent_this_turn += amount;
                    true
                } else { false }
            }
            SplatState::Werewolf { essence, .. } => {
                if *essence >= amount { *essence -= amount; true } else { false }
            }
            SplatState::Changeling { glamour, .. } => {
                if *glamour >= amount { *glamour -= amount; true } else { false }
            }
        }
    }

    /// Reset per-turn counters (called at start of each new turn).
    pub fn reset_turn_counters(&mut self) {
        if let SplatState::Vampire { vitae_spent_this_turn, .. } = &mut self.splat {
            *vitae_spent_this_turn = 0;
        }
        // Clear all per-turn conditions
        self.conditions.killer_instinct_active = false;
        self.conditions.war_howl_bonus = false;
        self.conditions.insubstantial = false;
        // Note: frightened, dominated, protean_claws_active, ogre_debuffed
        // persist until consumed (not just turn boundary).
        self.extra_actions_remaining = 0;
    }

    /// Effective wound penalty after Iron Stamina merit reduction.
    pub fn effective_wound_penalty(&self, build: &BuildDefinition) -> i8 {
        let raw = self.health.wound_penalty();
        let reduction = build.merit("iron_stamina") as i8;
        // raw is ≤ 0; adding reduction (positive) raises it toward 0
        (raw + reduction).min(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_track_applies_damage_in_order() {
        let mut track = HealthTrack::new(7);
        track.apply(3, DamageType::Bashing);
        assert_eq!(track.count(DamageType::Bashing), 3);
        track.apply(2, DamageType::Lethal);
        assert_eq!(track.count(DamageType::Lethal), 2);
        assert_eq!(track.count(DamageType::Bashing), 3);
    }

    #[test]
    fn full_bashing_upgrades_to_lethal() {
        let mut track = HealthTrack::new(3);
        track.apply(3, DamageType::Bashing);
        track.apply(1, DamageType::Bashing);
        assert_eq!(track.count(DamageType::Lethal), 1);
    }

    #[test]
    fn wound_penalty_escalates() {
        let mut track = HealthTrack::new(7);
        assert_eq!(track.wound_penalty(), 0);
        track.apply(5, DamageType::Bashing);
        assert_eq!(track.wound_penalty(), -1);
        track.apply(1, DamageType::Bashing);
        assert_eq!(track.wound_penalty(), -2);
        track.apply(1, DamageType::Bashing);
        assert_eq!(track.wound_penalty(), -3);
    }

    #[test]
    fn healing_removes_rightmost() {
        let mut track = HealthTrack::new(7);
        track.apply(3, DamageType::Bashing);
        assert!(track.heal_one(DamageType::Bashing));
        assert_eq!(track.count(DamageType::Bashing), 2);
    }

    fn make_mortal_build(str: u8, dex: u8, sta: u8, wits: u8, composure: u8, brawl: u8, athletics: u8) -> BuildDefinition {
        BuildDefinition {
            id: 0, name: "test".into(), splat: Splat::Mortal,
            attributes: Attributes::new(str, dex, sta, 2, wits, 3, 2, 2, composure),
            skills: CombatSkills { brawl, weaponry: 0, firearms: 0, athletics, stealth: 0 },
            weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
            splat_data: SplatBuild::Mortal, size: 5,
            merits: HashMap::new(),
        }
    }

    #[test]
    fn merit_fast_reflexes_initiative() {
        let mut b = make_mortal_build(3, 3, 2, 2, 3, 2, 2);
        b.merits.insert("fast_reflexes".into(), 2);
        let state = CharacterState::from_build(&b, 0, 5);
        // initiative = 5 (rolled) + 2 (fast reflexes)
        assert_eq!(state.initiative, 7);
    }

    #[test]
    fn merit_defensive_combat_defense() {
        // Without merit: defense = min(Dex3,Wits2) + Athletics1 = 2 + 1 = 3
        let b_no = make_mortal_build(3, 3, 2, 2, 3, 4, 1);
        let s_no = CharacterState::from_build(&b_no, 0, 0);
        assert_eq!(s_no.defense_base, 3);
        // With merit: defense = min(Dex3,Wits2) + Brawl4 = 2 + 4 = 6
        let mut b_yes = b_no.clone();
        b_yes.merits.insert("defensive_combat".into(), 1);
        let s_yes = CharacterState::from_build(&b_yes, 0, 0);
        assert_eq!(s_yes.defense_base, 6);
    }

    #[test]
    fn merit_iron_stamina_reduces_penalty() {
        let mut b = make_mortal_build(3, 3, 2, 2, 3, 2, 2);
        b.merits.insert("iron_stamina".into(), 2);
        let mut state = CharacterState::from_build(&b, 0, 0);
        // Fill 7-box track to get -3 penalty
        state.health.apply(7, DamageType::Bashing);
        assert_eq!(state.health.wound_penalty(), -3);
        // With Iron Stamina 2: effective penalty = -3 + 2 = -1
        assert_eq!(state.effective_wound_penalty(&b), -1);
    }

    #[test]
    fn merit_iron_skin_passive_armor_field() {
        // Iron Skin passive is checked at damage time, not in from_build.
        // Just verify the merit() accessor works.
        let mut b = make_mortal_build(3, 3, 2, 2, 3, 2, 2);
        b.merits.insert("iron_skin".into(), 4);
        assert_eq!(b.merit("iron_skin"), 4);
        assert_eq!(b.merit("nonexistent"), 0);
    }

    #[test]
    fn street_fighting_uses_max_dex_wits_for_defense() {
        // Without merit: defense = min(Dex4,Wits2) + Athletics2 = 2 + 2 = 4
        let b_no = make_mortal_build(3, 4, 2, 2, 3, 2, 2);
        let s_no = CharacterState::from_build(&b_no, 0, 0);
        assert_eq!(s_no.defense_base, 4);
        // With street_fighting: defense = max(Dex4,Wits2) + Athletics2 = 4 + 2 = 6
        let mut b_yes = b_no.clone();
        b_yes.merits.insert("street_fighting".into(), 1);
        let s_yes = CharacterState::from_build(&b_yes, 0, 0);
        assert_eq!(s_yes.defense_base, 6);
    }
}
