use serde::{Deserialize, Serialize};

/// All actions a character can take on their turn.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Action {
    /// Attack a target using the character's weapon/brawl
    Attack {
        target_idx: u8,
        spend_willpower: bool,
    },
    /// Activate a supernatural power (Discipline / Gift / Contract / Seeming)
    ActivatePower {
        /// Power slot index (splat-specific assignment):
        /// Vampire: 0=Celerity, 1=Vigor, 2=Resilience, 3=Protean, 4=Nightmare, 5=Dominate
        /// Werewolf: 0-4=forms (Hishu/Dalu/Gauru/Urshul/Urhan), 5=Killer Instinct, 6=War Howl
        /// Changeling: 0=Seeming power, 1=Combat Contract
        power_slot: u8,
        target_idx: u8,
    },
    /// Spend Vitae/Essence for physical intensity (+2 dice to Str/Dex/Sta)
    SpendResourcePhysical {
        /// 0=Strength bonus, 1=Dexterity bonus, 2=Stamina bonus
        attribute: u8,
    },
    /// Heal using Vitae (vampire only: 1 Vitae = 2B or 1L)
    HealWithVitae,
    /// Spend Essence to regenerate lethal damage this turn (werewolf)
    RegenerateEssence,
    /// Use Full Defense: double defense, use action
    FullDefense,
    /// Pass / do nothing
    Pass,
    /// Iron Skin active: spend 1 WP to downgrade 1 (or 2 at ••••) lethal → bashing
    IronSkinDowngrade,
}

pub const MAX_TARGETS: usize = 8;
pub const MAX_POWER_SLOTS: usize = 8;

/// Encodes the action space as a fixed-size discrete integer.
///
/// Layout:
///   [0..MAX_TARGETS*2)                  Attack × target × willpower
///   [A..A + MAX_POWER_SLOTS*MAX_TARGETS) ActivatePower × slot × target
///   [B..B+3)                            SpendResourcePhysical × attribute
///   [B+3]                               HealWithVitae
///   [B+4]                               RegenerateEssence
///   [B+5]                               FullDefense
///   [B+6]                               Pass
///   [B+7]                               IronSkinDowngrade  (new)
///
/// Total = MAX_TARGETS*2 + MAX_POWER_SLOTS*MAX_TARGETS + 8
pub const ACTION_SPACE_SIZE: usize =
    MAX_TARGETS * 2 + MAX_POWER_SLOTS * MAX_TARGETS + 8;

const POWER_OFFSET: usize = MAX_TARGETS * 2;
const RESOURCE_PHYSICAL_OFFSET: usize = POWER_OFFSET + MAX_POWER_SLOTS * MAX_TARGETS;
const HEAL_OFFSET: usize = RESOURCE_PHYSICAL_OFFSET + 3;
const REGEN_ESSENCE_OFFSET: usize = HEAL_OFFSET + 1;
const FULL_DEFENSE_OFFSET: usize = REGEN_ESSENCE_OFFSET + 1;
const PASS_OFFSET: usize = FULL_DEFENSE_OFFSET + 1;
pub const IRON_SKIN_OFFSET: usize = PASS_OFFSET + 1;

pub fn encode_action(action: Action) -> usize {
    match action {
        Action::Attack { target_idx, spend_willpower } => {
            let t = target_idx as usize;
            let w = spend_willpower as usize;
            t * 2 + w
        }
        Action::ActivatePower { power_slot, target_idx } => {
            POWER_OFFSET + power_slot as usize * MAX_TARGETS + target_idx as usize
        }
        Action::SpendResourcePhysical { attribute } => {
            RESOURCE_PHYSICAL_OFFSET + attribute as usize
        }
        Action::HealWithVitae => HEAL_OFFSET,
        Action::RegenerateEssence => REGEN_ESSENCE_OFFSET,
        Action::FullDefense => FULL_DEFENSE_OFFSET,
        Action::Pass => PASS_OFFSET,
        Action::IronSkinDowngrade => IRON_SKIN_OFFSET,
    }
}

pub fn decode_action(idx: usize) -> Option<Action> {
    if idx < POWER_OFFSET {
        let target_idx = (idx / 2) as u8;
        let spend_willpower = idx % 2 == 1;
        Some(Action::Attack { target_idx, spend_willpower })
    } else if idx < RESOURCE_PHYSICAL_OFFSET {
        let rel = idx - POWER_OFFSET;
        let power_slot = (rel / MAX_TARGETS) as u8;
        let target_idx = (rel % MAX_TARGETS) as u8;
        Some(Action::ActivatePower { power_slot, target_idx })
    } else if idx < HEAL_OFFSET {
        let attribute = (idx - RESOURCE_PHYSICAL_OFFSET) as u8;
        Some(Action::SpendResourcePhysical { attribute })
    } else if idx == HEAL_OFFSET {
        Some(Action::HealWithVitae)
    } else if idx == REGEN_ESSENCE_OFFSET {
        Some(Action::RegenerateEssence)
    } else if idx == FULL_DEFENSE_OFFSET {
        Some(Action::FullDefense)
    } else if idx == PASS_OFFSET {
        Some(Action::Pass)
    } else if idx == IRON_SKIN_OFFSET {
        Some(Action::IronSkinDowngrade)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_decode_roundtrip() {
        let actions = [
            Action::Attack { target_idx: 0, spend_willpower: false },
            Action::Attack { target_idx: 3, spend_willpower: true },
            Action::ActivatePower { power_slot: 2, target_idx: 1 },
            Action::SpendResourcePhysical { attribute: 0 },
            Action::HealWithVitae,
            Action::RegenerateEssence,
            Action::FullDefense,
            Action::Pass,
            Action::IronSkinDowngrade,
        ];
        for action in &actions {
            let idx = encode_action(*action);
            assert!(idx < ACTION_SPACE_SIZE, "idx {} out of bounds for {:?}", idx, action);
            let decoded = decode_action(idx).expect("should decode");
            assert_eq!(*action, decoded, "roundtrip failed for {:?}", action);
        }
    }

    #[test]
    fn action_space_size_is_correct() {
        assert_eq!(IRON_SKIN_OFFSET + 1, ACTION_SPACE_SIZE);
    }

    #[test]
    fn encode_decode_iron_skin_downgrade() {
        let idx = encode_action(Action::IronSkinDowngrade);
        assert_eq!(idx, IRON_SKIN_OFFSET);
        assert_eq!(decode_action(idx), Some(Action::IronSkinDowngrade));
    }
}
