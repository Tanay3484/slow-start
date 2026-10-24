"""The HTTP API (design section 7). Stateless: nothing a person sends is stored or logged (R3.4)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from slowstart import service
from slowstart.checkin.ollama import ChatJSON, OllamaClient
from slowstart.checkin.reader import read_checkin
from slowstart.config import Settings, get_settings
from slowstart.controllers import guard
from slowstart.data.hevy_import import HevyImportError, ImportedWorkouts, parse_hevy
from slowstart.data.steps_import import ImportedSteps, ImportError_, parse_steps
from slowstart.models import (
    Checkin,
    CheckinRequest,
    ExerciseGoal,
    ExerciseGoalRequest,
    ExerciseParams,
    Goal,
    ImportRequest,
    StepGoalRequest,
)
from slowstart.prediction.predictor import Predictor, TabPFNPredictor
from slowstart.ratelimit import RateLimiter, limit

log = logging.getLogger("slowstart")


@dataclass
class Services:
    settings: Settings
    predictor: Predictor | None
    llm: ChatJSON | None


def build_services(settings: Settings | None = None) -> Services:
    settings = settings or get_settings()
    predictor: Predictor | None = None
    if settings.use_tabpfn:
        try:
            import tabpfn  # noqa: F401

            predictor = TabPFNPredictor(n_estimators=settings.tabpfn_estimators)
        except ImportError:
            log.warning("tabpfn is not installed; goals will use the median cap")
    llm = OllamaClient(
        settings.ollama_base,
        settings.model,
        timeout_s=settings.llm_timeout_s,
        num_predict=settings.llm_num_predict,
        num_thread=settings.llm_num_thread,
    )
    return Services(settings=settings, predictor=predictor, llm=llm)


def create_app(services: Services | None = None) -> FastAPI:
    svc = services or build_services()
    app = FastAPI(title="Slow Start", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in svc.settings.cors_origins.split(",")],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # The routes that cost CPU or call the model are limited per client; the cheap ones are not.
    costly = Depends(limit(RateLimiter(svc.settings.rate_per_minute)))

    if isinstance(svc.predictor, TabPFNPredictor):
        # Load the weights in the background so the first goal request is not the slow one.
        threading.Thread(target=svc.predictor.warm, daemon=True).start()

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "predictor": svc.predictor.name if svc.predictor else "median",
            "model": svc.settings.model,
            "levels": guard.levels_state(),
        }

    @app.post("/api/goal/steps", response_model=Goal, dependencies=[costly])
    def goal_steps(body: StepGoalRequest) -> Goal:
        predictor = svc.predictor if body.use_cap else None
        return service.step_goal(
            body.history, body.today, predictor, svc.settings, use_cap=body.use_cap
        )

    @app.post("/api/goal/exercise", response_model=ExerciseGoal)
    def goal_exercise(body: ExerciseGoalRequest) -> ExerciseGoal:
        if body.exercise not in ExerciseParams().scheme:
            raise HTTPException(404, f"Unknown exercise {body.exercise!r}")
        return service.exercise_goal(body.sessions, body.exercise)

    @app.get("/api/exercises")
    def exercises() -> dict:
        return {k: v.model_dump() for k, v in ExerciseParams().scheme.items()}

    @app.post("/api/import/steps", response_model=ImportedSteps)
    def import_steps(body: ImportRequest) -> ImportedSteps:
        try:
            return parse_steps(body.text)
        except ImportError_ as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/import/hevy", response_model=ImportedWorkouts)
    def import_hevy(body: ImportRequest) -> ImportedWorkouts:
        try:
            return parse_hevy(body.text)
        except HevyImportError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/checkin", response_model=Checkin, dependencies=[costly])
    def checkin(body: CheckinRequest) -> Checkin:
        return read_checkin(body.text, svc.llm)

    static = Path(svc.settings.static_dir)
    if static.is_dir():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (static / path).resolve()
            if path and candidate.is_file() and static.resolve() in candidate.parents:
                return FileResponse(candidate, headers={"Cache-Control": "no-cache"})
            page = "play.html" if path.strip("/").startswith("play") else "index.html"
            if not (static / page).is_file():
                page = "index.html"
            return FileResponse(static / page, headers={"Cache-Control": "no-cache"})

    return app


def app_factory() -> FastAPI:  # uvicorn --factory slowstart.api:app_factory
    return create_app()
