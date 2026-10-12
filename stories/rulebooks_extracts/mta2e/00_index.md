# Mage: the Awakening 2e (2016 core) — extract index

Source: `../../../rulebooks/Mage the Awakening - Second Edition.txt` (32,532 lines). Built on the CoD core engine (`../cod_core/`); **MtA overrides core for mages**: Wisdom instead of
Integrity, **Gnosis = Supernatural Tolerance**, Mana as the power pool, spells **Withstood** rather than resisted.

## Files
| File | Covers |
|---|---|
| `01_lore.md` | Premise (Lie, Exarchs, Abyss, Quiescence), **Paths table** (Ruling/Inferior, Realms, entities), **Orders table + Rote Skills**, Consilium/Lex Magica, Shadow Names, Legacies overview, souls |
| `02_character_creation.md` | Steps 5/4/3, 11/7/4; **free traits** (Resistance +1, Order Status •, Occult +1, High Speech, 6 Arcana, 6 rote dots, Praxes = Gnosis, Gnosis 1, Wisdom 7); Gnosis 2/3 for Merit dots; **XP & Arcane XP costs**; Arcane Beats; **Gnosis table** |
| `03_spells.md` | §0 **spellcasting** (pool, Reach, Praxes/Rotes, factors tables, Yantras, Withstand, Aimed, results, **Paradox**, Clash of Wills, spell control, combined, teamwork, Practices, creative thaumaturgy); §1 **every spell** of the 10 Arcana; §2 **Attainments** (Counterspell, Lesser/Greater Utilities, **Mage Armor**, Create Rote); §3 **Legacies** |
| `04_merits.md` | Awakened Merits (Artifact, Imbued/Enhanced Item, Familiar, Hallow, Sanctum, Destiny, Occultation, Order Merits…), mundane Merits reprinted |
| `05_systems.md` | **Mana** (uses, Oblation, Scouring), **Wisdom & Acts of Hubris**, **Nimbus** (Tilt design), High Speech, **Mage Sight** (Peripheral/Active/Focused, Revelation, Scrutiny, Opacity), Supernal **summoning**, souls/soul stones/Demesnes, **Ch5 core deltas**, **places & realms** (Hallows, Verges, Irises, Underworld, Shadow, **Astral**), **Quiescence & Dissonance**, **Duel Arcane**, Ch7 city mechanics |
| `06_antagonists.md` | Left-Handed mages (Mad, Banishers, Liches, Reapers, Scelesti), Supernal entities & Bound, archmages, **ephemeral entity rules** (Rank table, Influence, Manifestation & Conditions, **Numina**), **Sleepers, Sleepwalkers (incl. holding spells), Proximi, Seer servitors**, Sleeper/Sleepwalker Merits |
| `07_conditions.md` | All App. 3 Conditions, Paradox Conditions, Tilt list |
| `08_factions_map.md` | Paths & Orders identity, Seer Ministries, Legacies index, Ch7 cities, Atlantis myth |
| `99_gaps_and_rulings.md` | Scramble repairs, book inconsistencies (1e sheet summary trap), [interp] rulings |

## Quick lookups
- Building a mage → `02` + Rote Skills in `01`. Merits → `04`. Free Reach & Paradox → `03` §0.3, §0.10. Spell by name → grep `03`.
- Combat magic: attack spells (Fraying bashing / Unraveling lethal = Potency), **Aimed** `03` §0.8, **Mage Armor** `03` §2, Counterspell `03` §2, Clash of Wills `03` §0.11, grapple casting `05` §8.
- Sleepers watching → Paradox +1 die, breaking point, Act of Hubris, Dissonance: `05` §10. Wisdom rolls → `05` §2.
- Ghosts/spirits/Goetia → `06` §C. Mage Sight & investigating Mysteries → `05` §5. Astral travel → `05` §9.

