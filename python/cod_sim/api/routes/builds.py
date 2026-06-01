"""Builds API routes."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/builds", tags=["builds"])


def _build_dict(build, rating=None) -> dict:
    r = {
        "id": build.id,
        "name": build.name,
        "splat": build.splat,
        "size": build.size,
        "attributes": {
            "strength":    build.strength,
            "dexterity":   build.dexterity,
            "stamina":     build.stamina,
            "intelligence":build.intelligence,
            "wits":        build.wits,
            "resolve":     build.resolve,
            "presence":    build.presence,
            "manipulation":build.manipulation,
            "composure":   build.composure,
        },
        "skills": {
            "brawl":    build.brawl,
            "weaponry": build.weaponry,
            "firearms": build.firearms,
            "athletics":build.athletics,
            "stealth":  build.stealth,
        },
        "weapon": {
            "damage_mod":         build.weapon_damage_mod,
            "damage_type":        build.weapon_damage_type,
            "initiative_penalty": build.weapon_initiative_penalty,
            "is_ranged":          build.weapon_is_ranged,
            "is_silver":          build.weapon_is_silver,
            "is_fire":            build.weapon_is_fire,
        },
        "armor": {
            "general":   build.armor_general,
            "ballistic": build.armor_ballistic,
        },
        "derived": {
            "max_health":    build.max_health,
            "max_willpower": build.max_willpower,
            "max_resource":  build.max_resource,
        },
        "splat_details": _splat_details(build),
    }
    if rating is not None:
        r["rating"] = {
            "r":        round(rating.r, 1),
            "RD":       round(rating.RD, 1),
            "sigma":    round(rating.sigma, 4),
            "n_matches":rating.n_matches,
            "ci_lo":    round(rating.confidence_interval[0], 1),
            "ci_hi":    round(rating.confidence_interval[1], 1),
        }
    return r


def _splat_details(build) -> dict:
    if build.splat == "vampire":
        return {
            "blood_potency": build.blood_potency,
            "celerity":      build.celerity,
            "vigor":         build.vigor,
            "resilience":    build.resilience,
        }
    if build.splat == "werewolf":
        return {"primal_urge": build.primal_urge}
    if build.splat == "changeling":
        return {
            "wyrd":        build.wyrd,
            "glamour_max": build.glamour_max,
            "seeming":     build.seeming,
        }
    return {}


@router.get("")
def list_builds(request: Request) -> list[dict]:
    reg   = request.app.state.registry
    rater = request.app.state.rater
    result = []
    for build in reg.all_builds():
        rating = rater.get_build_rating(build.id) if rater else None
        result.append(_build_dict(build, rating))
    # Sort by rating descending if ratings available
    if rater:
        result.sort(key=lambda b: b.get("rating", {}).get("r", 1500), reverse=True)
    return result


@router.get("/{build_id}")
def get_build(build_id: int, request: Request) -> dict:
    reg   = request.app.state.registry
    rater = request.app.state.rater
    if build_id not in reg.all_ids():
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")
    build  = reg.get(build_id)
    rating = rater.get_build_rating(build_id) if rater else None
    return _build_dict(build, rating)
