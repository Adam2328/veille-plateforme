import json
from datetime import datetime, timedelta
from pathlib import Path

from .timeutil import parse


def _file(root: Path, dt: datetime) -> Path:
    return root / "data" / "events" / f"{dt.strftime('%Y-%m')}.jsonl"


def _slim(ev: dict) -> dict:
    return {**ev, "items": [{**i, "snippet": i["snippet"][:300]} for i in ev["items"]]}


# ponytail: JSONL en ajout seul (une ligne par révision) ; compacter ou passer en .gz si le dépôt dépasse ~100 Mo
def append(root: Path, events: list, now: datetime) -> None:
    if not events:
        return
    path = _file(root, now)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(_slim(ev), ensure_ascii=False, separators=(",", ":")) + "\n")


def load_recent(root: Path, now: datetime, days: int = 7) -> list:
    cutoff = now - timedelta(days=days)
    latest = {}
    for path in sorted({_file(root, cutoff), _file(root, now)}):
        if not path.exists():
            continue
        for line in path.read_text("utf-8").splitlines():
            if line.strip():
                ev = json.loads(line)
                latest[ev["id"]] = ev
    return [e for e in latest.values() if parse(e["updated_at"]) >= cutoff]
