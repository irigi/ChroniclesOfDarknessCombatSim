# WtF 2e — Werewolf Systems [Ch3 pp. 93–105, Ch4 pp. 153–193]

Core dice engine, combat, Social maneuvering etc. are also in `../cod_core/05_systems.md`; WtF reprints them with
werewolf tweaks (§10–§14 below). **Spirit / Ridden / Numina rules → `06_antagonists.md`.**

## 1. Regeneration & healing [p. 93–94]
- **Bashing**: heal the PU regen rate (1–6, table in 02) **per turn**, automatically.
- **Lethal**: heal the regen rate **every 15 minutes**. **Spend 1 Essence (reflexive)** → regenerate **lethal instead of
  bashing that turn** (i.e. regen-rate lethal points that turn).
- **Aggravated**: **1 point per 4 days**. Only **silver** and **supernatural powers** (Gifts, spells, Disciplines…) inflict
  agg on Uratha directly; anything that would do agg to a human (massive trauma, fire? → treat as source) does **lethal**
  to Uratha. Lethal overflow still upgrades to agg normally.
- Tilts from agg wounds (lost limb/eye) heal when the wound heals.
- **Gauru: heal all bashing and lethal at the start of each turn.**
- **Toxins/disease**: subtract PU from the Toxicity.
- Witnessing regeneration of **lethal** damage triggers **Lunacy as if Dalu**, whatever the form.

## 2. Senses [pp. 94–95]
Three sense sets, available in **all forms**:
- **Human senses** (default in Hishu/Dalu; perfected: 20/10 vision, lost senses regrow). Switching to wolf senses is
  reflexive, no roll.
- **Wolf senses** (default in Urshul/Urhan): form's Perception bonus (Hishu +1, Dalu +2, Gauru +3, Urshul +3, Urhan +4)
  and **other senses negate deprivation penalties** (blindness, deafness, strong scents).
  - **Smell**: roll **Primal Urge** to identify someone remembered, even hidden/disguised. Link a scene smelled earlier to
    an Uratha met later: **Wits + PU**. Identify a werewolf/Wolf-Blooded by smell: **Wits + PU**, instant, must get into
    personal space.
  - **Hearing**: range **1 mile per PU dot**; ignore quiet/range penalties (city noise limits to surroundings).
  - **Vision**: **halve darkness penalties** (round down); ignore rapid-movement penalties.
  - **Blood**: after **tasting** the prey's blood, know its **exact direction**, any distance. One trail at a time; lost
    on tasting another's blood or after a lunar month.
- **Spirit senses**: **instant action** to send any sense across the Gauntlet (**reflexive for 1 Essence**). Each sense is
  binary (here or there). Sending some but not all → **−2** to Perception/concentration actions and lose wolf-sense penalty
  negation. Can only send the form's **default** senses. **Perception across suffers the Gauntlet modifier.**
  **Spirits in Twilight are sensed normally without focusing, unless the spirit is deliberately hiding** [p. 95].

## 3. Tracking [p. 95]
Skill: **Survival** (wild) or **Streetwise** (urban). Modifiers: strong/weak trail ±3; **−1 per day** old; prey Size 1–3 −1,
4–6 0, 7–9 +1, 10+ +2; prey bleeding +1; **Uratha add PU tracking bonus**.
- **Uncontested**: **Wits + Streetwise/Survival − prey's Streetwise/Survival**, instant. Dramatic fail: **Lost Tracker**;
  fail: lost, may retry; success: will find prey (ST sets time); exceptional: half time or **Invisible Predator**.
- **Contested (prey evading)**: extended & contested, **Wits + Streetwise/Survival vs Resolve + Streetwise/Survival**.
  Hunter needs spoor total = prey's **Resolve + Streetwise/Survival**; **starts with spoor = her Wits**. ~1 roll per hour per
  mile of distance; add form Perception bonus for that hour's main form. Total **−1 per day** (cool mild weather) /
  every 12 h warm dry, 6 h snow, 3 h light rain, 1 h heavy rain. Total 0 → trail lost.
  Results: hunter success +1 (exceptional +2 and **Invisible Predator** if enough); prey success −1 (exceptional −2 and
  **Untraceable** if total ≤0); both fail → either may turn it into a dramatic failure for a Beat; dramatic: hunter **Lost
  Tracker**, prey **Easy Prey**.

