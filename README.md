# Chronicles of Darkness 2e Combat Simulator

A physics-accurate combat simulator for **Chronicles of Darkness Second Edition**,
covering four supernatural splats: Vampire the Requiem, Werewolf the Forsaken,
Changeling the Lost, and Hunter the Vigil (as enhanced mortals).

Features:
- M-vs-N fights with arbitrary builds, weapons, and team compositions
- Full splat rules: CoD damage types, Vitae/Essence/Glamour, Disciplines, wolf forms
- **Reinforcement-learning policy** trained via self-play PPO (~16K sim steps/sec on CPU)
- **Glicko-2 ratings** for individual builds and team compositions
- **FastAPI web UI** with live combat streaming
- **Turn-by-turn combat log** for rule debugging (`scripts/replay.py`)

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | |
| Rust toolchain | stable | installed by `bootstrap.sh` if absent |
| pip packages | see below | installed by `bootstrap.sh` |

---

## Quick Start

```bash
# One-time setup: installs Rust, creates .venv, builds the Rust extension
bash scripts/bootstrap.sh

# Activate the virtualenv (or prefix all commands with .venv/bin/)
source .venv/bin/activate
```

After bootstrap, all commands below can be run without the `.venv/bin/` prefix if
the venv is activated.

---

## Building the Rust Extension

