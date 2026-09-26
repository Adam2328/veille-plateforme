import json
from datetime import timedelta

import pytest
from jsonschema import ValidationError

from engine.contract import validate
from engine.publish import build_domain, build_home, project, publish, write_if_changed
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item

CFG = {"global": {"home": {"window_hours": 36, "retain_max": 2}},
       "domains": {"ia": {"id": "ia", "name": "IA", "accent": "#5B3FA8", "order": 1, "quota": 2}}}
SUMMARY = {k: "v" for k in ("quoi", "qui", "quand", "pourquoi", "retenir")}


def full(id, importance, level, **kw):
    ev = mk_event([mk_item(id, f"Titre {id}", tier=2), mk_item(id + "x", "Autre", tier=5)], id=id)
    return {**ev, "importance": importance, "level": level, "reliability": "confirmé",
            "reliability_reason": "r", "summary": SUMMARY, "summary_mode": "llm", "summary_fp": "secret", **kw}


def test_project_matches_contract_and_drops_internal_fields():
    p = project(full("ev_a", 81.4, 1))
    validate("event", p)
    assert "items" not in p and "summary_fp" not in p and p["importance"] == 81
    assert [s["tier"] for s in p["sources"]] == [2, 5]


def test_level_three_without_summary_is_published_as_none():
    p = project(full("ev_a", 35, 3, summary=None, summary_mode="extractif"))
    validate("event", p)
    assert p["summary"] is None and p["summary_mode"] == "aucun"


def test_home_applies_quota_window_and_retain():
    evs = [full("ev_a", 90, 1), full("ev_b", 80, 1), full("ev_c", 60, 2),
           full("ev_old", 99, 1, updated_at=iso(NOW - timedelta(hours=40))), full("ev_hidden", 10, 0)]
    home = build_home(CFG, {"ia": evs}, NOW)
    validate("home", home)
    assert home["domains"][0]["levels"]["1"] == ["ev_a", "ev_b"]      # quota 2, ev_old hors fenêtre, ev_hidden masqué
    assert set(home["events"]) == {"ev_a", "ev_b"}
    assert home["retain"] == ["ev_a", "ev_b"] and home["sample"] is False


def test_domain_file_lists_seven_days_sorted_by_importance():
    evs = [full("ev_a", 60, 2), full("ev_b", 90, 1),
           full("ev_old", 95, 1, updated_at=iso(NOW - timedelta(days=8)))]
    f = build_domain(CFG["domains"]["ia"], evs, NOW)
    validate("domainFile", f)
    assert [e["id"] for e in f["events"]] == ["ev_b", "ev_a"]


def test_invalid_output_writes_nothing(tmp_path):
    good = build_home(CFG, {"ia": [full("ev_a", 90, 1)]}, NOW)
    bad_event = {k: v for k, v in good["events"]["ev_a"].items() if k != "reliability"}
    bad = {**good, "events": {"ev_a": bad_event}}
    with pytest.raises(ValidationError):
        publish(tmp_path, bad, [build_domain(CFG["domains"]["ia"], [full("ev_a", 90, 1)], NOW)])
    assert not (tmp_path / "site").exists()


def test_publish_writes_home_and_domain_files(tmp_path):
    evs = [full("ev_a", 90, 1)]
    publish(tmp_path, build_home(CFG, {"ia": evs}, NOW), [build_domain(CFG["domains"]["ia"], evs, NOW)])
    validate("home", json.loads((tmp_path / "site" / "data" / "home.json").read_text("utf-8")))
    validate("domainFile", json.loads((tmp_path / "site" / "data" / "domains" / "ia.json").read_text("utf-8")))


def test_write_if_changed_ignores_the_timestamp(tmp_path):
    p = tmp_path / "h.json"
    assert write_if_changed(p, {"generated_at": "t1", "x": 1}) is True
    assert write_if_changed(p, {"generated_at": "t2", "x": 1}) is False
    assert json.loads(p.read_text("utf-8"))["generated_at"] == "t1"
    assert write_if_changed(p, {"generated_at": "t3", "x": 2}) is True


def test_write_if_changed_refreshes_a_stale_stamp_when_asked(tmp_path):
    p = tmp_path / "health.json"
    write_if_changed(p, {"checked_at": iso(NOW), "x": 1}, NOW, max_age_min=55)
    later = NOW + timedelta(minutes=30)
    assert write_if_changed(p, {"checked_at": iso(later), "x": 1}, later, max_age_min=55) is False
    much_later = NOW + timedelta(minutes=90)
    assert write_if_changed(p, {"checked_at": iso(much_later), "x": 1}, much_later, max_age_min=55) is True
