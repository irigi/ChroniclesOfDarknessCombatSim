"""Self-play PPO training loop for Chronicles of Darkness combat."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import torch

from .build_registry import BuildRegistry
from .checkpoint import save, save_weights, list_checkpoints
from .cod_sim import VecEnv, ACTION_SPACE_SIZE, OBS_PER_CHAR, GLOBAL_OBS
from .policy import CoDPolicy

# Fixed to 1v1 for Phase 4 (2 combatants → obs_size = 2*24+3 = 51)
N_COMBATANTS = 2
OBS_SIZE = N_COMBATANTS * OBS_PER_CHAR + GLOBAL_OBS


@dataclass
class PPOConfig:
    # Environment
    n_envs: int = 64
    rollout_len: int = 128          # steps per env per rollout
    # PPO hypers
    gamma: float = 0.99
    lam: float = 0.95               # GAE lambda
    clip_eps: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.05  # raised from 0.01; encourages discipline exploration
    max_grad_norm: float = 0.5
    ppo_epochs: int = 4
    minibatch_size: int = 512
    # Learning rate (cosine decay)
    lr_start: float = 3e-4
    lr_end: float = 1e-5
    # Checkpointing
    checkpoint_every_steps: int = 50_000
    snapshot_every_steps: int = 50_000
    max_snapshots: int = 20
    # Logging
    log_every_steps: int = 10_000


@dataclass
class RolloutBuffer:
    obs: np.ndarray      # (T, N, obs_size)
    masks: np.ndarray    # (T, N, action_size)  bool
    actions: np.ndarray  # (T, N)               int64
    log_probs: np.ndarray# (T, N)               float32
    values: np.ndarray   # (T, N)               float32
    rewards: np.ndarray  # (T, N)               float32
    dones: np.ndarray    # (T, N)               bool
    advantages: np.ndarray = field(default_factory=lambda: np.array([]))
    returns: np.ndarray   = field(default_factory=lambda: np.array([]))


class SelfPlayTrainer:
    """
    PPO self-play trainer.

    Both teams use the SAME policy (mirror play). The observation is always
    from the current actor's POV, so the policy implicitly learns to help
    its team regardless of which side it's on.

    For diverse matchups, each env independently samples a random pair of
    builds from the registry on every episode reset. This exposes the policy
    to all splat matchups during training.
    """

    def __init__(
        self,
        build_registry: BuildRegistry,
        config: PPOConfig | None = None,
        checkpoint_dir: str | Path = "./checkpoints",
        resume: bool = True,
    ) -> None:
        self.reg = build_registry
        self.cfg = config or PPOConfig()
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.policy = CoDPolicy(OBS_SIZE, ACTION_SPACE_SIZE)
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=self.cfg.lr_start)
        self.steps_done = 0

        # Try to resume from latest checkpoint
        if resume:
            self._try_resume()

        # Snapshot pool: list of policy weight paths for opponent sampling
        self._snapshots: list[Path] = []

        # Per-env tracking: (build_id_a, build_id_b)
        self._env_matchups: list[tuple[int, int]] = []

        # VecEnv and current observations
        self._vec_env: VecEnv | None = None
        self._current_obs = np.zeros((self.cfg.n_envs, OBS_SIZE), dtype=np.float32)

        self._init_envs()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _try_resume(self) -> None:
        from .checkpoint import latest_checkpoint, load
        ckpt = latest_checkpoint(self.checkpoint_dir)
        if ckpt is not None:
            try:
                policy, opt, step = load(ckpt)
                self.policy.load_state_dict(policy.state_dict())
                if opt is not None:
                    self.optimizer.load_state_dict(opt.state_dict())
                self.steps_done = step
                print(f"[resume] loaded checkpoint from {ckpt} (step {step:,})")
            except (RuntimeError, KeyError) as e:
                print(f"[resume] checkpoint {ckpt} is incompatible with current architecture ({e}); starting fresh")

    def _sample_matchup(self) -> tuple[int, int]:
        """Randomly sample two build IDs (can be same splat, even same build)."""
        ids = self.reg.all_ids()
        return random.choice(ids), random.choice(ids)

    def _init_envs(self) -> None:
        """Create VecEnv with random matchups."""
        ids = self.reg.all_ids()
        # Use the first two builds for initial creation (will be overridden on first reset)
        a, b = ids[0], ids[min(1, len(ids) - 1)]
        builds_json = self.reg.builds_json([a, b])
        self._vec_env = VecEnv(builds_json, [0, 1], self.cfg.n_envs)
        self._env_matchups = [(a, b)] * self.cfg.n_envs

        # Randomise each env's matchup and reset
        obs_all = self._vec_env.reset_all()
        for env_idx in range(self.cfg.n_envs):
            a, b = self._sample_matchup()
            self._env_matchups[env_idx] = (a, b)
            builds_json = self.reg.builds_json([a, b])
            new_obs = self._vec_env.reset_env(env_idx, builds_json, [0, 1])
            obs_all[env_idx] = new_obs

        self._current_obs[:] = np.array(obs_all, dtype=np.float32)

    def _reset_env(self, env_idx: int) -> np.ndarray:
        """Reset one env with a newly sampled matchup. Returns the initial obs."""
        a, b = self._sample_matchup()
        self._env_matchups[env_idx] = (a, b)
        builds_json = self.reg.builds_json([a, b])
        obs = self._vec_env.reset_env(env_idx, builds_json, [0, 1])
        return np.array(obs, dtype=np.float32)

    # ------------------------------------------------------------------
    # Rollout collection
    # ------------------------------------------------------------------

    def _collect_rollout(self) -> RolloutBuffer:
        """Collect cfg.rollout_len steps from all cfg.n_envs environments."""
        T = self.cfg.rollout_len
        N = self.cfg.n_envs
        A = ACTION_SPACE_SIZE

        obs_buf   = np.zeros((T, N, OBS_SIZE), dtype=np.float32)
        mask_buf  = np.zeros((T, N, A), dtype=bool)
        act_buf   = np.zeros((T, N), dtype=np.int64)
        logp_buf  = np.zeros((T, N), dtype=np.float32)
        val_buf   = np.zeros((T, N), dtype=np.float32)
        rew_buf   = np.zeros((T, N), dtype=np.float32)
        done_buf  = np.zeros((T, N), dtype=bool)

        self.policy.eval()

        for t in range(T):
            obs_buf[t] = self._current_obs

            masks = np.array(self._vec_env.action_masks_all(), dtype=bool)
            mask_buf[t] = masks

            obs_t  = torch.from_numpy(self._current_obs)
            mask_t = torch.from_numpy(masks)
            actions, log_probs, values = self.policy.act(obs_t, mask_t)

            act_buf[t]  = actions.numpy()
            logp_buf[t] = log_probs.numpy()
            val_buf[t]  = values.numpy()

            obs_list, rew_list, term_list, trunc_list = self._vec_env.step_all(
                act_buf[t].tolist()
            )

            rew_buf[t] = np.array(rew_list, dtype=np.float32)
            done_arr   = np.array(term_list, dtype=bool) | np.array(trunc_list, dtype=bool)
            done_buf[t] = done_arr

            next_obs = np.array(obs_list, dtype=np.float32)
            for env_idx in range(N):
                if done_arr[env_idx]:
                    reset_obs = self._reset_env(env_idx)
                    self._current_obs[env_idx] = reset_obs
                else:
                    self._current_obs[env_idx] = next_obs[env_idx]

        # Bootstrap value for the state AFTER the last collected step
        masks_final = np.array(self._vec_env.action_masks_all(), dtype=bool)
        obs_t  = torch.from_numpy(self._current_obs)
        mask_t = torch.from_numpy(masks_final)
        with torch.no_grad():
            _, last_values = self.policy.forward(obs_t, mask_t)
        last_vals = last_values.numpy()
        # Envs that were done at the last step: bootstrap = 0
        last_vals = last_vals * ~done_buf[-1]

        buf = RolloutBuffer(
            obs=obs_buf, masks=mask_buf,
            actions=act_buf, log_probs=logp_buf,
            values=val_buf, rewards=rew_buf, dones=done_buf,
        )
        buf.advantages, buf.returns = self._compute_gae(buf, last_vals)
        return buf

    def _compute_gae(
        self, buf: RolloutBuffer, last_values: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generalised Advantage Estimation."""
        T, N = buf.rewards.shape
        advantages = np.zeros((T, N), dtype=np.float32)
        gae = np.zeros(N, dtype=np.float32)

        for t in reversed(range(T)):
            non_terminal = ~buf.dones[t]
            next_val = last_values if t == T - 1 else buf.values[t + 1]
            delta = buf.rewards[t] + self.cfg.gamma * next_val * non_terminal - buf.values[t]
            gae = delta + self.cfg.gamma * self.cfg.lam * non_terminal * gae
            advantages[t] = gae

        returns = advantages + buf.values
        return advantages, returns

    # ------------------------------------------------------------------
    # PPO update
    # ------------------------------------------------------------------

    def _ppo_update(self, buf: RolloutBuffer) -> dict[str, float]:
        """Run ppo_epochs passes over the rollout buffer. Returns loss metrics."""
        T, N = buf.rewards.shape
        total = T * N
        mb = self.cfg.minibatch_size

        # Flatten (T, N, ...) → (total, ...)
        obs_flat    = buf.obs.reshape(total, OBS_SIZE)
        mask_flat   = buf.masks.reshape(total, ACTION_SPACE_SIZE)
        act_flat    = buf.actions.reshape(total)
        old_logp    = buf.log_probs.reshape(total)
        adv_flat    = buf.advantages.reshape(total)
        ret_flat    = buf.returns.reshape(total)

        # Normalise advantages
        adv_flat = (adv_flat - adv_flat.mean()) / (adv_flat.std() + 1e-8)

        # To torch
        obs_t    = torch.from_numpy(obs_flat)
        mask_t   = torch.from_numpy(mask_flat)
        act_t    = torch.from_numpy(act_flat).long()
        old_logp_t = torch.from_numpy(old_logp)
        adv_t    = torch.from_numpy(adv_flat)
        ret_t    = torch.from_numpy(ret_flat)

        metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "approx_kl": 0.0}
        n_updates = 0

        self.policy.train()

        for _ in range(self.cfg.ppo_epochs):
            perm = torch.randperm(total)
            for start in range(0, total, mb):
                idx = perm[start : start + mb]
                if len(idx) < mb // 2:
                    continue

                new_logp, values, entropy = self.policy.evaluate(
                    obs_t[idx], mask_t[idx], act_t[idx]
                )

                # Ratio for PPO clipping
                log_ratio = new_logp - old_logp_t[idx]
                ratio = log_ratio.exp()
                with torch.no_grad():
                    approx_kl = ((ratio - 1) - log_ratio).mean().item()

                adv_mb = adv_t[idx]
                # Clipped surrogate objective
                surr1 = ratio * adv_mb
                surr2 = ratio.clamp(1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps) * adv_mb
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss with clipping
                ret_mb = ret_t[idx]
                value_loss = F.mse_loss(values, ret_mb)

                loss = (
                    policy_loss
                    + self.cfg.value_coef * value_loss
                    - self.cfg.entropy_coef * entropy.mean()
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), self.cfg.max_grad_norm)
                self.optimizer.step()

                metrics["policy_loss"] += policy_loss.item()
                metrics["value_loss"]  += value_loss.item()
                metrics["entropy"]     += entropy.mean().item()
                metrics["approx_kl"]   += approx_kl
                n_updates += 1

        if n_updates > 0:
            for k in metrics:
                metrics[k] /= n_updates
        return metrics

    def _update_lr(self, total_steps: int) -> None:
        """Cosine-decay the learning rate from lr_start to lr_end."""
        frac = min(self.steps_done / total_steps, 1.0)
        lr = self.cfg.lr_end + 0.5 * (self.cfg.lr_start - self.cfg.lr_end) * (
            1 + math.cos(math.pi * frac)
        )
        for pg in self.optimizer.param_groups:
            pg["lr"] = lr

    # ------------------------------------------------------------------
    # Snapshot pool
    # ------------------------------------------------------------------

    def _save_snapshot(self) -> None:
        """Save current weights to the snapshot pool."""
        path = self.checkpoint_dir / f"snapshot_{self.steps_done}.pt"
        save_weights(self.policy, path)
        self._snapshots.append(path)
        # Keep only the last max_snapshots
        while len(self._snapshots) > self.cfg.max_snapshots:
            old = self._snapshots.pop(0)
            old.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------

    def evaluate_vs_random(self, n_episodes: int = 200) -> tuple[float, float]:
        """
        Evaluate the trained policy against a uniform-random baseline.

        Returns (overall_win_rate, decided_win_rate) where:
        - overall_win_rate  = wins / n_episodes  (draws count against)
        - decided_win_rate  = wins / decided      (only games with a winner)
        The trained policy plays as team 0, the random baseline plays as team 1.
        """
        ids = self.reg.all_ids()
        wins = 0
        decided = 0
        self.policy.eval()

        for ep in range(n_episodes):
            a = random.choice(ids)
            b = random.choice(ids)
            builds_json = self.reg.builds_json([a, b])

            # Single env for clean evaluation
            from .cod_sim import CombatEnv
            env = CombatEnv(builds_json, [0, 1])
            obs_list, _ = env.reset(seed=ep)
            done = False
            steps = 0

            while not done and steps < 1000:
                current_actor = env.current_actor_idx()
                current_team = 0  # fallback
                # Determine the team of the current actor from summary
                summary = env.get_state_summary()
                if current_actor < len(summary["characters"]):
                    current_team = summary["characters"][current_actor]["team"]

                mask = env.action_mask()
                if current_team == 0:
                    # Trained policy acts
                    obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
                    mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
                    actions, _, _ = self.policy.act(obs_t, mask_t)
                    action = int(actions[0])
                else:
                    # Random baseline: uniform sample over all legal actions
                    legal = [i for i, m in enumerate(mask) if m]
                    action = random.choice(legal)

                obs_list, _, terminated, truncated, _ = env.step(action)
                done = terminated or truncated
                steps += 1

            summary = env.get_state_summary()
            winner = summary.get("winner_team")
            if winner is not None:
                decided += 1
                if winner == 0:
                    wins += 1

        overall = wins / n_episodes
        decided_rate = wins / decided if decided > 0 else 0.0
        return overall, decided_rate

    def win_rate_mirror(self, n_episodes: int = 100) -> float:
        """
        Quick win-rate sanity check: trained policy vs itself (should be ~50%).
        """
        ids = self.reg.all_ids()
        wins = {0: 0, 1: 0, None: 0}
        self.policy.eval()

        for ep in range(n_episodes):
            a = random.choice(ids)
            b = random.choice(ids)
            builds_json = self.reg.builds_json([a, b])

            from .cod_sim import CombatEnv
            env = CombatEnv(builds_json, [0, 1])
            obs_list, _ = env.reset(seed=ep)
            done = False
            steps = 0

            while not done and steps < 1000:
                mask = env.action_mask()
                obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
                mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
                actions, _, _ = self.policy.act(obs_t, mask_t)
                obs_list, _, t, tr, _ = env.step(int(actions[0]))
                done = t or tr
                steps += 1

            winner = env.get_state_summary().get("winner_team")
            wins[winner] += 1

        return wins[0] / n_episodes

    # ------------------------------------------------------------------
    # Main training entry point
    # ------------------------------------------------------------------

    def train(
        self,
        total_steps: int,
        callback: Callable[[dict], None] | None = None,
    ) -> None:
        """
        Run PPO self-play training for total_steps environment steps.

        `callback` is called after each rollout with a metrics dict.
        """
        rollout_steps = self.cfg.rollout_len * self.cfg.n_envs
        last_checkpoint = self.steps_done
        last_snapshot   = self.steps_done
        last_log        = self.steps_done
        t0 = time.perf_counter()

        print(
            f"[train] start step={self.steps_done:,} target={total_steps:,} "
            f"n_envs={self.cfg.n_envs} rollout_len={self.cfg.rollout_len} "
            f"builds={len(self.reg)}"
        )

        while self.steps_done < total_steps:
            self._update_lr(total_steps)

            buf    = self._collect_rollout()
            metrics = self._ppo_update(buf)

            self.steps_done += rollout_steps

            # Logging
            if self.steps_done - last_log >= self.cfg.log_every_steps:
                elapsed = time.perf_counter() - t0
                sps = self.steps_done / elapsed
                ep_rew_mean = buf.rewards.sum(axis=0).mean()
                frac = 100 * self.steps_done / total_steps
                lr = self.optimizer.param_groups[0]["lr"]
                print(
                    f"step={self.steps_done:>8,} ({frac:4.1f}%) "
                    f"sps={sps:,.0f} "
                    f"ep_rew={ep_rew_mean:+.3f} "
                    f"π_loss={metrics['policy_loss']:+.4f} "
                    f"v_loss={metrics['value_loss']:.4f} "
                    f"H={metrics['entropy']:.3f} "
                    f"KL={metrics['approx_kl']:.4f} "
                    f"lr={lr:.2e}"
                )
                last_log = self.steps_done

                if callback:
                    callback({**metrics, "step": self.steps_done, "sps": sps})

            # Snapshot (save weights only, for future opponent pool)
            if self.steps_done - last_snapshot >= self.cfg.snapshot_every_steps:
                self._save_snapshot()
                last_snapshot = self.steps_done

            # Full checkpoint (weights + optimizer)
            if self.steps_done - last_checkpoint >= self.cfg.checkpoint_every_steps:
                ckpt_path = self.checkpoint_dir / f"checkpoint_{self.steps_done}.pt"
                save(self.policy, self.optimizer, self.steps_done, ckpt_path)
                last_checkpoint = self.steps_done

        # Final checkpoint
        ckpt_path = self.checkpoint_dir / f"checkpoint_{self.steps_done}.pt"
        save(self.policy, self.optimizer, self.steps_done, ckpt_path)
        print(f"[train] done. final checkpoint saved to {ckpt_path}")


import torch.nn as nn
import torch.nn.functional as F
