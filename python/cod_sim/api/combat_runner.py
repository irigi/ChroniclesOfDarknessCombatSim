"""Step-by-step combat runner with event logging for the web API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch

from ..cod_sim import CombatEnv, ACTION_SPACE_SIZE

# ─── Action decoding (mirrors Rust action.rs constants) ───────────────────────

_MAX_TARGETS      = 8
_MAX_POWER_SLOTS  = 8
_ALL_OUT_OFFSET   = _MAX_TARGETS * 2            # 16
_POWER_OFFSET     = _MAX_TARGETS * 4            # 32
_RES_PHYS_OFFSET  = _POWER_OFFSET + _MAX_POWER_SLOTS * _MAX_TARGETS  # 96
_HEAL_OFFSET      = _RES_PHYS_OFFSET + 3        # 99
_REGEN_OFFSET     = _HEAL_OFFSET + 1            # 100
_FULL_DEF_OFFSET  = _REGEN_OFFSET + 1           # 101
_PASS_OFFSET      = _FULL_DEF_OFFSET + 1        # 102
_IRON_SKIN_OFFSET = _PASS_OFFSET + 1            # 103
_BITE_OFFSET      = _IRON_SKIN_OFFSET + 1       # 104

# Vampire power slots: 0=Celerity-jump, 1=Vigor-attack, 2=Resilience-armor
# Werewolf power slots: 0=Hishu, 1=Dalu, 2=Gauru, 3=Urshul, 4=Urhan
_WOLF_FORM_NAMES = ["Hishu", "Dalu", "Gauru", "Urshul", "Urhan"]
_VAMP_POWER_NAMES = ["Celerity (Initiative)", "Vigor (Attack)", "Resilience (Armor)",
                     "Protean (Claws)", "Nightmare (Frighten)", "Dominate (Mesmerize)"]


def _describe_action(
    action_idx: int,
    actor_name: str,
    actor_splat: str,
    char_names: list[str],
) -> str:
    if action_idx < _ALL_OUT_OFFSET:
        target_idx = action_idx // 2
        spends_wp  = action_idx % 2 == 1
        tname = char_names[target_idx] if target_idx < len(char_names) else f"target {target_idx}"
        wp_str = " (spending Willpower)" if spends_wp else ""
        return f"Attacks {tname}{wp_str}"

    if action_idx < _POWER_OFFSET:
        rel = action_idx - _ALL_OUT_OFFSET
        target_idx = rel // 2
        spends_wp  = rel % 2 == 1
        tname = char_names[target_idx] if target_idx < len(char_names) else f"target {target_idx}"
        wp_str = " (spending Willpower)" if spends_wp else ""
        return f"All-Out Attack on {tname}{wp_str}"

    if action_idx < _RES_PHYS_OFFSET:
        rel = action_idx - _POWER_OFFSET
        slot = rel // _MAX_TARGETS
        target_idx = rel % _MAX_TARGETS
        tname = char_names[target_idx] if target_idx < len(char_names) else f"target {target_idx}"
        if actor_splat == "vampire":
            pname = _VAMP_POWER_NAMES[slot] if slot < len(_VAMP_POWER_NAMES) else f"Power {slot}"
            return f"Activates {pname}"
        elif actor_splat == "werewolf":
            form = _WOLF_FORM_NAMES[slot] if slot < len(_WOLF_FORM_NAMES) else f"form {slot}"
            return f"Shapeshifts to {form}"
        return f"Activates power slot {slot}"

    if action_idx < _HEAL_OFFSET:
        attr = action_idx - _RES_PHYS_OFFSET
        attr_name = ["Strength", "Dexterity", "Stamina"][attr] if attr < 3 else "attribute"
        return f"Spends resource for +2 {attr_name} dice (reflexive)"

    if action_idx == _HEAL_OFFSET:
        return "Heals with Vitae"
    if action_idx == _REGEN_OFFSET:
        return "Spends Essence to regenerate lethal damage"
    if action_idx == _FULL_DEF_OFFSET:
        return "Takes Full Defense (doubles defense for the turn)"
    if action_idx == _PASS_OFFSET:
        return "Passes"
    if action_idx == _IRON_SKIN_OFFSET:
        return "Iron Skin: spends Willpower to downgrade lethal → bashing"
    if action_idx >= _BITE_OFFSET and action_idx < _BITE_OFFSET + _MAX_TARGETS * 2:
        rel = action_idx - _BITE_OFFSET
        target_idx = rel // 2
        spends_wp  = rel % 2 == 1
        tname = char_names[target_idx] if target_idx < len(char_names) else f"target {target_idx}"
        wp_str = " (spending Willpower)" if spends_wp else ""
        return f"Bites {tname} (Lethal + Vitae drain){wp_str}"
    return "Passes"


# ─── Data types ───────────────────────────────────────────────────────────────

@dataclass
class CharSnapshot:
    name:         str
    team:         int
    splat:        str = "mortal"
    bashing:      int = 0
    lethal:       int = 0
    aggravated:   int = 0
    max_health:   int = 7
    willpower:    int = 5
    resource:     int = 0
    initiative:   int = 0
    is_incap:     bool = False
    in_torpor:    bool = False

    @property
    def hp_remaining(self) -> int:
        return self.max_health - self.bashing - self.lethal - self.aggravated

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "team": self.team,
            "splat": self.splat,
            "bashing": self.bashing,
            "lethal": self.lethal,
            "aggravated": self.aggravated,
            "max_health": self.max_health,
            "hp_remaining": self.hp_remaining,
            "willpower": self.willpower,
            "resource": self.resource,
            "initiative": self.initiative,
            "is_incap": self.is_incap,
            "in_torpor": self.in_torpor,
        }


@dataclass
class CombatEvent:
    step:          int
    turn:          int
    actor_name:    str
    actor_team:    int
    actor_idx:     int
    action_idx:    int
    action_desc:   str
    characters:    list[CharSnapshot]
    is_terminal:   bool = False

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "turn": self.turn,
            "actor_name": self.actor_name,
            "actor_team": self.actor_team,
            "action_desc": self.action_desc,
            "is_terminal": self.is_terminal,
            "characters": [c.as_dict() for c in self.characters],
        }


@dataclass
class CombatLog:
    winner_team:   Optional[int]
    winner_name:   Optional[str]
    n_turns:       int
    n_steps:       int
    events:        list[CombatEvent] = field(default_factory=list)
    build_a:       dict = field(default_factory=dict)
    build_b:       dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "winner_team": self.winner_team,
            "winner_name": self.winner_name,
            "n_turns": self.n_turns,
            "n_steps": self.n_steps,
            "build_a": self.build_a,
            "build_b": self.build_b,
            "events": [e.as_dict() for e in self.events],
        }


# ─── Runner ───────────────────────────────────────────────────────────────────

def _snap_from_summary(summary: dict) -> list[CharSnapshot]:
    return [
        CharSnapshot(
            name=ch["name"],
            team=ch["team"],
            splat=_guess_splat(ch),
            bashing=ch["bashing"],
            lethal=ch["lethal"],
            aggravated=ch["aggravated"],
            max_health=ch["max_health"],
            willpower=ch["willpower"],
            resource=ch["resource"],
            initiative=ch["initiative"],
            is_incap=ch["is_incapacitated"],
            in_torpor=ch["in_torpor"],
        )
        for ch in summary["characters"]
    ]


def _guess_splat(ch: dict) -> str:
    """Infer splat from resource presence (approximate — no direct field in summary)."""
    r = ch.get("resource", 0)
    if r > 0:
        return "supernatural"
    return "mortal"


def run_combat(
    builds_json: str,
    teams: list[int],
    policy,
    seed: int = 0,
    build_names: list[str] | None = None,
    build_splats: list[str] | None = None,
    max_steps: int = 1000,
) -> CombatLog:
    """
    Run a full combat and return a structured log.

    Args:
        builds_json: JSON array of BuildDefinition objects.
        teams:       Team assignments [0, 1] matching builds order.
        policy:      CoDPolicy (used on both sides) or None (→ first-legal).
        seed:        Random seed for deterministic replays.
        build_names: Human-readable names for each build.
        build_splats: Splat strings for each build.
        max_steps:   Safety cap on total steps.
    """
    # Seed both the sim RNG (via reset) and PyTorch (for policy sampling)
    if seed is not None:
        torch.manual_seed(seed)
    env = CombatEnv(builds_json, teams)
    obs_list, _ = env.reset(seed=seed)
    names   = build_names  or [f"Character {i}" for i in range(len(teams))]
    splats  = build_splats or ["mortal"] * len(teams)

    all_names = names  # character name list indexed by char_idx

    events: list[CombatEvent] = []
    step = 0
    done = False

    while not done and step < max_steps:
        summary    = env.get_state_summary()
        actor_idx  = env.current_actor_idx()
        actor_name = names[actor_idx] if actor_idx < len(names) else f"char {actor_idx}"
        actor_team = teams[actor_idx] if actor_idx < len(teams) else 0
        actor_splat = splats[actor_idx] if actor_idx < len(splats) else "mortal"
        turn       = summary["turn"]
        chars      = _snap_from_summary(summary)

        # Fix splat from build data
        for i, ch in enumerate(chars):
            if i < len(splats):
                ch.splat = splats[i]

        # Choose action
        mask = env.action_mask()
        if policy is not None:
            obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
            mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                acts, _, _ = policy.act(obs_t, mask_t)
            action = int(acts[0])
        else:
            action = next(i for i, m in enumerate(mask) if m)

        action_desc = _describe_action(action, actor_name, actor_splat, all_names)

        obs_list, _, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        step += 1

        events.append(CombatEvent(
            step=step,
            turn=turn,
            actor_name=actor_name,
            actor_team=actor_team,
            actor_idx=actor_idx,
            action_idx=action,
            action_desc=action_desc,
            characters=chars,
            is_terminal=done,
        ))

    # Final state after last step
    final_summary = env.get_state_summary()
    winner_team   = final_summary.get("winner_team")
    winner_name   = names[0] if winner_team == 0 else (names[1] if winner_team == 1 else None)
    n_turns       = final_summary.get("turn", 0)

    return CombatLog(
        winner_team=winner_team,
        winner_name=winner_name,
        n_turns=n_turns,
        n_steps=step,
        events=events,
    )
