"""Build and team matchmaking for rating tournaments.

Prioritises high-uncertainty (high-RD) builds, then prefers close-rated opponents.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .build_registry import BuildRegistry
    from .glicko import GlickoRater

# Prefer opponents whose rating is within this many Elo points
_CLOSE_RATING_THRESHOLD = 400.0


class Matchmaker:
    """
    Selects build pairs for rating games.

    Sampling strategy:
        1. Compute an uncertainty score for each build = RD (higher = more uncertain).
        2. Weight the random selection toward high-RD builds.
        3. Among the top candidates, prefer opponents close in rating.
    """

    def sample_1v1(
        self,
        registry: "BuildRegistry",
        rater: "GlickoRater",
        exclude_same: bool = False,
    ) -> tuple[int, int]:
        """
        Sample a 1v1 matchup.  Returns (build_id_a, build_id_b).

        Args:
            exclude_same: If True, the two builds must be different IDs.
        """
        ids = registry.all_ids()
        if len(ids) < 2:
            raise ValueError("Need at least 2 builds for matchmaking")

        # Weight by RD (uncertainty) so uncertain builds play more
        weights = [rater.get_build_rating(bid).RD for bid in ids]
        total_w = sum(weights)
        if total_w == 0:
            weights = [1.0] * len(ids)

        # Sample build A with probability proportional to uncertainty
        bid_a = random.choices(ids, weights=weights, k=1)[0]
        rating_a = rater.get_build_rating(bid_a)

        # Sample build B, preferring close-rated opponents and excluding A if needed
        other_ids = [bid for bid in ids if not (exclude_same and bid == bid_a)]
        if not other_ids:
            other_ids = ids

        # Score each potential opponent: bonus for being close in rating
        def opp_weight(bid: int) -> float:
            rating_b = rater.get_build_rating(bid)
            gap = abs(rating_a.r - rating_b.r)
            # Exponential decay: weight halves every 200 Elo points apart
            closeness = 2.0 ** (-gap / 200.0)
            uncertainty = rating_b.RD
            return closeness * uncertainty

        opp_weights = [opp_weight(bid) for bid in other_ids]
        bid_b = random.choices(other_ids, weights=opp_weights, k=1)[0]
        return bid_a, bid_b

    def round_robin(
        self,
        registry: "BuildRegistry",
        repeats: int = 1,
        shuffle: bool = True,
    ) -> list[tuple[int, int]]:
        """
        Return all ordered pairs (a, b) for a round-robin tournament.

        Each unordered pair {a, b} appears twice: once with a as team 0
        and once with b as team 0, to cancel any systematic first-mover bias.

        Args:
            repeats: How many times to repeat the full round-robin.
            shuffle: Randomise the order.
        """
        ids = registry.all_ids()
        pairs: list[tuple[int, int]] = []
        for i, a in enumerate(ids):
            for j, b in enumerate(ids):
                if i != j:
                    pairs.append((a, b))
        pairs = pairs * repeats
        if shuffle:
            random.shuffle(pairs)
        return pairs
