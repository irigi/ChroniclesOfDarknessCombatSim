"""Tests for BuildRegistry: loading, validation, encoding."""

from pathlib import Path
import numpy as np
import pytest

from cod_sim import BuildRegistry, BuildDefinition, BUILD_VEC_LEN

BUILDS_DIR = Path(__file__).parent.parent.parent / "builds"


class TestBuildRegistry:
    def test_load_all_template_builds(self):
        reg = BuildRegistry()
        builds = reg.load_directory(BUILDS_DIR)
        assert len(builds) >= 5, "expected at least 5 template builds"

    def test_build_ids_unique(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        ids = reg.all_ids()
        assert len(ids) == len(set(ids)), "duplicate build IDs"

    def test_mortal_build_properties(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        brawler = reg.get(101)
        assert brawler.splat == "mortal"
        assert brawler.strength == 4
        assert brawler.brawl == 4
        assert brawler.max_health == 5 + 3  # size + stamina
        assert brawler.max_resource == 0

    def test_vampire_build_properties(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        vamp = reg.get(201)
        assert vamp.splat == "vampire"
        assert vamp.celerity == 3
        assert vamp.max_health == 5 + vamp.stamina + vamp.resilience

    def test_werewolf_build_properties(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        wolf = reg.get(301)
        assert wolf.splat == "werewolf"
        assert wolf.primal_urge == 2
        assert wolf.max_resource == 11  # essence_max at primal_urge 2

    def test_changeling_build_properties(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        ctl = reg.get(401)
        assert ctl.splat == "changeling"
        assert ctl.wyrd == 3

    def test_encode_returns_correct_shape(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        for b in reg.all_builds():
            vec = b.encode()
            assert vec.shape == (BUILD_VEC_LEN,), f"wrong shape for {b.name}"
            assert vec.dtype == np.float32

    def test_encode_values_in_range(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        for b in reg.all_builds():
            vec = b.encode()
            assert np.all(vec >= -0.1), f"negative value in {b.name}: {vec.min()}"
            assert np.all(vec <= 1.1), f"value > 1 in {b.name}: {vec.max()}"

    def test_splat_onehot(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        splat_map = {"mortal": 0, "vampire": 1, "werewolf": 2, "changeling": 3}
        for b in reg.all_builds():
            vec = b.encode()
            expected_idx = splat_map[b.splat]
            assert vec[expected_idx] == 1.0, f"splat one-hot wrong for {b.name}"
            # Only one splat bit set
            assert vec[:4].sum() == 1.0

    def test_to_rust_json_parses(self):
        import json
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        for b in reg.all_builds():
            parsed = json.loads(b.to_rust_json())
            assert parsed["id"] == b.id
            assert parsed["name"] == b.name

    def test_builds_json_array(self):
        import json
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        ids = reg.all_ids()[:2]
        arr_json = reg.builds_json(ids)
        parsed = json.loads(arr_json)
        assert len(parsed) == 2

    def test_invalid_build_returns_errors(self):
        reg = BuildRegistry()
        errors = reg.validate({"id": 999, "name": "bad", "splat": "unknown", "attributes": {}})
        assert errors, "unknown splat should produce validation errors"


class TestPhase7BuildRegistry:
    def _reg(self):
        reg = BuildRegistry()
        reg.load_directory(BUILDS_DIR)
        return reg

    def test_obs_per_char_is_30(self):
        from cod_sim.cod_sim import OBS_PER_CHAR
        assert OBS_PER_CHAR == 30, f"OBS_PER_CHAR should be 30, got {OBS_PER_CHAR}"

    def test_action_space_is_120(self):
        from cod_sim.cod_sim import ACTION_SPACE_SIZE
        assert ACTION_SPACE_SIZE == 120, f"ACTION_SPACE_SIZE should be 120, got {ACTION_SPACE_SIZE}"

    def test_all_new_builds_load(self):
        reg = self._reg()
        new_ids = [103, 104, 204, 205, 206, 303, 304, 403, 404, 405, 406]
        for nid in new_ids:
            b = reg.get(nid)
            assert b.id == nid, f"build {nid} not found"

    def test_merits_parse_correctly(self):
        reg = self._reg()
        iron_fighter = reg.get(103)
        assert iron_fighter.iron_skin == 4
        assert iron_fighter.iron_stamina == 2
        assert iron_fighter.fast_reflexes == 2

    def test_merits_serialize_to_rust_json(self):
        import json
        reg = self._reg()
        b = reg.get(104)  # brawling_defender
        parsed = json.loads(b.to_rust_json())
        assert "merits" in parsed
        assert parsed["merits"].get("defensive_combat") == 1
        assert parsed["merits"].get("street_fighting") == 1

    def test_new_disciplines_parse_correctly(self):
        reg = self._reg()
        protean = reg.get(204)  # gangrel_protean
        assert protean.protean == 4
        nightmare = reg.get(205)  # nosferatu_nightmare
        assert nightmare.nightmare == 3
        dominator = reg.get(206)  # ventrue_dominate
        assert dominator.dominate == 3

    def test_new_disciplines_serialize_to_json(self):
        import json
        reg = self._reg()
        b = reg.get(204)
        parsed = json.loads(b.to_rust_json())
        disc = parsed["splat_data"]["Vampire"]["disciplines"]
        assert disc["protean"] == 4

    def test_renown_parse_correctly(self):
        reg = self._reg()
        warrior = reg.get(303)  # full_moon_warrior
        assert warrior.purity == 3
        assert warrior.glory == 0
        leader = reg.get(304)  # howling_pack_leader
        assert leader.glory == 3

    def test_renown_serializes_to_rust_json(self):
        import json
        reg = self._reg()
        b = reg.get(303)
        parsed = json.loads(b.to_rust_json())
        assert parsed["splat_data"]["Werewolf"]["purity"] == 3
