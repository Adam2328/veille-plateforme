from datetime import timedelta

from engine.candidates import top_candidates, update_candidates
from engine.timeutil import iso
from tests.helpers import NOW


def test_unknown_names_are_counted_by_lowercase_key_and_known_names_are_skipped():
    data = update_candidates({}, [("Sam Altman", "ia"), ("sam altman", "finance"), ("OpenAI", "ia"), ("  ", "ia")],
                             lambda name: name == "OpenAI", NOW)
    assert data == {"sam altman": {"name": "Sam Altman", "count": 2, "last_seen": iso(NOW), "domains": ["finance", "ia"]}}


def test_old_candidates_are_forgotten_and_the_top_is_sorted_by_count():
    old = {"vieux": {"name": "Vieux", "count": 9, "last_seen": iso(NOW - timedelta(days=31)), "domains": ["ia"]}}
    data = update_candidates(old, [("B", "ia"), ("A", "ia"), ("B", "ia")], lambda name: False, NOW)
    assert "vieux" not in data
    assert [c["name"] for c in top_candidates(data)] == ["B", "A"]
