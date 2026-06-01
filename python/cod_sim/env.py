"""Gymnasium-compatible wrapper around the Rust CombatEnv."""

from __future__ import annotations

from typing import Any

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .cod_sim import CombatEnv as _RustEnv, ACTION_SPACE_SIZE, OBS_PER_CHAR, GLOBAL_OBS
from .build_registry import BuildDefinition


class CombatEnvWrapper(gym.Env):
    """Single Chronicles of Darkness combat environment.

    Observation space: flat float32 vector of length n_chars * OBS_PER_CHAR + GLOBAL_OBS.
    Action space:      Discrete(ACTION_SPACE_SIZE).

    The env steps one character at a time (the current actor). The agent provides
    an action for whoever is currently "up", regardless of team. Self-play
    training loops track which team the current actor belongs to and assign
    rewards accordingly.
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(
        self,
        builds: list[BuildDefinition],
        teams: list[int],
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        if len(builds) != len(teams):
            raise ValueError("builds and teams must have equal length")

        self.render_mode = render_mode
        self._builds = builds
        self._teams = [int(t) for t in teams]
        self._n_chars = len(builds)

        obs_len = self._n_chars * OBS_PER_CHAR + GLOBAL_OBS
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(obs_len,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(ACTION_SPACE_SIZE)

        self._builds_json = self._build_json_array()
        self._env: _RustEnv | None = None

    # ------------------------------------------------------------------

    def _build_json_array(self) -> str:
        return "[" + ",".join(b.to_rust_json() for b in self._builds) + "]"

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        if self._env is None:
            self._env = _RustEnv(self._builds_json, self._teams)
        obs_list, info = self._env.reset(seed=seed)
        obs = np.array(obs_list, dtype=np.float32)
        return obs, info

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict]:
        assert self._env is not None, "call reset() before step()"
        obs_list, reward, terminated, truncated, info = self._env.step(int(action))
        obs = np.array(obs_list, dtype=np.float32)
        return obs, float(reward), terminated, truncated, info

    def action_mask(self) -> np.ndarray:
        """Return a boolean mask of legal actions (True = legal)."""
        assert self._env is not None, "call reset() before action_mask()"
        return np.array(self._env.action_mask(), dtype=bool)

    def get_state_summary(self) -> dict:
        assert self._env is not None, "call reset() before get_state_summary()"
        return self._env.get_state_summary()

    def render(self) -> None:
        pass
