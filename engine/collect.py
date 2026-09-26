from collections.abc import Callable
from datetime import datetime, timezone

import feedparser
import requests

from .timeutil import iso, now_utc

_HEADERS = {"User-Agent": "veille-plateforme/1.0 (usage personnel)"}


def fetch_bytes(url: str) -> bytes:
    r = requests.get(url, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    return r.content


def _entry_time(entry: dict) -> datetime:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else now_utc()


def collect_rss(source: dict, fetch: Callable[[str], bytes] = fetch_bytes, limit: int = 30) -> tuple[list, dict]:
    try:
        feed = feedparser.parse(fetch(source["url"]))
        if feed.bozo and not feed.entries:
            raise ValueError(f"flux illisible : {feed.bozo_exception}")
        raws = []
        for e in feed.entries[:limit]:
            if not e.get("link") or not e.get("title"):
                continue
            raw = {"title": e["title"], "url": e["link"], "snippet": e.get("summary", ""),
                   "published_at": iso(_entry_time(e))}
            if source.get("publisher_suffix"):
                head, sep, pub = raw["title"].rpartition(" - ")
                if sep:
                    raw["title"], raw["publisher"] = head, pub.strip()
            raws.append(raw)
        return raws, {"source": source["id"], "ok": True, "count": len(raws), "error": None}
    except Exception as exc:  # une source défaillante ne doit jamais arrêter le cycle
        return [], {"source": source["id"], "ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"}


def collect_source(source: dict, fetch: Callable[[str], bytes] = fetch_bytes) -> tuple[list, dict]:
    if source["type"] == "rss":
        return collect_rss(source, fetch)
    return [], {"source": source["id"], "ok": False, "count": 0, "error": f"type non géré : {source['type']}"}
