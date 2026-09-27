"""« Ce qu'il faut savoir aujourd'hui » : plancher par univers, puis meilleurs scores du jour (spec §6)."""
from collections import Counter
from datetime import datetime, timedelta

from .timeutil import parse


def day_score(ev: dict, now: datetime, t: dict) -> float:
    score = ev["importance"]
    if now - parse(ev["first_seen"]) <= timedelta(hours=24):
        score += t["novelty_bonus"]
    if ev["rev"] > 1 and now - parse(ev["updated_at"]) <= timedelta(hours=12):
        score += t["evolution_bonus"]
    return score


def build_today(events: list, universes: dict, g: dict, now: datetime) -> list[dict]:
    t = g["today"]
    cutoff = now - timedelta(hours=t["window_hours"])
    pool = sorted((e for e in events if e.get("level", 0) >= 1 and e.get("universe") in universes
                   and parse(e["updated_at"]) >= cutoff), key=lambda e: (-day_score(e, now, t), e["id"]))
    picked = {u: [] for u in universes}
    per_entity, chosen = Counter(), set()

    def take(e: dict) -> None:
        lead = (e.get("entity_ids") or [None])[0]
        if e["id"] in chosen or (lead and per_entity[lead] >= t["max_per_entity"]):
            return
        chosen.add(e["id"])
        picked[e["universe"]].append(e["id"])
        if lead:
            per_entity[lead] += 1

    for u in universes:
        for e in pool:
            if len(picked[u]) >= t["floor"]:
                break
            if e["universe"] == u:
                take(e)
    for e in pool:
        if len(chosen) >= t["total"]:
            break
        take(e)
    rank = {e["id"]: n for n, e in enumerate(pool)}
    return [{"id": u, "name": uni["name"], "short": uni["short"], "color": uni["color"],
             "ids": sorted(picked[u], key=rank.__getitem__)} for u, uni in universes.items()]