The simulation core is a Rust crate compiled as a Python extension via
[maturin](https://github.com/PyO3/maturin).  You must rebuild it after any
change to `cod_sim/src/`.

```bash
# Development build (used during local work)
source ~/.cargo/env && .venv/bin/maturin develop --release

# Type-check only (fast, no codegen)
source ~/.cargo/env && cargo check -p cod_sim
```

The compiled `.so` lands in `python/cod_sim/` and is imported as `cod_sim.cod_sim`.

---

## Running Tests

```bash
# Rust unit tests (dice, health track, combat mechanics, splat rules)
source ~/.cargo/env && cargo test -p cod_sim

# Python tests (env wrapper, build registry, Glicko, training, API)
.venv/bin/pytest tests/python/ -v
```

All 180 tests (42 Rust + 138 Python) should pass on a clean checkout.

---

## Usage Modes

### 1. Combat Replay (rule debugging)

Print a turn-by-turn combat log for a single fight.  This is the primary tool
for verifying that game mechanics work as expected.

```bash
# List available builds
.venv/bin/python scripts/replay.py --list

# Vampire Celerity Bruiser vs Werewolf Iron Master (random-legal-action policy)
.venv/bin/python scripts/replay.py --build-a 201 --build-b 301

# Same fight with the trained policy
.venv/bin/python scripts/replay.py --build-a 201 --build-b 301 --policy

# 2v1 team fight
.venv/bin/python scripts/replay.py --team0 201 202 --team1 301

# Change seed for different dice outcomes
.venv/bin/python scripts/replay.py --build-a 101 --build-b 201 --seed 7
```

**Log format** (excerpt):
```
════════════════════════════════════════════════════════════════════════
  COMBAT: Team 0 [Daeva Celerity Bruiser]  vs  Team 1 [Iron Master]
  Seed: 42   Policy: random-legal-action
════════════════════════════════════════════════════════════════════════

INITIATIVE ORDER:
  Iron Master                      ini=12  team=1
  Daeva Celerity Bruiser           ini=8   team=0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TURN 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Iron Master                     [○○○○○○○○] hp=8/8  res=10  wp=6
  Daeva Celerity Bruiser          [○○○○○○○○] hp=8/8  res=11  wp=5

  Step   1 | [Wolf] Iron Master (team 1)
             → Attacks Daeva Celerity Bruiser
             ✦ Daeva Celerity Bruiser: +2B
               [BB○○○○○○] (6/8)
```

> **Performance note**: `replay.py` runs entirely in Python; the Rust
> simulation core has no logging code.  Running `train.py` or `rate_builds.py`
> incurs zero overhead from this script.

---

### 2. Training

Train the PPO self-play policy.  A checkpoint is saved every 50 K steps.

```bash
# Quick sanity check (finishes in ~1 min)
.venv/bin/python scripts/train.py --steps 10000 --n-envs 16

# Full training run (recommended)
.venv/bin/python scripts/train.py --steps 500000 --n-envs 64

# Resume from the latest checkpoint
.venv/bin/python scripts/train.py --steps 1000000 --resume

# Tune learning rate / entropy bonus
.venv/bin/python scripts/train.py --steps 500000 --lr 1e-4 --entropy-coef 0.02
```

Key flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--steps` | 500 000 | Total environment steps |
| `--n-envs` | 64 | Parallel Rust environments (via Rayon) |
| `--rollout-len` | 128 | Steps per env per PPO rollout |
| `--resume` | false | Load latest checkpoint from `--checkpoint-dir` |
| `--lr` | 3e-4 | Initial learning rate (cosine decay to 1e-5) |
| `--entropy-coef` | 0.01 | Entropy bonus (encourages exploration) |
| `--checkpoint-dir` | `checkpoints/` | Where to save checkpoints |
| `--no-eval` | false | Skip post-training evaluation |

Training output logs KL divergence, policy/value/entropy losses, and win rate
vs random every 10 K steps.  A well-trained policy achieves ≥ 90% win rate vs
random in decided matches.

---

### 3. Rating Tournament

Run a Glicko-2 round-robin tournament to rate all builds.

```bash
# Quick run (3 round-robins)
.venv/bin/python scripts/rate_builds.py --rounds 3

# Full run with stable ratings (10 round-robins)
.venv/bin/python scripts/rate_builds.py --rounds 10

# Save leaderboard and show top 5
.venv/bin/python scripts/rate_builds.py --rounds 5 --save ratings.json --top 5

# Load existing ratings and continue
.venv/bin/python scripts/rate_builds.py --rounds 5 --load ratings.json
```

Key flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--rounds` | 5 | Full round-robins to run |
| `--save` | `ratings.json` | Path to save ratings |
| `--load` | — | Load existing ratings and add games |
| `--tau` | 0.5 | Glicko-2 system constant (volatility) |
| `--rating-period` | 50 | Update ratings every N games |

The leaderboard shows individual build ratings plus the top team compositions.

---

### 4. Web UI

Interactive simulator: pick combatants, run fights with SSE live-streaming, and
browse the leaderboard.

```bash
# Start the server
.venv/bin/uvicorn cod_sim.api.main:app --reload --port 8000
```

Then open `http://localhost:8000` in a browser.

API endpoints:
- `GET /api/builds`           — list all builds with ratings
- `GET /api/builds/{id}`      — single build detail
- `POST /api/combat/run`      — run a fight, return full event log
- `GET /api/combat/stream`    — run a fight with SSE live events
- `GET /api/ratings/leaderboard` — Glicko-2 leaderboard (individual builds)
- `GET /api/ratings/teams`    — top team composition ratings

---

## Build Definition Format

Builds are YAML files in `builds/<splat>/`.  The schema is in `builds/schema.yaml`.

```yaml
id: 201                       # unique integer (mortal=1xx, vamp=2xx, wolf=3xx, fae=4xx, hunter=5xx)
name: "Daeva Celerity Bruiser"
splat: vampire                # mortal | vampire | werewolf | changeling
size: 5                       # base Size (5 for adult humans)

attributes:
  strength: 4
  dexterity: 4
  stamina: 3
  intelligence: 2
  wits: 3
  resolve: 3
  presence: 3
  manipulation: 2
  composure: 2

skills:
  brawl: 4
  weaponry: 2
  firearms: 0
  athletics: 3
  stealth: 1

weapon:
  damage_mod: 0               # bonus dice added to damage (after successes)
  damage_type: bashing        # bashing | lethal | aggravated
  initiative_penalty: 0       # subtracted from initiative roll
  is_ranged: false            # uses Dex+Firearms; bypasses melee defense
  is_silver: false            # deals Aggravated to werewolves
  is_fire: false              # deals Lethal to vampires (ignores bashing downgrade)
  is_sunlight: false          # deals Aggravated to vampires

armor:
  general: 0                  # subtracts from all non-agg damage
  ballistic: 0                # additional vs ranged attacks

# Splat-specific sections — only include the relevant one:

vampire:
  blood_potency: 2
  celerity: 3                 # +dots Defense (persistent); active (slot 0): extra action
  vigor: 2                    # +dots Strength (persistent); active (slot 1): reflexive bonus + extra action
  resilience: 0               # +dots Stamina/HP (persistent); active (slot 2): (dots+1) armor/turn
  protean: 0                  # active (slot 3): natural claws → unarmed Lethal (+1L or +2L at ••••)
  nightmare: 0                # passive: blocks WP vs this vampire; active (slot 4): Frightened condition
  dominate: 0                 # active (slot 5): Mesmerize contested roll → Dominated condition

werewolf:
  primal_urge: 2              # governs Essence max, regeneration rate, form penalties
  purity: 0                   # Warrior's Hide (≥2): +Purity HP; Killer Instinct (slot 5)
  glory: 0                    # War Howl (slot 6): +1L to all allies this turn
  cunning: 0                  # tracked; no Gift implemented yet
  honor: 0                    # tracked; no Gift implemented yet
  wisdom: 0                   # tracked; no Gift implemented yet

changeling:
  wyrd: 3                     # governs Glamour max; used by Combat Contract (+Wyrd attack dice)
  seeming: Beast              # Beast | Darkling | Elemental | Fairest | Ogre | Wizened
  glamour_max: 12             # overrides wyrd-derived default if specified

# Combat merits (optional; all default to 0 if absent):
merits:
  iron_skin: 4                # passive: +1/+2 armor vs bashing (••/••••); active: IronSkinDowngrade
  iron_stamina: 2             # reduce wound penalty by dots (min 0)
  fast_reflexes: 2            # +1/+2 to Initiative
  defensive_combat: 1        # use max(Brawl,Weaponry) instead of Athletics for Defense
  fighting_finesse: 1        # use Dexterity instead of Strength for melee attack pool
  martial_arts_lethal: 1     # unarmed attacks deal Lethal (same as Beast seeming)
  street_fighting: 1         # use max(Dex,Wits) instead of min for Defense
  brawling_dodge: 1          # use Brawl instead of Athletics for Defense
```

---

## Splat Rules Reference

### Core Mechanics (all splats)

- **Dice pool**: Attribute + Skill (or Attribute + Attribute); successes on 8, 9, 10.
- **10-Again**: every 10 is re-rolled (additional chances to succeed).
- **Chance die**: pool ≤ 0 → roll 1 die; 10 = success, 1 = dramatic failure.
- **Defense**: (Dexterity or Wits, whichever is lower) + Athletics. Subtracted from attacker's pool for melee/thrown; each additional attacker beyond the first loses 1 from defense.
- **Wound penalty**: –1 at 3rd-to-last health box, –2 at 2nd-to-last, –3 at last.
- **Full Defense**: uses your action; doubles effective defense for the turn.
- **Willpower**: spend 1 for +3 dice on any single roll.
- **Armor**: general armor subtracts from all non-aggravated damage; ballistic armor adds vs ranged.

### Vampire the Requiem

| Rule | Implementation |
|------|----------------|
| Most melee weapons deal **Bashing** (not lethal) | ✅ `effective_damage_type` |
| Fire deals **Lethal** | ✅ `weapon.is_fire` |
| Sunlight deals **Aggravated** | ✅ `weapon.is_sunlight` |
| **Torpor**: last health box = Lethal | ✅ `update_incapacitation` |
| **Final Death**: last health box = Aggravated | ✅ |
| Conscious with all-Bashing | ✅ no incap on bashing alone |
| **Celerity** persistent: +dots to Defense | ✅ `CharacterState::from_build` |
| Celerity active: immediate extra action | ✅ `extra_actions_remaining` (Phase 7E) |
| **Vigor** persistent: +dots to Strength | ✅ attack pool calculation |
| Vigor active: reflexive bonus + extra action | ✅ `apply_vampire_power` slot 1 (Phase 7E) |
| **Resilience** persistent: +dots to Stamina (HP) | ✅ `max_health` |
| Resilience active: (dots+1) armor for turn | ✅ `turn_bonuses.armor_value` |
| Vitae per-turn limit by Blood Potency | ✅ `vitae_per_turn` |
| Heal with Vitae: 1V = 2B or 1L | ✅ `HealWithVitae` action |
| **Protean** active: Predatory Aspect → natural claws (Lethal +1 or +2L at ••••) | ✅ `apply_vampire_power` slot 3 |
| **Nightmare** passive: blocks WP spending by attackers | ✅ `legal_mask` Nightmare check |
| **Nightmare** active: Frightened condition on target | ✅ `apply_vampire_power` slot 4 |
| **Dominate**: Mesmerize → Dominated (next action forced Pass) | ✅ `apply_vampire_power` slot 5 |

### Werewolf the Forsaken

| Rule | Implementation |
|------|----------------|
| **Silver** deals Aggravated | ✅ `weapon.is_silver` |
| **Gauru regeneration**: all B+L each turn | ✅ `on_turn_start` |
| **Gauru time limit**: reverts to Hishu after `turns_in_gauru > primal_urge` | ✅ `on_turn_start` (Phase 7E) |
| Non-Gauru regen: Bashing at Primal Urge rate | ✅ `bashing_regen_per_turn` |
| Non-Gauru lethal regen: 1L every N turns by Primal Urge | ✅ `lethal_regen_interval` (Phase 7C) |
| Form stat deltas (Str/Dex/Sta/Size) | ✅ `recalculate_werewolf_stats` |
| Form shapeshift during combat | ✅ `ActivatePower` slots 0–4 |
| Essence max by Primal Urge | ✅ `essence_max` |
| Spend Essence to heal Lethal | ✅ `RegenerateEssence` action |
| **Renown** (Purity/Glory/Cunning/Honor/Wisdom) | ✅ `SplatBuild::Werewolf` fields |
| **Warrior's Hide**: Purity ≥ 2 → +Purity to max health | ✅ `from_build` (Phase 7C) |
| **Killer Instinct**: 8-again on attacks this turn | ✅ `ActivatePower` slot 5 (Phase 7C) |
| **War Howl**: +1L to all allies this turn | ✅ `ActivatePower` slot 6 (Phase 7C) |

**Wolf form stat deltas** (vs Hishu baseline):

| Form | Str | Dex | Sta | Size | Notes |
|------|-----|-----|-----|------|-------|
| Hishu | — | — | — | — | Human form |
| Dalu | +1 | — | +1 | +1 | Near-human; claws (Lethal) |
| Gauru | +3 | +1 | +2 | +2 | War form; regenerates all B+L/turn |
| Urshul | +2 | +2 | +2 | +1 | Wolf-man; fast |
| Urhan | — | +2 | +1 | −1 | Wolf form |

### Changeling the Lost

| Rule | Implementation |
|------|----------------|
| Glamour max by Wyrd | ✅ `glamour_max` |
| **Beast** seeming: unarmed deals Lethal, +3 Initiative | ✅ `resolve_attack`, `from_build` |
| **Ogre** seeming: dealing damage debuffs target (−1 dice next roll); costs 1 Glamour | ✅ `resolve_attack` (Phase 7D) |
| **Darkling** seeming: spend 1 Glamour → insubstantial for 1 turn (no damage) | ✅ `ActivatePower` slot 0 (Phase 7D) |
| **Elemental** seeming: +1 Stamina (→ +1 HP) | ✅ `from_build` (Phase 7D) |
| **Fairest** seeming: +1 Composure (→ +1 WP, +1 Initiative mod) | ✅ `from_build` (Phase 7D) |
| **Wizened** seeming: +1 Wits (→ better Defense via min(Dex,Wits)) | ✅ `from_build` (Phase 7D) |
| **Combat Contract**: spend 2 Glamour → +Wyrd dice to attack + resolve attack | ✅ `ActivatePower` slot 1 (Phase 7D) |

### Hunter the Vigil

Hunters are implemented as enhanced mortals with access to special weapons
(silver blades, fire arms) and higher base stats.  Supernatural Endowments
are not yet implemented.

---

## Known Simplifications

The following rules are simplified or approximated relative to the source books:

1. **Spending Vitae/Essence for physical intensity** (`SpendResourcePhysical`) uses
   the character's full action.  In VtR 2e, spending Vitae for attribute enhancement
   is reflexive and can be combined with a regular attack in the same action.

2. **Dominate** uses a simplified Expression=2 constant for the attack roll (actual
   VtR 2e uses Manipulation + Expression + Dominate, where Expression is a tracked
   skill).  The contested roll vs Resolve + Composure/Blood Potency is correct.

3. **Changeling Contracts** are simplified to a single "Combat Contract" that costs
   2 Glamour for +Wyrd attack dice.  The full Contract system from CtL 2e (with its
   Clauses, Frailties, and element-specific rules) is not implemented.

4. **Silver vs vampires**: silver is a werewolf weakness only.  A silver melee
   weapon deals Bashing to a vampire (same as any other melee weapon).

5. **Werewolf Gifts** cover only Full Moon (Killer Instinct, Warrior's Hide) and
   Gibbous Moon (War Howl).  Other Moon gifts and Shadow Gifts are not yet
   implemented.

6. **Hunter Endowments** (Tactics, Edges, Blessings, Relics) are not implemented.
   Hunters are enhanced mortals with special weapons.

---

## Project Architecture

```
ChroniclesOfDarknessCombatSim/
├── cod_sim/              Rust simulation crate (PyO3/maturin)
│   └── src/
│       ├── lib.rs        PyO3 module entrypoint
│       ├── dice.rs       d10 pool: 10-Again, chance die, rote quality
│       ├── character.rs  BuildDefinition, CharacterState, HealthTrack, SplatState
│       ├── action.rs     Action enum + flat integer encode/decode
│       ├── combat.rs     CombatState: initiative, turn loop, damage, splat rules
│       ├── env.rs        CombatEnv (PyO3 #[pyclass]) + VecEnv
│       └── splats/       Per-splat constants (vampire.rs, werewolf.rs, changeling.rs)
├── python/cod_sim/       Python ML + API layer
│   ├── build_registry.py YAML loader + build encoder
│   ├── env.py            Gymnasium wrapper around Rust CombatEnv
│   ├── policy.py         CoDPolicy: masked MLP (actor-critic)
│   ├── selfplay.py       Custom PPO self-play trainer
│   ├── glicko.py         Glicko-2 rating system
│   ├── matchmaker.py     Round-robin + skill-based matchmaking
│   ├── checkpoint.py     Save/load policy checkpoints
│   └── api/              FastAPI web server
├── scripts/
│   ├── bootstrap.sh      One-time environment setup
│   ├── train.py          PPO training entry point
│   ├── rate_builds.py    Glicko-2 rating tournament
│   └── replay.py         Turn-by-turn combat log (debugging)
├── builds/               Character build YAML files
│   ├── schema.yaml       JSON-schema for build validation
│   ├── mortal/           Mortal builds (ID 1xx)
│   ├── vampire/          Vampire builds (ID 2xx)
│   ├── werewolf/         Werewolf builds (ID 3xx)
│   ├── changeling/       Changeling builds (ID 4xx)
│   └── hunter/           Hunter builds (ID 5xx)
├── tests/python/         pytest test suite
├── checkpoints/          Trained policy checkpoints (.pt files)  ← retrain after Phase 7 (OBS/ACTION changed)
├── checkpoints_phase6/   Phase 6 checkpoints (archived, incompatible with Phase 7 architecture)
└── ratings.json          Saved Glicko-2 ratings
```

### Observation Space

Flat `float32` vector of length `N_chars × 30 + 3` (`OBS_PER_CHAR = 30`).

Per character (30 floats):
```
[0]     Bashing damage ratio (bashing / max_hp)
[1]     Lethal damage ratio
[2]     Aggravated damage ratio
[3]     Empty health box ratio
[4]     Wound penalty normalised ((penalty+3)/3)
[5]     Willpower ratio (current / max)
[6]     Supernatural resource ratio (Vitae / Essence / Glamour)
[7]     Defense ratio (remaining / base)
[8]     Is incapacitated (0/1)
[9..12] Splat one-hot (Mortal, Vampire, Werewolf, Changeling)
[13]    Strength / 10
[14]    Dexterity / 10
[15]    Stamina / 10
[16]    Primary power /5   (Celerity | Primal Urge | Wyrd | 0)
[17]    Secondary power /5 (Vigor | 0 | 0 | 0)
[18]    Tertiary power /5  (Resilience | 0 | 0 | 0)
[19]    p4 /5  (Protean | Purity-renown | 0 | 0)
[20]    p5 /5  (Nightmare | Glory-renown | 0 | 0)
[21]    p6 /5  (Dominate | Cunning-renown | 0 | 0)
[22]    Wits / 10
[23]    Is frightened (0/1)  — Nightmare condition
[24]    Is dominated (0/1)   — Dominate condition
[25]    Combat buff: 0=none, 0.33=Killer Instinct, 0.66=War Howl, 1.0=Insubstantial
[26]    Armor general / 5
[27]    Weapon damage mod normalised
[28]    Wolf form index / 4  (0=Hishu … 1=Urhan)
[29]    Initiative / 30
```

Slot order: self at slot 0, teammates next, enemies last.

Global (3 floats): `turn/MAX_TURNS`, alive_allies_ratio, alive_enemies_ratio.

### Action Space

Discrete, fixed size `ACTION_SPACE_SIZE = 88`.

| Indices | Action |
|---------|--------|
| 0–15 | `Attack` × target × willpower_spend (8 targets × 2) |
| 16–79 | `ActivatePower` × power_slot × target (8 slots × 8 targets) |
| 80–82 | `SpendResourcePhysical` × attribute (Str/Dex/Sta) |
| 83 | `HealWithVitae` |
| 84 | `RegenerateEssence` |
| 85 | `FullDefense` |
| 86 | `Pass` |
| 87 | `IronSkinDowngrade` — spend 1 WP to convert 1 lethal → bashing (Iron Skin ••) or 2 (••••) |

**Vampire power slot assignment:**

| Slot | Power |
|------|-------|
| 0 | Celerity active: immediate extra action |
| 1 | Vigor active: reflexive bonus + extra action |
| 2 | Resilience active: (dots+1) armor for turn |
| 3 | Protean: natural claws (Predatory Aspect) |
| 4 | Nightmare: Face of the Beast → Frightened condition |
| 5 | Dominate: Mesmerize → Dominated condition |

**Werewolf power slot assignment:**

| Slot | Power |
|------|-------|
| 0–4 | Shapeshift: Hishu / Dalu / Gauru / Urshul / Urhan |
| 5 | Killer Instinct: 8-again on Brawl/Weaponry this turn |
| 6 | War Howl: +1L to all alive allies this turn |

**Changeling power slot assignment:**

| Slot | Power |
|------|-------|
| 0 | Seeming power: Darkling → insubstantial (1 Glamour); Ogre → passive (no slot needed) |
| 1 | Combat Contract: +Wyrd attack dice (2 Glamour) + resolve attack |

---

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Foundation: dice, mortal combat, PyO3 binding |
| 2 | ✅ Done | VecEnv (Rayon parallel), build registry (YAML), Gymnasium wrapper |
| 3 | ✅ Done | All 4 splat rules, silver/fire/sunlight, wolf forms, 9 template builds |
| 4 | ✅ Done | PPO self-play RL: 92 % win rate (decided games), 16 K steps/sec |
| 5 | ✅ Done | Glicko-2 rating: individual builds + team compositions |
| 6 | ✅ Done | FastAPI web UI: leaderboard + combat simulator with SSE live streaming |
| 7A | ✅ Done | Merit system: Iron Skin, Defensive Combat, Fast Reflexes, Fighting Finesse, Martial Arts, Street Fighting, Iron Stamina, Brawling Dodge |
| 7B | ✅ Done | Vampire discipline expansion: Protean (claws), Nightmare (fear + Frightened condition), Dominate (Mesmerize → Dominated condition) |
| 7C | ✅ Done | Werewolf Renown + Gifts: Warrior's Hide (HP), Killer Instinct (8-again), War Howl (+1L allies), non-Gauru lethal regen |
| 7D | ✅ Done | All 6 Changeling seeming blessings (Ogre/Darkling/Elemental/Fairest/Wizened) + Combat Contract |
| 7E | ✅ Done | Rule accuracy: Gauru time limit, Vigor and Celerity as reflexive extra actions |
