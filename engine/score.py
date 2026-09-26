import math
from datetime import datetime

from .reliability import LOW
from .timeutil import parse


def importance(ev: dict, dom: dict, g: dict, now: datetime) -> float:
    s = g["score"]
    items = ev["items"]
    best = min(i["tier"] for i in items)
    origins = {i["origin"] for i in items}
    authority = s["authority"][best]
    coverage = min(s["coverage_cap"], s["coverage_per_log2"] * math.log2(1 + len(origins)))
    kind = dom["kinds"].get(ev["kind"], {}).get("weight", s["default_kind_weight"])
    entities = s["entity_bonus"] if ev["entities"] else 0
    newest = max(parse(i["published_at"]) for i in items)
    age_h = max(0.0, (now - newest).total_seconds() / 3600)
    bucket = (age_h // s["freshness_bucket_h"]) * s["freshness_bucket_h"]
    freshness = s["freshness_max"] * 0.5 ** (bucket / s["freshness_half_life_h"])
    in_last_2h = sum(1 for i in items if (now - parse(i["published_at"])).total_seconds() <= 7200)
    velocity = s["velocity_bonus"] if in_last_2h >= 2 else 0
    penalty = s["social_only_penalty"] if best >= 4 else 0
    total = authority + coverage + kind + entities + freshness + velocity - penalty
    return round(max(0.0, min(100.0, total)), 1)


def assign_levels(events: list, dom: dict) -> list:
    t, cap = dom["thresholds"], dom["max_l1"]
    out, n1 = [], 0
    for ev in sorted(events, key=lambda e: -e["importance"]):
        imp = ev["importance"]
        level = 1 if imp >= t["l1"] else 2 if imp >= t["l2"] else 3 if imp >= t["l3"] else 0
        if level == 1 and (ev["reliability"] in LOW or n1 >= cap):
            level = 2
        elif level == 1:
            n1 += 1
        out.append({**ev, "level": level})
    return out
