"""Tests for Glicko-2 rating system and matchmaker."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from cod_sim.glicko import (
    GlickoRating, GlickoRater, glicko2_update, _g, _E, _DEFAULT_TAU,
)
from cod_sim.matchmaker import Matchmaker
from cod_sim import BuildRegistry

BUILDS_DIR = Path(__file__).parent.parent.parent / "builds"


def _reg() -> BuildRegistry:
    reg = BuildRegistry()
    reg.load_directory(BUILDS_DIR)
    return reg


# ─── Glicko-2 math tests ──────────────────────────────────────────────────────

class TestGlicko2Math:
    def test_g_phi_zero_is_one(self):
        """g(0) = 1 (zero uncertainty → no reduction)."""
        assert math.isclose(_g(0.0), 1.0, rel_tol=1e-6)

    def test_g_decreases_with_phi(self):
        """g(φ) should decrease as φ increases."""
        vals = [_g(p) for p in [0.0, 0.5, 1.0, 2.0, 5.0]]
        assert all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))

    def test_E_equal_ratings_is_half(self):
        """E(μ, μ, φ) = 0.5 when both players have equal ratings."""
        assert math.isclose(_E(0.0, 0.0, 1.0), 0.5, rel_tol=1e-6)

    def test_E_monotone_in_mu(self):
        """Expected score increases as the player's rating increases."""
        phi = 1.0
        mu_opp = 0.0
        es = [_E(mu, mu_opp, phi) for mu in [-2, -1, 0, 1, 2]]
        assert all(es[i] < es[i + 1] for i in range(len(es) - 1))

    def test_initial_rating_defaults(self):
        r = GlickoRating()
        assert math.isclose(r.r, 1500.0, rel_tol=1e-4)
        assert math.isclose(r.RD, 350.0, rel_tol=1e-2)
        assert math.isclose(r.sigma, 0.06, rel_tol=1e-6)

    def test_update_winner_gains_rating(self):
        """A player who wins should gain rating."""
        player = GlickoRating()
        opponent = GlickoRating()
        updated = glicko2_update(player, [(opponent, 1.0)])
        assert updated.r > player.r

    def test_update_loser_loses_rating(self):
        """A player who loses should lose rating."""
        player = GlickoRating()
        opponent = GlickoRating()
        updated = glicko2_update(player, [(opponent, 0.0)])
        assert updated.r < player.r

    def test_draw_moves_rating_toward_opponent(self):
        """A draw with an equal opponent should barely change rating."""
        player = GlickoRating()
        opponent = GlickoRating()
        updated = glicko2_update(player, [(opponent, 0.5)])
        assert abs(updated.r - player.r) < 5.0

    def test_update_reduces_RD(self):
        """Playing games should reduce uncertainty (lower RD)."""
        player = GlickoRating()
        opponent = GlickoRating()
        updated = glicko2_update(player, [(opponent, 1.0)])
        assert updated.RD < player.RD

    def test_no_games_increases_RD(self):
        """A player who plays no games should see RD increase (uncertainty grows)."""
        player = GlickoRating()
        # Decrease RD by winning a few games
        for _ in range(10):
            player = glicko2_update(player, [(GlickoRating(), 1.0)])
        rd_before = player.RD
        # Now do an empty period
        idle = glicko2_update(player, [])
        assert idle.RD > rd_before

    def test_match_count_increments(self):
        player = GlickoRating()
        opp = GlickoRating()
        updated = glicko2_update(player, [(opp, 1.0), (opp, 0.0), (opp, 0.5)])
        assert updated.n_matches == 3

    def test_strong_player_beats_weak_after_many_games(self):
        """After many wins, a player's rating should be significantly higher."""
        strong = GlickoRating()
        weak   = GlickoRating()
        # Strong wins 20 games against weak
        for _ in range(20):
            strong = glicko2_update(strong, [(weak, 1.0)])
            weak   = glicko2_update(weak,   [(strong, 0.0)])
        assert strong.r > weak.r + 100, \
            f"strong={strong.r:.0f} weak={weak.r:.0f} — should be 100+ points apart"

    def test_glicko2_symmetric(self):
        """Win for A + loss for B should produce symmetric rating changes."""
        a = GlickoRating()
        b = GlickoRating()
        a2 = glicko2_update(a, [(b, 1.0)])
        b2 = glicko2_update(b, [(a, 0.0)])
        # a gains exactly as much as b loses (not exact due to phi, but close)
        gain = a2.r - a.r
        loss = b.r - b2.r
        assert math.isclose(gain, loss, rel_tol=0.01), \
            f"gain={gain:.2f} != loss={loss:.2f}"

    def test_confidence_interval(self):
        r = GlickoRating()
        lo, hi = r.confidence_interval
        assert lo < r.r < hi
        assert math.isclose(hi - lo, 4 * r.RD, rel_tol=1e-6)


