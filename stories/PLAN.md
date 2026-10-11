# Rulebook Extraction Plan

Goal: read each rulebook in `../rulebooks/` **once**, in a single session, and
distil it into `rulebooks_extracts/<book>/` — notes dense enough that story/scene
sessions never need the full book again. Full-book reads are expensive
(~300–430K tokens each); extracts should be ~25–40K tokens per book.

## Book queue

| # | Book | File (`../rulebooks/`) | Size | Extract dir | Status |
|---|------|------------------------|------|-------------|--------|
| 1 | Vampire: the Requiem 2e | `Vampire the Requiem - SECOND EDITION.txt` | 1.30 MB / 29.6K lines | `vtr2e/` | ⏳ next |
| 2 | Chronicles of Darkness core | `Chronicles of Darkness.txt` | 1.63 MB / 16.5K lines | `cod_core/` | todo |
| 3 | Werewolf: the Forsaken 2e | `Werewolf_the_Forsaken_Second_Edition_(Download_Final).txt` | 1.47 MB / 38.5K lines | `wtf2e/` | todo |
| 4 | Changeling: the Lost 2e | `Changeling_the_Lost_2e_(Final_Download).txt` | 1.43 MB / 32.5K lines | `ctl2e/` | todo |
| 5 | Geist: the Sin-Eaters 2e | `Geist_the_Sin-Eaters_Second_Edition_(Final_Download)(1).txt` | 1.73 MB / 18.7K lines | `gts2e/` | todo |
| 6 | Mage: the Awakening 2e | `Mage the Awakening - Second Edition.txt` | 1.42 MB / 32.5K lines | `mta2e/` | optional |

Why core second: combat, skills, mortal merits, Conditions/Tilts and the
generic ephemeral-entity (ghost/spirit) rules live in the core book. During the
Vampire session, extract whatever generic rules VtR reprints, and log anything
deferred to core in `vtr2e/99_gaps_and_rulings.md`.

## Per-book session procedure (one session = one book, one push)

Start it with: `cd stories && claude --model opus --add-dir ../rulebooks`,
then `/extract-book vampire` (the command lives in `.claude/commands/`).

### Step 0 — Map (cheap, before reading)
- `wc -l` the book; `grep -n` for chapter/section headings and page markers
  (check how page numbers appear in the .txt — e.g. a bare number line, a
  running header). Build the section→line-range map. This becomes the
  **Source anchors** table in `00_index.md`.

### Step 1 — Read sequentially, write as you go
- Read the book front to back with the Read tool in large chunks
  (~2500–3000 lines, `allow_large: true`), never re-reading a chunk.
  Sequential reading keeps the prefix stable so every later turn is a cache read.
- After finishing each chapter, **immediately write/append** its notes to the
  matching extract file (protects against context compaction losing work).
- Skim fluff (fiction vignettes, long faction essays) — note only the map-level
  facts from factions.

### Step 2 — Extract files (per book)
Template for `vtr2e/`; other books adapt the names (Gifts/Renown for WtF,
Contracts/Wyrd for CtL, Haunts/Keys for GtS, Arcana for MtA):

| File | Contents |
|------|----------|
| `00_index.md` | What each file covers; **Source anchors**: section → book page + .txt line range, so a later session can re-read a 150-line slice instead of the book |
| `01_lore.md` | How the world/Kindred work: Embrace, the Beast, Vitae, Blood Potency (effects, ceilings, feeding restrictions), sunlight/fire, daysleep, torpor & awakening, frenzy/Rötschreck, Predatory Aura & Lashing Out, Masquerade, Danse Macabre, ghouls (creation, aging, Vitae addiction, Vinculum), blood bond, diablerie, Strix (nature, possession, powers), Requiem history in brief |
| `02_character_creation.md` | Step-by-step creation with exact dot allotments; everything granted **for free** (clan, favored Attribute +1, BP 1, Disciplines, Merits, Humanity 7, Touchstone, Mask/Dirge…); **aging rules** (BP gained by age/torpor, starting elders, XP equivalents); XP cost table; Banes; Willpower & Aspirations; derived traits (Health, Defense, Speed, Initiative, Size) |
| `03_disciplines.md` | Every Discipline & power: cost, dice pool, resistance/contest, action type, duration, exact effect. Clan in-clan lists. Devotions and blood sorcery (Crúac, Theban) with rituals summarised. This is the biggest file — be terse, table-like, but complete |
| `04_merits.md` | All vampire/covenant merits: dots, prerequisites, exact effect |
| `05_systems.md` | Feeding & hunting rolls, Vitae per turn by BP, healing costs, Humanity & breaking points (dice by level), Touchstones/detachment, frenzy resistance, blood bond stages, diablerie procedure, torpor duration table, social maneuvering/Doors if covered, combat rules reprinted in the book (grapple, all-out attack, Defense vs firearms, etc.), vampire-specific damage rules |
| `06_antagonists.md` | Strix (traits, Dread Powers, possession), ghouls & ghoul families, rival Kindred templates, mortal threats, VII, hunters, sample NPC stat blocks with full pools; any ephemeral/other entities the book covers |
| `07_conditions.md` | Every Condition/Tilt defined in the book: effect, resolution, Beat |
| `08_factions_map.md` | Clans, covenants, bloodlines: 2–4 lines each (identity, bane, in-clan Disciplines, signature powers/merits) — map only |
| `99_gaps_and_rulings.md` | Ambiguities, things deferred to the core book, common misreadings (record the ones caught in the self-test) |

Notation rules for all extracts:
- Cite page `[p. 123]` (and line `L12345` when useful) on every rule.
- Mark anything not RAW as **[interp]**.
- Prefer exact numbers and formulas over prose. Write dice pools as
  `Presence + Persuasion + Majesty − Composure`.

### Step 3 — Self-test with a cache-less subagent
1. Spawn a fresh `general-purpose` Agent (model `opus`). Its prompt:
   - Read only `stories/CLAUDE.md`, `stories/rulebooks_extracts/**`, and use
     `stories/tools/roll.py` for dice. **Forbidden:** `../rulebooks/` and
     `stories/example_*.md`.
   - Task: the **first user turn only** of the book's test case (verbatim).
   - At the end, list every rule it needed but couldn't find or had to guess.
2. Compare its answer against (a) the full book still in my context and
   (b) the example file, including the user's follow-up corrections.
3. Fix every discrepancy and every gap in the extracts — while the book is
   still cached. Run a second subagent round only if the fixes were large.

Test cases:
- Vampire: `example_daeva.md` first user turn (Daeva elder + 3 police arrest
  scene). Known traps from the follow-up: **favored Attribute +1 (Dex or Manip
  for Daeva)**, **Blood Potency rising with age rather than bought with XP**,
  **grapple = contested grab, then contested overpowering**.
- Werewolf: `example_werewolf_spirit.md` first user turn (spirit vs. two mortals,
  Numina, Essence, Manifestation Conditions).
- Core / Changeling / Geist / Mage: write a comparable scene prompt in-session
  that exercises that book's subsystems.

### Step 4 — Close out
- Update the Status column above and `rulebooks_extracts/README.md`.
- Add any workflow lessons to the "Lessons" section below.
- Report extract token sizes (`wc -c rulebooks_extracts/<book>/*` ÷ 4).

## Lessons
(append after each session)