## 4. Shapeshifting [pp. 96–98]
| Harmony | To change form |
|---|---|
| 9–10 | **1 Essence + instant action** |
| 7–8 | **1 Essence reflexive**, or **instant action free** |
| 4–6 | **reflexive, free** |
| 2–3 | free; must **spend 1 Essence (reflexive) or an instant action to *avoid* changing** |
| 0–1 | must **spend 1 Essence + instant action to *avoid* changing** |
- Low Harmony (≤3 by the table; text "low-Harmony"): must change shape **at least once per scene**; when **stressed**
  (combat, chase, threat) shifts **one form per turn** toward the appropriate form (flee→Urhan, hide→Hishu, fight→Gauru)
  and **cannot resist**; out of stress may spend Essence to avoid a shift. (Merit Self-Control lets WP resist.)
- High Harmony: change is agonising (first few times "removes consciousness from surroundings").
- **Belongings**: at **Harmony 9+** clothes/gear do **not** shift; below that they meld/stretch as fits.

### The five forms [pp. 96–98]
| Form | Traits | Size | Derived change | Notes |
|---|---|---|---|---|
| **Hishu** (human) | — | 5 | — | Perception +1 (wolf senses). **Sheep's Clothing**: attempts to pick her out of a crowd / pursue through populated areas suffer **−PU**. No Lunacy. |
| **Dalu** (near-human) | Str +1, Sta +1, Man −1 | +1 (6) | Health +2, Speed +1 | **Claws: unarmed attacks do lethal to humans**; in a grapple **bite = lethal** (bite needs grapple). **Defense applies vs Firearms.** Perception +2. **Lunacy, witness +2.** *Badass Motherfucker*: **Presence + PU vs prey's Composure + PU** → crowd/protectors back down or hand over the prey. Can pass for a big human. |
| **Gauru** (war) | Str +3, Dex +1, Sta +2 | +2 (7) | Health +4, Init +1, Speed +4 | **Regenerate all B/L each turn.** Claws **+2L**; bite **+2L, no grapple needed**; bite/claw can establish a grapple and damage; **+3 Initiative when using teeth/claws**. Defense vs Firearms. Perception +3. **Lunacy, witness −2** (text at L11220 duplicated under Urshul column; Gauru is the −2 form per p. 101). **Rage** (below). **Auto-fail Social rolls except Intimidation; auto-fail Mental rolls except Perception/Resistance.** **Primal Fear** (below). **Duration limit** (below). |
| **Urshul** (near-wolf, horse-sized) | Str +2, Dex +2, Sta +2, Man −1 | +1 (6) | Health +3, Init +2, Speed +7 (species factor +3) | Claws **+1L**; bite **+2L, no grapple needed**, bite can establish grapple. Defense vs Firearms. Perception +3. **Lunacy (no modifier).** Speaks First Tongue, not human speech. **Weaken the Prey**: once per scene on damaging with teeth/claws, apply **Arm Wrack, Leg Wrack or Knocked Down** (no targeted attack needed). |
| **Urhan** (wolf) | Dex +2, Sta +1, Man −1 | −1 (4) | Init +2, Speed +5 (species +3) | Bite **+1L**, no grapple needed, can establish grapple. Perception +4. No Lunacy (looks like a wolf). Few First Tongue words only. **Chase Down**: **1 Essence** to pre-empt another character's action with her own (usually an attack), replacing her normal action; can't if she already acted this turn; vs another pre-empter → **Clash of Wills**. In a foot chase, uses **Speed instead of Stamina + Athletics**. |
(Hishu Health = Size 5 + Sta; e.g. Sta 3 → Hishu 8, Dalu 11, Gauru 13, Urshul 12, Urhan 9 — per "Health +N" as printed,
which already includes the Stamina and Size changes.)

**Gauru specifics** [p. 97]:
- **Duration**: can take Gauru **once per scene**, for **(Hishu) Stamina + Primal Urge turns**. Then must shift to Dalu or
  Urshul, or fall into Kuruth: if she doesn't shift, roll **Resolve + Composure** (reflexive): success = one more turn, then
  must shift to Dalu/Urshul **and enters Wasu-Im**; failure = **Basu-Im immediately**.
