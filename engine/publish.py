import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .agenda import imported_events
from .contract import validate
from .timeutil import iso, parse

_PUBLIC = ("id", "rev", "domain", "kind", "title", "first_seen", "updated_at", "level", "reliability",
           "reliability_reason", "entities")
_STAMPS = ("generated_at", "checked_at")


def project(ev: dict) -> dict:
    p = {k: ev[k] for k in _PUBLIC}
    p["importance"] = round(ev["importance"])
    p["summary"] = ev.get("summary")
    p["summary_mode"] = ev.get("summary_mode", "aucun") if p["summary"] else "aucun"
    layers = ev.get("layers")
    if layers and any(layers.values()):
        p["layers"] = layers
    p["sources"] = [
        {"name": i["source"], "tier": i["tier"], "url": i["url"], "title": i["title"], "published_at": i["published_at"]}
        for i in sorted(ev["items"], key=lambda i: (i["tier"], i["published_at"]))
    ]
    return p


def _agenda_key(title: str, keywords: list[str]) -> str:
    low = title.lower()
    for k in keywords:
        if re.search(rf"\b{re.escape(k.lower())}\b", low):
            return k.lower()
    return low


def upcoming_events(dom: dict, now: datetime, imported: list[str] | None = None,
                    horizon_days: int = 21, limit: int = 6) -> list[dict]:
    today = now.date()
    keywords = dom.get("agenda_keywords", [])
    official = []
    for entry in dom.get("agenda", []):
        try:
            day = date.fromisoformat(str(entry["date"]))
            title = str(entry["title"])
        except (KeyError, ValueError, TypeError):
            continue
        if today <= day <= today + timedelta(days=horizon_days):
            official.append({"date": day.isoformat(), "title": title})
    extra = (imported_events(imported or [], keywords, today, horizon_days, dom.get("agenda_exclude", []))
             if keywords else [])
    seen, out = set(), []
    for entry in [*official, *extra]:                     # le calendrier officiel est prioritaire
        key = (entry["date"], _agenda_key(entry["title"], keywords))
        if key not in seen:
            seen.add(key)
            out.append(entry)
    return sorted(out, key=lambda a: (a["date"], a["title"]))[:limit]


def build_domain(dom: dict, events: list, now: datetime, imported: list[str] | None = None) -> dict:
    cutoff = now - timedelta(days=7)
    shown = sorted((e for e in events if e["level"] >= 1 and parse(e["updated_at"]) >= cutoff), key=lambda e: -e["importance"])
    out = {"generated_at": iso(now), "domain": {k: dom[k] for k in ("id", "name", "accent")},
           "events": [project(e) for e in shown], "upcoming": upcoming_events(dom, now, imported)}
    links = [{"title": str(link["title"]), "url": link["url"]} for link in dom.get("links", [])
             if isinstance(link, dict) and link.get("title") and str(link.get("url", "")).startswith("https://")]
    if links:
        out["links"] = links
    card = learn_card(dom, now)
    if card:
        out["learn"] = card
    return out


def learn_card(dom: dict, now: datetime) -> dict | None:
    """Fiche « À connaître » du jour : tourne une fois par jour dans la liste écrite en config (aucun LLM)."""
    cards = [c for c in dom.get("learn", []) if isinstance(c, dict) and all(c.get(k) for k in ("category", "title", "text"))]
    if not cards:
        return None
    c = cards[now.date().toordinal() % len(cards)]
    return {"category": str(c["category"]), "title": str(c["title"]), "text": str(c["text"])}


def build_home(cfg: dict, events_by_domain: dict, now: datetime, agendas: dict | None = None) -> dict:
    h = cfg["global"]["home"]
    cutoff = now - timedelta(hours=h["window_hours"])
    domains, events = [], {}
    for dom in sorted(cfg["domains"].values(), key=lambda d: d["order"]):
        top = sorted((e for e in events_by_domain.get(dom["id"], []) if e["level"] >= 1 and parse(e["updated_at"]) >= cutoff),
                     key=lambda e: -e["importance"])[: dom["quota"]]
        levels = {str(n): [e["id"] for e in top if e["level"] == n] for n in (1, 2, 3)}
        events.update({e["id"]: project(e) for e in top})
        entry = {"id": dom["id"], "name": dom["name"], "accent": dom["accent"], "levels": levels,
                 "upcoming": upcoming_events(dom, now, (agendas or {}).get(dom["id"]))}
        card = learn_card(dom, now)
        domains.append({**entry, "learn": card} if card else entry)
    level_one = sorted((e for e in events.values() if e["level"] == 1), key=lambda e: -e["importance"])
    return {"generated_at": iso(now), "sample": False, "domains": domains,
            "retain": [e["id"] for e in level_one[: h["retain_max"]]], "events": events}


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), "utf-8")
    os.replace(tmp, path)


def write_if_changed(path: Path, obj: dict, now: datetime | None = None, max_age_min: int | None = None) -> bool:
    stamp = next((k for k in _STAMPS if k in obj), None)
    if path.exists():
        old = json.loads(path.read_text("utf-8"))
        same = {k: v for k, v in old.items() if k != stamp} == {k: v for k, v in obj.items() if k != stamp}
        fresh = max_age_min is None or (now - parse(old[stamp])).total_seconds() < max_age_min * 60
        if same and fresh:
            return False
    write_json(path, obj)
    return True


def publish(root: Path, home: dict, domain_files: list) -> None:
    validate("home", home)
    for d in domain_files:
        validate("domainFile", d)
    out = root / "site" / "data"
    write_if_changed(out / "home.json", home)
    for d in domain_files:
        write_if_changed(out / "domains" / f"{d['domain']['id']}.json", d)


def publish_quotes(root: Path, quotes: dict) -> None:
    validate("quotes", quotes)
    write_if_changed(root / "site" / "data" / "quotes.json", quotes)


def publish_football(root: Path, data: dict) -> None:
    validate("football", data)
    write_if_changed(root / "site" / "data" / "football.json", data)


def publish_json(root: Path, kind: str, name: str, data: dict) -> None:
    validate(kind, data)
    write_if_changed(root / "site" / "data" / name, data)
