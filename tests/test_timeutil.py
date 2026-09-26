from datetime import timezone

from engine.timeutil import iso, now_utc, parse


def test_parse_accepts_z_suffix_and_roundtrips():
    dt = parse("2026-09-26T10:00:00Z")
    assert dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0
    assert parse(iso(dt)) == dt


def test_now_utc_is_timezone_aware():
    assert now_utc().tzinfo == timezone.utc
