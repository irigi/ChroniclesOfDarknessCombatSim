"""Tests for the FastAPI web application."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The TestClient runs the lifespan context synchronously, so it exercises
# the real startup code (loads registry, ratings, policy from disk).

@pytest.fixture(scope="module")
def client():
    from cod_sim.api.main import app
    with TestClient(app) as c:
        yield c


class TestStatus:
    def test_status_returns_counts(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        d = r.json()
        assert "builds" in d
        assert "ratings" in d
        assert "policy" in d
        assert d["builds"] > 0

    def test_static_index_served(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Chronicles of Darkness" in r.text


class TestBuildsAPI:
    def test_list_builds(self, client):
        r = client.get("/api/builds")
        assert r.status_code == 200
        builds = r.json()
        assert len(builds) > 0
        # Each build should have required fields
        for b in builds:
            assert "id" in b
            assert "name" in b
            assert "splat" in b
            assert "attributes" in b
            assert "derived" in b

    def test_list_builds_sorted_by_rating(self, client):
        r = client.get("/api/builds")
        builds = r.json()
        # Ratings should be present and sorted descending
        rated = [b for b in builds if "rating" in b]
        if rated:
            ratings = [b["rating"]["r"] for b in rated]
            assert ratings == sorted(ratings, reverse=True)

    def test_get_specific_build(self, client):
        # Get any build ID from the list
        r = client.get("/api/builds")
        builds = r.json()
        bid = builds[0]["id"]

        r2 = client.get(f"/api/builds/{bid}")
        assert r2.status_code == 200
        b = r2.json()
        assert b["id"] == bid
        assert "splat" in b
        assert "splat_details" in b

    def test_get_nonexistent_build_404(self, client):
        r = client.get("/api/builds/99999")
        assert r.status_code == 404

    def test_vampire_build_has_disciplines(self, client):
        r = client.get("/api/builds")
        builds = r.json()
        vampires = [b for b in builds if b["splat"] == "vampire"]
        if vampires:
            vamp = vampires[0]
            d = vamp["splat_details"]
            assert "celerity" in d
            assert "vigor" in d
            assert "resilience" in d

    def test_werewolf_build_has_primal_urge(self, client):
        r = client.get("/api/builds")
        builds = r.json()
        wolves = [b for b in builds if b["splat"] == "werewolf"]
        if wolves:
            wolf = wolves[0]
            assert "primal_urge" in wolf["splat_details"]


class TestCombatAPI:
    def _get_two_build_ids(self, client) -> tuple[int, int]:
        builds = client.get("/api/builds").json()
        return builds[0]["id"], builds[1]["id"]

    def test_run_combat_returns_log(self, client):
        bid_a, bid_b = self._get_two_build_ids(client)
        r = client.post("/api/combat/run", json={
            "build_id_a": bid_a,
            "build_id_b": bid_b,
            "seed": 42,
            "use_policy": True,
        })
        assert r.status_code == 200
        log = r.json()
        assert "winner_team" in log
        assert "n_steps" in log
        assert "n_turns" in log
        assert "events" in log
        assert "build_a" in log
        assert "build_b" in log

    def test_run_combat_has_events(self, client):
        bid_a, bid_b = self._get_two_build_ids(client)
        r = client.post("/api/combat/run", json={
            "build_id_a": bid_a,
            "build_id_b": bid_b,
            "seed": 0,
        })
        log = r.json()
        assert len(log["events"]) > 0
        first = log["events"][0]
        assert "step" in first
        assert "turn" in first
        assert "actor_name" in first
        assert "actor_team" in first
        assert "action_desc" in first
        assert "characters" in first

    def test_run_combat_characters_have_health(self, client):
        bid_a, bid_b = self._get_two_build_ids(client)
        r = client.post("/api/combat/run", json={
            "build_id_a": bid_a,
            "build_id_b": bid_b,
            "seed": 1,
        })
        log = r.json()
        chars = log["events"][0]["characters"]
        assert len(chars) == 2
        for ch in chars:
            assert "max_health" in ch
            assert "bashing" in ch
            assert "lethal" in ch
            assert "aggravated" in ch
            assert ch["max_health"] > 0

    def test_run_combat_deterministic(self, client):
        bid_a, bid_b = self._get_two_build_ids(client)
        body = {"build_id_a": bid_a, "build_id_b": bid_b, "seed": 77}
        r1 = client.post("/api/combat/run", json=body).json()
        r2 = client.post("/api/combat/run", json=body).json()
        assert r1["winner_team"] == r2["winner_team"]
        assert r1["n_steps"] == r2["n_steps"]

    def test_run_combat_terminates(self, client):
        bid_a, bid_b = self._get_two_build_ids(client)
        r = client.post("/api/combat/run", json={
            "build_id_a": bid_a,
            "build_id_b": bid_b,
            "seed": 5,
        })
        log = r.json()
        assert log["n_turns"] <= 31  # MAX_TURNS=30; turn counter increments before check

    def test_run_combat_invalid_build(self, client):
        r = client.post("/api/combat/run", json={
            "build_id_a": 99999,
            "build_id_b": 101,
            "seed": 0,
        })
        assert r.status_code == 404

    def test_stream_endpoint_exists(self, client):
        # Streaming requires an SSE client; just verify the endpoint responds.
        bid_a, bid_b = self._get_two_build_ids(client)
        r = client.get(
            f"/api/combat/stream?build_id_a={bid_a}&build_id_b={bid_b}&seed=0&delay_ms=0",
            headers={"Accept": "text/event-stream"},
        )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        # Should contain at least meta + some step events + done
        content = r.text
        assert '"type": "meta"' in content or "meta" in content
        assert '"type": "done"' in content or "done" in content


class TestRatingsAPI:
    def test_leaderboard_returns_sorted_list(self, client):
        r = client.get("/api/ratings/leaderboard")
        assert r.status_code == 200
        rows = r.json()
        if rows:
            ratings = [row["r"] for row in rows]
            assert ratings == sorted(ratings, reverse=True)

    def test_leaderboard_has_required_fields(self, client):
        r = client.get("/api/ratings/leaderboard")
        rows = r.json()
        for row in rows:
            assert "rank" in row
            assert "name" in row
            assert "splat" in row
            assert "r" in row
            assert "RD" in row
            assert "n_matches" in row

    def test_leaderboard_splat_filter(self, client):
        r = client.get("/api/ratings/leaderboard?splat=mortal")
        rows = r.json()
        for row in rows:
            assert row["splat"] == "mortal"

    def test_build_rating_endpoint(self, client):
        # Get a known build ID
        builds = client.get("/api/builds").json()
        bid = builds[0]["id"]
        r = client.get(f"/api/ratings/build/{bid}")
        assert r.status_code == 200
        d = r.json()
        assert "r" in d
        assert "RD" in d
        assert "ci_lo" in d
        assert "ci_hi" in d
        assert d["ci_lo"] < d["r"] < d["ci_hi"]

    def test_team_leaderboard(self, client):
        r = client.get("/api/ratings/teams")
        assert r.status_code == 200
        rows = r.json()
        # May be empty if no team matches were played
        for row in rows:
            assert "build_ids" in row
            assert "r" in row


class TestCombatRunnerUnit:
    """Unit tests for the combat runner without going through the API."""

    def test_action_description_attack(self):
        from cod_sim.api.combat_runner import _describe_action
        desc = _describe_action(0, "Alice", "mortal", ["Alice", "Bob"])
        assert "Bob" in desc or "attacks" in desc.lower()

    def test_action_description_full_defense(self):
        from cod_sim.api.combat_runner import _describe_action, _FULL_DEF_OFFSET
        desc = _describe_action(_FULL_DEF_OFFSET, "Alice", "mortal", ["Alice", "Bob"])
        assert "defense" in desc.lower() or "Defense" in desc

    def test_action_description_pass(self):
        from cod_sim.api.combat_runner import _describe_action, _PASS_OFFSET
        desc = _describe_action(_PASS_OFFSET, "Alice", "mortal", ["Alice", "Bob"])
        assert "pass" in desc.lower() or "Pass" in desc

    def test_run_combat_function(self):
        from cod_sim.api.combat_runner import run_combat
        from cod_sim import BuildRegistry, checkpoint
        from pathlib import Path

        reg = BuildRegistry()
        reg.load_directory(Path("builds"))
        ids = reg.all_ids()
        bid_a, bid_b = ids[0], ids[1]
        builds_json = reg.builds_json([bid_a, bid_b])
        ba, bb = reg.get(bid_a), reg.get(bid_b)

        ckpt = checkpoint.latest_checkpoint("checkpoints")
        policy = None
        if ckpt:
            loaded_policy = checkpoint.load(ckpt)[0]
            from cod_sim.cod_sim import ACTION_SPACE_SIZE as _ASZ
            policy = loaded_policy if loaded_policy.action_size == _ASZ else None

        log = run_combat(
            builds_json=builds_json,
            teams=[0, 1],
            policy=policy,
            seed=99,
            build_names=[ba.name, bb.name],
            build_splats=[ba.splat, bb.splat],
        )
        assert log.n_steps > 0
        assert log.n_turns <= 30
        assert log.winner_team in [0, 1, None]
        assert len(log.events) == log.n_steps
