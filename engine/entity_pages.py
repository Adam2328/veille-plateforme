"""Index des entités (recherche, pastilles) et fiche de chaque entité (spec §7)."""
from collections import defaultdict
from datetime import datetime, timedelta

from .catalog import TYPES
from .search import _entry
from .timeutil import iso, parse


def _page(eid: str, ent: dict, fact: dict, rels: list, evs: list, catalog: dict, now: datetime) -> dict:
    return {
        "generated_at": iso(now),
        "entity": {"id": eid, "name": ent["name"], "type": ent["type"], "type_label": TYPES[ent["type"]],
                   "universes": ent["universes"], **{k: ent[k] for k in ("ticker", "wikidata") if ent.get(k)}},
        "description": fact.get("description"), "image": fact.get("image"), "facts": fact.get("facts", []),
        "relations": [{"id": r["id"], "name": catalog[r["id"]]["name"], "type": catalog[r["id"]]["type"],
                       "label": r["label"], "origin": r["origin"], "weight": r["weight"]} for r in rels],
        "events": [_entry(e) for e in evs],
    }


def build_entity_pages(catalog: dict, facts: dict, adj: dict, events: list, quotes: dict | None, now: datetime,
                       days: int = 30, max_events: int = 40, max_relations: int = 40) -> tuple[dict, dict]:
    cutoff = now - timedelta(days=days)
    recent = sorted((e for e in events if e.get("level", 0) >= 1 and parse(e["updated_at"]) >= cutoff),
                    key=lambda e: e["updated_at"], reverse=True)
    by_entity = defaultdict(list)
    for e in recent:
        for eid in e.get("entity_ids", []):
            by_entity[eid].append(e)
    by_symbol = {q["symbol"]: q for q in (quotes or {}).get("quotes", [])}
    index, pages = [], {}
    for eid, ent in sorted(catalog.items()):
        fact, evs = (facts or {}).get(eid, {}), by_entity.get(eid, [])
        index.append({"id": eid, "name": ent["name"], "type": ent["type"], "universes": ent["universes"],
                      "aliases": [str(a).lstrip("=") for a in ent["aliases"][:4]], "n30": len(evs),
                      **({"image": fact["image"]} if fact.get("image") else {})})
        rels = sorted((r for r in adj.get(eid, []) if r["id"] in catalog),
                      key=lambda r: (r["origin"] == "cooccurrence", -r["weight"], r["id"]))[:max_relations]
        page = _page(eid, ent, fact, rels, evs[:max_events], catalog, now)
        quote = by_symbol.get(ent.get("quote"))
        if quote:
            page["quote"] = {k: quote[k] for k in ("price", "change_pct", "currency", "as_of", "stale")}
        pages[eid] = page
    return {"generated_at": iso(now), "types": TYPES, "entities": index}, pages
