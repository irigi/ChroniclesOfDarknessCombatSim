# CLAUDE.md — Chronicles of Darkness stories

This directory is a **rules-faithful storytelling workspace** for Chronicles of
Darkness 2e (Vampire, Werewolf, Changeling, Geist, Mage, mortals). It is
unrelated to the combat-simulator code in the parent repo — ignore `../cod_sim`,
`../python`, etc.

## Two kinds of sessions

1. **Extraction sessions** — follow `PLAN.md` exactly. Only these read the full
   rulebooks in `../rulebooks/`.
2. **Story/scene sessions** (the default) — character sheets, scenes, rule
   questions, simulated fights.

## Rules for story/scene sessions

- **Do not read `../rulebooks/*.txt` in full.** Use `rulebooks_extracts/`.
  Start with `rulebooks_extracts/README.md`, then the book's `00_index.md`,
  then only the files the task needs.
- If the extracts lack a rule, use the **Source anchors** in `00_index.md` to
  read just that slice of the rulebook (`Read` with offset/limit, or `grep -n`).
  Then add the missing rule to the extract file so it's never looked up again.
- Cite pages (`VtR p. 123`) for rules you apply. Flag house rulings as such.
- **All dice rolls go through `tools/roll.py`** — never invent results. Show the
  raw dice. Example: `python3 tools/roll.py 7 --label "Dex+Firearms"`,
  `python3 tools/roll.py 0` (chance die), `--again 9`, `--rote`.
- Character sheets: list every free/automatic trait (clan favored Attribute,
  starting Blood Potency, in-clan Disciplines, etc.) and show an XP ledger that
  separates bought traits from age/template-granted ones.
- Before resolving a subsystem (grapple, social maneuvering, frenzy, Numina,
  possession…), restate the procedure in 2–4 lines from the extract, then apply.
- Output stories as Markdown files in this directory (`<slug>.md`), structured
  like `example_daeva.md`: fiction + sheets + mechanical ledger + raw rolls.

## Layout

- `PLAN.md` — extraction plan and per-book status
- `rulebooks_extracts/<book>/` — condensed rules (see its README)
- `tools/roll.py` — CoD d10 dice roller (OS randomness)
- `example_*.md` — reference outputs (produced by another model; contain
  user corrections — useful as test cases)
