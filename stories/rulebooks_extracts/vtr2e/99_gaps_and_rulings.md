# VtR 2e — gaps, ambiguities, book errata, rulings

## Book contradictions / typos (RAW-faithful reading noted)
- **Speed**: creation text (p. 81) says Size + Str + Dex; quick ref (p. 82) adds **+ Vigor**. Since Vigor's persistent
  effect adds to Strength (p. 141), both agree: use effective Strength → Speed = 5 + (Str + Vigor) + Dex.
- **Torpor table** (p. 105) prints Humanity "9–10 → one night" and "8–9 → two nights" (overlap). **[interp]** 10 = one
  night, 8–9 = two nights, 6–7 = one week.
- **Blood bond stage 3** text says "+3 die penalty" — clearly a **+3 bonus** to the regnant (p. 100).
- **Touch of Deprivation** (Obf 4 + Dom 2) lists pool Int + Medicine + **Auspex** (p. 148) — likely meant Obfuscate or
  Dominate. **[interp]** use Int + Medicine + Obfuscate.
- **Diablerie** (p. 101): "once the victim's Health boxes are full of aggravated damage" though draining deals lethal;
  [interp] lethal draining continues to upgrade via core wrap-around until full agg.
- **Charmed** is labelled Persistent but expires after 1 hour per BP (p. 301); treat as timed.
- **Teach** Strix Corpus printed 2 (Res 3 + Size 2 should be 5) [p. 233]. **Lady of Shivs** Size 5 (probably 2).
- Mekhet bane text is split in the .txt (L8040–8047 and L8093–8095): bane = extra non-breaking-point bane at Humanity 6
  + Humanity −1 for Humanity-based banes (sunlight, torpor).
- Some Strix stat blocks say "Possess Vampire" = Possess Kindred.
- BP 0 row of the BP table = ghouls (Vitae max = Stamina, 1/turn).

## Common misreadings (caught in the example_daeva corrections — test cases)
1. **Favored Attribute**: every Kindred gets **+1 free dot** in one of the clan's two favored Attributes (Daeva: Dex
   or Manip). Show it as a separate line on sheets (p. 80).
2. **Blood Potency comes from age**: +1 per ~50 years awake, −1 per 25 years in torpor (pp. 84, 89; Ch7 p. 276 repeats
   it and suggests ~15 XP per century for generational play). Don't charge 5 XP/dot for an elder's age-earned BP. At
   creation only BP 2–3 can be bought (5 Merit dots each).
3. **Grapple is two-stage**: the **grab** is an attack roll **Str + Brawl − Defense** (target doesn't roll); afterwards
   each turn is **contested Str + Brawl vs Str + Brawl** (no Defense). Handcuffing = Str + Brawl − target's Strength
   (p. 177, 191).
4. **Firearms vs vampires deal bashing** (p. 90, 179); Defense doesn't apply vs guns, but **Celerity still subtracts its
   dots from the shooter's pool** (p. 131). Resilience active: −(Res + 1) per non-bane attack that turn.
5. Majesty **Awe needs no roll** and resists only via a vampire's predatory aura; Confidant/Loyalty are **contested by
   Resolve + BP** (mortals: BP 0). Charmed adds Majesty to the vampire's **Manipulation** rolls vs the victim (p. 301).
6. Mesmerize needs **eye contact** and is contested by **Resolve + BP**; commands ≤ 3–4 words (p. 131).
7. Breaking points only apply at or below current Humanity; WP can't be spent on detachment rolls (p. 107–108).
8. WP can't add +3 to frenzy resistance — it delays one turn and adds +1 per WP when finally rolled (p. 104).
9. Clan banes don't apply until Humanity drops to 6 (Ventrue's Touchstone-at-7 rule is from creation) (p. 103).

## Deferred to CoD core (`../cod_core/`)
- Mortal NPC templates (police officers, SWAT, hunters), Tilts list (Stunned, Immobilized, Knocked Down, Blinded…),
  extended Integrity/breaking points for mortals, Fighting Style Merits beyond Kindred ones, Supernatural Merits for
  mortals, ghosts/spirits (abjuration rules used by Strix banes), chases, vehicles, Fate.
- Aim, Disarm (VtR doesn't reprint Disarm except as a grapple move), Fighting styles, Tilts from specified targets.

## RAW-silent points → rulings used in these extracts
- **Mortals fighting a predatory aura**: roll Power Attribute alone (no BP) **[interp]**.
- **Lashing out against a mortal is free and instant**; mortal can still "fight" (+2 if they win) or "flee".
- **Celerity interrupt + Vigor/Resilience**: each Vitae effect also counts toward Vitae-per-turn (BP table) — all
  Discipline active effects, Physical Intensity, healing share that cap.
- **Stun gun / pepper spray on Kindred**: book silent; pepper spray (sight) plausibly works; electricity damage would be
  bashing; ST call **[interp]**.
- **Ghoul resisting a vampire**: ghoul can't add Discipline dots; bonded ghouls auto-fail Disciplines against their regnant.
- **Starting elders**: VtR has no rule for granting age-based BP to starting characters beyond "+1 per 50 years" and
  Ch7's ~15 XP/century benchmark; combine both **[interp]**.
- **Strix possessing a vampire defeats stakes** (host uses Strix banes) — RAW p. 205.

## Self-test lessons (2026-10-12, Daeva elder + 3 police, cache-less subagent)
Result: **no rules errors** — favored Attribute, age-BP, Majesty/Dominate pools, Defense vs taser darts, bashing from
guns, XP ledger all correct. Gaps it hit (all RAW-silent; now patched as [interp] in 03/05):
- Charmed exceptional duration → **1 night per BP** (follows from p. 133 + p. 301; not a free-floating interp).
  Mesmerize commands need no further roll.
- Idol: per-attempt roll; what counts as "harmful" is ST call; only already-Charmed roll for Enthralled on activation;
  Indomitable vs a non-contested/non-resisted roll → +2 dice.
- Reflexive powers can fire outside Initiative order — **RAW p. 170** ("at any time"), stated in 05 §13.
- Humanity relate-to-humans penalty vs Discipline pools using Empathy → **default: don't apply** (revised after an external
  cross-check citing 1e precedent; the self-test had applied −1 to Confidant).
- Starting Vitae roll is after the waking Vitae cost.
- Does Mesmerize work on an Enthralled target? Book silent → roll normally (Enthralled doesn't block contest) [interp].
- Mortals don't face breaking points for being Majesty/Dominate victims (no rule) [interp].
- Taser Initiative penalty not listed → 0; semi-auto patrol rifle → assault-rifle profile without autofire.
- Not exercised: damage to Kindred, grapple. Elder build convention: bonus-XP tier + free age-BP (02).
- External cross-check (GPT reading, 2026-10-12), verified against the .txt: pages 92, 95, 98, 106, 133–134, 170,
  301, 303 cited correctly; Idol establishes Awe on activation; Enthralled check only at activation; BP 1 can't pay
  Idol's 2 Vitae in one turn. Its 1e (p. 185) claim and Onyx Path forum/FAQ references were not verifiable here.

