"""Build registry: loads, validates, and encodes character builds from YAML files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

try:
    import jsonschema
    _HAVE_JSONSCHEMA = True
except ImportError:
    _HAVE_JSONSCHEMA = False

# Length of the per-build numpy vector (must match OBS_PER_CHAR layout in Rust).
BUILD_VEC_LEN = 24

_SPLAT_IDX = {"mortal": 0, "vampire": 1, "werewolf": 2, "changeling": 3}
_DAMAGE_TYPE_IDX = {"bashing": 0, "lethal": 1, "aggravated": 2}


def _load_schema() -> dict:
    schema_path = Path(__file__).parent.parent.parent / "builds" / "schema.yaml"
    if schema_path.exists():
        try:
            with open(schema_path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


_SCHEMA: dict = {}


def _get_schema() -> dict:
    global _SCHEMA
    if not _SCHEMA:
        _SCHEMA = _load_schema()
    return _SCHEMA


class BuildDefinition:
    """Python-side mirror of the Rust BuildDefinition, loaded from YAML."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.id: int = raw["id"]
        self.name: str = raw["name"]
        self.splat: str = raw["splat"].lower()
        self.size: int = raw.get("size", 5)

        attr = raw["attributes"]
        self.strength: int = attr["strength"]
        self.dexterity: int = attr["dexterity"]
        self.stamina: int = attr["stamina"]
        self.intelligence: int = attr.get("intelligence", 2)
        self.wits: int = attr["wits"]
        self.resolve: int = attr["resolve"]
        self.presence: int = attr.get("presence", 2)
        self.manipulation: int = attr.get("manipulation", 2)
        self.composure: int = attr["composure"]

        skills = raw.get("skills", {})
        self.brawl: int = skills.get("brawl", 0)
        self.weaponry: int = skills.get("weaponry", 0)
        self.firearms: int = skills.get("firearms", 0)
        self.athletics: int = skills.get("athletics", 0)
        self.stealth: int = skills.get("stealth", 0)

        weapon = raw.get("weapon", {})
        self.weapon_damage_mod: int = weapon.get("damage_mod", 0)
        self.weapon_damage_type: str = weapon.get("damage_type", "bashing")
        self.weapon_initiative_penalty: int = weapon.get("initiative_penalty", 0)
        self.weapon_is_ranged: bool = weapon.get("is_ranged", False)
        self.weapon_is_silver: bool = weapon.get("is_silver", False)
        self.weapon_is_fire: bool = weapon.get("is_fire", False)
        self.weapon_is_sunlight: bool = weapon.get("is_sunlight", False)

        armor = raw.get("armor", {})
        self.armor_general: int = armor.get("general", 0)
        self.armor_ballistic: int = armor.get("ballistic", 0)

        # Splat-specific — vampire
        vamp = raw.get("vampire", {})
        self.blood_potency: int = vamp.get("blood_potency", 0)
        self.celerity: int = vamp.get("celerity", 0)
        self.vigor: int = vamp.get("vigor", 0)
        self.resilience: int = vamp.get("resilience", 0)
        self.protean: int = vamp.get("protean", 0)
        self.nightmare: int = vamp.get("nightmare", 0)
        self.dominate: int = vamp.get("dominate", 0)

        # Splat-specific — werewolf
        wolf = raw.get("werewolf", {})
        self.primal_urge: int = wolf.get("primal_urge", 1)
        self.purity: int = wolf.get("purity", 0)
        self.glory: int = wolf.get("glory", 0)
        self.cunning: int = wolf.get("cunning", 0)
        self.honor: int = wolf.get("honor", 0)
        self.wisdom: int = wolf.get("wisdom", 0)

        # Splat-specific — changeling
        ctl = raw.get("changeling", {})
        self.wyrd: int = ctl.get("wyrd", 1)
        self.glamour_max: int = ctl.get("glamour_max", 10)
        self.seeming: str = ctl.get("seeming", "Ogre")

        # Combat merits (all optional)
        merits_raw = raw.get("merits", {})
        self.merits: dict[str, int] = {k: int(v) for k, v in merits_raw.items()}
        self.iron_skin: int = self.merits.get("iron_skin", 0)
        self.iron_stamina: int = self.merits.get("iron_stamina", 0)
        self.fast_reflexes: int = self.merits.get("fast_reflexes", 0)
        self.defensive_combat: int = self.merits.get("defensive_combat", 0)
        self.fighting_finesse: int = self.merits.get("fighting_finesse", 0)
        self.martial_arts_lethal: int = self.merits.get("martial_arts_lethal", 0)
        self.street_fighting: int = self.merits.get("street_fighting", 0)
        self.brawling_dodge: int = self.merits.get("brawling_dodge", 0)

    # ------------------------------------------------------------------
    # Derived stats (mirrors Rust BuildDefinition methods)
    # ------------------------------------------------------------------

    @property
    def max_health(self) -> int:
        stamina_bonus = self.resilience if self.splat == "vampire" else 0
        return self.size + self.stamina + stamina_bonus

    @property
    def max_willpower(self) -> int:
        return self.resolve + self.composure

    @property
    def max_resource(self) -> int:
        if self.splat == "mortal":
            return 0
        if self.splat == "vampire":
            return _vitae_max(self.blood_potency)
        if self.splat == "werewolf":
            return _essence_max(self.primal_urge)
        if self.splat == "changeling":
            return self.glamour_max
        return 0

    def encode(self) -> np.ndarray:
        """Encode this build as a fixed-length float32 numpy vector.

        Layout (BUILD_VEC_LEN = 24 floats):
          [0..4]   splat one-hot (mortal, vampire, werewolf, changeling)
          [4..10]  attributes /5: Str, Dex, Sta, Wits, Composure, Resolve
          [10..14] skills /5: Brawl, Weaponry, Firearms, Athletics
          [14..20] powers /5: Celerity, Vigor, Resilience, PrimalUrge, Wyrd, BloodPotency
          [20]     weapon_damage_mod /10 (normalised)
          [21]     weapon_is_ranged (0/1)
          [22]     armor_general /5
          [23]     max_resource /20
        """
        v = np.zeros(BUILD_VEC_LEN, dtype=np.float32)
        splat_i = _SPLAT_IDX.get(self.splat, 0)
        v[splat_i] = 1.0

        v[4] = self.strength / 5.0
        v[5] = self.dexterity / 5.0
        v[6] = self.stamina / 5.0
        v[7] = self.wits / 5.0
        v[8] = self.composure / 5.0
        v[9] = self.resolve / 5.0

        v[10] = self.brawl / 5.0
        v[11] = self.weaponry / 5.0
        v[12] = self.firearms / 5.0
        v[13] = self.athletics / 5.0

        v[14] = self.celerity / 5.0
        v[15] = self.vigor / 5.0
        v[16] = self.resilience / 5.0
        v[17] = self.primal_urge / 10.0
        v[18] = self.wyrd / 10.0
        v[19] = self.blood_potency / 10.0

        v[20] = self.weapon_damage_mod / 10.0
        v[21] = float(self.weapon_is_ranged)
        v[22] = self.armor_general / 5.0
        v[23] = self.max_resource / 20.0

        return v

    def to_rust_json(self) -> str:
        """Serialize to JSON matching the Rust BuildDefinition serde format."""
        splat_map = {"mortal": "Mortal", "vampire": "Vampire", "werewolf": "Werewolf", "changeling": "Changeling"}
        splat_rust = splat_map[self.splat]
        damage_map = {"bashing": "Bashing", "lethal": "Lethal", "aggravated": "Aggravated"}

        splat_data: dict[str, Any]
        if self.splat == "mortal":
            splat_data = "Mortal"
        elif self.splat == "vampire":
            vitae_max = _vitae_max(self.blood_potency)
            splat_data = {
                "Vampire": {
                    "blood_potency": self.blood_potency,
                    "vitae_max": vitae_max,
                    "disciplines": {
                        "celerity": self.celerity,
                        "vigor": self.vigor,
                        "resilience": self.resilience,
                        "protean": self.protean,
                        "nightmare": self.nightmare,
                        "dominate": self.dominate,
                    },
                }
            }
        elif self.splat == "werewolf":
            essence_max = _essence_max(self.primal_urge)
            splat_data = {
                "Werewolf": {
                    "primal_urge": self.primal_urge,
                    "essence_max": essence_max,
                    "purity": self.purity,
                    "glory": self.glory,
                    "cunning": self.cunning,
                    "honor": self.honor,
                    "wisdom": self.wisdom,
                }
            }
        elif self.splat == "changeling":
            # Normalise seeming to Title case for Rust enum matching
            seeming_rust = self.seeming.strip().capitalize() if self.seeming else "Ogre"
            splat_data = {
                "Changeling": {
                    "wyrd": self.wyrd,
                    "glamour_max": self.glamour_max,
                    "seeming": seeming_rust,
                }
            }
        else:
            splat_data = "Mortal"

        obj = {
            "id": self.id,
            "name": self.name,
            "splat": splat_rust,
            "attributes": {
                "strength": self.strength,
                "dexterity": self.dexterity,
                "stamina": self.stamina,
                "intelligence": self.intelligence,
                "wits": self.wits,
                "resolve": self.resolve,
                "presence": self.presence,
                "manipulation": self.manipulation,
                "composure": self.composure,
            },
            "skills": {
                "brawl": self.brawl,
                "weaponry": self.weaponry,
                "firearms": self.firearms,
                "athletics": self.athletics,
                "stealth": self.stealth,
            },
            "weapon": {
                "damage_mod": self.weapon_damage_mod,
                "damage_type": damage_map[self.weapon_damage_type],
                "initiative_penalty": self.weapon_initiative_penalty,
                "is_ranged": self.weapon_is_ranged,
                "is_silver": self.weapon_is_silver,
                "is_fire": self.weapon_is_fire,
                "is_sunlight": self.weapon_is_sunlight,
            },
            "armor": {
                "general": self.armor_general,
                "ballistic": self.armor_ballistic,
            },
            "splat_data": splat_data,
            "size": self.size,
            "merits": self.merits,
        }
        return json.dumps(obj)


