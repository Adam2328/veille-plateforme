import re
from datetime import date, timedelta

import requests

REGIONS = {"usa": "États-Unis", "europe": "Europe", "asie": "Asie", "afrique": "Afrique", "global": "Monde"}
_POINT = re.compile(r"^\s*(\d{1,2})(?:-(\d{1,2}))?/(\d{1,2})\s*$")


def parse_point(point: str, today: date) -> dict | None:
    parts = [p.strip() for p in re.split(r"\s*::\s*", point)]
    if len(parts) < 4:
        return None
    m = _POINT.match(parts[0])
    if not m:
        return None
    first, last, month = int(m.group(1)), int(m.group(2) or m.group(1)), int(m.group(3))
    try:
        start = date(today.year, month, first)
        if (today - start).days > 60:
            start = date(today.year + 1, month, first)
        end = date(start.year, month, last)
    except ValueError:
        return None
    if end < start:
        return None
    return {"start": start, "end": end, "region": parts[1].lower(), "title": parts[3]}


def _has_keyword(title: str, keywords: list[str]) -> bool:
    low = title.lower()
    return any(re.search(rf"\b{re.escape(k.lower())}\b", low) for k in keywords)


def imported_events(points: list[str], keywords: list[str], today: date, horizon_days: int = 21,
                    exclude: list[str] | tuple[str, ...] = ()) -> list[dict]:
    out, limit = [], today + timedelta(days=horizon_days)
    for point in points:
        parsed = parse_point(point, today)
        if not parsed or not _has_keyword(parsed["title"], keywords) or _has_keyword(parsed["title"], list(exclude)):
            continue
        if parsed["end"] < today or parsed["start"] > limit:
            continue
        label = REGIONS.get(parsed["region"], parsed["region"].capitalize())
        out.append({"date": max(parsed["start"], today).isoformat(), "title": f"{label} · {parsed['title']}"})
    return out


def fetch_points(url: str) -> list[str]:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return [e["point"] for e in r.json() if isinstance(e, dict) and isinstance(e.get("point"), str)]
