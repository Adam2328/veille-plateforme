"""Index compact pour la recherche et les archives côté navigateur (aucun serveur)."""
from datetime import datetime, timedelta

from .timeutil import iso, parse

FULL_DAYS = 30        # niveaux 1 et 2
SHORT_DAYS = 7        # niveau 3
# ponytail: un seul fichier ; découper par mois (archive/AAAA-MM.json) si l'index dépasse ~1 Mo
CAP = 3000           # ~1,5 Mo au plus, chargé à la demande côté site


def _entry(ev: dict) -> dict:
    best = min(ev["items"], key=lambda i: (i["tier"], i["published_at"]))
    return {"id": ev["id"], "domain": ev["domain"], "title": ev["title"],
            "retenir": (ev.get("summary") or {}).get("retenir", ""), "entities": ev.get("entities", []),
            "date": ev["updated_at"], "level": ev["level"], "reliability": ev["reliability"],
            "source": best["source"], "url": best["url"]}


def build_index(events: list, domains: dict, now: datetime, cap: int = CAP) -> dict:
    full, short = now - timedelta(days=FULL_DAYS), now - timedelta(days=SHORT_DAYS)
    kept = [e for e in events if e["domain"] in domains and e.get("level", 0) >= 1
            and parse(e["updated_at"]) >= (full if e["level"] <= 2 else short)]
    kept.sort(key=lambda e: e["updated_at"], reverse=True)
    return {"generated_at": iso(now), "domains": [{"id": d["id"], "name": d["name"]} for d in domains.values()],
            "events": [_entry(e) for e in kept[:cap]]}
