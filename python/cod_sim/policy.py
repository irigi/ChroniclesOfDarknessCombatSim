"""Actor-critic policy network for Chronicles of Darkness combat."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical


class CoDPolicy(nn.Module):
    """
    Universal actor-critic MLP for CoD combat.

    One network generalises across all builds because the build vector is
    embedded in the observation (splat one-hot, attributes, powers, etc.).
    The observation is always from the POV of the current actor, so "self"
    is always in slot 0 regardless of initiative order or team.

    Architecture:
        obs → LayerNorm → Linear(hidden) → GELU → Linear(hidden) → GELU
            ├─ actor_head → Linear(action_size)   (logits, then mask + softmax)
            └─ critic_head → Linear(1)             (state value)
    """

    def __init__(self, obs_size: int, action_size: int, hidden: int = 256) -> None:
        super().__init__()
        self.obs_size = obs_size
        self.action_size = action_size

        self.backbone = nn.Sequential(
            nn.LayerNorm(obs_size),
            nn.Linear(obs_size, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )
        self.actor_head = nn.Linear(hidden, action_size)
        self.critic_head = nn.Linear(hidden, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.backbone.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=2 ** 0.5)
                nn.init.zeros_(m.bias)
        nn.init.orthogonal_(self.actor_head.weight, gain=0.01)
        nn.init.zeros_(self.actor_head.bias)
        nn.init.orthogonal_(self.critic_head.weight, gain=1.0)
        nn.init.zeros_(self.critic_head.bias)

    def forward(
        self,
        obs: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            obs:  (B, obs_size)   float32
            mask: (B, action_size) bool — True = legal action

        Returns:
            log_probs: (B, action_size)  normalised over legal actions
            values:    (B,)
        """
        hidden = self.backbone(obs)
        logits = self.actor_head(hidden)
        logits = logits.masked_fill(~mask, -1e9)
        log_probs = F.log_softmax(logits, dim=-1)
        values = self.critic_head(hidden).squeeze(-1)
        return log_probs, values

    @torch.no_grad()
    def act(
        self,
        obs: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Sample actions stochastically.

        Returns:
            actions:   (B,)  int64
            log_probs: (B,)  float32  — log prob of the sampled action
            values:    (B,)  float32
        """
        log_probs_all, values = self.forward(obs, mask)
        dist = Categorical(logits=log_probs_all)
        actions = dist.sample()
        selected_log_probs = log_probs_all.gather(1, actions.unsqueeze(1)).squeeze(1)
        return actions, selected_log_probs, values

    def evaluate(
        self,
        obs: torch.Tensor,
        mask: torch.Tensor,
        actions: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Evaluate selected actions under the current (potentially updated) policy.

        Used inside the PPO inner loop.

        Returns:
            log_probs: (B,)  log prob of each action under current policy
            values:    (B,)
            entropy:   (B,)  per-sample entropy of the masked distribution
        """
        log_probs_all, values = self.forward(obs, mask)
        dist = Categorical(logits=log_probs_all)
        log_probs = log_probs_all.gather(1, actions.unsqueeze(1)).squeeze(1)
        entropy = dist.entropy()
        return log_probs, values, entropy
