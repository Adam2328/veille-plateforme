from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
