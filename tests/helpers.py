from datetime import datetime, timedelta, timezone

from engine.config import load_config
from engine.timeutil import iso

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
G = load_config()["global"]
DOM = {
    "id": "ia", "name": "IA", "accent": "#5B3FA8", "order": 1, "quota": 12, "max_l1": 2,
    "thresholds": {"l1": 70, "l2": 50, "l3": 30},
    "entities": {"OpenAI": ["openai", "gpt-6"], "NVIDIA": ["nvidia"]},
    "kinds": {"model_release": {"weight": 25, "keywords": ["lance", "dévoile", "releases"]}},
    "sources": [],
}


def mk_item(id, title, tier=2, origin=None, minutes_ago=30, snippet=""):
    return {
        "id": id, "source": f"src-{id}", "tier": tier, "origin": origin or f"origin-{id}",
        "title": title, "snippet": snippet, "url": f"https://example.com/{id}",
        "published_at": iso(NOW - timedelta(minutes=minutes_ago)), "domain": "ia",
    }


def mk_event(items, **kw):
    base = {
        "id": "ev_test", "rev": 1, "domain": "ia", "kind": "model_release", "title": items[0]["title"],
        "first_seen": iso(NOW), "updated_at": iso(NOW), "entities": ["OpenAI"], "items": items,
    }
    return {**base, **kw}
