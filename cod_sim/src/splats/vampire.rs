// Vampire the Requiem 2e rule constants and helpers.

/// Vitae max per Blood Potency level.
pub fn vitae_max(blood_potency: u8) -> u8 {
    match blood_potency {
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

/// Vitae per turn limit per Blood Potency.
pub fn vitae_per_turn(blood_potency: u8) -> u8 {
    blood_potency.max(1)
}
