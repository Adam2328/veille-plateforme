import re
from datetime import timedelta

from .timeutil import parse

LOW = {"rumeur", "non_confirmé"}
GROWTH_WINDOW = timedelta(minutes=60)
GROWTH_MIN = 3
_HEDGE = re.compile(
    r"\b(serait|seraient|pourrait|pourraient|aurait|auraient|selon nos informations|rumeurs?|"
    r"would|could|reportedly|rumou?rs?|allegedly|sources say|apparently)\b", re.I)


def classify(items, now):
    by_origin = {}
    for it in items:
        cur = by_origin.get(it["origin"])
        if cur is None or it["tier"] < cur["tier"]:
            by_origin[it["origin"]] = it
    top = min(by_origin.values(), key=lambda i: i["tier"])
    best, n_origins = top["tier"], len(by_origin)
    n_reliable = sum(1 for i in by_origin.values() if i["tier"] <= 3)
    recent = sum(1 for i in items if now - parse(i["published_at"]) <= GROWTH_WINDOW)

    if best == 1:
        return "officiel", f"source officielle : {top['source']}"
    if n_reliable >= 2 or (best <= 2 and n_origins >= 2):
        return "confirmé", f"{n_origins} origines indépendantes dont {top['source']}"
    if best <= 3 and recent >= GROWTH_MIN:
        return "en_développement", f"{recent} publications en moins d'une heure"
    if best <= 2:
        return "rapporté", f"1 origine fiable : {top['source']}"
    if best >= 4 and _HEDGE.search(" ".join(f"{i['title']} {i['snippet']}" for i in items)):
        return "rumeur", "formulation au conditionnel, sources tier 4-5 uniquement"
    return "non_confirmé", "aucune source fiable identifiée"
