"""Univers, catalogue d'entités et relations rédigées (config/universes, config/entities, config/relations.yml)."""
import re
import unicodedata
from pathlib import Path

import yaml

TYPES = {
    "company": "Entreprise", "country": "Pays", "org": "Organisation", "person": "Personnalité", "etf": "ETF",
    "crypto": "Cryptomonnaie", "index": "Indice", "rate": "Taux", "commodity": "Matière première", "sector": "Secteur",
    "tech": "Technologie", "ai_model": "Modèle d'IA", "central_bank": "Banque centrale", "team": "Équipe",
    "player": "Joueur", "driver": "Pilote", "competition": "Compétition", "topic": "Sujet",
}
# verbe : (lecture source → cible, lecture cible → source)
VERBS = {
    "membre_de": ("membre de", "a pour membre"),
    "dirige": ("dirige", "dirigé par"),
    "fournit": ("fournisseur de", "client de"),
    "concurrent": ("concurrent de", "concurrent de"),
    "detient": ("détient", "détenu par"),
    "suit": ("suit", "suivi par"),
    "expose": ("exposé à", "influence"),
    "produit": ("produit", "produit par"),
    "secteur": ("appartient au secteur", "regroupe"),
    "investit": ("investit dans", "financé par"),
    "joue_pour": ("joue pour", "compte dans ses rangs"),
    "participe": ("participe à", "a pour participant"),
    "voisin": ("frontalier de", "frontalier de"),
    "lie_a": ("souvent cité avec", "souvent cité avec"),
}
# Liens suivis par « Concernés » : ceux qui transmettent un effet économique.
EXPOSURE = frozenset({"expose", "fournit", "detient", "suit", "produit", "secteur", "investit"})
_ID = re.compile(r"^([a-z_]+):[a-z0-9]+(?:-[a-z0-9]+)*$")
_QID = re.compile(r"^Q\d+$")


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text("utf-8"))


def load_universes(root: Path) -> dict:
    folder = Path(root) / "config" / "universes"
    unis = [_yaml(p) for p in sorted(folder.glob("*.yml"))] if folder.exists() else []
    return {u["id"]: u for u in sorted(unis, key=lambda u: u["order"])}


def check_universes(universes: dict, domains: dict) -> list[str]:
    errors, owner = [], {}
    for u in universes.values():
        for d in u["domains"]:
            if d not in domains:
                errors.append(f"univers {u['id']} : rubrique inconnue {d}")
            elif d in owner:
                errors.append(f"rubrique {d} dans deux univers ({owner[d]}, {u['id']})")
            owner.setdefault(d, u["id"])
    if universes:
        errors += [f"rubrique {d} rattachée à aucun univers" for d in domains if d not in owner]
    return errors


def _entity_errors(e: dict, universes: dict) -> list[str]:
    errors = []
    if not e.get("name") or not e.get("aliases"):
        errors.append(f"{e['id']} : nom ou alias manquant")
    bad = [u for u in [*e.get("universes", []), *e.get("link_in", [])] if u not in universes]
    if not e.get("universes") or bad:
        errors.append(f"{e['id']} : univers manquants ou inconnus {bad}")
    if e.get("wikidata") and not _QID.match(str(e["wikidata"])):
        errors.append(f"{e['id']} : identifiant Wikidata invalide {e['wikidata']}")
    return errors


def load_catalog(root: Path, universes: dict) -> dict:
    folder = Path(root) / "config" / "entities"
    entries = [e for p in sorted(folder.glob("*.yml")) for e in (_yaml(p) or [])] if folder.exists() else []
    catalog, errors = {}, []
    for e in entries:
        m = _ID.match(str(e.get("id", "")))
        if not m or m.group(1) not in TYPES:
            errors.append(f"identifiant invalide : {e.get('id')}")
            continue
        if e["id"] in catalog:
            errors.append(f"identifiant en double : {e['id']}")
        errors += _entity_errors(e, universes)
        catalog[e["id"]] = {**e, "type": m.group(1)}
    if errors:
        raise ValueError("catalogue d'entités invalide :\n" + "\n".join(errors))
    return catalog


def load_relations(root: Path, catalog: dict) -> list[tuple[str, str, str]]:
    path = Path(root) / "config" / "relations.yml"
    rows = (_yaml(path) or []) if path.exists() else []
    errors = [f"relation invalide : {r}" for r in rows
              if not (isinstance(r, list) and len(r) == 3 and r[0] in catalog and r[2] in catalog
                      and r[1] in VERBS and r[1] != "lie_a")]
    if errors:
        raise ValueError("relations invalides :\n" + "\n".join(errors))
    return [tuple(r) for r in rows]


def football_teams(football: dict | None, catalog: dict, universes: dict) -> dict:
    """Équipes des classements déjà publiés et absentes du catalogue : entités « team » limitées au Sport."""
    if not football or "sport" not in universes:
        return {}
    known = {str(a).lstrip("=").lower() for e in catalog.values() for a in e.get("aliases", [])}
    out = {}
    for comp in football.get("competitions", []):
        for row in comp.get("standings", []):
            name = row["team"]
            eid = f"team:{slug(name)}"
            if name.lower() not in known and eid not in catalog and slug(name):
                out[eid] = {"id": eid, "name": name, "type": "team", "aliases": [name.lower()],
                            "universes": ["sport"], "link_in": ["sport"]}
    return out
