"""Bandeau Vigie : une ligne de repères, tous univers confondus (nouveautés, agenda, matchs, Grand Prix, marchés)."""
from datetime import datetime, timedelta

from .timeutil import iso, parse


def _item(universe: str, kind: str, label: str, value: object = None, delta: float | None = None,
          unit: str | None = None, at: str | None = None, href: str | None = None) -> dict:
    return {"universe": universe, "kind": kind, "label": label, "value": value, "delta": delta, "unit": unit, "at": at, "href": href}


def _news(home: dict, cfg: dict, now: datetime) -> list[dict]:
    fresh = sorted((e for e in home.get("events", {}).values() if e["level"] == 1 and e.get("universe")
                    and now - parse(e["first_seen"]) <= timedelta(hours=cfg["new_hours"])),
                   key=lambda e: e["first_seen"], reverse=True)
    return [_item(e["universe"], "new", e.get("title_fr") or e["title"], href=f"#/e/{e['id']}") for e in fresh][: cfg["max_new"]]


def _agenda(home: dict, uni_of: dict, cfg: dict, now: datetime) -> list[dict]:
    horizon = (now + timedelta(days=cfg["agenda_days"])).date().isoformat()
    rows = sorted(((u, d["id"]) for d in home.get("domains", []) if d["id"] in uni_of for u in d.get("upcoming", [])
                   if u["date"] <= horizon), key=lambda x: (x[0]["date"], x[0]["title"]))
    return [_item(uni_of[dom], "agenda", u["title"], at=u["date"]) for u, dom in rows][: cfg["max_agenda"]]


def _matches(football: dict | None, cfg: dict, now: datetime) -> list[dict]:
    fb = football or {}
    upcoming = [_item("sport", "match", f"{m['home']} – {m['away']}", at=m["date"], href="#/u/sport/foot")
                for m in fb.get("fixtures", []) if now <= parse(m["date"]) <= now + timedelta(hours=36)]
    played = [_item("sport", "match", f"{m['home']} – {m['away']}", value=f"{m['home_score']}–{m['away_score']}",
                    at=m["date"], href="#/u/sport/foot")
              for m in fb.get("results", []) if m.get("home_score") is not None
              and now - timedelta(hours=18) <= parse(m["date"]) <= now]
    return [*upcoming, *played][: cfg["max_matches"]]


def _race(f1: dict | None, now: datetime) -> list[dict]:
    nxt = (f1 or {}).get("next") or {}
    race = next((s for s in nxt.get("sessions", []) if s["name"] == "Course"), None)
    if race and now <= parse(race["start"]) <= now + timedelta(days=7):
        return [_item("sport", "race", nxt["name"], at=race["start"], href="#/u/sport/f1")]
    return []


def _quotes(quotes: dict | None, cfg: dict) -> list[dict]:
    by_symbol = {q["symbol"]: q for q in (quotes or {}).get("quotes", [])}
    out = []
    for q in (by_symbol[s] for s in cfg["quotes"] if s in by_symbol):
        rate = q["group"] == "Taux"
        out.append(_item("finance", "quote", q["name"], value=q["price"], delta=q["change"] if rate else q["change_pct"],
                         unit="pt" if rate else "%", at=q["as_of"], href="#/u/finance"))
    return out


def build_band(quotes: dict | None, football: dict | None, f1: dict | None, home: dict, uni_of: dict,
               g: dict, now: datetime) -> dict:
    cfg = g["band"]
    items = [*_news(home, cfg, now), *_agenda(home, uni_of, cfg, now), *_matches(football, cfg, now),
             *_race(f1, now), *_quotes(quotes, cfg)]
    return {"generated_at": iso(now), "items": items}