- **Rage**: must **attack an active opponent in reach each turn** (may switch off a crippled one if others exist); if out of
  reach, move toward/throw things; no opponents → attacks anything in reach. Doing anything else → **Resolve + Composure
  or fall into Kuruth**.
- **Primal Fear**: all **lesser** enemies (most humans, **spirits of lower Rank**, mundane animals) must use **Down and Dirty
  combat** (§12) against her. If they're mixed in with more powerful enemies → normal combat, but opponents add only
  **Dex or Wits (no Athletics) to Defense**.
- Taking Gauru **outside combat** or **staying too long** are general Kuruth triggers.
- **The Predator's Jaws** [p. 98]: an Uratha's **bite in every form counts as a mystical source** for foes vulnerable to
  such (e.g. **Hishu bite does lethal to vampires**).

## 5. Hunter's Aspect [p. 98]
Instant action: **Power Attribute (Str in pursuit / Pre for staredown / Int for outwitting) + Skill (fits the action:
Intimidation, Persuasion, Subterfuge, Stealth, Streetwise, Survival, Brawl, Athletics…) + Auspice Renown**
vs **Composure + Primal Urge** (contested). Success: prey gets the auspice's Condition **for the scene**; exceptional:
lasts **1 day per PU dot** (that expiry gives no Beat). Only **one** hunter's-aspect Condition at a time; further attempts
fail. Works on humans, spirits, Uratha, others (using it on Uratha = insult/grudge).
| Auspice | Aspect | Condition |
|---|---|---|
| Cahalith | Monstrous | **Resigned** |
| Elodoth | Isolating | **Isolated** |
| Irraka | Blissful | **Unaware** |
| Ithaeur | Mystic | **Mystified** |
| Rahu | Dominant | **Swaggering** |

