use rand::Rng;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgainRule {
    TenAgain,
    NineAgain,
    EightAgain,
    NoAgain,
}

impl AgainRule {
    pub fn threshold(self) -> u8 {
        match self {
            AgainRule::TenAgain => 10,
            AgainRule::NineAgain => 9,
            AgainRule::EightAgain => 8,
            AgainRule::NoAgain => 255,
        }
    }
}

#[derive(Debug, Clone)]
pub struct RollResult {
    /// Negative = dramatic failure (only possible on chance die with a 1)
    pub successes: i8,
    pub tens: u8,
}

/// Roll a standard dice pool. Returns 0 if pool <= 0 (chance die rules apply separately).
pub fn roll_pool(pool: i8, again: AgainRule, rng: &mut impl Rng) -> RollResult {
    if pool <= 0 {
        return roll_chance_die(rng);
    }

    let threshold = again.threshold();
    let mut successes: i8 = 0;
    let mut tens: u8 = 0;
    let mut dice_to_roll: u32 = pool as u32;
    let mut reroll_cap = 0u32;

    while dice_to_roll > 0 {
        dice_to_roll -= 1;
        let face: u8 = rng.gen_range(1..=10);
        if face >= 8 {
            successes += 1;
        }
        if face == 10 {
            tens += 1;
        }
        // 10-Again / 9-Again / 8-Again: reroll dice that meet the threshold
        if face >= threshold && threshold < 255 {
            reroll_cap += 1;
            // Safety cap: prevent infinite loops in edge cases
            if reroll_cap <= 50 {
                dice_to_roll += 1;
            }
        }
    }

    RollResult { successes, tens }
}

/// Chance die: only a 10 succeeds; a 1 is a dramatic failure.
pub fn roll_chance_die(rng: &mut impl Rng) -> RollResult {
    let face: u8 = rng.gen_range(1..=10);
    let successes = if face == 10 {
        1
    } else if face == 1 {
        -1
    } else {
        0
    };
    RollResult {
        successes,
        tens: if face == 10 { 1 } else { 0 },
    }
}

/// Rote quality: re-roll all non-successes once.
pub fn roll_rote(pool: i8, again: AgainRule, rng: &mut impl Rng) -> RollResult {
    if pool <= 0 {
        return roll_chance_die(rng);
    }
    let mut successes: i8 = 0;
    let mut tens: u8 = 0;
    let threshold = again.threshold();
    let mut reroll_cap = 0u32;

    // First pass: each die, re-roll if it didn't succeed
    for _ in 0..pool {
        let face: u8 = rng.gen_range(1..=10);
        if face >= 8 {
            successes += 1;
            if face == 10 {
                tens += 1;
            }
        } else {
            // Re-roll the failure once
            let face2: u8 = rng.gen_range(1..=10);
            if face2 >= 8 {
                successes += 1;
                if face2 == 10 {
                    tens += 1;
                }
            }
            // Apply again-rule to re-roll result
            if face2 >= threshold && threshold < 255 {
                reroll_cap += 1;
                if reroll_cap <= 50 {
                    let extra = roll_pool(1, again, rng);
                    successes = successes.saturating_add(extra.successes);
                    tens = tens.saturating_add(extra.tens);
                }
            }
        }
    }
    RollResult { successes, tens }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand_xoshiro::Xoshiro256PlusPlus;

    fn seeded() -> Xoshiro256PlusPlus {
        Xoshiro256PlusPlus::seed_from_u64(42)
    }

    #[test]
    fn zero_pool_is_chance_die() {
        let mut rng = seeded();
        let result = roll_pool(0, AgainRule::TenAgain, &mut rng);
        // chance die: only 10 or 1 are interesting
        assert!(result.successes >= -1 && result.successes <= 1);
    }

    #[test]
    fn large_pool_always_positive_expectation() {
        let mut rng = seeded();
        let mut total = 0i32;
        for _ in 0..1000 {
            let r = roll_pool(10, AgainRule::TenAgain, &mut rng);
            total += r.successes as i32;
        }
        // 10 dice @ 30% success rate ≈ 3 successes/roll × 1000 = ~3000
        assert!(total > 2000, "expected ~3000, got {}", total);
    }

    #[test]
    fn no_again_fewer_successes_than_ten_again() {
        let mut rng = seeded();
        let mut rng2 = Xoshiro256PlusPlus::seed_from_u64(42);
        let mut total_ten = 0i64;
        let mut total_no = 0i64;
        for _ in 0..10000 {
            total_ten += roll_pool(5, AgainRule::TenAgain, &mut rng).successes as i64;
            total_no += roll_pool(5, AgainRule::NoAgain, &mut rng2).successes as i64;
        }
        assert!(total_ten > total_no, "10-again should beat no-again");
    }

    #[test]
    fn chance_die_can_dramatic_fail() {
        let mut rng = Xoshiro256PlusPlus::seed_from_u64(0);
        let mut found_df = false;
        for _ in 0..1000 {
            if roll_chance_die(&mut rng).successes == -1 {
                found_df = true;
                break;
            }
        }
        assert!(found_df, "should see at least one dramatic failure");
    }
}
