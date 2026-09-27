"""Noms propres importants absents du catalogue, proposés par le LLM : jamais ajoutés sans validation (spec §5.3)."""
from collections.abc import Callable
from datetime import datetime, timedelta

from .timeutil import iso, parse


def update_candidates(old: dict, names: list[tuple[str, str]], is_known: Callable[[str], bool],
                      now: datetime, keep_days: int = 30) -> dict:
    data = dict(old)
    for raw, domain in names:
        name = raw.strip()
        if not name or is_known(name):
            continue
        key = name.lower()
        cur = data.get(key, {"name": name, "count": 0, "domains": []})
        data[key] = {"name": cur["name"], "count": cur["count"] + 1, "last_seen": iso(now),
                     "domains": sorted({*cur["domains"], domain})}
    cutoff = now - timedelta(days=keep_days)
    return {k: v for k, v in sorted(data.items()) if parse(v["last_seen"]) >= cutoff}


def top_candidates(data: dict, n: int = 30) -> list[dict]:
    return sorted(data.values(), key=lambda c: (-c["count"], c["name"]))[:n]
