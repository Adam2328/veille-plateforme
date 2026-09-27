"""Alertes rares et justifiées, envoyées par ntfy.sh (gratuit). Le serveur ne connaît pas les suivis de l'utilisateur."""
from collections.abc import Callable
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

from .timeutil import parse

STRONG = {"officiel", "confirmé"}


def _minimum(dom: dict) -> float:
    return dom.get("alert_min", dom["thresholds"]["l1"] + 10)


def select_alerts(events: list, domains: dict, g: dict, sent: dict, now: datetime) -> list:
    cfg = g["alerts"]
    today = now.date()
    sent_today = sum(1 for when in sent.values() if parse(when).date() == today)
    budget = max(0, cfg["max_per_day"] - sent_today)
    recent = now - timedelta(hours=cfg["recent_hours"])
    candidates = []
    for e in events:
        dom = domains.get(e["domain"])
        if (dom and e["id"] not in sent and e.get("level") == 1 and e.get("reliability") in STRONG
                and e.get("kind") in dom.get("alert_kinds", []) and e["importance"] >= _minimum(dom)
                and parse(e["first_seen"]) >= recent):
            candidates.append(e)
    return sorted(candidates, key=lambda e: -e["importance"])[:budget]


def send_ntfy(topic: str, event: dict, dom: dict, g: dict,
              post: Callable[..., object] = requests.post) -> None:
    retenir = (event.get("summary") or {}).get("retenir", "")
    body = f"{event['title']}\n{retenir}".strip()
    link = f"{g['alerts']['site_url']}#/e/{quote(event['id'])}"
    # Les en-têtes HTTP doivent rester en ASCII : le texte accentué passe dans le corps (UTF-8).
    title = dom["name"].encode("ascii", "ignore").decode() or "Veille"
    post(f"https://ntfy.sh/{quote(topic, safe='')}", data=body.encode("utf-8"), timeout=15,
         headers={"Title": f"{title} - alerte", "Click": link, "Tags": "rotating_light", "Priority": "high"})


def prune_sent(sent: dict, now: datetime, days: int = 7) -> dict:
    cutoff = now - timedelta(days=days)
    return {k: v for k, v in sent.items() if parse(v) >= cutoff}
