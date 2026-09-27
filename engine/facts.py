"""Faits hebdomadaires sur les entités : Wikidata (sans clé) et PIB de la Banque mondiale (spec §5.2)."""
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

from .publish import write_json
from .timeutil import iso, parse

WIKIDATA = "https://www.wikidata.org/w/api.php"
WORLD_BANK = "https://api.worldbank.org/v2/country/{iso2}/indicator/NY.GDP.MKTP.CD"
HEADERS = {"User-Agent": "Vigie/1.0 (https://github.com/Adam2328/veille-plateforme)"}
MAX_AGE = timedelta(days=7)
BATCH = 50
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
# propriété Wikidata : (libellé affiché, types d'entités concernés)
FACTS = {
    "P36": ("Capitale", {"country"}), "P1082": ("Population", {"country"}), "P35": ("Chef de l'État", {"country"}),
    "P6": ("Chef du gouvernement", {"country"}), "P122": ("Régime", {"country"}), "P38": ("Monnaie", {"country"}),
    "P452": ("Secteur", {"company"}), "P159": ("Siège", {"company", "org", "central_bank"}),
    "P169": ("Directeur général", {"company"}), "P488": ("Président", {"company", "org", "central_bank", "team"}),
    "P112": ("Fondateur", {"company", "org"}),
    "P571": ("Création", {"company", "org", "team", "central_bank", "competition", "crypto"}),
    "P17": ("Pays", {"company", "team", "competition"}), "P569": ("Naissance", {"person", "player", "driver"}),
    "P27": ("Nationalité", {"person", "player", "driver"}), "P39": ("Fonction", {"person"}),
    "P54": ("Club", {"player"}), "P413": ("Poste", {"player"}), "P286": ("Entraîneur", {"team"}),
    "P115": ("Stade", {"team"}), "P178": ("Développeur", {"ai_model"}), "P577": ("Sortie", {"ai_model"}),
}
SINGLE = {"P1082", "P569", "P571", "P577"}                    # une seule valeur (la plus récente ou préférée)
IMAGE = {"country": "P41", "company": "P154", "org": "P154", "team": "P154", "competition": "P154",
         "central_bank": "P154", "crypto": "P154", "ai_model": "P154"}      # sinon P18 (photo)
# propriété : (verbe, sens) ; « out » = entité → cible, « in » = cible → entité
EDGES = {"P463": ("membre_de", "out"), "P35": ("dirige", "in"), "P6": ("dirige", "in"), "P169": ("dirige", "in"),
         "P178": ("produit", "in"), "P127": ("detient", "in"), "P355": ("detient", "out"), "P54": ("joue_pour", "out")}


def fetch_json(url: str, params: dict | None = None) -> object:
    r = requests.get(url, params=params, headers=HEADERS, timeout=(5, 10))   # le cycle entier doit tenir en 15 min
    r.raise_for_status()
    return r.json()


def _claims(entity: dict, pid: str) -> list[dict]:
    """Valeurs actuelles : ni dépréciées, ni terminées (qualificatif P582), rang préféré en priorité."""
    claims = [c for c in entity.get("claims", {}).get(pid, [])
              if c.get("rank") != "deprecated" and c["mainsnak"].get("snaktype") == "value"
              and "P582" not in c.get("qualifiers", {})]
    preferred = [c for c in claims if c.get("rank") == "preferred"]
    return [c["mainsnak"]["datavalue"] for c in (preferred or claims)]


def _text(entity: dict, key: str) -> str | None:
    for lang in ("fr", "en"):
        v = entity.get(key, {}).get(lang)
        if v:
            return v["value"]
    return None


def _entities(ids: list[str], fetch: Callable) -> dict:
    out = {}
    for start in range(0, len(ids), BATCH):
        data = fetch(WIKIDATA, {"action": "wbgetentities", "ids": "|".join(ids[start:start + BATCH]),
                                "props": "labels|descriptions|claims", "languages": "fr|en", "format": "json"})
        if "error" in data:              # réponse HTTP 200 porteuse d'une erreur : ne jamais écraser les faits connus
            raise ValueError(f"Wikidata : {data['error'].get('code')} {data['error'].get('info', '')}".strip())
        out.update(data.get("entities", {}))
    return {q: e for q, e in out.items() if "missing" not in e}


def _date(value: dict) -> str:
    raw, precision = value["time"], value.get("precision", 11)
    year, month, day = str(int(raw[1:5])), int(raw[6:8]), int(raw[9:11])
    if precision >= 11 and month and day:
        return f"{day} {MONTHS[month - 1]} {year}"
    if precision == 10 and month:
        return f"{MONTHS[month - 1]} {year}"
    return year


def _big(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f} milliards".replace(".", ",")
    if n >= 1e6:
        return f"{n / 1e6:.1f} millions".replace(".", ",")
    return f"{int(n):,}".replace(",", " ")


def _value(dv: dict, labels: dict) -> str | None:
    kind = dv.get("type")
    if kind == "wikibase-entityid":
        return labels.get(dv["value"]["id"])
    if kind == "quantity":
        return _big(float(dv["value"]["amount"]))
    if kind == "time":
        return _date(dv["value"])
    return dv["value"] if kind == "string" else None


