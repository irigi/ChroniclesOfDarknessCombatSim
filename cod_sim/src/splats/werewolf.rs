// Werewolf the Forsaken 2e rule constants and helpers.

/// Essence max per Primal Urge level.
pub fn essence_max(primal_urge: u8) -> u8 {
    match primal_urge {
        0 | 1 => 10,
        2 => 11,
        3 => 12,
        4 => 13,
        5 => 15,
        6 => 20,
        7 => 25,
        8 => 30,
        9 => 50,
        _ => 75,
    }
}

/// Bashing regeneration per turn by Primal Urge.
pub fn bashing_regen_per_turn(primal_urge: u8) -> u8 {
    match primal_urge {
        0..=3 => 1,
        4 | 5 => 2,
        6 | 7 => 3,
        8 => 4,
        9 => 5,
        _ => 6,
    }
}

/// How many turns between 1 point of lethal regeneration (non-Gauru forms).
/// Gauru regenerates lethal automatically each turn; this is for slower healing.
pub fn lethal_regen_interval(primal_urge: u8) -> u8 {
    match primal_urge {
        0..=2 => 5,
        3 | 4 => 3,
        5 | 6 => 2,
        _ => 1,
    }
}
