"""Ratings API routes."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/ratings", tags=["ratings"])


@router.get("/leaderboard")
def leaderboard(
    request: Request,
    splat: str | None = Query(default=None),
    n: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    rater = request.app.state.rater
    reg   = request.app.state.registry
    if rater is None:
        return []
    top = rater.top_builds(n=n, splat=splat, build_registry=reg if splat else None)
    result = []
    for rank, (bid, rating) in enumerate(top, 1):
        build = reg.get(bid) if bid in reg.all_ids() else None
        row = {
            "rank":      rank,
            "build_id":  bid,
            "name":      build.name if build else f"Build {bid}",
            "splat":     build.splat if build else "unknown",
            "r":         round(rating.r, 1),
            "RD":        round(rating.RD, 1),
            "sigma":     round(rating.sigma, 4),
            "n_matches": rating.n_matches,
        }
        result.append(row)
    return result


@router.get("/build/{build_id}")
def build_rating(build_id: int, request: Request) -> dict:
    rater = request.app.state.rater
    reg   = request.app.state.registry
    if build_id not in reg.all_ids():
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    rating = rater.get_build_rating(build_id) if rater else None
    if rating is None:
        raise HTTPException(status_code=404, detail="No ratings loaded")
    build = reg.get(build_id)
    return {
        "build_id": build_id,
        "name":     build.name,
        "splat":    build.splat,
        "r":        round(rating.r, 1),
        "RD":       round(rating.RD, 1),
        "sigma":    round(rating.sigma, 4),
        "n_matches":rating.n_matches,
        "ci_lo":    round(rating.confidence_interval[0], 1),
        "ci_hi":    round(rating.confidence_interval[1], 1),
    }


@router.get("/teams")
def team_leaderboard(
    request: Request,
    n: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    rater = request.app.state.rater
    reg   = request.app.state.registry
    if rater is None:
        return []
    top = rater.top_teams(n=n)
    result = []
    for rank, (key, rating) in enumerate(top, 1):
        names = " + ".join(
            reg.get(bid).name for bid in sorted(key)
            if bid in reg.all_ids()
        )
        result.append({
            "rank":       rank,
            "build_ids":  sorted(list(key)),
            "names":      names,
            "r":          round(rating.r, 1),
            "RD":         round(rating.RD, 1),
            "n_matches":  rating.n_matches,
        })
    return result
