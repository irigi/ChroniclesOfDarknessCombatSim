# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chronicles of Darkness 2e combat simulator. Simulates M-vs-N fights across 4 supernatural splats (Vampire the Requiem, Werewolf the Forsaken, Changeling the Lost, Hunter the Vigil), trains a universal RL policy via self-play PPO, and rates builds/teams with Glicko-2.

## Build Commands

```bash
# One-time setup
bash scripts/bootstrap.sh

# Build Rust extension (development, run after any Rust change)
source ~/.cargo/env && .venv/bin/maturin develop --release

# Rust tests
source ~/.cargo/env && cargo test -p cod_sim

# Rust type-check (fast, no codegen)
source ~/.cargo/env && cargo check -p cod_sim

# Python tests
.venv/bin/pytest tests/python/ -v

# Web UI
.venv/bin/uvicorn cod_sim.api.main:app --reload --port 8000

# Training
.venv/bin/python scripts/train.py --steps 500000 --n-envs 64

# Rating tournament
.venv/bin/python scripts/rate_builds.py --n-matches 1000
```

## Architecture

### Language Split
- **Rust** (`cod_sim/` crate): simulation core, compiled as a Python extension via PyO3/maturin
- **Python** (`python/cod_sim/`): RL training, Glicko-2 rating, FastAPI web server

### Rust Crate Layout (`cod_sim/src/`)
- `lib.rs` — PyO3 module entrypoint, exports `CombatEnv` + helper functions
- `dice.rs` — d10 pool mechanics (10-Again, chance die, dramatic failure, rote)
- `character.rs` — `BuildDefinition` (immutable), `CharacterState` (mutable), `HealthTrack`, `SplatState`
- `action.rs` — `Action` enum + encode/decode to flat integer index
- `combat.rs` — `CombatState`: initiative, turn resolution, damage application, werewolf regeneration
- `env.rs` — `CombatEnv` (PyO3 `#[pyclass]`): `reset()`, `step()`, `action_mask()`, `get_state_summary()`
- `splats/` — splat-specific constants (currently `vampire.rs`, `werewolf.rs`)

### Key Abstractions
- **`BuildDefinition`**: immutable character sheet. `SplatBuild` enum holds splat-specific data (Vitae for vampires, Essence for werewolves, Glamour for changelings)
- **`HealthTrack`**: sorted array (aggravated leftmost), handles damage insertion and CoD overflow rules
- **`SplatState`**: mutable per-combat state (resource tracking, wolf form, torpor)
- **`TurnBonuses`** (private in combat.rs): per-turn modifiers that reset each turn (Vigor bonus, Resilience armor, etc.)

### Observation Space
Flat `f32` vector: `n_chars × 16 + 3`. Per character (16 floats): health ratios (B/L/A/empty), wound penalty, willpower/resource/defense ratios, incap flag, splat one-hot (4), strength. Global (3): turn ratio, ally/enemy alive counts. Always from POV of current actor (self at slot 0, allies, then enemies).

### Action Space
Discrete, fixed size `ACTION_SPACE_SIZE = 120`. Layout: Attack×8×2 [0..16), AllOutAttack×8×2 [16..32), ActivatePower×8×8 [32..96), SpendResourcePhysical×3 [96..99), HealWithVitae [99], RegenerateEssence [100], FullDefense [101], Pass [102], IronSkinDowngrade [103], Bite×8×2 [104..120).

### Vampire Rule Notes
- **All** mundane weapons (melee + firearms) deal **bashing** to vampires. Fire = lethal, sunlight = aggravated. (VtR 2e: "Kindred take bashing damage from all mundane weapons, including knives and guns.")
- **Bite** (fangs): Str+Brawl−Defense pool, deals **lethal** equal to successes (0L weapon), vampire gains 1 Vitae on hit. Standalone action (simplified frenzy-bite model; strict RAW requires grapple first).
- **Torpor** when last health box = lethal. **Final Death** when last = aggravated. Conscious with all bashing.
- Celerity active (1 Vitae): **reflexive** — grants extra action immediately, net 0 action slots spent.
- Vigor active (1 Vitae): **reflexive** — +Vigor dice bonus + extra action (net 0 action slots).
- Resilience active (1 Vitae): **reflexive** — (Resilience+1) armor for turn + extra action (net 0 slots).
- SpendResourcePhysical (1 Vitae): **reflexive** — +2 attack dice + extra action (net 0 action slots).

### Werewolf Rule Notes
- Regenerates 1 bashing per turn (Primal Urge 1). Gauru form: all bashing+lethal per turn.
- Silver deals **aggravated** damage directly.
- Form stat deltas (vs Hishu): Dalu +1/+1 Str/Sta +1 Size; Gauru +3/+1/+2 Str/Dex/Sta +2 Size; Urshul +2/+2/+2 Str/Dex/Sta +1 Size; Urhan +2 Dex +1 Sta −1 Size.

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Foundation: dice, mortal combat, PyO3 binding |
| 2 | ✅ Done | VecEnv (rayon parallel), build registry (YAML), gymnasium wrapper |
| 3 | ✅ Done | All 4 splat rules, silver/fire/sunlight vulnerabilities, wolf forms, 9 template builds |
| 4 | ✅ Done | PPO self-play RL: 92% win rate (decided games), 16K steps/sec on CPU |
| 5 | ✅ Done | Glicko-2 rating: individual builds + team compositions, round-robin tournament |
| 6 | ✅ Done | FastAPI web UI: leaderboard + combat simulator with SSE live streaming |
| 7 | ✅ Done | Merit system, discipline expansion, werewolf gifts, changeling seemings, rule accuracy |
| 8 | ✅ Done | Weapon audit, AllOutAttack, fighting style merits, 5 new builds, ACTION_SPACE_SIZE 88→104 |
| 9 | ✅ Done | Firearms→bashing to vampires (bug fix), vampire bite action, reflexive disciplines, combat_runner.py offset fix, entropy 0.01→0.05 |

## Rulebooks
Source material is in `rulebooks/`. Key files:
- `Chronicles of Darkness.txt` — core rules (combat, dice, health, merits)
- `Vampire the Requiem - SECOND EDITION.txt` — Disciplines, Vitae, Blood Potency
- `Werewolf_the_Forsaken_Second_Edition_(Download_Final).txt` — Forms, Gifts, Essence, Regeneration
- `Changeling_the_Lost_2e_(Final_Download).txt` — Contracts, Glamour, Wyrd, Clarity
- `Mage the Awakening - Second Edition.txt` — not in scope for combat sim

Note: No Hunter the Vigil rulebook provided; implement Hunters as enhanced mortals initially.
