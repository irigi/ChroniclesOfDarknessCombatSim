"""
Glicko-2 rating system for Chronicles of Darkness build and team ratings.

Implements the algorithm from Glickman (2012):
  http://www.glicko.net/glicko/glicko2.pdf

Individual builds and team compositions are rated separately.
The same trained policy plays both sides in every match; the rating measures
how well the policy performs *with* a given build, not the build's intrinsic power.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# ─── Glicko-2 constants ───────────────────────────────────────────────────────

_SCALE = 173.7178          # Conversion between external (r, RD) and internal (μ, φ)
_INITIAL_MU  = 0.0         # Internal rating = (1500 - 1500) / 173.7178
_INITIAL_PHI = 350.0 / _SCALE   # Initial RD = 350
_INITIAL_SIGMA = 0.06      # Initial volatility
_DEFAULT_TAU   = 0.5       # System constant τ (controls volatility change rate)
_EPS = 1e-6                # Convergence threshold for Illinois algorithm


# ─── Core Glicko-2 math ───────────────────────────────────────────────────────

def _g(phi: float) -> float:
    """g(φ) — reduces impact of opponents with high uncertainty."""
    return 1.0 / math.sqrt(1.0 + 3.0 * phi ** 2 / math.pi ** 2)


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    """E(μ, μ_j, φ_j) — expected score against opponent j."""
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def _f(x: float, delta: float, phi: float, v: float, a: float, tau: float) -> float:
    """Illinois algorithm objective function."""
    ex = math.exp(x)
    denom = 2.0 * (phi ** 2 + v + ex) ** 2
    return ex * (delta ** 2 - phi ** 2 - v - ex) / denom - (x - a) / tau ** 2


def _update_sigma(phi: float, sigma: float, v: float, delta: float, tau: float) -> float:
    """Find new volatility σ' using the Illinois algorithm."""
    a = math.log(sigma ** 2)
    f = lambda x: _f(x, delta, phi, v, a, tau)

    A = a
    if delta ** 2 > phi ** 2 + v:
        B = math.log(delta ** 2 - phi ** 2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fA, fB = f(A), f(B)

    for _ in range(200):           # Illinois iterations
        C  = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB < 0:
            A, fA = B, fB
        else:
            fA /= 2.0
        B, fB = C, fC
        if abs(B - A) < _EPS:
            break

    return math.exp(A / 2.0)


# ─── Rating dataclass ─────────────────────────────────────────────────────────

@dataclass
class GlickoRating:
    """Mutable Glicko-2 rating for one entity (build or team composition)."""

    mu:    float = _INITIAL_MU      # Internal rating
    phi:   float = _INITIAL_PHI     # Internal RD (uncertainty)
    sigma: float = _INITIAL_SIGMA   # Volatility
    n_matches: int = 0

    # ── Conversions ────────────────────────────────────────────────────────

    @property
    def r(self) -> float:
        """External rating (Elo-style, centred at 1500)."""
        return _SCALE * self.mu + 1500.0

    @property
    def RD(self) -> float:
        """External rating deviation."""
        return _SCALE * self.phi

    @property
    def confidence_interval(self) -> tuple[float, float]:
        """95% confidence interval for the true rating."""
        return (self.r - 2 * self.RD, self.r + 2 * self.RD)

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {"mu": self.mu, "phi": self.phi, "sigma": self.sigma,
                "n_matches": self.n_matches}

    @classmethod
    def from_dict(cls, d: dict) -> "GlickoRating":
        return cls(**d)

    def __repr__(self) -> str:
        return f"GlickoRating(r={self.r:.0f}, RD={self.RD:.0f}, σ={self.sigma:.3f}, n={self.n_matches})"


def glicko2_update(
    rating: GlickoRating,
    opponents: list[tuple[GlickoRating, float]],
    tau: float = _DEFAULT_TAU,
) -> GlickoRating:
    """
    Compute new rating after a rating period.

    Args:
        rating:    The entity's current rating.
        opponents: List of (opponent_rating, score) where score ∈ {0, 0.5, 1}.
        tau:       Glicko-2 system constant.

    Returns:
        Updated GlickoRating.
    """
    if not opponents:
        # Entity did not play: increase uncertainty by one period
        new_phi = math.sqrt(rating.phi ** 2 + rating.sigma ** 2)
        return GlickoRating(rating.mu, new_phi, rating.sigma, rating.n_matches)

    mu, phi, sigma = rating.mu, rating.phi, rating.sigma

    # Step 3: estimated variance v
    v_inv = sum(
        _g(opp.phi) ** 2 * _E(mu, opp.mu, opp.phi) * (1.0 - _E(mu, opp.mu, opp.phi))
        for opp, _ in opponents
    )
    v = 1.0 / v_inv if v_inv > 1e-12 else 1e9

    # Step 4: improvement Δ
    delta = v * sum(
        _g(opp.phi) * (score - _E(mu, opp.mu, opp.phi))
        for opp, score in opponents
    )

    # Step 5: new volatility σ'
    new_sigma = _update_sigma(phi, sigma, v, delta, tau)

    # Step 6: pre-rating-period uncertainty φ*
    phi_star = math.sqrt(phi ** 2 + new_sigma ** 2)

    # Step 7: new φ'
    new_phi = 1.0 / math.sqrt(1.0 / phi_star ** 2 + 1.0 / v)

    # Step 8: new μ'
    new_mu = mu + new_phi ** 2 * sum(
        _g(opp.phi) * (score - _E(mu, opp.mu, opp.phi))
        for opp, score in opponents
    )

    return GlickoRating(new_mu, new_phi, new_sigma, rating.n_matches + len(opponents))


# ─── Rating store ─────────────────────────────────────────────────────────────

# Pending match result for one entity within a rating period
_MatchResult = tuple[GlickoRating, float]   # (opponent_rating_at_match_time, score)

# Key for team compositions: frozenset of build_ids, e.g. frozenset({101, 201})
TeamKey = frozenset


class GlickoRater:
    """
    Maintains Glicko-2 ratings for individual builds and team compositions.

    Usage::

        rater = GlickoRater(tau=0.5)
        rater.record_match([101], [201], winner_team=0)
        rater.record_match([101], [201], winner_team=1)
        rater.update_ratings()   # call every rating_period matches
        print(rater.top_builds(5))
    """

    def __init__(
        self,
        tau: float = _DEFAULT_TAU,
        rating_period: int = 200,
    ) -> None:
        self.tau = tau
        self.rating_period = rating_period

        # {build_id: GlickoRating}
        self._build_ratings: dict[int, GlickoRating] = {}
        # {frozenset(build_ids): GlickoRating}
        self._team_ratings: dict[TeamKey, GlickoRating] = {}

        # Buffered results for the current rating period
        self._build_pending: dict[int, list[_MatchResult]] = {}
        self._team_pending: dict[TeamKey, list[_MatchResult]] = {}
        self._games_since_update = 0

    # ------------------------------------------------------------------
    # Rating access
    # ------------------------------------------------------------------

    def get_build_rating(self, build_id: int) -> GlickoRating:
        if build_id not in self._build_ratings:
            self._build_ratings[build_id] = GlickoRating()
        return self._build_ratings[build_id]

    def get_team_rating(self, build_ids: list[int]) -> GlickoRating:
        key = frozenset(build_ids)
        if key not in self._team_ratings:
            self._team_ratings[key] = GlickoRating()
        return self._team_ratings[key]

    # ------------------------------------------------------------------
    # Recording matches
    # ------------------------------------------------------------------

    def record_match(
        self,
        team_a_ids: list[int],
        team_b_ids: list[int],
        winner_team: Optional[int],   # 0 = A wins, 1 = B wins, None = draw
    ) -> None:
        """
        Record one match result.  Updates internal buffers; call
        update_ratings() every rating_period matches.

        Args:
            team_a_ids:  Build IDs for team A (usually [single_id] for 1v1).
            team_b_ids:  Build IDs for team B.
            winner_team: 0 → A wins; 1 → B wins; None → draw.
        """
        if winner_team == 0:
            score_a, score_b = 1.0, 0.0
        elif winner_team == 1:
            score_a, score_b = 0.0, 1.0
        else:
            score_a, score_b = 0.5, 0.5

        # Individual build ratings
        # Each build on team A is rated against each build on team B
        for bid_a in team_a_ids:
            for bid_b in team_b_ids:
                opp_b_rating = self.get_build_rating(bid_b)
                self._build_pending.setdefault(bid_a, []).append((opp_b_rating, score_a))
                opp_a_rating = self.get_build_rating(bid_a)
                self._build_pending.setdefault(bid_b, []).append((opp_a_rating, score_b))

        # Team composition ratings
        key_a = frozenset(team_a_ids)
        key_b = frozenset(team_b_ids)
        team_a_rating = self.get_team_rating(team_a_ids)
        team_b_rating = self.get_team_rating(team_b_ids)
        self._team_pending.setdefault(key_a, []).append((team_b_rating, score_a))
        self._team_pending.setdefault(key_b, []).append((team_a_rating, score_b))

        self._games_since_update += 1

    # ------------------------------------------------------------------
    # Rating period update
    # ------------------------------------------------------------------

    def update_ratings(self) -> None:
        """Process all buffered match results and update ratings."""
        # Update individual build ratings
        for bid, results in self._build_pending.items():
            self._build_ratings[bid] = glicko2_update(
                self.get_build_rating(bid), results, self.tau
            )
        self._build_pending.clear()

        # Update team ratings
        for key, results in self._team_pending.items():
            self._team_ratings[key] = glicko2_update(
                self._team_ratings.get(key, GlickoRating()), results, self.tau
            )
        self._team_pending.clear()

        self._games_since_update = 0

    def maybe_update(self) -> bool:
        """Auto-update if enough games have been buffered. Returns True if updated."""
        if self._games_since_update >= self.rating_period:
            self.update_ratings()
            return True
        return False

    @property
    def pending_games(self) -> int:
        return self._games_since_update

    # ------------------------------------------------------------------
    # Leaderboards
    # ------------------------------------------------------------------

    def top_builds(
        self,
        n: int = 20,
        splat: Optional[str] = None,
        build_registry=None,
    ) -> list[tuple[int, GlickoRating]]:
        """
        Return top-n build ratings sorted by external rating r descending.

        If build_registry is given and splat is not None, filter by splat.
        """
        ids = list(self._build_ratings.keys())
        if splat and build_registry:
            ids = [
                bid for bid in ids
                if build_registry.get(bid).splat == splat
            ]
        ids.sort(key=lambda bid: self._build_ratings[bid].r, reverse=True)
        return [(bid, self._build_ratings[bid]) for bid in ids[:n]]

    def top_teams(
        self, n: int = 20
    ) -> list[tuple[frozenset, GlickoRating]]:
        """Return top-n team composition ratings."""
        items = sorted(
            self._team_ratings.items(),
            key=lambda kv: kv[1].r,
            reverse=True,
        )
        return items[:n]

    def all_build_ratings(self) -> dict[int, GlickoRating]:
        return dict(self._build_ratings)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tau": self.tau,
            "rating_period": self.rating_period,
            "build_ratings": {
                str(bid): r.to_dict()
                for bid, r in self._build_ratings.items()
            },
            "team_ratings": {
                json.dumps(sorted(list(key))): r.to_dict()
                for key, r in self._team_ratings.items()
            },
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "GlickoRater":
        with open(path) as f:
            payload = json.load(f)
        rater = cls(
            tau=payload.get("tau", _DEFAULT_TAU),
            rating_period=payload.get("rating_period", 200),
        )
        for bid_str, d in payload.get("build_ratings", {}).items():
            rater._build_ratings[int(bid_str)] = GlickoRating.from_dict(d)
        for key_str, d in payload.get("team_ratings", {}).items():
            key = frozenset(json.loads(key_str))
            rater._team_ratings[key] = GlickoRating.from_dict(d)
        return rater
