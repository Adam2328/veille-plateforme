"""Données structurées F1 depuis Jolpica (successeur d'Ergast, gratuit, sans clé) : calendrier, résultats, classements."""
from collections.abc import Callable
from datetime import datetime

import requests

from .timeutil import iso, parse

_BASE = "https://api.jolpi.ca/ergast/f1"
_SESSIONS = [("FirstPractice", "Essais libres 1"), ("SecondPractice", "Essais libres 2"), ("ThirdPractice", "Essais libres 3"),
             ("SprintQualifying", "Qualifications sprint"), ("Sprint", "Sprint"), ("Qualifying", "Qualifications")]


def fetch_json(url: str) -> dict:
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def _when(block: dict) -> str:
    return iso(parse(f"{block['date']}T{block.get('time', '00:00:00Z')}"))


def _driver(d: dict) -> str:
    return f"{d['givenName']} {d['familyName']}"


def _result(x: dict, text: str) -> dict:
    return {"position": int(x["position"]), "driver": _driver(x["Driver"]), "team": x["Constructor"]["name"],
            "result": text, "points": float(x.get("points", 0))}


def _race_line(x: dict) -> dict:
    return _result(x, (x.get("Time") or {}).get("time") or x.get("status", ""))


def _quali_line(x: dict) -> dict:
    return _result(x, x.get("Q3") or x.get("Q2") or x.get("Q1") or "")


def _races(payload: dict) -> list:
    return payload["MRData"]["RaceTable"]["Races"]


def parse_next(schedule: dict, now: datetime) -> dict | None:
    for r in _races(schedule):
        if parse(_when(r)) > now:
            sessions = [{"name": label, "start": _when(r[key])} for key, label in _SESSIONS if key in r]
            sessions.append({"name": "Course", "start": _when(r)})
            return {"round": int(r["round"]), "name": r["raceName"], "country": r["Circuit"]["Location"]["country"],
                    "sessions": sorted(sessions, key=lambda s: s["start"])}
    return None


def _standings(payload: dict, key: str) -> list:
    return payload["MRData"]["StandingsTable"]["StandingsLists"][0][key]


def collect_f1(previous: dict | None, now: datetime,
               fetch: Callable[[str], dict] = fetch_json) -> tuple[dict | None, list[dict]]:
    old = previous or {}
    health, got = [], {}

    def attempt(name: str, ep: str, parser: Callable[[dict], object]) -> None:
        try:
            got[name] = parser(fetch(f"{_BASE}/{ep}"))
            health.append({"source": f"f1:{name}", "ok": True, "count": 1, "error": None})
        except Exception as exc:  # une source défaillante ne doit jamais arrêter le cycle
            health.append({"source": f"f1:{name}", "ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"})

    attempt("schedule", "current.json?limit=40", lambda p: (p["MRData"]["RaceTable"]["season"], parse_next(p, now)))
    attempt("drivers", "current/driverStandings.json", lambda p: [
        {"position": int(s["position"]), "driver": _driver(s["Driver"]), "team": s["Constructors"][-1]["name"],
         "points": float(s["points"]), "wins": int(s["wins"])} for s in _standings(p, "DriverStandings")])
    attempt("constructors", "current/constructorStandings.json", lambda p: [
        {"position": int(s["position"]), "team": s["Constructor"]["name"], "points": float(s["points"]), "wins": int(s["wins"])}
        for s in _standings(p, "ConstructorStandings")])
    attempt("results", "current/last/results.json", lambda p: _races(p)[0])
    attempt("qualifying", "current/last/qualifying.json", lambda p: [_quali_line(x) for x in _races(p)[0]["QualifyingResults"]])
    attempt("sprint", "current/last/sprint.json", lambda p: [_race_line(x) for r in _races(p) for x in r["SprintResults"]])

    if not got and not previous:
        return None, health
    last = old.get("last")
    if "results" in got:
        race = got["results"]
        last = {"round": int(race["round"]), "name": race["raceName"], "country": race["Circuit"]["Location"]["country"],
                "date": race["date"], "race": [_race_line(x) for x in race["Results"]],
                "qualifying": got.get("qualifying", (last or {}).get("qualifying", [])),
                "sprint": got.get("sprint", (last or {}).get("sprint", []))}
    season, nxt = got.get("schedule", (old.get("season", ""), old.get("next")))
    return {"checked_at": iso(now), "season": season, "stale": len(got) < 6,
            "last": last, "next": nxt, "drivers": got.get("drivers", old.get("drivers", [])),
            "constructors": got.get("constructors", old.get("constructors", []))}, health
