from uuid import uuid4

from sqlmodel import Session, col, select

from app.game.state import RunState
from app.models import Run, _utcnow


def create_run(session: Session, state: RunState) -> Run:
    run = Run(
        id=uuid4().hex,
        team=state.team,
        stage=state.stage,
        result=state.result,
        state=state.model_dump_json(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def load_run(session: Session, run_id: str) -> tuple[Run, RunState] | None:
    run = session.get(Run, run_id)
    if run is None:
        return None
    return run, RunState.model_validate_json(run.state)


def save_run(session: Session, run: Run, state: RunState) -> None:
    run.stage = state.stage
    run.result = state.result
    run.state = state.model_dump_json()
    run.updated_at = _utcnow()
    session.add(run)
    session.commit()


def recent_runs(session: Session, limit: int) -> list[tuple[Run, RunState]]:
    rows = session.exec(select(Run).order_by(col(Run.updated_at).desc()).limit(limit)).all()
    return [(row, RunState.model_validate_json(row.state)) for row in rows]
