#!/usr/bin/env python3
"""Rating tournament: compute Glicko-2 ratings for all builds using the trained policy.

Usage:
    .venv/bin/python scripts/rate_builds.py [options]

Examples:
    # Quick run (3 full round-robins)
    .venv/bin/python scripts/rate_builds.py --rounds 3

    # Full run (10 round-robins, stable ratings)
    .venv/bin/python scripts/rate_builds.py --rounds 10

    # Save ratings and display leaderboard
    .venv/bin/python scripts/rate_builds.py --rounds 5 --save ratings.json
"""

import argparse
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cod_sim.build_registry import BuildRegistry
from cod_sim.cod_sim import CombatEnv
from cod_sim.glicko import GlickoRater
from cod_sim.matchmaker import Matchmaker
from cod_sim import checkpoint as ckpt_mod

BUILDS_DIR = Path(__file__).resolve().parent.parent / "builds"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a Glicko-2 rating tournament")
    p.add_argument("--rounds", type=int, default=5,
                   help="Full round-robins to run (default: 5)")
    p.add_argument("--checkpoint-dir", type=str, default="checkpoints",
                   help="Directory containing the policy checkpoint (default: checkpoints)")
    p.add_argument("--builds-dir", type=str, default=str(BUILDS_DIR))
    p.add_argument("--save", type=str, default="ratings.json",
                   help="Path to save ratings JSON (default: ratings.json)")
    p.add_argument("--load", type=str, default=None,
                   help="Load existing ratings file instead of starting fresh")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tau", type=float, default=0.5,
                   help="Glicko-2 system constant τ (default: 0.5)")
    p.add_argument("--rating-period", type=int, default=50,
                   help="Update ratings every N games (default: 50)")
    p.add_argument("--top", type=int, default=None,
                   help="Show top-N builds in leaderboard (default: all)")
    return p.parse_args()


def run_match(
    env: CombatEnv,
    policy,
    build_id_a: int,
    build_id_b: int,
    seed: int,
    reg: BuildRegistry,
) -> int | None:
    """
    Play one match using the trained policy on both sides.

    Returns:
        0 if build A wins, 1 if build B wins, None if draw.
    """
    builds_json = reg.builds_json([build_id_a, build_id_b])
    env = CombatEnv(builds_json, [0, 1])
    obs_list, _ = env.reset(seed=seed)
    done = False
    steps = 0

    while not done and steps < 2000:
        mask = env.action_mask()
        obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
        mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
        with torch.no_grad():
            actions, _, _ = policy.act(obs_t, mask_t)
        obs_list, _, terminated, truncated, _ = env.step(int(actions[0]))
        done = terminated or truncated
        steps += 1

    summary = env.get_state_summary()
    return summary.get("winner_team")


def print_leaderboard(
    rater: GlickoRater,
    reg: BuildRegistry,
    top: int | None = None,
) -> None:
    all_rated = rater.top_builds(n=top or 1000, build_registry=reg)
    if not all_rated:
        print("No ratings yet.")
        return

    print()
    print("─" * 75)
    print(f"  {'Rank':>4}  {'Build Name':30s}  {'Splat':12s}  {'Rating':>6}  {'RD':>5}  {'σ':>5}  {'N':>5}")
    print("─" * 75)
    for rank, (bid, rating) in enumerate(all_rated, 1):
        build = reg.get(bid)
        print(
            f"  {rank:>4}  {build.name:30s}  {build.splat:12s}  "
            f"{rating.r:6.0f}  {rating.RD:5.0f}  {rating.sigma:.3f}  {rating.n_matches:5}"
        )
    print("─" * 75)

    # Team composition ratings
    top_teams = rater.top_teams(n=10)
    if top_teams:
        print()
        print("Top team compositions:")
        print("─" * 55)
        for i, (key, rating) in enumerate(top_teams, 1):
            names = " + ".join(reg.get(bid).name for bid in sorted(key) if bid in reg.all_ids())
            print(f"  {i:>3}. {names:40s}  {rating.r:6.0f}  RD={rating.RD:.0f}")
        print("─" * 55)


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    # Load registry
    reg = BuildRegistry()
    builds = reg.load_directory(args.builds_dir)
    ids = reg.all_ids()
    print(f"[setup] {len(builds)} builds loaded from {args.builds_dir}")

    # Load policy
    ckpt_path = ckpt_mod.latest_checkpoint(args.checkpoint_dir)
    if ckpt_path is None:
        print(f"[warn] No checkpoint found in {args.checkpoint_dir} — using untrained policy")
        from cod_sim.selfplay import OBS_SIZE
        from cod_sim.policy import CoDPolicy
        from cod_sim.cod_sim import ACTION_SPACE_SIZE
        policy = CoDPolicy(OBS_SIZE, ACTION_SPACE_SIZE)
    else:
        policy, _, step = ckpt_mod.load(ckpt_path)
        print(f"[setup] Loaded policy from {ckpt_path} (step {step:,})")
    policy.eval()

    # Initialise or load ratings
    if args.load and Path(args.load).exists():
        rater = GlickoRater.load(args.load)
        print(f"[setup] Ratings loaded from {args.load}")
    else:
        rater = GlickoRater(tau=args.tau, rating_period=args.rating_period)
        # Ensure all builds are registered with a default rating
        for bid in ids:
            rater.get_build_rating(bid)

    matchmaker = Matchmaker()
    total_games = 0
    t0 = time.perf_counter()

    for round_num in range(1, args.rounds + 1):
        pairs = matchmaker.round_robin(reg, repeats=1)
        print(f"\n[round {round_num}/{args.rounds}] {len(pairs)} games ...", end="", flush=True)

        for i, (bid_a, bid_b) in enumerate(pairs):
            builds_json = reg.builds_json([bid_a, bid_b])
            env = CombatEnv(builds_json, [0, 1])
            seed = args.seed + total_games
            winner = run_match(env, policy, bid_a, bid_b, seed, reg)
            rater.record_match([bid_a], [bid_b], winner_team=winner)
            rater.maybe_update()
            total_games += 1

            if (i + 1) % 50 == 0:
                print(f" {i+1}", end="", flush=True)

        print()

    # Final update
    if rater.pending_games > 0:
        rater.update_ratings()

    elapsed = time.perf_counter() - t0
    print(f"\n[done] {total_games} games in {elapsed:.1f}s "
          f"({total_games/elapsed:.0f} games/sec)")

    # Print leaderboard
    print_leaderboard(rater, reg, top=args.top)

    # Save
    if args.save:
        rater.save(args.save)
        print(f"\n[saved] ratings → {args.save}")


if __name__ == "__main__":
    main()
