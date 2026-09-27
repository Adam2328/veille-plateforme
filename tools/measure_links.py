"""Mesure du rattachement aux entités sur les données publiées : taux de liaison et échantillon de 50 à relire.

Usage : .venv/Scripts/python tools/measure_links.py
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = ROOT / "site" / "data"
    names = {e["id"]: e["name"] for e in json.loads((data / "entities" / "index.json").read_text("utf-8"))["entities"]}
    events = {e["id"]: e for p in sorted((data / "universes").glob("*.json"))
              for e in json.loads(p.read_text("utf-8"))["events"]}
    major = [e for e in events.values() if e["level"] in (1, 2)]
    linked = [e for e in major if e.get("entity_ids")]
    pct = 100 * len(linked) / max(1, len(major))
    print(f"Niveaux 1-2 : {len(major)} ; reliés à au moins une entité : {len(linked)} ({pct:.0f} %)")
    print(f"Titres traduits : {sum(1 for e in major if e.get('title_fr'))} ; avec photo : {sum(1 for e in major if e.get('image'))} ; "
          f"avec Concernés : {sum(1 for e in major if e.get('concerned'))}")
    health = json.loads((data / "health.json").read_text("utf-8"))
    print("Candidats inconnus les plus cités :", ", ".join(f"{c['name']} ({c['count']})" for c in health.get("candidates", [])[:10]))
    for e in random.Random(1).sample(linked, min(50, len(linked))):
        print(f"- {e.get('title_fr') or e['title']} → {', '.join(names.get(i, i) for i in e['entity_ids'])}")


if __name__ == "__main__":
    main()
