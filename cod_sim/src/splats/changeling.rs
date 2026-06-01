// Changeling the Lost 2e rule constants and helpers.

/// Glamour max by Wyrd level (approximate; can be overridden per build).
pub fn glamour_max(wyrd: u8) -> u8 {
    match wyrd {
        1 => 10,
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
