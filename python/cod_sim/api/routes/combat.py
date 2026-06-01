"""Combat API routes — synchronous run + Server-Sent Event stream."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/combat", tags=["combat"])


class CombatRunRequest(BaseModel):
    build_id_a: int
    build_id_b: int
    seed: int = 0
    use_policy: bool = True  # False → first-legal-action on both sides


@router.post("/run")
def run_combat(body: CombatRunRequest, request: Request) -> dict:
    """Run a full combat and return the complete event log."""
    reg    = request.app.state.registry
    policy = request.app.state.policy if body.use_policy else None

    for bid in [body.build_id_a, body.build_id_b]:
        if bid not in reg.all_ids():
            raise HTTPException(status_code=404, detail=f"Build {bid} not found")

    build_a = reg.get(body.build_id_a)
    build_b = reg.get(body.build_id_b)
    builds_json = reg.builds_json([body.build_id_a, body.build_id_b])

    from ..combat_runner import run_combat as _run
    log = _run(
        builds_json=builds_json,
        teams=[0, 1],
        policy=policy,
        seed=body.seed,
        build_names=[build_a.name, build_b.name],
        build_splats=[build_a.splat, build_b.splat],
    )
    result = log.as_dict()
    result["build_a"] = {"id": build_a.id, "name": build_a.name, "splat": build_a.splat}
    result["build_b"] = {"id": build_b.id, "name": build_b.name, "splat": build_b.splat}
    return result


@router.get("/stream")
async def stream_combat(
    request: Request,
    build_id_a: int = Query(...),
    build_id_b: int = Query(...),
    seed: int = Query(default=0),
    use_policy: bool = Query(default=True),
    delay_ms: int = Query(default=100, ge=0, le=2000),
) -> StreamingResponse:
    """
    Stream combat events as Server-Sent Events (SSE).

    Each event is a JSON-encoded CombatEvent dict.
    Connect with: EventSource('/api/combat/stream?build_id_a=101&build_id_b=201')
    """
    reg    = request.app.state.registry
    policy = request.app.state.policy if use_policy else None

    for bid in [build_id_a, build_id_b]:
        if bid not in reg.all_ids():
            raise HTTPException(status_code=404, detail=f"Build {bid} not found")

    build_a = reg.get(build_id_a)
    build_b = reg.get(build_id_b)
    builds_json = reg.builds_json([build_id_a, build_id_b])

    async def event_generator() -> AsyncGenerator[str, None]:
        from ..combat_runner import run_combat as _run, CombatLog
        import torch
        from ...cod_sim import CombatEnv
        from ..combat_runner import _snap_from_summary, _describe_action, CombatEvent

        # Stream meta event
        meta = {
            "type": "meta",
            "build_a": {"id": build_a.id, "name": build_a.name, "splat": build_a.splat},
            "build_b": {"id": build_b.id, "name": build_b.name, "splat": build_b.splat},
        }
        yield f"data: {json.dumps(meta)}\n\n"
        if delay_ms:
            await asyncio.sleep(delay_ms / 1000)

        # Run combat step by step, yielding each event
        env = CombatEnv(builds_json, [0, 1])
        obs_list, _ = env.reset(seed=seed)
        names  = [build_a.name, build_b.name]
        splats = [build_a.splat, build_b.splat]
        teams  = [0, 1]
        step = 0
        done = False

        while not done and step < 1000:
            if await request.is_disconnected():
                break

            summary   = env.get_state_summary()
            actor_idx = env.current_actor_idx()
            actor_name  = names[actor_idx] if actor_idx < len(names) else f"char {actor_idx}"
            actor_team  = teams[actor_idx] if actor_idx < len(teams) else 0
            actor_splat = splats[actor_idx] if actor_idx < len(splats) else "mortal"
            turn = summary["turn"]
            chars = _snap_from_summary(summary)
            for i, ch in enumerate(chars):
                if i < len(splats):
                    ch.splat = splats[i]

            mask = env.action_mask()
            if policy is not None:
                obs_t  = torch.tensor(obs_list, dtype=torch.float32).unsqueeze(0)
                mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
                with torch.no_grad():
                    acts, _, _ = policy.act(obs_t, mask_t)
                action = int(acts[0])
            else:
                action = next(i for i, m in enumerate(mask) if m)

            action_desc = _describe_action(action, actor_name, actor_splat, names)
            obs_list, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            step += 1

            event = {
                "type":        "step",
                "step":        step,
                "turn":        turn,
                "actor_name":  actor_name,
                "actor_team":  actor_team,
                "action_desc": action_desc,
                "is_terminal": done,
                "characters":  [c.as_dict() for c in chars],
            }
            yield f"data: {json.dumps(event)}\n\n"
            if delay_ms:
                await asyncio.sleep(delay_ms / 1000)

        # Final state
        final = env.get_state_summary()
        winner_team = final.get("winner_team")
        winner_name = names[0] if winner_team == 0 else (names[1] if winner_team == 1 else None)
        done_event = {
            "type":        "done",
            "winner_team": winner_team,
            "winner_name": winner_name,
            "n_steps":     step,
            "n_turns":     final.get("turn", 0),
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
