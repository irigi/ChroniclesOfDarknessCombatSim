# Rulebook Extraction Plan

Goal: read each rulebook in `../rulebooks/` **once**, in a single session, and
distil it into `rulebooks_extracts/<book>/` — notes dense enough that story/scene
sessions never need the full book again. Full-book reads are expensive
(~300–430K tokens each); extracts should be ~25–40K tokens per book.

## Book queue

| # | Book | File (`../rulebooks/`) | Size | Extract dir | Status |
|---|------|------------------------|------|-------------|--------|
| 1 | Vampire: the Requiem 2e | `Vampire the Requiem - SECOND EDITION.txt` | 1.30 MB / 29.6K lines | `vtr2e/` | ✅ done 2026-10-12 (~38K tokens) |
| 2 | Chronicles of Darkness core | `Chronicles of Darkness.txt` | 1.63 MB / 16.5K lines | `cod_core/` | ✅ done 2026-10-12 (~33K tokens) |
| 3 | Werewolf: the Forsaken 2e | `Werewolf_the_Forsaken_Second_Edition_(Download_Final).txt` | 1.47 MB / 38.5K lines | `wtf2e/` | ✅ done 2026-10-12 (~40K tokens) |
| 4 | Changeling: the Lost 2e | `Changeling_the_Lost_2e_(Final_Download).txt` | 1.43 MB / 32.5K lines | `ctl2e/` | ✅ done 2026-10-12 (~44K tokens) |
| 5 | Geist: the Sin-Eaters 2e | `Geist_the_Sin-Eaters_Second_Edition_(Final_Download)(1).txt` | 1.73 MB / 18.7K lines | `gts2e/` | ✅ done 2026-10-13 (~44K tokens) |
| 6 | Mage: the Awakening 2e | `Mage the Awakening - Second Edition.txt` | 1.42 MB / 32.5K lines | `mta2e/` | ✅ done 2026-10-12 (~49K tokens) |

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
- **Core (2026-10-12)**: page numbers in the .txt are bare number lines at the *end* of each page — build the
  page→line map from `grep -nE '^\s*[0-9]{1,3}\s*$'` first. Read limit is ~25K tokens per call when a turn has
  other large reads: use ~700–850-line chunks, not 2500. The God-Machine chapter (pp. 162–237) is mostly scenario
  fluff — grepping it for mechanics (Merit, roll, dice, Rank) and reading only NPC/angel stat blocks saved ~100K
  tokens. Two-column layout interleaves text; tables (weapons, Tilts) survive OK. Self-test scene (mortals +
  Social Maneuvering + Rank 2 ghost possession + grapple + abjuration) found no rules errors, only RAW-silent gaps
  (ties, grapple action economy, darkness) — patched as [interp] in the extracts.
- **Vampire (2026-10-12)**: page numbers again bare lines at page end (one false hit: "100" at L5701 is a table cell).
  ~44 bytes/line, so ~1500–1800-line Read chunks fit the 25K limit. Ch1 (clans/covenants), Ch2 (setting) and Ch6
  (sample cities) are fluff — skimmed/grepped Ch6 for mechanics (Jiang Shi clan, Tokyo zaibatsu). Two-column layout
  splits some sentences across distant lines (Mekhet bane L8040+L8093; Raptured/Sated mixed). VtR reprints core combat,
  Social Maneuvering and equipment, so the extract is self-sufficient except mortal stat blocks and Tilts. Self-test
  (Daeva + 3 police) passed all three known traps; only RAW-silent gaps (Idol edge cases, Charmed duration, reflexive
  timing, Humanity penalty scope) — patched as [interp].

- **Werewolf (2026-10-12)**: Same page-marker layout; the TOC fills L1–1824 and also has bare numbers, so start the page map
  after it. ~38 bytes/line → ~1500-line Read chunks (2000 overflowed once). Ch1 (auspices/tribes), Ch2 (setting), Ch6 (hunting
  grounds) and the fiction pages are fluff. Fiction vignettes come out as character-shredded two-column garbage: skip them.
  Grepped Ch6 and the named-idigam pages (pp. 222–245) for stat lines and read only those. The spirit rules (pp. 178–193) are the
  heart of the book. The Numina [R] icon is lost (as in core), so a house list is in 06 §I. The PU table and some Merit pages are
  scrambled; they were reconstructed by content. Self-test (Rank 2 spirit vs two mortals: Reach, Hallucination, Open, Fetter/
  Urged, Possess, abjuration, Drain) found no extract errors. It found one misleading phrase (possession penalties shrink per
  day Fettered) and ~35 RAW-silent points (starting Essence, bleed rounding, Urge cost, Drain math, abjuration vs Conditions).
  These were ruled [interp] in 99. Key RAW insight added: Strengthen → temporary Open → Fetter freezes Open (p. 188).

