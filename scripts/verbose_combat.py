#!/usr/bin/env python3
"""
Verbose combat trace: Mortal Policeman (id=105) vs Daeva Celerity Bruiser (id=201).
Prints initiative setup, then for each action: actor, action type, dice pool breakdown,
and observed outcome (health/resource deltas).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from cod_sim import BuildRegistry
from cod_sim.cod_sim import CombatEnv

# ─── Action space constants (must match action.rs) ────────────────────────────
MAX_TARGETS       = 8
MAX_POWER_SLOTS   = 8
ALL_OUT_OFFSET    = MAX_TARGETS * 2           # 16
POWER_OFFSET      = MAX_TARGETS * 4           # 32
RES_PHYS_OFFSET   = POWER_OFFSET + MAX_POWER_SLOTS * MAX_TARGETS  # 96
HEAL_OFFSET       = RES_PHYS_OFFSET + 3       # 99
REGEN_OFFSET      = HEAL_OFFSET + 1           # 100
FULL_DEF_OFFSET   = REGEN_OFFSET + 1          # 101
PASS_OFFSET       = FULL_DEF_OFFSET + 1       # 102
IRON_SKIN_OFFSET  = PASS_OFFSET + 1           # 103
BITE_OFFSET       = IRON_SKIN_OFFSET + 1      # 104

VAMP_POWER_NAMES = {
    0: "Celerity (extra action)",
    1: "Vigor (attack bonus + extra action)",
    2: "Resilience (armor)",
    3: "Protean (claws)",
    4: "Nightmare (frighten)",
    5: "Dominate (mesmerize)",
}
PHYS_ATTR_NAMES = ["Strength", "Dexterity", "Stamina"]


def decode_action(idx):
    """Returns dict with keys: kind, target, spend_wp, power_slot, attribute."""
    if idx < ALL_OUT_OFFSET:
        return {"kind": "Attack",         "target": idx // 2, "spend_wp": bool(idx % 2)}
    if idx < POWER_OFFSET:
        rel = idx - ALL_OUT_OFFSET
        return {"kind": "AllOutAttack",   "target": rel // 2, "spend_wp": bool(rel % 2)}
    if idx < RES_PHYS_OFFSET:
        rel = idx - POWER_OFFSET
        return {"kind": "ActivatePower",  "target": rel % MAX_TARGETS, "power_slot": rel // MAX_TARGETS}
    if idx < HEAL_OFFSET:
        return {"kind": "SpendPhysical",  "attribute": idx - RES_PHYS_OFFSET}
    if idx == HEAL_OFFSET:   return {"kind": "HealWithVitae"}
    if idx == REGEN_OFFSET:  return {"kind": "RegenerateEssence"}
    if idx == FULL_DEF_OFFSET: return {"kind": "FullDefense"}
    if idx == PASS_OFFSET:   return {"kind": "Pass"}
    if idx == IRON_SKIN_OFFSET: return {"kind": "IronSkinDowngrade"}
    if BITE_OFFSET <= idx < BITE_OFFSET + MAX_TARGETS * 2:
        rel = idx - BITE_OFFSET
        return {"kind": "Bite", "target": rel // 2, "spend_wp": bool(rel % 2)}
    return {"kind": "Pass"}


# ─── Pool calculator (mirrors combat.rs resolve_attack) ───────────────────────

def wound_penalty(bashing, lethal, aggravated, max_hp, iron_stamina=0):
    total = bashing + lethal + aggravated
    if total == 0:
        return 0
    third_to_last = max(max_hp - 3, 0)
    second_to_last = max(max_hp - 2, 0)
    last = max(max_hp - 1, 0)
    if total > last:
        raw = -3
    elif total > second_to_last:
        raw = -2
    elif total > third_to_last:
        raw = -1
    else:
        raw = 0
    return max(raw + iron_stamina, -3 if iron_stamina == 0 else raw + iron_stamina)


def defense_base(bd):
    """Compute defense base from Python BuildDefinition (mirrors character.rs base_defense + celerity)."""
    if bd.street_fighting > 0:
        def_attr = max(bd.dexterity, bd.wits)
    else:
        def_attr = min(bd.dexterity, bd.wits)

    if bd.defensive_combat > 0:
        def_skill = max(bd.brawl, bd.weaponry)
    elif bd.brawling_dodge > 0:
        def_skill = bd.brawl
    else:
        def_skill = bd.athletics

    base = def_attr + def_skill
    # Celerity persistent defense bonus (VtR 2e)
    if bd.splat == "vampire":
        base += bd.celerity
    return base


def format_attack_pool(actor_bd, target_bd, spend_wp, all_out,
                       actor_state, target_state, vigor_bonus=0):
    """
    Return (pool_int, breakdown_str).
    actor_state / target_state: dicts from get_state_summary characters.
    vigor_bonus: dice bonus from active Vigor (if spent same turn).
    """
    parts = []

    # Base pool
    if actor_bd.weapon_is_ranged:
        base = actor_bd.dexterity + actor_bd.firearms
        parts.append(f"Dex({actor_bd.dexterity}) + Firearms({actor_bd.firearms})")
    elif actor_bd.fighting_finesse:
        skill = max(actor_bd.brawl, actor_bd.weaponry)
        base = actor_bd.dexterity + skill
        parts.append(f"Dex({actor_bd.dexterity}) + max(Brawl,Wpn)({skill}) [Finesse]")
    else:
        skill = max(actor_bd.brawl, actor_bd.weaponry)
        base = actor_bd.strength + skill
        parts.append(f"Str({actor_bd.strength}) + max(Brawl,Wpn)({skill})")

    pool = base

    # Willpower
    if spend_wp:
        pool += 3
        parts.append("+3 WP")

    # All-Out Attack
    if all_out:
        pool += 2
        parts.append("+2 AllOut")

    # Vigor bonus
    if vigor_bonus:
        pool += vigor_bonus
        parts.append(f"+{vigor_bonus} Vigor")

    # Wound penalty (actor)
    wp_pen = wound_penalty(
        actor_state["bashing"], actor_state["lethal"], actor_state["aggravated"],
        actor_state["max_health"], actor_bd.iron_stamina
    )
    if wp_pen:
        pool += wp_pen
        parts.append(f"{wp_pen} wound")

    # Defense (melee only) or Celerity penalty (ranged vs vampire)
    if not actor_bd.weapon_is_ranged:
        tdef = target_state.get("_defense_remaining", defense_base(target_bd))
        pool -= tdef
        parts.append(f"-{tdef} Def")
    elif target_bd.splat == "vampire" and target_bd.celerity:
        pool -= target_bd.celerity
        parts.append(f"-{target_bd.celerity} Celerity(firearms)")

    # Damage info
    dmg_type = actor_bd.weapon_damage_type
    if target_bd.splat == "vampire":
        if not actor_bd.weapon_is_ranged:
            dmg_type = "bashing"  # melee → bashing to vampires
    dmg_mod = actor_bd.weapon_damage_mod
    # Martial Arts Touch of Death
    if not actor_bd.weapon_is_ranged and actor_bd.martial_arts >= 5:
        dmg_mod += 2

    breakdown = " | ".join(parts)
    return pool, breakdown, f"dmg+{dmg_mod} {dmg_type}"


# ─── State helpers ────────────────────────────────────────────────────────────

def hp_str(s):
    b, l, a = s["bashing"], s["lethal"], s["aggravated"]
    total = b + l + a
    return f"{s['max_health'] - total}/{s['max_health']} hp (B{b}/L{l}/A{a})"


def resource_label(bd):
    if bd.splat == "vampire":   return "Vitae"
    if bd.splat == "werewolf":  return "Essence"
    if bd.splat == "changeling": return "Glamour"
    return "Resource"


def delta_str(before, after, label):
    d = after - before
    if d == 0:
        return ""
    sign = "+" if d > 0 else ""
    return f"{label}{sign}{d}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(seed: int = 42, use_policy: bool = False):
    BUILDS_DIR = ROOT / "builds"
    reg = BuildRegistry()
    reg.load_directory(BUILDS_DIR)

    BID_A = 105   # Mortal Policeman
    BID_B = 201   # Daeva Celerity Bruiser

    bd = {0: reg.get(BID_A), 1: reg.get(BID_B)}

    print("=" * 70)
    print(f"  COMBAT: {bd[0].name}  vs  {bd[1].name}")
    print(f"  Seed: {seed}")
    print("=" * 70)
    print()
    for i, b in bd.items():
        res_label = resource_label(b)
        print(f"[{i}] {b.name} ({b.splat.upper()})")
        if b.splat == "vampire":
            print(f"     Str{b.strength}/Dex{b.dexterity}/Sta{b.stamina}  "
                  f"Brawl{b.brawl}/Wpn{b.weaponry}/Fire{b.firearms}/Ath{b.athletics}")
            print(f"     Celerity{b.celerity}/Vigor{b.vigor}/Resilience{b.resilience}  "
                  f"BP{b.blood_potency}  {res_label}_max={b.max_resource}")
            print(f"     Weapon: {b.raw['weapon'].get('name','?')}  dmg{b.weapon_damage_mod:+d} "
                  f"{b.weapon_damage_type}  init{b.weapon_initiative_penalty:+d}  "
                  f"ranged={b.weapon_is_ranged}")
        elif b.splat == "mortal":
            print(f"     Str{b.strength}/Dex{b.dexterity}/Sta{b.stamina}  "
                  f"Brawl{b.brawl}/Wpn{b.weaponry}/Fire{b.firearms}/Ath{b.athletics}")
            merits_str = ", ".join(f"{k}:{v}" for k, v in b.merits.items())
            print(f"     Merits: {merits_str}")
            print(f"     Weapon: {b.raw['weapon'].get('name','?')}  dmg{b.weapon_damage_mod:+d} "
                  f"{b.weapon_damage_type}  init{b.weapon_initiative_penalty:+d}  "
                  f"ranged={b.weapon_is_ranged}")
            print(f"     Armor: general={b.armor_general}  ballistic={b.armor_ballistic}")
        print(f"     HP={b.max_health}  WP={b.max_willpower}  DefBase={defense_base(b)}")
        ini_mod = b.dexterity + b.composure + b.fast_reflexes + b.weapon_initiative_penalty
        if b.splat == "vampire" and b.celerity >= 1:
            # Celerity 1: Perfected Accelerant — +Celerity to initiative... wait, actually
            # let me check character.rs from_build_and_team for the exact formula
            pass
        print(f"     InitMod: Dex({b.dexterity})+Com({b.composure})+FastRef({b.fast_reflexes})"
              f"+WpnInit({b.weapon_initiative_penalty}) = {ini_mod}")
    print()

    # Policy (optional)
    policy = None
    if use_policy:
        from cod_sim import checkpoint as ckpt_mod
        from cod_sim.cod_sim import ACTION_SPACE_SIZE
        ckpt = ckpt_mod.latest_checkpoint(ROOT / "checkpoints")
        if ckpt:
            loaded, _, _ = ckpt_mod.load(ckpt)
            if loaded.action_size == ACTION_SPACE_SIZE:
                import torch
                policy = loaded
                policy.eval()
                print(f"[policy] loaded from {ckpt.name}\n")
            else:
                print(f"[policy] stale checkpoint (action_size mismatch) — using first-legal\n")

    # Build env
    builds_json = reg.builds_json([BID_A, BID_B])
    env = CombatEnv(builds_json, [0, 1])
    obs_list, _ = env.reset(seed=seed)

    # Per-character defense tracking
    char_names = [bd[0].name, bd[1].name]
    builds_by_idx = [bd[0], bd[1]]

    # Initialize defense tracking from base values
    def_remaining = [defense_base(builds_by_idx[0]), defense_base(builds_by_idx[1])]

    # Per-character active bonuses (reset each turn)
    vigor_bonus = [0, 0]

    prev_summary = env.get_state_summary()
    prev_turn = prev_summary["turn"]

    print(f"--- Initiative ---")
    for i, ch in enumerate(prev_summary["characters"]):
        print(f"  {ch['name']}: {ch['initiative']:+d}")
    print()

    step = 0
    MAX_STEPS = 200
    done = False

    while not done and step < MAX_STEPS:
        summary = env.get_state_summary()
        cur_turn = summary["turn"]
        actor_idx = env.current_actor_idx()
        chars = summary["characters"]

        # Detect turn boundary — reset defense and bonuses
        if cur_turn != prev_turn:
            print(f"\n{'='*40}")
            print(f"  TURN {cur_turn}")
            print(f"{'='*40}")
            def_remaining = [defense_base(builds_by_idx[i]) for i in range(2)]
            vigor_bonus = [0, 0]
            prev_turn = cur_turn

        # Inject defense_remaining into state so pool calc can use it
        for i in range(2):
            chars[i]["_defense_remaining"] = def_remaining[i]

        actor_bd = builds_by_idx[actor_idx]
        actor_name = char_names[actor_idx]
        actor_state = chars[actor_idx]

        # Choose action
        mask = env.action_mask()
        if policy is not None:
            import torch
            obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
            mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                acts, _, _ = policy.act(obs_t, mask_t)
            action_idx = int(acts[0])
        else:
            action_idx = next(i for i, m in enumerate(mask) if m)

        act = decode_action(action_idx)

        step += 1
        prefix = f"  [Step {step:2d}] {actor_name}"

        # ── Describe action and compute pool ──────────────────────────────────
        if act["kind"] in ("Attack", "AllOutAttack"):
            t = act["target"]
            if t >= len(char_names):
                t = 0
            tgt_name = char_names[t]
            tgt_bd = builds_by_idx[t]
            tgt_state = chars[t]

            all_out = act["kind"] == "AllOutAttack"
            spend_wp = act.get("spend_wp", False)

            pool, breakdown, dmg_info = format_attack_pool(
                actor_bd, tgt_bd, spend_wp, all_out,
                actor_state, tgt_state, vigor_bonus[actor_idx]
            )

            wp_tag = " +WP" if spend_wp else ""
            aoa_tag = " [ALL-OUT, Defense→0]" if all_out else ""
            print(f"{prefix} → {act['kind']} {tgt_name}{wp_tag}{aoa_tag}")
            print(f"          Pool: {breakdown}")
            print(f"          Dice: {pool} dice | {dmg_info}")

            if all_out:
                def_remaining[actor_idx] = 0

        elif act["kind"] == "ActivatePower":
            slot = act.get("power_slot", 0)
            if actor_bd.splat == "vampire":
                pname = VAMP_POWER_NAMES.get(slot, f"power slot {slot}")
                print(f"{prefix} → Activate {pname}")
                # Track vigor bonus for next attack this turn
                if slot == 1:  # Vigor active
                    vigor_bonus[actor_idx] = actor_bd.vigor
                    print(f"          (spends 1 Vitae → +{actor_bd.vigor} dice on attacks this turn)")
                elif slot == 0:  # Celerity active
                    print(f"          (spends 1 Vitae → gains 1 extra action)")
                elif slot == 2:  # Resilience active
                    print(f"          (spends 1 Vitae → {actor_bd.resilience+1} armor this turn)")
            else:
                print(f"{prefix} → Activate power slot {slot}")

        elif act["kind"] == "SpendPhysical":
            attr = act.get("attribute", 0)
            aname = PHYS_ATTR_NAMES[attr] if attr < 3 else f"attr{attr}"
            print(f"{prefix} → Spend Resource for +2 {aname} dice")

        elif act["kind"] == "HealWithVitae":
            print(f"{prefix} → Heal with Vitae (1 Vitae → 2B or 1L healed)")

        elif act["kind"] == "FullDefense":
            new_def = defense_base(actor_bd) * 2
            def_remaining[actor_idx] = new_def
            print(f"{prefix} → Full Defense (defense → {new_def})")

        elif act["kind"] == "Pass":
            print(f"{prefix} → Pass")

        elif act["kind"] == "Bite":
            t = act.get("target", 0)
            if t >= len(char_names): t = 0
            tgt_name = char_names[t]
            tgt_bd = builds_by_idx[t]
            tgt_state = chars[t]
            spend_wp = act.get("spend_wp", False)
            pool = (actor_bd.strength + actor_bd.brawl
                    + (3 if spend_wp else 0)
                    + wound_penalty(actor_state["bashing"], actor_state["lethal"],
                                    actor_state["aggravated"], actor_state["max_health"],
                                    actor_bd.iron_stamina)
                    - tgt_state.get("_defense_remaining", defense_base(tgt_bd)))
            wp_tag = " +WP" if spend_wp else ""
            print(f"{prefix} → Bite {tgt_name}{wp_tag} (Lethal + 1 Vitae drain)")
            print(f"          Pool: Str({actor_bd.strength})+Brawl({actor_bd.brawl})"
                  f"-Def({tgt_state.get('_defense_remaining', defense_base(tgt_bd))}) = {pool} dice | dmg+0 lethal + Vitae")

        elif act["kind"] == "IronSkinDowngrade":
            print(f"{prefix} → Iron Skin (spend 1 WP: downgrade lethal→bashing)")

        else:
            print(f"{prefix} → {act['kind']}")

        # ── Execute step ──────────────────────────────────────────────────────
        obs_list, _, terminated, truncated, _ = env.step(action_idx)
        done = terminated or truncated

        # ── Observe outcome ───────────────────────────────────────────────────
        new_summary = env.get_state_summary()
        new_chars = new_summary["characters"]

        deltas = []
        for i in range(len(chars)):
            old = chars[i]
            new = new_chars[i]
            name = char_names[i]

            # Health delta — also catch overflow conversions (B→L, L→A) where total is unchanged
            old_dmg = old["bashing"] + old["lethal"] + old["aggravated"]
            new_dmg = new["bashing"] + new["lethal"] + new["aggravated"]
            health_changed = (new["bashing"] != old["bashing"] or
                              new["lethal"] != old["lethal"] or
                              new["aggravated"] != old["aggravated"])
            if health_changed:
                bD = new["bashing"] - old["bashing"]
                lD = new["lethal"] - old["lethal"]
                aD = new["aggravated"] - old["aggravated"]
                parts = []
                if bD > 0: parts.append(f"+{bD}B")
                if lD > 0: parts.append(f"+{lD}L")
                if aD > 0: parts.append(f"+{aD}A")
                if bD < 0 and new_dmg >= old_dmg: parts.append(f"{abs(bD)}B→L/A overflow")
                elif bD < 0: parts.append(f"{bD}B healed")
                if lD < 0 and aD >= 0 and new_dmg >= old_dmg: parts.append(f"{abs(lD)}L→A overflow")
                elif lD < 0: parts.append(f"{lD}L healed")
                if aD < 0: parts.append(f"{aD}A healed")
                hp_rem = new["max_health"] - new_dmg
                incap_tag = " [INCAPACITATED]" if new["is_incapacitated"] else ""
                torpor_tag = " [TORPOR]" if new.get("in_torpor") else ""
                deltas.append(f"  → {name}: {','.join(parts)}  [{hp_rem}/{new['max_health']} hp]{incap_tag}{torpor_tag}")

            # Resource delta
            r_old, r_new = old["resource"], new["resource"]
            if r_new != r_old:
                rl = resource_label(builds_by_idx[i])
                deltas.append(f"  → {name}: {rl} {r_old}→{r_new}")

            # Willpower delta
            w_old, w_new = old["willpower"], new["willpower"]
            if w_new != w_old:
                deltas.append(f"  → {name}: WP {w_old}→{w_new}")

        # Update defense tracking after melee attack or bite
        if act["kind"] in ("Attack", "AllOutAttack") and not actor_bd.weapon_is_ranged:
            t = act.get("target", 0)
            if t < 2 and def_remaining[t] > 0:
                def_remaining[t] -= 1
        elif act["kind"] == "Bite":
            t = act.get("target", 0)
            if t < 2 and def_remaining[t] > 0:
                def_remaining[t] -= 1

        if deltas:
            for d in deltas:
                print(d)
        else:
            if act["kind"] in ("Attack", "AllOutAttack"):
                print("  → Miss (no damage dealt)")

        prev_summary = new_summary

    # ── Final result ──────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    final = env.get_state_summary()
    winner = final.get("winner_team")
    if winner is not None:
        wname = bd[winner].name
        print(f"  RESULT: {wname} (team {winner}) WINS  |  {step} steps, turn {final['turn']}")
    else:
        print(f"  RESULT: DRAW / timeout  |  {step} steps, turn {final['turn']}")
    print()
    for i, ch in enumerate(final["characters"]):
        status = "INCAPACITATED" if ch["is_incapacitated"] else "alive"
        b = builds_by_idx[i]
        rl = resource_label(b)
        print(f"  {ch['name']}: {hp_str(ch)}  WP={ch['willpower']}  {rl}={ch['resource']}  [{status}]")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--policy", action="store_true", help="Use trained policy instead of first-legal")
    args = p.parse_args()
    main(seed=args.seed, use_policy=args.policy)
