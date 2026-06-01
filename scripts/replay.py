#!/usr/bin/env python3
"""Combat replay — run a single fight and print a turn-by-turn log.

This script is intended for debugging and rule verification.  It has NO
effect on training speed: the Rust simulation core contains no logging code;
all output is produced at the Python level only when this script is run.

Usage examples
--------------
# Celerity Bruiser vs Iron Master, using random-legal-action policy:
    .venv/bin/python scripts/replay.py --build-a 201 --build-b 301

# Same fight with the trained policy:
    .venv/bin/python scripts/replay.py --build-a 201 --build-b 301 --policy

# 3-fighter free-for-all (two builds on one team vs one build):
    .venv/bin/python scripts/replay.py --team0 201 202 --team1 301

# List available build IDs:
    .venv/bin/python scripts/replay.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cod_sim.build_registry import BuildRegistry
from cod_sim import checkpoint as ckpt_mod

BUILDS_DIR = Path(__file__).resolve().parent.parent / "builds"

# ─── Formatting helpers ───────────────────────────────────────────────────────

_SPLAT_ABBR = {
    "mortal": "Mortal",
    "vampire": "Vamp",
    "werewolf": "Wolf",
    "changeling": "Fae",
}

def _hp_bar(bashing: int, lethal: int, agg: int, max_hp: int) -> str:
    """Visual health bar: A=aggravated, L=lethal, B=bashing, ○=empty."""
    bar = "A" * agg + "L" * lethal + "B" * bashing + "○" * (max_hp - agg - lethal - bashing)
    return f"[{bar}]"


def _char_line(ch: dict, *, prefix: str = "  ") -> str:
    name     = ch["name"]
    hp_bar   = _hp_bar(ch["bashing"], ch["lethal"], ch["aggravated"], ch["max_health"])
    hp_nums  = f"{ch['max_health'] - ch['bashing'] - ch['lethal'] - ch['aggravated']}/{ch['max_health']}"
    resource = f"  res={ch['resource']}" if ch["resource"] > 0 else ""
    wp       = f"  wp={ch['willpower']}"
    status   = "  [INCAP]" if ch["is_incapacitated"] else ""
    torpor   = "  [TORPOR]" if ch.get("in_torpor") else ""
    return f"{prefix}{name:30s} {hp_bar} hp={hp_nums}{resource}{wp}{status}{torpor}"


def _diff_health(before: dict, after: dict) -> str:
    """Show damage taken / healed between two snapshots."""
    parts: list[str] = []
    for dtype in ("aggravated", "lethal", "bashing"):
        delta = after[dtype] - before[dtype]
        if delta > 0:
            parts.append(f"+{delta}{dtype[0].upper()}")
        elif delta < 0:
            parts.append(f"{delta}{dtype[0].upper()} healed")
    if after["is_incapacitated"] and not before["is_incapacitated"]:
        parts.append("→ INCAPACITATED")
    if after.get("in_torpor") and not before.get("in_torpor"):
        parts.append("→ TORPOR")
    return ", ".join(parts) if parts else "(no change)"


# ─── Main replay logic ────────────────────────────────────────────────────────

def run_replay(
    builds: list,
    teams: list[int],
    policy,
    seed: int,
    max_steps: int = 1000,
) -> None:
    """Step through a combat and print a verbose turn-by-turn log."""
    import torch
    from cod_sim.cod_sim import CombatEnv
    from cod_sim.api.combat_runner import _describe_action

    build_names  = [b.name  for b in builds]
    build_splats = [b.splat for b in builds]
    builds_json  = "[" + ",".join(b.to_rust_json() for b in builds) + "]"

    if seed is not None:
        torch.manual_seed(seed)

    env = CombatEnv(builds_json, teams)
    obs_list, _ = env.reset(seed=seed)

    # ─── Header ───────────────────────────────────────────────────────────────
    sep = "═" * 72
    print(sep)
    team0 = [builds[i].name for i, t in enumerate(teams) if t == 0]
    team1 = [builds[i].name for i, t in enumerate(teams) if t == 1]
    print(f"  COMBAT: Team 0 [{', '.join(team0)}]  vs  Team 1 [{', '.join(team1)}]")
    policy_label = "trained policy" if policy is not None else "random-legal-action"
    print(f"  Seed: {seed}   Policy: {policy_label}")
    print(sep)

    # ─── Initial state ────────────────────────────────────────────────────────
    init_summary = env.get_state_summary()
    print("\nINITIATIVE ORDER:")
    chars_by_ini = sorted(
        init_summary["characters"],
        key=lambda c: c["initiative"],
        reverse=True,
    )
    for ch in chars_by_ini:
        print(f"  {ch['name']:30s}  ini={ch['initiative']}  team={ch['team']}")
    print()

    step       = 0
    done       = False
    prev_turn  = 0

    while not done and step < max_steps:
        summary    = env.get_state_summary()
        turn       = summary["turn"]
        actor_idx  = env.current_actor_idx()
        chars_pre  = {ch["name"]: ch for ch in summary["characters"]}
        is_werewolf = {ch["name"]: build_splats[i] == "werewolf"
                       for i, ch in enumerate(summary["characters"])}

        if turn != prev_turn:
            prev_turn = turn
            print(f"{'━'*72}")
            print(f"  TURN {turn}")
            print(f"{'━'*72}")
            for ch in summary["characters"]:
                print(_char_line(ch))
            print()

        actor_name  = build_names[actor_idx]
        actor_splat = _SPLAT_ABBR.get(build_splats[actor_idx], build_splats[actor_idx])
        actor_team  = teams[actor_idx]

        # Select action
        mask = env.action_mask()
        if policy is not None:
            import torch
            obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
            mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                acts, _, _ = policy.act(obs_t, mask_t)
            action = int(acts[0])
        else:
            action = next(i for i, m in enumerate(mask) if m)

        action_desc = _describe_action(action, actor_name, build_splats[actor_idx], build_names)
        print(f"  Step {step+1:3d} | [{actor_splat}] {actor_name} (team {actor_team})")
        print(f"           → {action_desc}")

        obs_list, _, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        step += 1

        # Show health changes.
        # NOTE: on_turn_start() fires inside env.step() when the initiative
        # order wraps — werewolf passive regeneration appears here on the last
        # step of each turn.  Changes on the actor's own health from regen are
        # labelled "(regen)" to distinguish them from action-based effects.
        post_summary = env.get_state_summary()
        turn_changed = post_summary["turn"] != turn
        for ch_after in post_summary["characters"]:
            ch_before = chars_pre.get(ch_after["name"])
            if ch_before is None:
                continue
            diff = _diff_health(ch_before, ch_after)
            if diff == "(no change)":
                continue
            # Annotate passive regen that happened at turn rollover
            regen_note = ""
            if turn_changed and is_werewolf.get(ch_after["name"], False):
                b_healed = ch_before["bashing"] - ch_after["bashing"]
                l_healed = ch_before["lethal"]  - ch_after["lethal"]
                if b_healed > 0 or l_healed > 0:
                    regen_note = " (incl. regen)"
            print(f"           ✦ {ch_after['name']}: {diff}{regen_note}")
            hp_bar = _hp_bar(
                ch_after["bashing"], ch_after["lethal"],
                ch_after["aggravated"], ch_after["max_health"],
            )
            hp_rem = ch_after["max_health"] - ch_after["bashing"] - ch_after["lethal"] - ch_after["aggravated"]
            print(f"             {hp_bar} ({hp_rem}/{ch_after['max_health']})")
        print()

    # ─── Final result ─────────────────────────────────────────────────────────
    final = env.get_state_summary()
    print(sep)
    wt = final.get("winner_team")
    if wt is None:
        print("  RESULT: Draw (turn limit reached)")
    else:
        winner_names = [builds[i].name for i, t in enumerate(teams) if t == wt]
        print(f"  RESULT: Team {wt} wins ({', '.join(winner_names)}) on turn {final['turn']}, {step} steps")
    print()
    print("Final character states:")
    for ch in final["characters"]:
        print(_char_line(ch, prefix="  "))
    print(sep)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a single combat and print a detailed turn-by-turn log.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Simple 1v1 shortcuts
    p.add_argument("--build-a", type=int, metavar="ID",
                   help="Build ID for team 0 fighter (1v1 shorthand)")
    p.add_argument("--build-b", type=int, metavar="ID",
                   help="Build ID for team 1 fighter (1v1 shorthand)")
    # Multi-fighter teams
    p.add_argument("--team0", type=int, nargs="+", metavar="ID",
                   help="One or more build IDs for team 0")
    p.add_argument("--team1", type=int, nargs="+", metavar="ID",
                   help="One or more build IDs for team 1")
    # Options
    p.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    p.add_argument("--policy", action="store_true",
                   help="Use the trained policy instead of random-legal-action")
    p.add_argument("--checkpoint-dir", default="checkpoints",
                   help="Checkpoint directory (default: checkpoints)")
    p.add_argument("--builds-dir", default=str(BUILDS_DIR),
                   help="Builds directory (default: builds/)")
    p.add_argument("--max-steps", type=int, default=1000,
                   help="Safety cap on total steps (default: 1000)")
    p.add_argument("--list", action="store_true",
                   help="List available build IDs and exit")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    reg = BuildRegistry()
    reg.load_directory(args.builds_dir)

    if args.list:
        print("Available builds:")
        print(f"  {'ID':>5}  {'Splat':12s}  {'Name'}")
        print(f"  {'─'*5}  {'─'*12}  {'─'*40}")
        for b in sorted(reg.all_builds(), key=lambda x: x.id):
            print(f"  {b.id:>5}  {b.splat:12s}  {b.name}")
        return

    # Assemble combatant list and team assignments
    team0_ids: list[int] = []
    team1_ids: list[int] = []

    if args.team0 or args.team1:
        team0_ids = list(args.team0 or [])
        team1_ids = list(args.team1 or [])
    elif args.build_a is not None and args.build_b is not None:
        team0_ids = [args.build_a]
        team1_ids = [args.build_b]
    else:
        # Default: first two builds, one per team
        ids = reg.all_ids()
        if len(ids) < 2:
            print("ERROR: need at least 2 builds. Use --list to see available IDs.")
            sys.exit(1)
        team0_ids = [ids[0]]
        team1_ids = [ids[1]]
        print(f"No builds specified — using {ids[0]} vs {ids[1]} (use --build-a/--build-b to choose).\n")

    all_ids = team0_ids + team1_ids
    try:
        builds = [reg.get(bid) for bid in all_ids]
    except KeyError as exc:
        print(f"ERROR: unknown build ID {exc}. Use --list to see available builds.")
        sys.exit(1)
    teams = [0] * len(team0_ids) + [1] * len(team1_ids)

    # Load policy if requested
    policy = None
    if args.policy:
        ckpt_path = ckpt_mod.latest_checkpoint(args.checkpoint_dir)
        if ckpt_path is None:
            print(f"WARNING: no checkpoint found in '{args.checkpoint_dir}' — falling back to random-legal-action.\n")
        else:
            policy, _, step = ckpt_mod.load(ckpt_path)
            policy.eval()
            print(f"Loaded policy from {ckpt_path} (step {step:,})\n")

    run_replay(builds, teams, policy, seed=args.seed, max_steps=args.max_steps)


if __name__ == "__main__":
    main()