- **Changeling (2026-10-12)**: Same bare-number page markers; TOC fills L1–1465. ~44 bytes/line, so ~1250-line Read chunks
  were fine. Ch1 seemings/courts and Ch2 lore are mostly fiction: I grepped "Blessing/Curse/Regalia/Kith Blessing/Mantle
  Effects" and read only those blocks plus the kith section. Ch4 pp. 169–197 reprint the core engine: I grepped for deltas and
  read only from the Hedge onward. Ch6 is setting; only its alternative-court Mantle blocks are mechanics. Several
  tables and sidebars came out column-scrambled: Wyrd table, sample breaking points, hobgoblin table, four court-Contract
  pairs, Tide Court Mantles. They were reconstructed and logged in 99 §A. Self-test (Beast + Fairest vs a Huntsman with an
  iron snare, Siren Song, portaling, Hedge chase, harvest, sealing) found no RAW errors. It surfaced ~30 RAW-silent points:
  starting Glamour, snare procedure, Hedge chase with a pursuer, the navigation pool, Royal Court Contracts at creation
  needing Mantle 3. These are now patched as [interp] in 99 §C. **Warning:** during this session several task-notifications
  claimed the subagent had completed, with invented content, while its transcript showed it still reading. Trust only the
  SubagentHandback/report, and verify roll calls in the subagent JSONL.

- **Mage (2026-10-12)**: Same bare-number page markers. The TOC fills L1–1717, so start the page map after it. The book is ~44 bytes/line, and 600–900-line Read chunks were comfortable.
  Fluff that I skimmed or grepped only: Ch1 Paths/Orders (I read only the "X Magic" Ruling/Inferior blocks), Ch2 Awakening narratives, Ch7 cities (grepped for mechanics: Ansho, Paradox
  beacons, LA Astral) and App. 2 Atlantis. The fiction interludes are character-shredded. Ch5 reprints core, so I grepped it for "mage/Gnosis/Paradox/Hubris" deltas only.
  The spell chapter is the bulk of the book (pp. 128–191, ~6.3K lines). It extracts well as one line per spell (Practice · Primary Factor · Withstand · cost · rote Skills · effect · Reach options).
  About 20 spells had headers separated from their bodies, and I re-paired them by content. Cross-check the scrambled Gnosis and Paradox tables against App. 4 (the spellcasting quick reference).
  **Trap:** the p. 328 sheet carries a 1e creation summary (7 Merits, Mana = Wisdom). I logged it in 99.
  There's no example file for Mage, so I wrote a test scene: an Obrimos Arrow vs a Panopticon Seer in a garage with two Sleeper guards. It covered Counterspell, Mage Armor, an Aimed spell that hit a
  bystander in its area, Paradox contain/release, Withstand, Dissonance, Hubris and Scrutiny. It found **no extract errors** and ~20 RAW-silent points (witness counts, Counterspell timing/Mana,
  Active Sight penalty scope, Dissonance scope, experienced-start XP), which I ruled in 99 §C. The subagent's handback arrived properly this time.

- **Geist (2026-10-13)**: **Different page-marker layout.** There are no bare-number lines. Pages are marked by running headers at the **top** of each page: even pages read `NN   Chapter …`, odd pages are right-aligned `Section   NN`. Build the map with `grep -nE '^[0-9]{1,3}\s{2,}(Chapter|Introduction|Appendix)|^\s{30,}[A-Z].*\s{3,}[0-9]{1,3}\s*$'`. The TOC fills L1–358.
  The lines are long (~92 bytes, heavy indentation), so ~550–850-line chunks fit the 25K limit; 1000 lines overflowed.
  Ch1 (Burdens and archetypes) is grep-able: the Haunt affinities and starting Ceremonies sit in tagged lines. Ch2 is lore. Ch4 pp. 139–173 reprint core: I grepped for Sin-Eater deltas (Abjuration, Warding, Beaten Down) and read krewes, ghosts and the Underworld in full. Ch6 is setting, so I read only the Dominions (pp. 251–255). Ch7 has the Remembrance and end-game mechanics.
  The book contradicts itself in a few places: geist Defense on the sheet, Dead Condition timing, the Absent's Virtue regain, the Remembrance Trait cap. These are logged in 99 §A.
  Self-test scene: a Vengeful Sin-Eater plus a dead celebrant vs a masked Reaper in a cemetery, covering Aura Flare, Key unlocks and Doom, Engulf, a crisis point, Plasmic healing, opening the Gate, and a mortal witness. It found **no extract errors** and ~20 RAW-silent points (ghost attack pools, Engulf timing, Reaper reform location, Gate keys from the living side, Aura Flare scope). These are ruled in 99 §D. The subagent handback arrived cleanly.
