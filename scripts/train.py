#!/usr/bin/env python3
"""Training script for the Chronicles of Darkness PPO self-play policy.

Usage:
    .venv/bin/python scripts/train.py [options]

Examples:
    # Quick sanity check (10K steps)
    .venv/bin/python scripts/train.py --steps 10000 --n-envs 16

    # Full training run
    .venv/bin/python scripts/train.py --steps 500000 --n-envs 64

    # Resume from latest checkpoint
    .venv/bin/python scripts/train.py --steps 1000000 --resume
"""

import argparse
import sys
from pathlib import Path

# Ensure the project root is on the path when called from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cod_sim.build_registry import BuildRegistry
from cod_sim.selfplay import SelfPlayTrainer, PPOConfig

BUILDS_DIR = Path(__file__).resolve().parent.parent / "builds"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a PPO policy for CoD combat")
    p.add_argument("--steps", type=int, default=500_000,
                   help="Total env steps to train for (default: 500000)")
    p.add_argument("--n-envs", type=int, default=64,
                   help="Parallel environments (default: 64)")
    p.add_argument("--rollout-len", type=int, default=128,
                   help="Steps per env per rollout (default: 128)")
    p.add_argument("--checkpoint-dir", type=str, default="checkpoints",
                   help="Directory for checkpoints (default: ./checkpoints)")
    p.add_argument("--resume", action="store_true",
                   help="Resume from latest checkpoint in checkpoint-dir")
    p.add_argument("--lr", type=float, default=3e-4,
                   help="Initial learning rate (default: 3e-4)")
    p.add_argument("--entropy-coef", type=float, default=0.01,
                   help="Entropy bonus coefficient (default: 0.01)")
    p.add_argument("--eval-episodes", type=int, default=200,
                   help="Episodes for final evaluation vs random (default: 200)")
    p.add_argument("--no-eval", action="store_true",
                   help="Skip post-training evaluation")
    p.add_argument("--builds-dir", type=str, default=str(BUILDS_DIR),
                   help="Path to YAML builds directory")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Load build registry
    reg = BuildRegistry()
    builds = reg.load_directory(args.builds_dir)
    print(f"[setup] loaded {len(builds)} builds from {args.builds_dir}")
    for b in builds:
        print(f"        {b.id:4d}  {b.splat:12s}  {b.name}")

    # Configure training
    cfg = PPOConfig(
        n_envs=args.n_envs,
        rollout_len=args.rollout_len,
        lr_start=args.lr,
        entropy_coef=args.entropy_coef,
    )

    trainer = SelfPlayTrainer(
        build_registry=reg,
        config=cfg,
        checkpoint_dir=args.checkpoint_dir,
        resume=args.resume,
    )

    # Run training
    trainer.train(total_steps=args.steps)

    # Final evaluation
    if not args.no_eval:
        print(f"\n[eval] evaluating trained policy vs random baseline "
              f"({args.eval_episodes} episodes) ...")
        win_rate = trainer.evaluate_vs_random(n_episodes=args.eval_episodes)
        mirror_rate = trainer.win_rate_mirror(n_episodes=100)
        print(f"[eval] win rate vs random:  {win_rate:.1%}")
        print(f"[eval] win rate vs mirror:  {mirror_rate:.1%} (expect ~50%)")
        if win_rate >= 0.80:
            print("[eval] PASS — policy beats random baseline ≥ 80%")
        else:
            print(f"[eval] win rate {win_rate:.1%} < 80% — may need more training")


if __name__ == "__main__":
    main()
