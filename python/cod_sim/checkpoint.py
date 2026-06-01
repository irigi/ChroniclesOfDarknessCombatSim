"""Policy checkpoint save/load utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from .policy import CoDPolicy


def save(
    policy: CoDPolicy,
    optimizer: torch.optim.Optimizer,
    step: int,
    path: str | Path,
    extra: dict[str, Any] | None = None,
) -> None:
    """Save a full training checkpoint (policy weights + optimizer state)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Infer hidden size from first backbone linear layer
    hidden = next(
        m.out_features for m in policy.backbone.modules()
        if isinstance(m, __import__("torch").nn.Linear)
    )
    payload = {
        "step": step,
        "obs_size": policy.obs_size,
        "action_size": policy.action_size,
        "hidden": hidden,
        "policy_state": policy.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "extra": extra or {},
    }
    torch.save(payload, path)


def save_weights(policy: CoDPolicy, path: str | Path) -> None:
    """Save only the policy weights (for snapshot pool — no optimizer state)."""
    import torch.nn as nn
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hidden = next(
        m.out_features for m in policy.backbone.modules()
        if isinstance(m, nn.Linear)
    )
    torch.save(
        {
            "obs_size": policy.obs_size,
            "action_size": policy.action_size,
            "hidden": hidden,
            "policy_state": policy.state_dict(),
        },
        path,
    )


def load(
    path: str | Path,
    map_location: str = "cpu",
) -> tuple[CoDPolicy, torch.optim.Optimizer | None, int]:
    """
    Load a full checkpoint.

    Returns:
        (policy, optimizer_or_None, step)
    """
    path = Path(path)
    payload = torch.load(path, map_location=map_location, weights_only=False)
    policy = CoDPolicy(
        payload["obs_size"],
        payload["action_size"],
        hidden=payload.get("hidden", 256),
    )
    policy.load_state_dict(payload["policy_state"])

    optimizer: torch.optim.Optimizer | None = None
    if "optimizer_state" in payload:
        optimizer = torch.optim.Adam(policy.parameters())
        optimizer.load_state_dict(payload["optimizer_state"])

    return policy, optimizer, payload.get("step", 0)


def load_weights(path: str | Path, map_location: str = "cpu") -> CoDPolicy:
    """Load a snapshot (weights only)."""
    path = Path(path)
    payload = torch.load(path, map_location=map_location, weights_only=False)
    policy = CoDPolicy(
        payload["obs_size"],
        payload["action_size"],
        hidden=payload.get("hidden", 256),
    )
    policy.load_state_dict(payload["policy_state"])
    return policy


def list_checkpoints(directory: str | Path) -> list[Path]:
    """Return checkpoint files sorted by step number (ascending)."""
    directory = Path(directory)
    if not directory.exists():
        return []
    files = list(directory.glob("checkpoint_*.pt"))
    files.sort(key=lambda p: int(p.stem.split("_")[-1]))
    return files


def latest_checkpoint(directory: str | Path) -> Path | None:
    """Return the most recent checkpoint, or None if none exist."""
    checkpoints = list_checkpoints(directory)
    return checkpoints[-1] if checkpoints else None
