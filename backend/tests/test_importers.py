from __future__ import annotations

import datetime as dt
import json

import pytest
from slowstart.data.hevy_import import HevyImportError, canonical_exercise, parse_hevy
from slowstart.data.steps_import import ImportError_, parse_steps, people_in_fitabase


def test_takeout_minute_records_are_summed_per_day():
    rows = [
        {"dateTime": "10/01/26 00:00:00", "value": "1000"},
        {"dateTime": "10/01/26 00:01:00", "value": "20"},
        {"dateTime": "10/02/26 07:30:00", "value": "5000"},
    ]
    out = parse_steps(json.dumps(rows))
    assert out.format == "fitbit_takeout_json"
    assert [(d.date, d.steps) for d in out.days] == [
        (dt.date(2026, 10, 1), 1020),
        (dt.date(2026, 10, 2), 5000),
    ]


def test_days_under_min_steps_are_not_carried_and_counted():
    out = parse_steps("date,steps\n2026-10-01,0\n2026-10-02,4000\n2026-10-03,499\n2026-10-04,500\n")
    assert out.not_worn == 2
    assert [d.steps for d in out.days] == [None, 4000, None, 500]
    assert any("not carried" in w for w in out.warnings)


def test_near_miss_google_fit_files_are_refused_with_the_right_file_named():
    slots = "Start time,End time,Move Minutes count,Step count\n00:00:00.000+05:30,00:15:00.000+05:30,,12\n"
    raw = json.dumps({"Data Source": "derived:com.google.step_count.delta", "Data Points": []})
    for text in (slots, raw):
        with pytest.raises(ImportError_, match="Daily activity metrics.csv"):
            parse_steps(text)


def test_fitabase_daily_activity():
    text = "Id,ActivityDate,TotalSteps,Calories\n1,3/12/2016,13162,1985\n1,3/13/2016,10735,1797\n"
    out = parse_steps(text)
    assert out.format == "fitabase_csv"
    assert out.first == dt.date(2016, 3, 12) and out.days[1].steps == 10735


def test_google_fit_daily_activity_metrics():
    text = (
        "Date,Move Minutes count,Calories (kcal),Distance (m),Step count,Average weight (kg)\n"
        "2026-10-20,40,2100,3100,4438,\n"
        "2026-10-21,12,1900,,,\n"
        "2026-10-22,61,2300,5800,7922,\n"
    )
    out = parse_steps(text)
    assert out.format == "google_fit_csv"
    assert [d.steps for d in out.days] == [4438, None, 7922]
    assert out.not_worn == 1
    assert not any("could not be read" in w for w in out.warnings)


def test_a_file_with_several_people_is_refused_for_a_single_import():
    text = "Id,ActivityDate,TotalSteps\n1,3/12/2016,100\n2,3/12/2016,200\n"
    with pytest.raises(ImportError_):
        parse_steps(text)
    assert set(people_in_fitabase(text)) == {"1", "2"}


@pytest.mark.parametrize("text", ["", "hello", "a,b\n1,2\n", "[1,2,3]"])
def test_unrecognised_steps_input_raises_a_clear_error(text):
    with pytest.raises(ImportError_):
        parse_steps(text)


HEVY = (
    "title,start_time,end_time,description,exercise_title,superset_id,exercise_notes,set_index,set_type,"
    "weight_kg,reps,distance_km,duration_seconds,rpe\n"
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Bench Press (Barbell),,,0,warmup,20,10,,,\n'
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Bench Press (Barbell),,,1,normal,60,8,,,\n'
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Bench Press (Barbell),,,2,normal,60,8,,,\n'
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Push Up,,,0,normal,,15,,,\n'
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Cable Fly,,,0,normal,15,12,,,\n'
    'Push,"11 Oct 2026, 18:30","11 Oct 2026, 19:30",,Squat (Barbell),,,0,normal,80,0,,,\n'
)


def test_hevy_groups_working_sets_by_day_and_exercise():
    out = parse_hevy(HEVY)
    by_ex = {s.exercise: s for s in out.sessions}
    assert set(by_ex) == {"bench_press", "push_up"}
    assert [(s.weight_kg, s.reps) for s in by_ex["bench_press"].sets] == [(60.0, 8), (60.0, 8)]
    assert by_ex["push_up"].sets[0].weight_kg is None
    assert out.unsupported == {"Cable Fly": 1}
    assert out.skipped_rows == 1  # the zero-rep squat set
    assert out.first == dt.date(2026, 10, 11)


def test_hevy_pounds_are_converted():
    text = HEVY.replace("weight_kg", "weight_lbs")
    out = parse_hevy(text)
    bench = next(s for s in out.sessions if s.exercise == "bench_press")
    assert bench.sets[0].weight_kg == pytest.approx(27.22, abs=0.01)


def test_hevy_rejects_other_csvs():
    with pytest.raises(HevyImportError):
        parse_hevy("a,b\n1,2\n")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Squat (Barbell)", "squat"),
        ("Bench Press (Barbell)", "bench_press"),
        ("Bench Press (Dumbbell)", "dumbbell_bench_press"),
        ("Deadlift (Barbell)", "deadlift"),
        ("Romanian Deadlift (Barbell)", None),
        ("Overhead Press (Barbell)", "overhead_press"),
        ("Bent Over Row (Barbell)", "barbell_row"),
        ("Goblet Squat", "goblet_squat"),
        ("Push Up", "push_up"),
        ("Pull Up", "pull_up"),
        ("Triceps Dip", "dip"),
        ("Chest Dip", "dip"),
        ("Chest Dip (Assisted)", None),
        ("Chest Dip (Weighted)", None),
        ("Pull Up (Assisted)", None),
        ("Pull Up (Weighted)", None),
        ("Leg Press", None),
    ],
)
def test_exercise_names_map_to_supported_ids(title, expected):
    assert canonical_exercise(title) == expected
