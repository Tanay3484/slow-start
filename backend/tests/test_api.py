"""API tests. They must pass whether the `@human` levels are stubs or written."""

from __future__ import annotations

import datetime as dt

from conftest import FakeLLM, days
from slowstart import service
from slowstart.api import Services, create_app
from slowstart.checkin.reader import is_excused, keyword_body, read_checkin
from slowstart.models import StepParams

WEEK = [6000, 7000, 5000, 8000, 6500, 9000, 4000, 7500, 6800, 7200]


def payload(history, today):
    return {
        "today": today.isoformat(),
        "history": [
            {"date": d.date.isoformat(), "steps": d.steps, "goal": d.goal, "excused": d.excused}
            for d in history
        ],
    }


def test_health_reports_levels_and_predictor(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and set(body["levels"]) == {"H1", "H2"}
    assert all(v in {"locked", "unlocked"} for v in body["levels"].values())


def test_new_person_gets_a_small_starting_goal(client):
    r = client.post("/api/goal/steps", json=payload([], dt.date(2026, 10, 1)))
    assert r.status_code == 200
    g = r.json()
    assert g["goal"] == StepParams().start and g["cap"]["source"] == "none"


def test_goal_never_exceeds_the_cap_or_the_window(client):
    hist = days(WEEK)
    today = hist[-1].date + dt.timedelta(days=1)
    g = client.post("/api/goal/steps", json=payload(hist, today)).json()
    assert g["source"] in {"controller", "fallback"}
    assert StepParams().floor <= g["goal"] <= StepParams().ceiling
    assert g["goal"] <= g["window"] and g["goal"] <= g["cap"]["value"]


def test_history_from_today_or_later_is_ignored(client):
    hist = days(WEEK)
    today = hist[-1].date + dt.timedelta(days=1)
    a = client.post("/api/goal/steps", json=payload(hist, today)).json()
    peek = hist + days([99999], start=today)
    b = client.post("/api/goal/steps", json=payload(peek, today)).json()
    assert a == b


def test_clean_history_dedupes_by_date():
    hist = days([1000, 2000]) + days([3000], start=dt.date(2026, 10, 1))
    out = service.clean_history(hist, dt.date(2026, 10, 3))
    assert [d.steps for d in out] == [3000, 2000]


def test_exercise_goal_and_unknown_exercise(client):
    r = client.post("/api/goal/exercise", json={"exercise": "bench_press", "sessions": []})
    assert r.status_code == 200 and r.json()["target"]["weight_kg"] == 20.0
    assert (
        client.post("/api/goal/exercise", json={"exercise": "curl", "sessions": []}).status_code
        == 404
    )


def test_import_endpoints_return_422_with_a_reason(client):
    assert client.post("/api/import/steps", json={"text": "nonsense"}).status_code == 422
    assert client.post("/api/import/hevy", json={"text": "a,b\n1,2"}).status_code == 422
    ok = client.post("/api/import/steps", json={"text": "date,steps\n2026-10-01,5000\n"})
    assert ok.status_code == 200 and ok.json()["days"][0]["steps"] == 5000


def test_oversized_history_is_rejected(client):
    big = [{"date": "2026-10-01", "steps": 1}] * 801
    assert (
        client.post("/api/goal/steps", json={"today": "2026-10-02", "history": big}).status_code
        == 422
    )


# ---- check-in ----


def test_excused_is_decided_by_code_with_negation():
    assert is_excused("I have a fever today")
    assert is_excused("sprained my ankle")
    assert not is_excused("I'm not sick, just tired")
    assert not is_excused("knees a bit sore but ok")
    assert keyword_body("knees and lower back sore") == ["knees", "back"]


def test_checkin_without_the_model_uses_templates():
    out = read_checkin("so tired, knees sore", None)
    assert out.source == "template" and out.energy == "low" and not out.excused
    assert "knees" in out.body and out.line


def test_checkin_accepts_a_clean_model_line_and_rejects_a_dirty_one():
    good = FakeLLM({"energy": "ok", "body": ["knees"], "line": "Slow steps, little friend."})
    assert read_checkin("knees sore", good).source == "gemma"
    dirty = FakeLLM({"energy": "ok", "body": [], "line": "Walk 5000 steps now!"})
    out = read_checkin("feeling fine", dirty)
    assert out.source == "template" and not any(c.isdigit() for c in out.line)


def test_model_cannot_excuse_a_day_or_invent_body_parts():
    llm = FakeLLM({"energy": "low", "body": ["spleen", "knee"], "line": "Rest, big one."})
    out = read_checkin("my knee hurts a bit", llm)
    assert out.body == ["knee"] and out.excused is False


def test_checkin_endpoint_survives_a_dead_model(client):
    r = client.post("/api/checkin", json={"text": "flu today"})
    assert r.status_code == 200 and r.json()["excused"] is True and r.json()["source"] == "template"


def test_app_serves_the_built_frontend(tmp_path, settings):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "a.js").write_text("1")
    s = settings.model_copy(update={"static_dir": str(tmp_path)})
    from fastapi.testclient import TestClient

    c = TestClient(create_app(Services(settings=s, predictor=None, llm=None)))
    assert c.get("/").text == "<html>app</html>"
    assert c.get("/some/route").text == "<html>app</html>"
    assert c.get("/assets/a.js").text == "1"
    assert c.get("/../secret").status_code in (200, 404)
    assert c.get("/api/health").json()["status"] == "ok"


def test_costly_routes_are_rate_limited_per_client(settings):
    from fastapi.testclient import TestClient

    s = settings.model_copy(update={"rate_per_minute": 3})
    c = TestClient(create_app(Services(settings=s, predictor=None, llm=None)))
    body = {"today": "2026-10-02", "history": []}
    codes = [c.post("/api/goal/steps", json=body).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert c.get("/api/health").status_code == 200  # cheap routes are not limited
    other = c.post("/api/goal/steps", json=body, headers={"x-forwarded-for": "203.0.113.9"})
    assert other.status_code == 200  # another client has its own allowance


def test_rate_limiter_forgets_old_hits():
    from slowstart.ratelimit import RateLimiter

    now = [0.0]
    r = RateLimiter(2, clock=lambda: now[0])
    assert r.check("a") and r.check("a") and not r.check("a")
    now[0] = 61.0
    assert r.check("a")


def test_goal_without_the_cap_is_the_window_alone(client):
    hist = days(WEEK)
    today = hist[-1].date + dt.timedelta(days=1)
    body = payload(hist, today) | {"use_cap": False}
    g = client.post("/api/goal/steps", json=body).json()
    assert g["cap"]["source"] == "none" and g["goal"] == g["window"]


def test_play_route_serves_the_game_page(tmp_path, settings):
    from fastapi.testclient import TestClient

    (tmp_path / "index.html").write_text("landing")
    (tmp_path / "play.html").write_text("game")
    s = settings.model_copy(update={"static_dir": str(tmp_path)})
    c = TestClient(create_app(Services(settings=s, predictor=None, llm=None)))
    assert c.get("/").text == "landing"
    assert c.get("/play").text == "game"
    assert c.get("/play.html").text == "game"
    assert c.get("/anything-else").text == "landing"
