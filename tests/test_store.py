import json
from datetime import timedelta

from engine.store import append, load_recent
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item


def test_later_line_wins_for_the_same_event(tmp_path):
    e1 = mk_event([mk_item("a", "x")])
    append(tmp_path, [e1], NOW)
    append(tmp_path, [{**e1, "rev": 2}], NOW)
    assert [e["rev"] for e in load_recent(tmp_path, NOW)] == [2]


def test_old_events_are_not_loaded(tmp_path):
    old = mk_event([mk_item("a", "x")], updated_at=iso(NOW - timedelta(days=9)))
    append(tmp_path, [old], NOW)
    assert load_recent(tmp_path, NOW) == []


def test_events_straddling_a_month_boundary_are_found(tmp_path):
    first_of_month = NOW.replace(day=1, hour=2)
    prev_month = first_of_month - timedelta(days=2)
    ev = mk_event([mk_item("a", "x")], updated_at=iso(prev_month))
    append(tmp_path, [ev], prev_month)
    assert [e["id"] for e in load_recent(tmp_path, first_of_month)] == ["ev_test"]


def test_snippets_are_trimmed_in_storage(tmp_path):
    append(tmp_path, [mk_event([mk_item("a", "x", snippet="z" * 900)])], NOW)
    line = next((tmp_path / "data" / "events").glob("*.jsonl")).read_text("utf-8").strip()
    assert len(json.loads(line)["items"][0]["snippet"]) == 300


def test_missing_history_is_empty_and_append_of_nothing_writes_nothing(tmp_path):
    assert load_recent(tmp_path, NOW) == []
    append(tmp_path, [], NOW)
    assert not (tmp_path / "data").exists()