## 6. Renown [pp. 98–100]
Five Renown (1–5): **Cunning** (Irraka, Iron Masters), **Glory** (Cahalith, Blood Talons), **Honor** (Elodoth, Storm Lords),
**Purity** (Rahu, Hunters in Darkness), **Wisdom** (Ithaeur, Bone Shadows). Branded by Lunes as silver runes visible only in
the Hisil. Renown adds to **Gift dice pools** and hunter's aspect; each dot grants a Gift Facet (02).
**Effective spirit Rank by total Renown**: 0–3 → 1; 4–7 → 2; 8–12 → 3; 13–18 → 4; 19+ → 5 [p. 99]. (Matters for Spirit
Howl, Primal Fear, Clash of Wills with spirits, Numina that compare Rank.)
**Display brands**: once per story, **1 Essence** → brands faintly visible in Flesh; pick a Renown → gain its Condition
(**Cunning, Glorious, Honorable, Pure, Wise**; strength = that Renown's rating); invites challenges (respectful among Uratha).
Sample acts per Renown on pp. 99–100 (Cunning: lure prey into trap, trick spirit…; Glory: defeat superior foe, face
overwhelming numbers…; Honor: mediate, submit to judgment, announce attacks…; Purity: sacrifice for the Oath, respect prey,
kill witnesses of exposure, spare enemy Uratha…; Wisdom: deal with dangerous spirit, heal resonance, make fetish, exploit ban…).

## 7. Essence (werewolf) [pp. 100–101]
- **Start 7** (02). Max & per-turn spend by PU (02 table). Can't spend more per turn than PU allows; if a power needs
  more, spend across several turns, it activates when paid.
- **Gain**: touch the heart of a **locus** (Flesh) / eat the strange growths near it (Hisil); **Siskur-Dah** rite → hunt &
  **devour spirits** in the Hisil; **eat human/wolf flesh**: per point of bite damage, may ingest → **+1 Essence** per
  point, wounds become **aggravated**, always **breaking point toward Spirit (−3)** and Oath violation; **destroy a fetish**
  → take its Essence; **first sight of your auspice moon each night → +1 Essence**.
- **Spend**: regenerate lethal (1/turn), speed Reaching (instant cross), shapeshift (Harmony 7–10), Gifts, fetishes,
  spirit senses reflexively, Chase Down, Spirit Howl, brands, etc.
- **Loss**: −1/day without proper food (PU feeding restriction) or past hunt time.

## 8. Reaching & the Gauntlet [pp. 101]
- Normally need a **locus**. Dice pool: **to Shadow: 10 − Harmony**; **to Flesh: Harmony**; + Gauntlet dice modifier +
  circumstances (**reflective surface +1; into Shadow by day −2; into Flesh by day +2**).
- **Harmony ≤3**: no locus needed to enter Shadow. **Harmony ≥8**: no locus needed to enter Flesh. **Harmony 10**: can't
  Reach at all; **Harmony 0**: trapped in the Shadow [p. 104].
- Bodily crossing takes **2 turns per level of Gauntlet strength**; vanish at start, appear at end (safe, can't act).
  **Exceptional success or 1 Essence → instant.**
- **Gauntlet strength / dice modifier** [p. 101]:
| Location | Strength | Dice mod |
|---|---|---|
| Dense urban | 5 | −3 |
| Suburbs, towns | 4 | −2 |
| Small towns, villages | 3 | −1 |
| Wilderness | 2 | 0 |
| Locus | 1 | +2 |
| Verge | 0 | n/a |
The **dice modifier** also applies to: Perception across the Gauntlet (spirit senses), spirits' Reaching Influences/Numina
across, etc. (06).

## 9. Weaknesses [pp. 101–104]
### Silver
- Silver weapons **always deal aggravated** to Uratha. Non-damaging contact = intense pain while touching + scars as from
  agg. Must be real silver, alloys ≥80%. **Silver-coated weapons work for one damaging hit.** Non-weapon silver item =
  improvised weapon. Damage from silver is a **general Kuruth trigger**.
### Lunacy [p. 101–102]
- Trigger: a human sees a werewolf in **Dalu, Gauru or Urshul up close**, or witnesses **shapeshifting** or **regenerating
  (lethal) damage** → **breaking point** (Integrity), rolled at the dramatically appropriate moment.
- Roll: witness's normal breaking-point pool (**Resolve + Composure** + Integrity-based modifier per core) **− werewolf's PU
  Lunacy penalty** (0/−2/−3/−4/−5 by PU) **+2 if Dalu, −2 if Gauru**; prey (vs bystander) is less affected: **+1 if the
  Uratha caused lethal damage to the witness**; **add the witness's wound penalty as a *bonus***.
  Groups: 2 focused on same task **+1** each; small group (≤5) **+2**; large (≤10) **+3**; mob **+4**.
- **Success**: **Guilty, Shaken or Spooked** Condition; **−2 to all actions for the scene**; rationalises.
- **Exceptional**: no Condition/penalty; **regains all Willpower**; remembers clearly.
- **Failure**: **loses 1 Integrity** and gains a Lunacy Condition — **Atavism, Delusion or Reception** (App. 2) — flees or
  panics, then rationalises. If unresolved for **PU days**, it fades with no Beat.
- **Dramatic failure**: becomes **Wolf-Blooded** over the next lunar month (biased to that werewolf's auspice moon).
- **Immune**: Wolf-Blooded, and **anything without Integrity** (vampires, spirits, Uratha, other supernaturals).

## 10. Kuruth — Death Rage [pp. 102–104]
- A **trigger** → **Wasu-Im** (Soft Rage). If in Gauru when triggered, or **takes Gauru** at any point → **Basu-Im**.
- **Wasu-Im**: immediately shift to **Urshul or Dalu**, stay there; under a modified **Gauru Rage** (must attack; doing
  otherwise → Resolve + Composure or Basu-Im). Instead of attacking: **Resolve + Composure** (instant) → each success = 1 turn
  of lucidity; **exceptional success ends Wasu-Im**. Lasts the **Control** time by Harmony (table below), then Basu-Im
  unless ended. May enter Basu-Im voluntarily.
- **Basu-Im**: immediately **Gauru** (even if already used this scene; ignores Gauru time limit) for the **PU Basu-Im
  duration** (02 table). **Ignores wound penalties.** Attempts to influence/intimidate/redirect her (mundane or
  supernatural) suffer **−2×PU** (on top of Supernatural Tolerance). Attacks **everyone** except other werewolves in
  Basu-Im (happily packmates, Wolf-Blooded, humans); no prey → property damage. Afterwards collapses into **Hishu**,
  **no memory**; learning what she did is likely a breaking point **toward Spirit**.
- **Contagion**: werewolf packmates within **10 yards** who see/smell her fall into Basu-Im **after a turn**; resist with
  **Resolve + Composure needing 1 success per character in the scene currently in Kuruth**; re-roll each time another
  packmate falls in.
- **Personal trigger sets** (one chosen at creation; severity by Harmony; personal trigger only **once per night**):
| Set | Passive | Common | Specific |
|---|---|---|---|
| Blood | smell human blood | taste human blood | swallow human blood |
| Moon | auspice moon in the sky | see auspice moon | hear a wolf/werewolf howl while auspice moon is up |
| The Other | within 10 yd of a supernatural creature | witness one doing something obviously inhuman | targeted by a supernatural power |
| Pack | packmate takes lethal | see someone attack a packmate | you cause lethal to a packmate |
| Territory | unknown werewolf enters territory without permission | see unknown werewolf in territory | unknown werewolf challenges the pack's ability to do its duty |
| Wounds | in the area of a Wound | interact with a Wound-born spirit | attacked by a Wound-born spirit |
  Passive = happens regardless of awareness; Common = must perceive it; Specific = rare circumstance.
- **General triggers** (any werewolf, no once-per-night limit): **spending too long in Gauru; taking Gauru outside combat;
  taking damage from silver; forced by an Elodoth** (Darkness Into Light).
- Elodoth can also **cure** Death Rage (08). Controlled Burn Merit modifies Wasu-Im (04).

## 11. Harmony [pp. 104–105]
- 0–10; **10 = locked in Flesh, 0 = locked in Spirit, 5 = balance**. Start **7** (humans who Change start at 9 per text;
  PCs start 7). Replaces Integrity. **No XP** — only breaking points.
- **Breaking point roll: Resolve + Composure** (no Willpower), + listed modifier, + Touchstone bonus (+2 physical vs
  loss, +2 spiritual vs gain; Anchored Merit raises it).
  - **Toward Spirit**: **−1 die per Harmony dot below 5**; **failure → Harmony −1**.
  - **Toward Flesh**: **−1 die per Harmony dot above 5**; **failure → Harmony +1**.
- **Breaking points toward Flesh**: defiling a locus; refusing to participate in Siskur-Dah; staying out of the Hisil a
  week; using a silver weapon on another werewolf; violating the Oath of the Moon (Forsaken only, **−2**); out of the Hisil
  a month (**−3**). *At Harmony ≤3 also*: allowing a spirit safe passage into the physical world; eating processed food;
  mating with a human; out of the Hisil for a day. Plus: exceeding PU hunt time; Self-Control Merit use.
- **Toward Spirit**: killing a human or wolf; staying in the Hisil a week; hunting humans/wolves for food (**−2**); killing
  a packmate (**−2**); eating human/wolf flesh for Essence (**−3**); in the Hisil a month (**−3**). *At Harmony ≥8 also*:
  inflicting Lunacy on a loved one; leading the Siskur-Dah; >2 days away from pack; a full day in the Hisil.
- Player + ST define 1–2 personal breaking points each way from auspice, tribe, Touchstones.
- **Harmony table**:
| Harmony | Bans | Personal Kuruth trigger | Wasu-Im control time |
|---|---|---|---|
| 10 | — | Passive | 3 s |
| 9 | — | Common | 10 s |
| 8 | — | Common | 30 s |
| 7 | — | Specific | 1 min |
| 6 | — | Specific | 5 min |
| 5 | — | none | 15 min |
| 4 | 1 | Specific | 5 min |
| 3 | 1 | Specific | 1 min |
| 2 | 2 | Common | 30 s |
| 1 | 3 | Common | 10 s |
| 0 | 4 | Passive | 3 s |
- **Harmony ≤4**: persistent **Ban Condition(s)** like a spirit's ban (number per table); resolved only by raising Harmony.
- Harmony also sets **shapeshifting cost** (§4) and **Reaching** (§8).

## 12. Core rules as reprinted in WtF Ch4 [pp. 153–178] — werewolf-relevant deltas only
Full core text: `../cod_core/05_systems.md`, equipment `../cod_core/03_equipment.md`. WtF reprint is identical except:
- **Supernatural Tolerance** for Uratha = **Primal Urge**; for spirits = **Rank** [pp. 160, 183]. Contested supernatural
  powers usually add it to the resisting pool.
- **Humans: Virtue (all WP, twice per chapter) / Vice (1 WP, once per scene)**; Uratha use Blood/Bone instead [p. 158].
- **Speed species factors** [p. 159]: turtle 1, toddler 3, **human 5, wolf 8**, caribou 10, horse 12, cheetah 15.
  (Urshul/Urhan get "species factor +3" i.e. 8.)
- Exceptional success → beneficial Condition (usually **Inspired**), may be passed to a packmate [p. 159].
- Unskilled: −3 Mental, −1 Physical/Social. WP: +3 dice or +2 to a resisting trait; one per action.
- **Teamwork**: helpers roll first; each success +1 die to primary; helper dramatic failure → −4 [p. 162].
- Extended actions: max rolls = Attribute + Skill (+Specialty); failure → accept a Condition or lose progress [p. 160].

### Social maneuvering [pp. 163–165]
- Doors = lower of Resolve/Composure; +2 if goal is a breaking point; +1 if it blocks an Aspiration; +1 if against Virtue
  (**or Bone** for werewolves). One Door per successful roll (exceptional: two).
- Impression → time per roll: **Perfect 1 turn, Excellent 1 hour, Good 1 day, Average 1 week, Hostile can't roll**.
  Raise impression: setting, a successful roll, tempting the Vice (**or Blood**), gifts/bribes (Merit use).
- Failure: cumulative −1; ST may drop impression (player takes a Beat). Knowing an Aspiration and offering a path opens a Door.
- **Forcing Doors**: roll − remaining Doors; success opens all, failure burns the target forever.
  **Hard Leverage** (threats, drugging, blackmail): **breaking point toward Flesh**. Removes **2 Doors**, except **vs humans
  only 1 if Harmony ≥8**, and **vs spirits only 1 if Harmony ≤2**. Only with forcing.
- Repeat attempts: after success −1 Door; after failure/Hard Leverage +2 Doors (min 1).
- **Spirits**: need **gathra** before any Door rolls (06 §L).

### Combat deltas [pp. 165–172]
- **Intent**; **Beaten Down** (> Stamina bashing or any lethal → WP to take violent actions) and **Surrender** (gain WP + Beat)
  apply only to those who'd take a breaking point for murder — **most Uratha (and similar killers) ignore surrender without
  penalty and don't get Beaten Down** [p. 165]. If the other side's intent is to kill, victims aren't Beaten Down either.
- **Down and Dirty combat** [p. 165]: whole fight in one contested roll (combat pool vs combat pool or escape pool — Str/Dex
  + Athletics); **Defense ignored**; winner deals damage = difference + weapon and achieves intent (incl. killing);
  exceptional: +1 WP. **Only PCs initiate it.** Gauru's Primal Fear forces it on lesser foes.
- Initiative = 1d10 + Dex + Com (+ weapon penalty; two weapons: largest −1 more). Surprise: Wits + Com vs Dex + Stealth;
  losers lose first turn & Defense.
- Attacks: Str + Brawl − Def; Str + Weaponry − Def; Dex + Firearms; Dex + Athletics − Def (thrown).
- **Defense vs firearms**: **normal humans and Uratha in Hishu or Urhan don't apply Defense vs Firearms**; Dalu, Gauru,
  Urshul do (05 §4). Spirits apply Defense vs all attacks (06).
- Defense −1 per extra attacker; WP +2 Defense vs one attacker. **Dodge**: double Defense rolled as a pool, successes subtract
  (before weapon bonus); multiple opponents reduce Defense first.
- **Bite**: human −1B, only in a grapple (Damage move); wolves +1, shark +4; werewolf forms +0 to +2L (05 §4).
- **Grapple**: grab Str + Brawl − Def; then each turn contested Str + Brawl vs Str + Brawl on the higher Initiative; moves:
  Break Free, Control Weapon, Damage, Disarm, Drop Prone, Hold, Restrain, Take Cover. Touch: Dex + Brawl/Weaponry, no damage.
- Autofire (short +1, medium +2 up to 3 targets, long +3 any), range −1/−2, cover −1/−2/−3, human shields, reloading,
  all-out attack +2 (no Defense), prone (−2 ranged / +2 close vs), specified targets (arm/leg −2 Wrack if dmg > Sta; head −3
  Stun; hand −4; eye −5 Blinded), **Killing Blow** = full pool + weapon vs a helpless target (breaking point for humans).
- All weapon damage is lethal; improvised = Durability − 1, −1 to hit, takes same damage. Armor: ballistic downgrades L→B
  for firearms; general subtracts; lethal attacks vs armor always do ≥1 bashing. Armor piercing.
- **Weapons/armor charts** (p. 169–171): lt revolver 1, hvy revolver 2, lt pistol 1, hvy pistol 2, SMG small 1 / large 2,
  rifle 4, assault rifle 3, shotgun 3 (9-again), crossbow 2; sap 0 (stun), brass knuckles 0, baton 1, crowbar 2, tire iron 1
  (+1 Def), chain 1 (grapple), knife 0, rapier 1, machete 2, hatchet 1, fire ax 3, chainsaw 5, stake 0, spear 2 (+1 Def).
  Armor: reinforced clothing 1/0, Kevlar 1/3, flak 2/4, riot 3/5; leather 2/0, chain 3/1, plate 4/2.

### Injury [pp. 169–172]
- Bashing full → Stamina roll each turn to stay conscious; lethal full → each minute without help upgrade 1 to agg → death.
- **A werewolf in Gauru suffers no wound penalties, no unconsciousness rolls, doesn't bleed out** [p. 169]. **As long as a
  werewolf can regenerate her rightmost box she doesn't bleed out** [p. 171].
- Wound penalties −1/−2/−3 on the last three boxes. Human healing: B 15 min, **L 2 days**, A 1 week per point.
- **Temporary Health** (forms, Warrior's Hide…): boxes added on the right; when lost, damage in them **upgrades** existing
  damage left-to-right (e.g. Dalu 10 boxes with 9 L → Hishu 8 boxes: the extra L upgrades the leftmost L to agg) [p. 172].
- Objects: Durability (1 wood/plastic/glass, 2 stone/aluminium, 3 steel), Structure = Durability + Size; agg ignores Durability.
- Sources of harm: car hits (Dex + Drive + equip − Def; Size + 1 per 20 mph, lethal); disease/drugs Sta + Res;
  poison Sta + Res − Toxicity (each success −1 damage); Extreme environments levels 0–4 (penalty = level; after Stamina hours
  bashing per hour; L3 lethal; L4 lethal per turn after Stamina turns).
- **Tilts** inflicted with B/L damage end when that damage heals; with agg are permanent for humans, regrown by werewolves [p. 178].

## 13. Siskur-Dah (the Sacred Hunt) — see 03 §4 Sacred Hunt rite; grants the **Siskur-Dah** Condition (07), which enables
the 3-dot Moon Gift Facets, Tireless Hunter, etc.

## 14. Wolf-Blooded (uragarum) [App. 1, pp. 296–305; pack rules p. 90]
- Humans with Wolf/Moon heritage (or spontaneous: **dramatic failure on a Lunacy roll**, 05 §9). **Use Integrity, Virtue &
  Vice** (not Harmony / Blood & Bone). **Never suffer Lunacy.** Any Wolf-Blooded may undergo the First Change at any time
  (Luna's choice; can't be triggered). Can learn **Pack Rites** (not Wolf Rites); Horse/Spirit Double/Waystone Tells may
  **lead** Pack Rites.
- **Creation**: as Uratha steps 1–4 & 6 (5/4/3, 11/7/4 for a PC; supporting WB get 15 Skill dots and 5 Merit dots per p. 90),
  **one Tell** (more via the Tell Merit), WB Merits. First Change → loses Tells (and possibly WB Merits); becoming another
  supernatural keeps the Tell.
- **Tells** [pp. 300–304] (flaw / **Boon**): A Wolf's Meat (silver = agg, blocks regen / **regenerates as PU 1; WP to heal
  lethal**) · Anger Issues (a Kuruth trigger; 15 min Wasu-Im & Basu-Im / **Dalu form in both stages with its benefits**) ·
  Bite (−3 to seem innocent / **bite without grapple, +1L**) · Bitten (+3 to track her by scent / blood gives visions of
  werewolf victims) · Clever Fingers (/ **Advanced Action on rituals she leads or assists**) · Devil Inside (/ forceful
  religious iconography → Dalu for the scene) · Evil Eye (/ **WP + Manip + Occult vs Resolve + PU: victim's next named action
  is a dramatic failure** (+Beat), cumulative −1 per reuse) · Exciting (/ sweaty skin contact → both +1 WP; addictive) ·
  Familiar (/ Hursih spirit or small animal follows; first damage point transfers) · Fuck Ugly (no 10-again on first
  impressions / WP: add target's Empathy to later Social actions vs them) · **Horse** (bears spirit's ban dusk–dawn or
  dawn–dusk / **lets Twilight spirits speak through her (not possession, no Fetter); can make herself Resonant or Open to a
  spirit at will**) · Host-Ache (/ senses Hosts within 10 miles; Sta + Survival to track) · Liar's Skin (fur under the skin:
  Lunacy as Urshul / **1/1 armor**) · Marker (/ marks a Safe Place area: Res + Com or Demoralized) · Moon Marked (/ inflict
  that auspice's Hunter's Aspect while the mark shows) · Phantom Pack (/ +2 vs fear; Pack Dynamics w/o drawback) · **Piercing
  Eyes** (/ **always sees Twilight beings — ghosts, spirits, angels**) · Second Skin (live pelt: wear it → Urhan with
  benefits) · Shape-Shifted (Urshul the 3 nights around full moon, causes Lunacy) · Shadow Twin (/ swap places at a locus
  = Reach) · Skinner (/ wear another's skin to look like them) · Spirit Double (/ spirit roams while asleep at ≤½ WP) ·
  Strong Scent (/ −2 to notice anything else about her) · Third Nipple (/ WP + 1 bashing → leak 1 Essence to feed spirits) ·
  Tongues (/ WP: speak First Tongue for a scene) · **Waystone** (/ **is a 1-dot locus for Reaching**; shutting it off needs
  concentration and gives her **Open**) · Wolf Sign (/ untrackable by scent).
- **WB Merits** [pp. 304–305]: tribal affiliate (••, one): Fenris-Ur's Blood (8-again crafting/wielding silver weapons),
  Kamduis-Ur's Blood (Int + Occult: sigil traps a specific ghost for successes hours), Hikaon-Ur's Blood (no darkness
  penalties; +2 to other senses when one is denied), Sagrim-Ur's Blood (+Safe Place & 8-again to Crafts/Computer traps),
  Skolis-Ur's Blood (**immune to Urged**; never forced to show weakness), Ghost Child (9-again on Skills 1–3, no 10-again on
  4–5). Moon birth (••): Crescent (+3 Durability/Structure to fetishes she helps make), Full (WP + instant: Presence-many
  allies get +3 and 8-again on a pre-planned coordinated action), Gibbous (8-again & half time on one Mental Skill), Half
  (needs Safe Place 1: +2 breaking points in territory; once/chapter add Safe Place & 8-again), No Moon (untraceable spy on
  assigned missions). General: **Pack Bond** (• may buy Totem 1; ••• up to Totem 5), **Raised by Wolves** (•: no Com/Sta/Res
  rolls needed to withstand the mystical or biologically strange), **Tell** (•••: second Tell; humans may buy with XP to
  become WB).

## 15. Optional rules from Ch7 [pp. 284–295]
- **Primal Urge hack** [p. 286]: any time, swap a dice pool (after modifiers) for **3 + PU**; then must roll to resist
  Kuruth and mark a box above a PU dot; with the track full, no resistance roll.
- Blood/Bone hidden-archetype guessing (+/−3 dice); rite trappings +1/+2 dice per peculiar implement; sensory Beats [p. 286].
- **The Father's Form** discussion [p. 288]: groups may grant the Facet free or let all Gauru be rage-free.
- **First Change story & Tension pool** [pp. 290–291]: pre-Change WB teens; Tension = 10 − Willpower; stress → accept +1
  Tension and a Beat (ST rolls Tension vs Resolve + Composure; win → the Change/blackout) or take a Condition. Choosing to
  stay WB = Integrity breaking point as dramatic failure + second Tell.
- **Putting It On the Line** [pp. 292–294]: index cards of things the character loves; the ST may black-out a Death Rage and
  destroy a carded thing; putting another card on the line = free Willpower benefit.
- **Pregnancy Conditions** [p. 295]: First Trimester (−1 Init & Stamina rolls; +1 WP from ≥4 h sleep), Second (+1 Stamina; −2
  extended actions), Third (+1 Wits & Composure rolls; −1 Dex & Resolve) — all Persistent, Beat per milestone.