def _commons(filename: str) -> str:
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename.replace(' ', '_'))}?width=480"


def _facts_of(ent: dict, etype: str, labels: dict) -> list[dict]:
    out = []
    for pid, (label, types) in FACTS.items():
        if etype not in types:
            continue
        values = []
        for dv in _claims(ent, pid)[: 1 if pid in SINGLE else 3]:
            v = _value(dv, labels)
            if v and v not in values:
                values.append(v)
        if values:
            out.append({"label": label, "value": ", ".join(values)})
    return out


def _edges_of(ent: dict, eid: str, by_qid: dict) -> list[dict]:
    edges = []
    for pid, (verb, direction) in EDGES.items():
        for dv in _claims(ent, pid):
            other = by_qid.get(dv["value"].get("id")) if dv.get("type") == "wikibase-entityid" else None
            if other and other != eid:
                src, dst = (eid, other) if direction == "out" else (other, eid)
                edges.append({"src": src, "verb": verb, "dst": dst, "weight": 1, "origin": "wikidata"})
    return edges


def collect_facts(catalog: dict, fetch: Callable = fetch_json) -> dict:
    by_qid = {e["wikidata"]: eid for eid, e in catalog.items() if e.get("wikidata")}
    main = _entities(sorted(by_qid), fetch)
    refs = sorted({dv["value"]["id"] for ent in main.values() for pid in FACTS for dv in _claims(ent, pid)
                   if dv.get("type") == "wikibase-entityid"} - set(main))
    labels = {q: _text(e, "labels") for q, e in {**_entities(refs, fetch), **main}.items()}
    out = {}
    for qid, ent in main.items():
        eid = by_qid.get(qid)
        if eid is None:                  # clé inattendue (ex. élément redirigé) : ignorée, les autres fiches restent
            continue
        etype = catalog[eid]["type"]
        images = _claims(ent, IMAGE.get(etype, "P18")) or _claims(ent, "P18")
        iso2 = next((dv["value"] for dv in _claims(ent, "P297")), None) if etype == "country" else None
        out[eid] = {"description": _text(ent, "descriptions"),
                    "image": _commons(images[0]["value"]) if images and images[0].get("type") == "string" else None,
                    "facts": _facts_of(ent, etype, labels), "edges": _edges_of(ent, eid, by_qid),
                    **({"iso2": iso2} if iso2 else {})}
    return out


def with_gdp(facts: dict, fetch: Callable = fetch_json) -> tuple[dict, list[str]]:
    out, errors = {}, []
    for eid, f in facts.items():
        extra = []
        if f.get("iso2") and not errors:     # coupe-circuit : une banque lente ne coûte qu'un seul délai d'attente
            try:
                data = fetch(WORLD_BANK.format(iso2=f["iso2"]), {"format": "json", "mrnev": 1})
                rows = data[1] if isinstance(data, list) and len(data) > 1 and data[1] else []
                row = next((r for r in rows if r.get("value") is not None), None)
                if row:
                    extra = [{"label": "PIB", "value": f"{round(row['value'] / 1e9):,} Md$ ({row['date']})".replace(",", " ")}]
            except Exception as exc:  # PIB indisponible : la fiche reste sans cette ligne, l'erreur est remontée
                errors.append(f"PIB {eid} : {type(exc).__name__}: {exc}")
        out[eid] = {**f, "facts": [*f["facts"], *extra]}
    return out, errors


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text("utf-8")) if path.exists() else None
    except ValueError:
        return None


def load_facts(root: Path) -> dict:
    return (_read(Path(root) / "data" / "facts" / "entities.json") or {}).get("entities", {})


def refresh_facts(root: Path, catalog: dict, now: datetime, fetch: Callable = fetch_json) -> tuple[dict, dict | None]:
    """Rafraîchit au plus une fois par semaine, ou dès qu'un identifiant Wikidata est ajouté au catalogue."""
    path = Path(root) / "data" / "facts" / "entities.json"
    old = _read(path)
    qids = sorted(e["wikidata"] for e in catalog.values() if e.get("wikidata"))
    if not qids:
        return {}, None
    if old and old.get("qids") == qids and now - parse(old["checked_at"]) < MAX_AGE:
        return old["entities"], {"source": "facts:wikidata", "ok": True, "count": len(old["entities"]), "error": None}
    try:
        facts, errors = with_gdp(collect_facts(catalog, fetch), fetch)
    except Exception as exc:  # Wikidata injoignable : les faits de la semaine précédente restent en place
        return (old or {}).get("entities", {}), {"source": "facts:wikidata", "ok": False, "count": 0,
                                                 "error": f"{type(exc).__name__}: {exc}"}
    write_json(path, {"checked_at": iso(now), "qids": qids, "entities": facts})
    return facts, {"source": "facts:wikidata", "ok": not errors, "count": len(facts), "error": "; ".join(errors[:3]) or None}