class BuildRegistry:
    """Loads and validates build definitions from YAML files."""

    def __init__(self) -> None:
        self._builds: dict[int, BuildDefinition] = {}

    def load_file(self, path: str | Path) -> BuildDefinition:
        path = Path(path)
        with open(path) as f:
            raw = yaml.safe_load(f)
        errors = self.validate(raw)
        if errors:
            raise ValueError(f"Build validation errors in {path}:\n" + "\n".join(errors))
        build = BuildDefinition(raw)
        self._builds[build.id] = build
        return build

    def load_directory(self, directory: str | Path) -> list[BuildDefinition]:
        directory = Path(directory)
        loaded = []
        for yaml_file in sorted(directory.rglob("*.yaml")):
            if yaml_file.name == "schema.yaml":
                continue
            try:
                b = self.load_file(yaml_file)
                loaded.append(b)
            except Exception as e:
                raise ValueError(f"Failed to load {yaml_file}: {e}") from e
        return loaded

    def validate(self, raw: dict) -> list[str]:
        errors: list[str] = []
        schema = _get_schema()
        if schema and _HAVE_JSONSCHEMA:
            try:
                jsonschema.validate(raw, schema)
            except jsonschema.ValidationError as e:
                errors.append(str(e.message))
        # Additional semantic checks
        splat = raw.get("splat", "").lower()
        if splat not in _SPLAT_IDX:
            errors.append(f"Unknown splat: {splat!r}")
        if splat == "vampire" and "vampire" not in raw:
            errors.append("vampire splat requires a 'vampire:' section")
        if splat == "werewolf" and "werewolf" not in raw:
            errors.append("werewolf splat requires a 'werewolf:' section")
        if splat == "changeling" and "changeling" not in raw:
            errors.append("changeling splat requires a 'changeling:' section")
        return errors

    def get(self, build_id: int) -> BuildDefinition:
        return self._builds[build_id]

    def all_builds(self) -> list[BuildDefinition]:
        return list(self._builds.values())

    def all_ids(self) -> list[int]:
        return list(self._builds.keys())

    def __len__(self) -> int:
        return len(self._builds)

    def builds_json(self, build_ids: list[int]) -> str:
        """Return a JSON array of Rust-serialized build definitions."""
        jsons = [self._builds[bid].to_rust_json() for bid in build_ids]
        return "[" + ",".join(jsons) + "]"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _vitae_max(blood_potency: int) -> int:
    table = {0: 10, 1: 10, 2: 11, 3: 12, 4: 13, 5: 15, 6: 20, 7: 25, 8: 30, 9: 50}
    return table.get(blood_potency, 75)


def _essence_max(primal_urge: int) -> int:
    table = {0: 10, 1: 10, 2: 11, 3: 12, 4: 13, 5: 15, 6: 20, 7: 25, 8: 30, 9: 50}
    return table.get(primal_urge, 75)
