from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from slowstart.api import Services, create_app
from slowstart.checkin.ollama import LLMError
from slowstart.config import Settings
from slowstart.models import DayResult
from slowstart.prediction.predictor import EmpiricalPredictor

START = dt.date(2026, 10, 1)


def days(steps: list[int | None], goals: list[int | None] | None = None, start: dt.date = START):
    """DayResults on consecutive dates. `None` steps means the tracker was not worn."""
    goals = goals or [None] * len(steps)
    return [
        DayResult(date=start + dt.timedelta(days=i), steps=s, goal=g)
        for i, (s, g) in enumerate(zip(steps, goals, strict=True))
    ]


class FakeLLM:
    def __init__(self, reply: dict | None = None, fail: bool = False) -> None:
        self.reply = reply or {}
        self.fail = fail
        self.calls = 0

    def chat_json(self, messages, schema, temperature=0.6):
        self.calls += 1
        if self.fail:
            raise LLMError("down")
        return self.reply


@pytest.fixture
def settings() -> Settings:
    return Settings(use_tabpfn=False, prior_rows=60)


@pytest.fixture
def client(settings) -> TestClient:
    services = Services(settings=settings, predictor=EmpiricalPredictor(), llm=FakeLLM(fail=True))
    return TestClient(create_app(services))
