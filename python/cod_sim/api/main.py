"""FastAPI application for the Chronicles of Darkness Combat Simulator."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..build_registry import BuildRegistry
from ..glicko import GlickoRater
from .. import checkpoint as _ckpt_mod  # cod_sim.checkpoint

_BUILDS_DIR  = Path(__file__).resolve().parent.parent.parent.parent / "builds"
_STATIC_DIR  = Path(__file__).resolve().parent / "static"
_RATINGS_FILE = Path("ratings.json")
_CKPT_DIR    = Path("checkpoints")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load shared resources once at startup."""
    # Build registry
    reg = BuildRegistry()
    reg.load_directory(_BUILDS_DIR)
    app.state.registry = reg
    print(f"[startup] {len(reg)} builds loaded")

    # Glicko ratings (optional)
    if _RATINGS_FILE.exists():
        app.state.rater = GlickoRater.load(_RATINGS_FILE)
        n = len(app.state.rater.all_build_ratings())
        print(f"[startup] ratings loaded ({n} builds rated)")
    else:
        # Provide a fresh rater with default ratings for all builds
        app.state.rater = GlickoRater()
        for bid in reg.all_ids():
            app.state.rater.get_build_rating(bid)
        print("[startup] no ratings.json found — using default ratings (run scripts/rate_builds.py)")

    # Trained policy (optional)
    from .. import checkpoint as _ck
    from ..cod_sim import ACTION_SPACE_SIZE as _ASZ
    ckpt_path = _ck.latest_checkpoint(_CKPT_DIR)
    if ckpt_path:
        policy, _, step = _ck.load(ckpt_path)
        if policy.action_size != _ASZ:
            app.state.policy = None
            print(
                f"[startup] checkpoint {ckpt_path.name} has action_size={policy.action_size}, "
                f"current={_ASZ} — skipping (retrain with scripts/train.py)"
            )
        else:
            policy.eval()
            app.state.policy = policy
            print(f"[startup] policy loaded from {ckpt_path} (step {step:,})")
    else:
        app.state.policy = None
        print("[startup] no policy checkpoint found — using first-legal-action baseline")

    yield
    # No cleanup needed


def create_app() -> FastAPI:
    app = FastAPI(
        title="Chronicles of Darkness Combat Simulator",
        description="ML-powered combat sim for Vampire, Werewolf, Changeling & Hunter",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    from .routes.builds  import router as builds_router
    from .routes.combat  import router as combat_router
    from .routes.ratings import router as ratings_router
    app.include_router(builds_router)
    app.include_router(combat_router)
    app.include_router(ratings_router)

    # Status endpoint
    @app.get("/api/status")
    def status(request_app=None):
        from fastapi import Request
        return {
            "builds":  len(app.state.registry) if hasattr(app.state, "registry") else 0,
            "ratings": len(app.state.rater.all_build_ratings()) if hasattr(app.state, "rater") else 0,
            "policy":  app.state.policy is not None if hasattr(app.state, "policy") else False,
        }

    # Serve the single-page app
    if _STATIC_DIR.exists():
        @app.get("/")
        def index():
            return FileResponse(_STATIC_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    return app


app = create_app()
