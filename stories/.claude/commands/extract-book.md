---
description: Run one rulebook extraction session from PLAN.md
argument-hint: <book, e.g. vampire | core | werewolf | changeling | geist | mage>
---

Execute the extraction session for **$ARGUMENTS** exactly as described in
`PLAN.md` (Steps 0–4). Read the whole book in one push, sequentially, writing
extract files chapter by chapter into `rulebooks_extracts/<book dir>/`. Then
run the cache-less subagent self-test, fix discrepancies while the book is
still in context, and update the status tables. Do not read any other rulebook.
