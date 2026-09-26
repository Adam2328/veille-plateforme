import math
from collections.abc import Callable
from datetime import datetime
from urllib.parse import quote

import requests

from .timeutil import iso

_RELAY = "https://ticker-relay.onrender.com/latest-custom?symbols={symbols}"
# ponytail: le relais Render gratuit se réveille en 30 à 60 s après une période d'inactivité
_TIMEOUT_SECONDS = 100


def fetch_relay(url: str) -> dict:
    r = requests.get(url, timeout=_TIMEOUT_SECONDS)
    r.raise_for_status()
    return r.json()


def _number(x: object) -> float | None:
    if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x):
        return float(x)
    return None


def _quote(spec: dict, price: float, pct: float | None, now: datetime, prev: dict | None) -> dict:
    change = round(price - price / (1 + pct / 100), 4) if pct is not None and pct != -100 else None
    pct_out = pct if change is not None else None
    unchanged = bool(prev) and not prev["stale"] and prev["price"] == price and prev["change_pct"] == pct_out
    return {"symbol": spec["symbol"], "name": spec["name"], "group": spec["group"], "price": price, "change": change,
            "change_pct": pct_out, "currency": "",
            "as_of": prev["as_of"] if unchanged else iso(now),      # stable tant que le cours ne bouge pas : évite de réécrire le fichier
            "stale": False}


def collect_quotes(specs: list[dict], previous: dict | None, now: datetime,
                   fetch: Callable[[str], dict] = fetch_relay) -> tuple[dict, list[dict]]:
    old = {q["symbol"]: q for q in (previous or {}).get("quotes", [])}
    url = _RELAY.format(symbols=",".join(quote(s["symbol"], safe="=") for s in specs))
    try:
        rows = {r["nom"]: r for r in fetch(url)["indices"]}
        error = None
    except Exception as exc:  # un relais défaillant ne doit jamais arrêter le cycle
        rows, error = {}, f"{type(exc).__name__}: {exc}"
    health = [{"source": "quote-relay", "ok": error is None, "count": len(rows), "error": error}]
    quotes = []
    for spec in specs:
        row = rows.get(spec["symbol"]) or {}
        price = _number(row.get("valeur"))
        if price is not None:
            quotes.append(_quote(spec, price, _number(row.get("variation")), now, old.get(spec["symbol"])))
        elif spec["symbol"] in old:
            quotes.append({**old[spec["symbol"]], "name": spec["name"], "group": spec["group"], "stale": True})
        if error is None:
            health.append({"source": f"quote:{spec['symbol']}", "ok": price is not None,
                           "count": 1 if price is not None else 0, "error": None if price is not None else "valeur absente"})
    return {"checked_at": iso(now), "quotes": quotes}, health
