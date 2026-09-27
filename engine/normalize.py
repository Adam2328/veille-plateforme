import hashlib
import html
import re
from datetime import datetime, timedelta

from .timeutil import parse

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# ponytail: heuristique de syndication par regex ; un vrai résolveur de citations si les faux positifs pèsent sur les mesures
_ATTR = re.compile(r"\b(?i:selon|d'après|d’après|according to|via)\s+(?:le |la |l'|l’|the )?"
                   r"([A-ZÀ-Ý][\w'’.&-]*(?: [A-ZÀ-Ý][\w'’.&-]*){0,2})")


def clean(text: str | None) -> str:
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", text or ""))).strip()


def item_id(url: str) -> str:
    return "it_" + hashlib.sha1(url.strip().lower().encode("utf-8")).hexdigest()[:12]


def origin_of(default_origin: str, title: str, snippet: str) -> str:
    m = _ATTR.search(f"{title}. {snippet}")
    return (m.group(1) if m else default_origin).lower()


def normalize(raw: dict, source: dict, publishers: dict | None = None) -> dict:
    title = clean(raw["title"])
    snippet = clean(raw.get("snippet", ""))[:600]
    pub = raw.get("publisher")
    default_origin = (pub or source.get("origin") or source["name"]).lower()
    tier = (publishers or {}).get(default_origin, source["tier"]) if pub else source["tier"]
    image = str(raw.get("image") or "")
    item = {
        "id": item_id(raw["url"]), "source": pub or source["name"], "tier": tier,
        "origin": origin_of(default_origin, title, snippet), "title": title, "snippet": snippet,
        "url": raw["url"], "published_at": raw["published_at"], "domain": source["domain"],
    }
    # https uniquement : ni contenu mixte ni schéma exécutable dans la page
    return {**item, "image": image} if image.startswith("https://") and len(image) <= 500 else item


def _title_key(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def dedupe(items: list, known_ids: set) -> list:
    seen_ids, seen_titles, out = set(known_ids), set(), []
    for it in items:
        key = _title_key(it["title"])
        if it["id"] in seen_ids or key in seen_titles:
            continue
        seen_ids.add(it["id"])
        seen_titles.add(key)
        out.append(it)
    return out


def recent(items: list, now: datetime, hours: int) -> list:
    cutoff = now - timedelta(hours=hours)
    return [i for i in items if parse(i["published_at"]) >= cutoff]


def excluded(item: dict, patterns: list[str]) -> bool:
    text = f"{item['title']} {item['snippet']} {item.get('url', '')}".lower()
    return any(p.lower() in text for p in patterns)