## Source anchors (page = bare number line at the **end** of each page; L1–1717 is the TOC)
| Section | Pages | Lines |
|---|---|---|
| Intro, themes | 7–15 | L1719–2345 |
| Ch1 Paths (Acanthus L2569, Mastigos L2861, Moros L3148, Obrimos L3428, Thyrsus L3734) | 19–33 | L2454–3990 |
| Ch1 Orders (Arrow L4045, Guardians L4314, Mysterium L4604, Ladder ~L4837, Free Council L5085, Seers L5369) | 35–55 | L3990–5560 |
| Ch2 Awakening, Supernal Realms | 59–65 | L5696–6340 |
| Ch2 High Speech, Nimbus, Shadow Names, Mage Society, Lex Magica (L6691), Caucuses, Legacies, Lexicon (L7000) | 66–75 | L6352–7350 |
| Ch3 Character creation (quick ref L7622), XP L7743, Arcane Beats L7750 | 79–84 | L7359–7897 |
| Gnosis (table L8091–8310), Mana L8315, Wisdom L8372, Nimbus L8503 | 84–90 | L7898–8636 |
| High Speech, Mage Sight (Focused L8833), Building Mysteries | 91–94 | L8637–9102 |
| Summoning Supernal entities | 94–97 | L9103–9365 |
| Souls, soul stones, Demesnes | 97–99 | L9366–9552 |
| Awakened Merits / mundane Merits | 99–107 | L9553–10072 / L10072–10415 |
| Ch4 Spellcasting, Reach, Praxes, Rotes | 111–113 | L10562–10703 |
| Spell factors tables, Withstand, Aimed, results | 113–115 | L10704–11111 |
| Paradox, Paradox Conditions, Down & Dirty, Clash of Wills, Dispel, combat/grapple, spell control, combined, teamwork | 115–119 | L11112–11490 |
| Yantras (Dedicated tool L11885) | 119–123 | L11491–11904 |
| Practices, creative thaumaturgy | 123–127 | L11905–12318 |
| Death / Fate / Forces / Life / Matter | 128–159 | L12319 / 12918 / 13522 / 14272 / 14902 |
| Mind / Prime / Space (sympathy table L16712) / Spirit (Gauntlet L17351) / Time (temporal sympathy L18006) | 159–191 | L15399 / 16002 / 16610 / 17341 / 17948 |
| Attainments (Mage Armor L18791) | 192–197 | L18597–19123 |
| Legacies, Eleventh Question, other Legacies | 197–203 | L19124–19840 |
| Ch5 Fallen Laws (Social maneuvering L21002, combat L21165, injury ~L22123, equipment L22473, Tilts L23348) | 207–231 | L19841–23540 |
| Ch6 Left-Handed mages | 235–239 | L23541–23883 |
| Fallen Worlds: sancta, Hallows, ley lines, Verges (L24140), Irises (L24230), ruins & Bound | 239–244 | L23884–24382 |
| Realms Invisible: Lower Depths, Underworld, Shadow, **Astral** (L24557–24925), Emanations, archmages | 244–252 | L24383–25098 |
| Invisible entities: Twilight, Rank table (L25263), Essence, traits, bans/banes, combat, Influence (L25690), Manifestation & Conditions (L25772–26070), Numina (L26071) | 252–263 | L25099–26233 |
| Ch7 London / LA / Salamanca / Tokyo / Tucson | 267–283 | L26449 / 26747 / 27071 / 27396 / 27761–28330 |
| Ch8 Storytelling; creating Conditions (L28469); **Duel Arcane** (L28977) | 287–295 | L28333–29095 |
| App. 1 Sleepers (Quiescence, Dissonance L29542, Integrity L29586), Sleeper Merits (L29817), Sleepwalkers (L29893; holding spells L29974), Sleepwalker Merits (L30124), Proximi (L30258), Servitors (L30426) | 298–311 | L29456–30516 |
| App. 2 Legends of the Fall | 312–313 | L30517–30725 |
| App. 3 Conditions / Tilts | 314–324 | L30726–31191 / L31192–31850 |
| App. 4 Spellcasting quick reference | 325–328 | L31852–32300 |
