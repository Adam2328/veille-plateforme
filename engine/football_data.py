from collections.abc import Callable
from datetime import datetime, timedelta

import requests

from .timeutil import iso, parse

_BASE = "https://api.football-data.org/v4"
_FIXTURE_STATUSES = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "POSTPONED"}
_KEEP = 40


def fetch_fd(url: str, token: str) -> dict:
    r = requests.get(url, headers={"X-Auth-Token": token}, timeout=15)
    r.raise_for_status()
    return r.json()


def _team(team: dict) -> str:
    return team.get("shortName") or team.get("name") or "?"


def parse_standings(payload: dict) -> list[dict]:
    tables = [s for s in payload.get("standings", []) if s.get("type") == "TOTAL" and s.get("table")]
    if not tables:
        raise ValueError("aucun classement TOTAL dans la réponse")
    return [{
        "position": r["position"], "team": _team(r["team"]), "played": r["playedGames"], "won": r["won"],
        "draw": r["draw"], "lost": r["lost"], "gf": r["goalsFor"], "ga": r["goalsAgainst"],
        "gd": r["goalDifference"], "points": r["points"], "form": (r.get("form") or "").replace(",", ""),
    } for r in tables[0]["table"]]


def parse_matches(payload: dict, statuses: set[str]) -> list[dict]:
    out = []
    for m in payload.get("matches", []):
        if m.get("status") not in statuses:
            continue
        full = (m.get("score") or {}).get("fullTime") or {}
        out.append({
            "id": m["id"], "competition": m["competition"]["code"], "date": iso(parse(m["utcDate"])),
            "home": _team(m["homeTeam"]), "away": _team(m["awayTeam"]),
            "home_score": full.get("home"), "away_score": full.get("away"),
            "status": m["status"], "matchday": m.get("matchday"),
        })
    return out


def _try(health: list, source: str, action: Callable[[], list]) -> list | None:
    try:
        result = action()
        health.append({"source": source, "ok": True, "count": len(result), "error": None})
        return result
    except Exception as exc:  # un appel défaillant ne doit jamais arrêter le cycle
        health.append({"source": source, "ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"})
        return None


def collect_football(cfg: dict, token: str | None, previous: dict | None, now: datetime,
                     fetch: Callable[[str, str], dict] = fetch_fd) -> tuple[dict | None, list[dict]]:
    if not token:
        return None, [{"source": "football-data", "ok": False, "count": 0,
                       "error": "FOOTBALL_DATA_TOKEN absent : classements, résultats et calendrier non mis à jour"}]
    old = previous or {}
    old_comps = {c["code"]: c for c in old.get("competitions", [])}
    health, comps = [], []
    for c in cfg["competitions"]:
        rows = _try(health, f"football:standings:{c['code']}",
                    lambda c=c: parse_standings(fetch(f"{_BASE}/competitions/{c['code']}/standings", token)))
        links = {"flashscore": c["flashscore"]} if c.get("flashscore") else {}
        if rows:
            comps.append({"code": c["code"], "name": c["name"], "standings": rows, "stale": False, **links})
        elif c["code"] in old_comps:
            comps.append({**old_comps[c["code"]], "name": c["name"], "stale": True, **links})
    codes = ",".join(c["code"] for c in cfg["competitions"])
    today = now.date()

    def window(start, end) -> str:
        return f"{_BASE}/matches?competitions={codes}&dateFrom={start.isoformat()}&dateTo={end.isoformat()}"

    played = _try(health, "football:matches:results", lambda: sorted(parse_matches(
        fetch(window(today - timedelta(days=cfg.get("results_days", 9)), today), token), {"FINISHED"}),
        key=lambda m: m["date"], reverse=True)[:_KEEP])
    ahead = cfg.get("fixtures_days", 9)

    def fixtures(start, end) -> list:
        return sorted(parse_matches(fetch(window(start, end), token), _FIXTURE_STATUSES), key=lambda m: m["date"])[:_KEEP]

    upcoming = _try(health, "football:matches:fixtures", lambda: fixtures(today, today + timedelta(days=ahead)))
    if upcoming == []:      # trêve : une seule requête de plus sur les 10 jours suivants (9 requêtes au plus par cycle)
        start = today + timedelta(days=ahead + 1)
        upcoming = _try(health, "football:matches:fixtures-next", lambda: fixtures(start, start + timedelta(days=9)))
    return {"checked_at": iso(now), "competitions": comps,
            "results": played if played is not None else old.get("results", []),
            "fixtures": upcoming if upcoming is not None else old.get("fixtures", [])}, health
