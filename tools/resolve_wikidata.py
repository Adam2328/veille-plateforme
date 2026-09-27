"""Propose et écrit les identifiants Wikidata manquants du catalogue (config/entities/*.yml).

Usage : .venv/Scripts/python tools/resolve_wikidata.py          (affiche seulement)
        .venv/Scripts/python tools/resolve_wikidata.py --write  (écrit les identifiants trouvés)
Les entités non résolues sont listées à la fin, pour saisie à la main.
"""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.catalog import load_catalog, load_universes  # noqa: E402
from engine.facts import WIKIDATA, fetch_json  # noqa: E402
from engine.wikidata_ids import HINTS, insert_qid, pick  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    catalog = load_catalog(ROOT, load_universes(ROOT))
    found, missing = {}, []
    for eid, e in catalog.items():
        if e.get("wikidata") or e["type"] not in HINTS:
            continue
        name = re.sub(r"\s*\(.*?\)", "", e["name"])
        results = fetch_json(WIKIDATA, {"action": "wbsearchentities", "search": name, "language": "fr", "uselang": "fr",
                                        "type": "item", "limit": 5, "format": "json"}).get("search", [])
        qid = pick(results, e["type"])
        desc = next((r.get("description", "") for r in results if r["id"] == qid), "")
        print(f"{eid:48} {qid or '—':12} {desc}")
        if qid:
            found[eid] = qid
        else:
            missing.append(eid)
        time.sleep(0.2)
    if "--write" in sys.argv:
        for path in sorted((ROOT / "config" / "entities").glob("*.yml")):
            text = path.read_text("utf-8")
            new = text
            for eid, qid in found.items():
                new = insert_qid(new, eid, qid)
            if new != text:
                path.write_text(new, "utf-8")
    print(f"\n{len(found)} identifiants trouvés ; {len(missing)} à saisir à la main : {', '.join(missing)}")


if __name__ == "__main__":
    main()