# ─── GlickoRater store tests ──────────────────────────────────────────────────

class TestGlickoRater:
    def test_default_rating_is_1500(self):
        rater = GlickoRater()
        rating = rater.get_build_rating(101)
        assert math.isclose(rating.r, 1500.0, rel_tol=1e-4)

    def test_record_and_update(self):
        rater = GlickoRater()
        rater.record_match([101], [201], winner_team=0)
        rater.update_ratings()
        # Winner should have gained rating
        assert rater.get_build_rating(101).r > 1500
        assert rater.get_build_rating(201).r < 1500

    def test_draw_keeps_equal_ratings(self):
        rater = GlickoRater()
        rater.record_match([101], [201], winner_team=None)
        rater.update_ratings()
        # After a draw, ratings should still be close to each other
        r101 = rater.get_build_rating(101).r
        r201 = rater.get_build_rating(201).r
        assert abs(r101 - r201) < 50

    def test_top_builds_sorted(self):
        rater = GlickoRater()
        for _ in range(5):
            rater.record_match([101], [201], winner_team=0)
        rater.update_ratings()
        top = rater.top_builds(n=10)
        ratings = [r.r for _, r in top]
        assert ratings == sorted(ratings, reverse=True)

    def test_team_rating_recorded(self):
        rater = GlickoRater()
        rater.record_match([101, 201], [301, 401], winner_team=0)
        rater.update_ratings()
        team_a = rater.get_team_rating([101, 201])
        team_b = rater.get_team_rating([301, 401])
        assert team_a.r > team_b.r

    def test_maybe_update_triggers_at_period(self):
        rater = GlickoRater(rating_period=5)
        initial_n = rater.get_build_rating(101).n_matches
        for i in range(4):
            rater.record_match([101], [201], winner_team=0)
        # Not yet updated
        assert rater.pending_games == 4
        rater.record_match([101], [201], winner_team=0)
        rater.maybe_update()
        # Now updated
        assert rater.pending_games == 0
        assert rater.get_build_rating(101).n_matches > initial_n

    def test_save_load_roundtrip(self, tmp_path):
        rater = GlickoRater()
        rater.record_match([101], [201], winner_team=0)
        rater.update_ratings()
        path = tmp_path / "ratings.json"
        rater.save(path)
        loaded = GlickoRater.load(path)
        orig_r   = rater.get_build_rating(101).r
        loaded_r = loaded.get_build_rating(101).r
        assert math.isclose(orig_r, loaded_r, rel_tol=1e-6)

    def test_save_load_team_ratings(self, tmp_path):
        rater = GlickoRater()
        rater.record_match([101, 201], [301, 401], winner_team=0)
        rater.update_ratings()
        path = tmp_path / "ratings.json"
        rater.save(path)
        loaded = GlickoRater.load(path)
        key = frozenset([101, 201])
        assert math.isclose(
            rater.get_team_rating([101, 201]).r,
            loaded.get_team_rating([101, 201]).r,
            rel_tol=1e-6,
        )

    def test_convergence_after_many_games(self):
        """Ratings should stabilise and strong player should rank first."""
        rater = GlickoRater(rating_period=10)
        # Build 101 wins every game against all others
        for _ in range(50):
            for opp in [201, 301, 401, 501]:
                rater.record_match([101], [opp], winner_team=0)
            rater.maybe_update()
        if rater.pending_games:
            rater.update_ratings()

        top = rater.top_builds(n=1)
        assert top[0][0] == 101, f"build 101 should be #1, got {top[0][0]}"


