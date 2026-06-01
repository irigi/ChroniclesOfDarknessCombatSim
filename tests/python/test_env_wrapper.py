"""Tests for CombatEnvWrapper: gymnasium compliance and functional checks."""

from pathlib import Path
import numpy as np
import pytest

from cod_sim import BuildRegistry, CombatEnvWrapper, ACTION_SPACE_SIZE, OBS_PER_CHAR, GLOBAL_OBS

BUILDS_DIR = Path(__file__).parent.parent.parent / "builds"


def _load_registry() -> BuildRegistry:
    reg = BuildRegistry()
    reg.load_directory(BUILDS_DIR)
    return reg


def _make_env(build_ids: list[int], teams: list[int], reg: BuildRegistry | None = None) -> CombatEnvWrapper:
    if reg is None:
        reg = _load_registry()
    builds = [reg.get(bid) for bid in build_ids]
    return CombatEnvWrapper(builds=builds, teams=teams)


class TestObsActionSpaces:
    def test_obs_space_shape(self):
        env = _make_env([101, 102], [0, 1])
        n = 2
        expected = (n * OBS_PER_CHAR + GLOBAL_OBS,)
        assert env.observation_space.shape == expected

    def test_action_space_size(self):
        env = _make_env([101, 102], [0, 1])
        assert env.action_space.n == ACTION_SPACE_SIZE

    def test_reset_returns_obs_in_space(self):
        env = _make_env([101, 102], [0, 1])
        obs, info = env.reset(seed=0)
        assert env.observation_space.contains(obs), \
            f"obs out of space bounds: min={obs.min():.3f} max={obs.max():.3f}"
        assert isinstance(info, dict)

    def test_step_returns_obs_in_space(self):
        env = _make_env([101, 102], [0, 1])
        obs, _ = env.reset(seed=42)
        mask = env.action_mask()
        action = int(np.where(mask)[0][0])
        obs2, reward, terminated, truncated, info = env.step(action)
        assert env.observation_space.contains(obs2)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)

    def test_obs_dtype_float32(self):
        env = _make_env([101, 201], [0, 1])
        obs, _ = env.reset()
        assert obs.dtype == np.float32

    def test_action_mask_length(self):
        env = _make_env([101, 201], [0, 1])
        env.reset()
        mask = env.action_mask()
        assert len(mask) == ACTION_SPACE_SIZE
        assert mask.dtype == bool
        assert mask.any(), "at least one action must be legal"


class TestCombatBehavior:
    def test_combat_terminates(self):
        env = _make_env([101, 201], [0, 1])
        env.reset(seed=0)
        done = False
        steps = 0
        while not done:
            mask = env.action_mask()
            action = int(np.where(mask)[0][0])
            _, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            steps += 1
            assert steps < 2000, "combat should terminate"
        assert done

    def test_vampire_vs_mortal(self):
        env = _make_env([201, 101], [0, 1])
        env.reset(seed=7)
        done = False
        while not done:
            mask = env.action_mask()
            action = int(np.where(mask)[0][0])
            _, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
        summary = env.get_state_summary()
        assert summary["done"]

    def test_werewolf_vs_mortal(self):
        env = _make_env([301, 101], [0, 1])
        env.reset(seed=3)
        done = False
        while not done:
            mask = env.action_mask()
            action = int(np.where(mask)[0][0])
            _, _, t, tr, _ = env.step(action)
            done = t or tr
        summary = env.get_state_summary()
        assert summary["done"]

    def test_all_builds_vs_each_other(self):
        reg = _load_registry()
        ids = reg.all_ids()
        for i, bid_a in enumerate(ids):
            for bid_b in ids[i:]:
                env = _make_env([bid_a, bid_b], [0, 1], reg)
                env.reset(seed=bid_a * 1000 + bid_b)
                done = False
                steps = 0
                while not done:
                    mask = env.action_mask()
                    action = int(np.where(mask)[0][0])
                    _, _, t, tr, _ = env.step(action)
                    done = t or tr
                    steps += 1
                    assert steps < 3000, f"match {bid_a} vs {bid_b} did not terminate"

    def test_deterministic_with_same_seed(self):
        env = _make_env([101, 201], [0, 1])
        rewards_a = []
        env.reset(seed=99)
        for _ in range(10):
            mask = env.action_mask()
            action = int(np.where(mask)[0][0])
            _, r, t, tr, _ = env.step(action)
            rewards_a.append(r)
            if t or tr:
                break

        env2 = _make_env([101, 201], [0, 1])
        rewards_b = []
        env2.reset(seed=99)
        for _ in range(10):
            mask = env2.action_mask()
            action = int(np.where(mask)[0][0])
            _, r, t, tr, _ = env2.step(action)
            rewards_b.append(r)
            if t or tr:
                break

        assert rewards_a == rewards_b, "same seed should give same rewards"


class TestVecEnv:
    def test_vec_env_runs(self):
        from cod_sim import VecEnv
        reg = _load_registry()
        b = reg.builds_json([101, 201])
        vec = VecEnv(b, [0, 1], 8)
        obs_list = vec.reset_all()
        assert len(obs_list) == 8
        assert all(len(o) == vec.obs_size() for o in obs_list)

    def test_vec_env_step_all(self):
        from cod_sim import VecEnv
        reg = _load_registry()
        b = reg.builds_json([101, 201])
        vec = VecEnv(b, [0, 1], 4)
        vec.reset_all()
        masks = vec.action_masks_all()
        actions = [int(np.where(m)[0][0]) for m in masks]
        obs_list, rewards, terminated, truncated = vec.step_all(actions)
        assert len(obs_list) == 4
        assert len(rewards) == 4

    def test_vec_env_parallel_results_differ(self):
        """Different seeds should (almost always) produce different observations."""
        from cod_sim import VecEnv
        reg = _load_registry()
        b = reg.builds_json([101, 201])
        vec = VecEnv(b, [0, 1], 4)
        obs_list = vec.reset_all()
        # Not all observations should be identical
        all_same = all(np.allclose(obs_list[0], o) for o in obs_list[1:])
        assert not all_same, "parallel envs with different seeds should differ"


class TestGymnasiumChecker:
    def test_env_checker(self):
        """Run gymnasium's official env_checker."""
        from gymnasium.utils.env_checker import check_env

        reg = _load_registry()
        builds = [reg.get(101), reg.get(201)]
        env = CombatEnvWrapper(builds=builds, teams=[0, 1])
        # check_env calls reset and step multiple times
        check_env(env, warn=True, skip_render_check=True)
