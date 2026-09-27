import json
import pathlib
from datetime import datetime, timezone

from engine.contract import validate
from engine.f1_data import collect_f1

FIX = pathlib.Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 27, 11, 0, tzinfo=timezone.utc)      # lendemain du GP d'Azerbaïdjan (manche 15)


def real(url):
    for key, name in (("driverStandings", "drivers"), ("constructorStandings", "constructors"), ("last/results", "results"),
                      ("last/qualifying", "qualifying"), ("last/sprint", "sprint"), ("current.json", "schedule")):
        if key in url:
            return json.loads((FIX / f"jolpica_{name}.json").read_text("utf-8"))
    raise AssertionError(url)


def test_collect_builds_a_valid_file_from_real_responses():
    data, health = collect_f1(None, NOW, real)
    validate("f1", data)
    assert all(h["ok"] for h in health) and len(health) == 6
    assert data["last"]["round"] == 15 and data["last"]["race"][0]["driver"] == "George Russell"
    assert data["last"]["race"][0]["result"] == "1:38:02.143" and data["last"]["race"][1]["result"] == "+0.196"
    assert data["last"]["qualifying"][0]["driver"] == "George Russell" and data["last"]["sprint"] == []
    assert data["drivers"][0] == {"position": 1, "driver": "Andrea Kimi Antonelli", "team": "Mercedes", "points": 302.0, "wins": 8}
    assert data["constructors"][0]["team"] == "Mercedes"


def test_next_grand_prix_lists_every_session_in_time_order():
    data, _ = collect_f1(None, NOW, real)
    nxt = data["next"]
    assert nxt["round"] == 16 and "Malaysia" in nxt["country"]
    names = [s["name"] for s in nxt["sessions"]]
    assert names[0] == "Essais libres 1" and names[-1] == "Course"
    assert "Qualifications" in names
    assert [s["start"] for s in nxt["sessions"]] == sorted(s["start"] for s in nxt["sessions"])
    assert all(s["start"].endswith("+00:00") for s in nxt["sessions"])


def test_sprint_weekend_has_sprint_sessions():
    data, _ = collect_f1(None, datetime(2026, 10, 6, tzinfo=timezone.utc), real)
    names = [s["name"] for s in data["next"]["sessions"]]
    assert data["next"]["round"] == 17 and "Sprint" in names and "Qualifications sprint" in names


def test_after_the_last_race_there_is_no_next_grand_prix():
    data, _ = collect_f1(None, datetime(2026, 12, 20, tzinfo=timezone.utc), real)
    assert data["next"] is None
    validate("f1", data)


def test_failures_keep_the_previous_values_marked_stale():
    first, _ = collect_f1(None, NOW, real)

    def flaky(url):
        if "driverStandings" in url or "last/results" in url:
            raise TimeoutError("boom")
        return real(url)

    second, health = collect_f1(first, NOW, flaky)
    assert second["drivers"] == first["drivers"] and second["last"] == first["last"] and second["stale"] is True
    assert sum(not h["ok"] for h in health) == 2
    validate("f1", second)


def test_everything_down_without_history_publishes_nothing():
    def down(url):
        raise ConnectionError("down")
    data, health = collect_f1(None, NOW, down)
    assert data is None and not any(h["ok"] for h in health)


def test_malformed_answers_are_handled_like_failures():
    data, health = collect_f1(None, NOW, lambda url: {"MRData": {}})
    assert data is None and not any(h["ok"] for h in health)


def test_run_publishes_f1_only_when_the_f1_domain_exists(tmp_path):
    import shutil

    import yaml

    from engine.config import ROOT
    from engine.run import run
    from tests.test_run import DOM, fake_fetch

    (tmp_path / "config" / "domains").mkdir(parents=True)
    shutil.copy(ROOT / "config" / "global.yml", tmp_path / "config" / "global.yml")
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(DOM, allow_unicode=True), "utf-8")
    path = tmp_path / "site" / "data" / "f1.json"
    run(tmp_path, now=NOW, fetch=fake_fetch, f1_fetch=real)
    assert not path.exists()
    f1 = {**DOM, "id": "f1", "name": "F1", "order": 9, "sources": []}
    (tmp_path / "config" / "domains" / "f1.yml").write_text(yaml.safe_dump(f1, allow_unicode=True), "utf-8")
    report = run(tmp_path, now=NOW, fetch=fake_fetch, f1_fetch=real)
    validate("f1", json.loads(path.read_text("utf-8")))
    assert report["f1"] == {"ok": 6, "failed": 0}
