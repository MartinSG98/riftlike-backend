import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app import repository
from app.db import get_session
from app.game import engine
from app.game.state import Action
from app.game.views import RunSummary, RunView, build_view, summary_label

router = APIRouter(prefix="/api/runs", tags=["runs"])


class NewRun(BaseModel):
    team: str


@router.post("", response_model=RunView, status_code=201)
def create_run(body: NewRun, session: Session = Depends(get_session)) -> RunView:
    try:
        state = engine.new_run(body.team, seed=secrets.randbits(32))
    except engine.IllegalAction as exc:
        raise HTTPException(400, str(exc)) from exc
    run = repository.create_run(session, state)
    return build_view(run.id, state)


@router.get("", response_model=list[RunSummary])
def list_runs(
    limit: int = Query(8, ge=1, le=50), session: Session = Depends(get_session)
) -> list[RunSummary]:
    return [
        RunSummary(
            id=run.id,
            team=state.team,
            stage=state.stage,
            result=state.result,
            label=summary_label(state),
            updated_at=run.updated_at,
        )
        for run, state in repository.recent_runs(session, limit)
    ]


@router.get("/{run_id}", response_model=RunView)
def get_run(run_id: str, session: Session = Depends(get_session)) -> RunView:
    loaded = repository.load_run(session, run_id)
    if loaded is None:
        raise HTTPException(404, "run not found")
    _, state = loaded
    return build_view(run_id, state)


@router.post("/{run_id}/actions", response_model=RunView)
def act(
    run_id: str,
    action: Action = Body(...),
    session: Session = Depends(get_session),
) -> RunView:
    loaded = repository.load_run(session, run_id)
    if loaded is None:
        raise HTTPException(404, "run not found")
    run, state = loaded
    try:
        engine.apply(state, action)
    except engine.IllegalAction as exc:
        raise HTTPException(409, str(exc)) from exc
    repository.save_run(session, run, state)
    return build_view(run_id, state)