# ─── Matchmaker tests ─────────────────────────────────────────────────────────

class TestMatchmaker:
    def test_sample_1v1_returns_two_ids(self):
        mm = Matchmaker()
        reg = _reg()
        rater = GlickoRater()
        for bid in reg.all_ids():
            rater.get_build_rating(bid)
        a, b = mm.sample_1v1(reg, rater)
        assert a in reg.all_ids()
        assert b in reg.all_ids()

    def test_round_robin_count(self):
        mm = Matchmaker()
        reg = _reg()
        n = len(reg.all_ids())
        pairs = mm.round_robin(reg, repeats=1, shuffle=False)
        # Each ordered pair (a, b) with a != b: n*(n-1) pairs
        assert len(pairs) == n * (n - 1)

    def test_round_robin_repeats(self):
        mm = Matchmaker()
        reg = _reg()
        n = len(reg.all_ids())
        pairs = mm.round_robin(reg, repeats=3)
        assert len(pairs) == 3 * n * (n - 1)

    def test_round_robin_covers_all_pairs(self):
        mm = Matchmaker()
        reg = _reg()
        pairs = set(mm.round_robin(reg, repeats=1, shuffle=False))
        ids = reg.all_ids()
        for a in ids:
            for b in ids:
                if a != b:
                    assert (a, b) in pairs


# ─── Full mini-tournament integration test ────────────────────────────────────

class TestMiniTournament:
    def test_tournament_produces_ranked_leaderboard(self):
        """
        Run a tiny tournament (3 rounds, 1 game per pair) and verify
        that ratings change and are sorted correctly in the leaderboard.
        """
        reg = _reg()
        rater = GlickoRater(tau=0.5, rating_period=20)
        mm = Matchmaker()

        from cod_sim.cod_sim import CombatEnv
        import torch
        from cod_sim import checkpoint as ckpt_mod
        from cod_sim.selfplay import OBS_SIZE
        from cod_sim.policy import CoDPolicy
        from cod_sim.cod_sim import ACTION_SPACE_SIZE

        # Use trained policy if available, otherwise random
        ckpt = ckpt_mod.latest_checkpoint("checkpoints")
        if ckpt:
            policy, _, _ = ckpt_mod.load(ckpt)
        else:
            policy = CoDPolicy(OBS_SIZE, ACTION_SPACE_SIZE)
        policy.eval()

        random.seed(7)
        pairs = mm.round_robin(reg, repeats=1)
        for seed, (bid_a, bid_b) in enumerate(pairs):
            builds_json = reg.builds_json([bid_a, bid_b])
            env = CombatEnv(builds_json, [0, 1])
            obs_list, _ = env.reset(seed=seed)
            done = False; steps = 0
            while not done and steps < 2000:
                mask = env.action_mask()
                obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
                mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
                with torch.no_grad():
                    acts, _, _ = policy.act(obs_t, mask_t)
                obs_list, _, t, tr, _ = env.step(int(acts[0]))
                done = t or tr; steps += 1
            winner = env.get_state_summary().get("winner_team")
            rater.record_match([bid_a], [bid_b], winner_team=winner)
            rater.maybe_update()
        if rater.pending_games:
            rater.update_ratings()

        # Leaderboard should be sorted
        top = rater.top_builds()
        ratings = [r.r for _, r in top]
        assert ratings == sorted(ratings, reverse=True), "leaderboard must be sorted"
        # At least some ratings should have changed
        assert not all(math.isclose(r, 1500, abs_tol=1) for r in ratings), \
            "at least some ratings should have changed after a tournament"

    def test_strong_build_ranks_higher(self):
        """A build that wins all games should end up with the highest rating."""
        reg = _reg()
        rater = GlickoRater(rating_period=10)

        ids = reg.all_ids()
        winner_id = ids[0]

        for _ in range(30):
            for opp_id in ids[1:]:
                # Winner always wins
                rater.record_match([winner_id], [opp_id], winner_team=0)
            rater.maybe_update()
        if rater.pending_games:
            rater.update_ratings()

        top = rater.top_builds(n=1)
        assert top[0][0] == winner_id, \
            f"build {winner_id} should be #1 after winning every game"
