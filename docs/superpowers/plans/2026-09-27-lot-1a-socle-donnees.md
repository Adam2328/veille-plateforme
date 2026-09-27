# Lot 1, partie A : socle de données de Vigie 2, plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner au moteur les quatre univers, un catalogue d'environ 400 entités reliées entre elles, le rattachement de chaque événement à ses entités, les titres en français, les photos, les chaînes « Concernés », la sélection « Ce qu'il faut savoir aujourd'hui », les fiches entités (faits Wikidata) et le bandeau, publiés en JSON validés, **sans rien changer au site actuel** (la nouvelle interface est la partie B).

**Architecture:** Tout est ajouté au moteur Python existant. Les rubriques restent l'unité de collecte ; un fichier par univers les regroupe. Le catalogue (`config/entities/*.yml`) et les relations (`config/relations.yml`) sont chargés avec la config. Chaque cycle : rattachement par alias (une expression régulière par univers), confirmation et traduction du titre dans l'appel Gemini existant, graphe (relations rédigées + Wikidata + co-occurrences), parcours « Concernés », puis publication de nouveaux fichiers (`universes/`, `entities/`, `band.json`) à côté des anciens. Faits Wikidata et PIB Banque mondiale rafraîchis une fois par semaine, dans le même cycle.

**Tech Stack:** Python 3.11 (`requests`, `PyYAML`, `feedparser`, `scikit-learn`, `jsonschema`, `pytest`), API Wikidata et Banque mondiale sans clé.

**Spec:** `docs/superpowers/specs/2026-09-27-vigie-2-design.md` (§3 à §9, §12 lot 1). La partie B (interface) a son propre plan, écrit après la mise en production de cette partie.

## Écarts assumés par rapport à la spec (tranchés à l'écriture du plan)

| Point | Décision | Pourquoi | Coût si c'est faux |
|---|---|---|---|
| Dictionnaires `entities` des rubriques | **Conservés** pour le score et le filtre de pertinence ; le catalogue les couvre tous (test) | Calibrés sur données réelles ; les remplacer changerait les niveaux de tous les événements | Deux listes à tenir ; suppression possible plus tard |
| Champ public des entités | Nouveau champ `entity_ids` (identifiants) ; `entities` (noms) inchangé | Le site actuel suit des noms ; il ne doit pas casser avant la partie B | Aucun |
| `graph.json` | Non publié : les relations sont dans chaque fiche entité | Aucune vue n'a besoin du graphe entier (YAGNI) | Un fichier à ajouter si une vue globale est voulue |
| Types et verbes | Type `index` (indices boursiers) et verbe `secteur` ajoutés | Nécessaires aux chaînes « entreprise → secteur → ETF » et aux ETF qui suivent un indice | Aucun |
| Rugby, joueurs générés, fiches match | Reportés au lot Sport | Demandent des sources à tester | Aucun (prévu au lot Sport) |
| Équipes de football | Générées depuis les classements déjà publiés (`football.json`), sans appel d'API | Budget football-data (10 req/min) déjà utilisé à 8 | Aucune photo ni fait pour ces équipes avant le lot Sport |
| Pilotes et écuries F1 | Écrits dans le catalogue | 22 pilotes, stable sur une saison | Mise à jour manuelle en début de saison |

## Global Constraints

- Python 3.11 ; commandes via `.venv/Scripts/python` ; annotations de types sur toutes les fonctions ; **aucune dépendance nouvelle**.
- Coût 0 € ; dépôt public : aucun secret dans le code, les tests, les JSON ni les messages.
- Wikidata et Banque mondiale : sans clé ; en-tête `User-Agent: Vigie/1.0 (https://github.com/Adam2328/veille-plateforme)` ; jamais l'adresse e-mail de l'utilisateur.
- Aucun JSON publié sans validation par `schemas/public.schema.json`. Une source ou une API qui échoue ne bloque jamais le cycle : l'échec va dans `site/data/health.json`.
- Le LLM ne décide jamais de la fiabilité, de l'importance ni du niveau. Il **choisit uniquement parmi les entités candidates** ; tout identifiant hors liste est ignoré par le code. Filtre `has_advice` inchangé.
- Réécriture conditionnelle des fichiers (`write_if_changed`) : deux cycles sans nouvel article ne réécrivent aucun fichier publié (limite de déploiements Vercel).
- Images : uniquement des URL `https://` (pas de contenu mixte, pas de `javascript:`).
- Le site actuel (`site/js`, `site/css`, `site/index.html`) n'est pas modifié dans cette partie ; ses tests (`cd site && node --test "tests/*.test.mjs"`) doivent rester verts.
- Les fichiers de code s'écrivent avec les outils d'écriture et d'édition, jamais avec des scripts Python en ligne contenant des `\`.
- Commits au format conventionnel, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Branche `feat/vigie-socle-a`. **Aucune fusion dans `main` ni push de `main` sans l'accord explicite de l'utilisateur** ; avant de pousser : `git pull --rebase origin main`, en cas de conflit sur `site/data/` ou `data/events/`, garder la version du robot.
- Chemins relatifs à `veille-générale/plateforme/`.

## Review Focus

1. **Alias ambigu** (« Apple » le fruit, « Lille » la ville dans une actu politique, « Meta » dans « metaverse ») → mot entier, casse exacte avec `=`, restriction `link_in` : tests de la tâche 3.
2. **Réponse Gemini imparfaite** (identifiant inventé, champs `titre`/`entites` absents ou mal typés, quota épuisé) → extras ignorés sans perdre le résumé ; un résumé LLM existant n'est jamais remplacé par un extractif sur un échec : tests des tâches 5 et 11.
3. **Wikidata imparfait** (entité supprimée, valeur « inconnue » sans `datavalue`, valeur dépréciée ou terminée, service injoignable) → faits précédents conservés, rien ne plante : tests de la tâche 9.
4. **Image dangereuse ou non sécurisée** (`http://`, `javascript:`) → rejetée : test de la tâche 4.
5. **Déterminisme** : deux cycles identiques ne réécrivent aucun fichier de `site/data/` : test de la tâche 11.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `engine/catalog.py` (nouveau) | Types, verbes, chargement et validation des univers, du catalogue et des relations ; équipes de football générées |
| `engine/linker.py` (nouveau) | Rattachement par alias, texte d'un événement, identifiants finaux |
| `engine/graph.py` (nouveau) | Arêtes (rédigées, Wikidata, co-occurrences), voisinage, chaînes « Concernés » |
| `engine/today.py` (nouveau) | Sélection « Ce qu'il faut savoir aujourd'hui » |
| `engine/entity_pages.py` (nouveau) | Index des entités et fiches |
| `engine/facts.py` (nouveau) | Faits Wikidata + PIB Banque mondiale, rafraîchis chaque semaine |
| `engine/wikidata_ids.py` (nouveau) + `tools/resolve_wikidata.py` (nouveau) | Aide ponctuelle pour renseigner les identifiants Wikidata |
| `engine/band.py` (nouveau) | Bandeau Vigie |
| `engine/candidates.py` (nouveau) | Noms inconnus proposés par Gemini |
| `engine/config.py`, `collect.py`, `normalize.py`, `enrich.py`, `summarize.py`, `publish.py`, `search.py`, `run.py` | Modifiés |
| `config/universes/*.yml`, `config/entities/*.yml`, `config/relations.yml` (nouveaux), `config/global.yml` (modifié) | Configuration |
| `schemas/public.schema.json` | Contrat étendu (champs facultatifs + 5 nouveaux fichiers) |
| `tools/measure_links.py` (nouveau) | Mesure sur les données publiées |

---

### Task 1 : univers, chargement du catalogue et des relations

**Files:**
- Create: `engine/catalog.py`, `config/universes/finance.yml`, `config/universes/ia.yml`, `config/universes/geopolitique.yml`, `config/universes/sport.yml`, `tests/test_catalog.py`
- Modify: `engine/config.py`, `config/global.yml`

**Interfaces:**
- Produces : `TYPES: dict[str, str]`, `VERBS: dict[str, tuple[str, str]]`, `EXPOSURE: frozenset[str]`, `slug(text) -> str`, `load_universes(root) -> dict`, `check_universes(universes, domains) -> list[str]`, `load_catalog(root, universes) -> dict[str, dict]` (chaque entité reçoit `type`), `load_relations(root, catalog) -> list[tuple[str, str, str]]`, `football_teams(football, catalog, universes) -> dict` ; `load_config()` renvoie en plus `universes`, `catalog`, `relations`.

- [ ] **Step 1 : écrire les tests**

`tests/test_catalog.py` :

```python
import pytest
import yaml

from engine.catalog import check_universes, football_teams, load_catalog, load_relations, load_universes, slug
from engine.config import load_config

UNI = {"id": "ia", "name": "IA", "short": "IA", "color": "ia", "order": 1, "domains": ["ia"], "subthemes": []}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")


def test_slug_removes_accents_and_punctuation():
    assert slug("Équipe de France !") == "equipe-de-france"
    assert slug("S&P 500") == "s-p-500"


def test_repo_universes_are_ordered_and_cover_every_domain():
    cfg = load_config()
    assert list(cfg["universes"]) == ["finance", "ia", "geopolitique", "sport"]
    assert check_universes(cfg["universes"], cfg["domains"]) == []
    assert {"today", "links", "band"} <= set(cfg["global"])


def test_a_domain_in_two_universes_or_in_none_is_reported():
    unis = {"a": {**UNI, "id": "a", "domains": ["ia", "finance"]}, "b": {**UNI, "id": "b", "domains": ["ia"]}}
    errors = check_universes(unis, {"ia": {}, "finance": {}, "tennis": {}})
    assert any("deux univers" in e for e in errors) and any("tennis" in e for e in errors)


def test_catalog_rejects_bad_ids_duplicates_missing_aliases_unknown_universes_and_bad_qids(tmp_path):
    write(tmp_path / "config" / "entities" / "x.yml", [
        {"id": "company:ok", "name": "Ok", "aliases": ["ok"], "universes": ["ia"]},
        {"id": "company:ok", "name": "Ok", "aliases": ["ok2"], "universes": ["ia"]},
        {"id": "planet:mars", "name": "Mars", "aliases": ["mars"], "universes": ["ia"]},
        {"id": "company:sans-alias", "name": "X", "universes": ["ia"]},
        {"id": "company:ailleurs", "name": "Y", "aliases": ["y"], "universes": ["espace"]},
        {"id": "company:qid", "name": "Z", "aliases": ["z"], "universes": ["ia"], "wikidata": "142"},
    ])
    with pytest.raises(ValueError) as err:
        load_catalog(tmp_path, {"ia": UNI})
    msg = str(err.value)
    assert "double" in msg and "planet:mars" in msg and "sans-alias" in msg and "espace" in msg and "company:qid" in msg


def test_catalog_entries_receive_their_type(tmp_path):
    write(tmp_path / "config" / "entities" / "x.yml", [{"id": "company:ok", "name": "Ok", "aliases": ["ok"], "universes": ["ia"]}])
    assert load_catalog(tmp_path, {"ia": UNI})["company:ok"]["type"] == "company"


def test_relations_must_link_known_entities_with_a_known_verb(tmp_path):
    catalog = {"company:a": {}, "company:b": {}}
    write(tmp_path / "config" / "relations.yml", [["company:a", "fournit", "company:b"]])
    assert load_relations(tmp_path, catalog) == [("company:a", "fournit", "company:b")]
    write(tmp_path / "config" / "relations.yml", [["company:a", "aime", "company:b"], ["company:a", "fournit", "company:z"]])
    with pytest.raises(ValueError):
        load_relations(tmp_path, catalog)


def test_missing_folders_give_an_empty_configuration(tmp_path):
    assert load_universes(tmp_path) == {} and load_catalog(tmp_path, {}) == {} and load_relations(tmp_path, {}) == []


def test_football_teams_are_added_for_unknown_names_and_only_in_sport():
    football = {"competitions": [{"standings": [{"team": "Lille"}, {"team": "Real Sociedad"}]}]}
    catalog = {"team:lille": {"aliases": ["lille"]}}
    teams = football_teams(football, catalog, {"sport": {}})
    assert list(teams) == ["team:real-sociedad"]
    assert teams["team:real-sociedad"] == {"id": "team:real-sociedad", "name": "Real Sociedad", "type": "team",
                                          "aliases": ["real sociedad"], "universes": ["sport"], "link_in": ["sport"]}
    assert football_teams(football, catalog, {}) == {} and football_teams(None, catalog, {"sport": {}}) == {}
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_catalog.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'engine.catalog'`.

- [ ] **Step 3 : écrire `engine/catalog.py`**

```python
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
```

- [ ] **Step 4 : brancher la config**

Dans `engine/config.py`, remplacer tout le fichier par :

```python
import pathlib

import yaml

from .catalog import check_universes, load_catalog, load_relations, load_universes

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config(root: pathlib.Path | str = ROOT) -> dict:
    root = pathlib.Path(root)
    g = yaml.safe_load((root / "config" / "global.yml").read_text("utf-8"))
    domains = {}
    for path in sorted((root / "config" / "domains").glob("*.yml")):
        d = yaml.safe_load(path.read_text("utf-8"))
        domains[d["id"]] = d
    quotes_path = root / "config" / "quotes.yml"
    quotes = yaml.safe_load(quotes_path.read_text("utf-8"))["symbols"] if quotes_path.exists() else []
    football_path = root / "config" / "football.yml"
    football = yaml.safe_load(football_path.read_text("utf-8")) if football_path.exists() else None
    universes = load_universes(root)
    errors = check_universes(universes, domains)
    if errors:
        raise ValueError("univers invalides :\n" + "\n".join(errors))
    catalog = load_catalog(root, universes)
    return {"global": g, "domains": domains, "quotes": quotes, "football": football,
            "universes": universes, "catalog": catalog, "relations": load_relations(root, catalog)}
```

- [ ] **Step 5 : écrire les univers**

`config/universes/finance.yml` :

```yaml
id: finance
name: Finance & Marchés
short: Finance
color: finance           # jeton de couleur de l'interface (partie B)
order: 1                 # ordre par défaut des bandes de l'accueil (modifiable par l'utilisateur dans le site)
domains: [finance]
# Un sous-thème filtre les événements de l'univers : type d'événement (kinds), type d'entité (entity_types),
# entité précise (entities) ou rubrique (domains). Un seul critère rempli suffit.
subthemes:
  - {id: actions, name: Actions, kinds: [earnings, m_and_a], entity_types: [company]}
  - {id: taux, name: Taux & obligations, entity_types: [rate, central_bank]}
  - {id: etf, name: ETF & indices, entity_types: [etf, index]}
  - {id: crypto, name: Crypto, kinds: [crypto], entity_types: [crypto]}
  - {id: macro, name: Macro & banques centrales, kinds: [macro_data, central_bank]}
  - {id: matieres, name: Matières premières, kinds: [commodities], entity_types: [commodity]}
```

`config/universes/ia.yml` :

```yaml
id: ia
name: Intelligence artificielle
short: IA
color: ia
order: 2
domains: [ia]
subthemes:
  - {id: modeles, name: Modèles & produits, kinds: [model_release, product_launch], entity_types: [ai_model]}
  - {id: argent, name: Business & argent, kinds: [funding_acquisition]}
  - {id: infra, name: Infrastructure, entities: [tech:gpu, tech:data-centers, tech:puces-ia, sector:semi-conducteurs, company:nvidia, company:tsmc, company:asml, commodity:electricite]}
  - {id: regulation, name: Société & régulation, kinds: [regulation]}
  - {id: recherche, name: Recherche, kinds: [research]}
```

`config/universes/geopolitique.yml` :

```yaml
id: geopolitique
name: Géopolitique
short: Géo
color: geo
order: 3
domains: [geopolitique]
subthemes:
  - {id: conflits, name: Conflits, kinds: [conflict, humanitarian]}
  - {id: diplomatie, name: Diplomatie & alliances, kinds: [diplomacy, alliance]}
  - {id: sanctions, name: Économie & sanctions, kinds: [sanctions], entity_types: [commodity]}
  - {id: politique, name: Élections & institutions, kinds: [election, institutions]}
  - {id: europe, name: France & Europe, entities: [country:france, org:ue, org:commission-europeenne, org:parlement-europeen, country:allemagne, country:italie, country:espagne, country:pologne]}
```

`config/universes/sport.yml` :

```yaml
id: sport
name: Sport
short: Sport
color: sport
order: 4
domains: [football, tennis, f1, nba, volley, sport-essentiel]
subthemes:
  - {id: foot, name: Football, domains: [football]}
  - {id: tennis, name: Tennis, domains: [tennis]}
  - {id: f1, name: F1, domains: [f1]}
  - {id: basket, name: Basket, domains: [nba]}
  - {id: volley, name: Volley, domains: [volley]}
  - {id: autres, name: Autres sports, domains: [sport-essentiel]}
```

À la fin de `config/global.yml`, ajouter :

```yaml
today:                   # « Ce qu'il faut savoir aujourd'hui » (spec §6)
  window_hours: 36       # événements mis à jour dans les 36 dernières heures
  floor: 3               # au moins 3 événements par univers quand il y en a
  total: 18              # total visé ; les places au-delà du plancher vont aux meilleurs scores du jour
  max_per_entity: 2      # diversité : 2 événements au plus par entité principale
  novelty_bonus: 8       # événement apparu il y a moins de 24 h
  evolution_bonus: 5     # nouvelle révision (nouvelles sources) dans les 12 dernières heures
links:
  cooccurrence_min: 3    # deux entités citées ensemble dans au moins 3 événements (30 jours) sont reliées
band:                    # bandeau Vigie (spec §9)
  quotes: ["^FCHI", "^GSPC", "^IXIC", "^STOXX50E", "EURUSD=X", "^TNX", "BZ=F", "GC=F", "BTC-USD"]
  new_hours: 6
  max_new: 4
  agenda_days: 3
  max_agenda: 4
  max_matches: 6
```

- [ ] **Step 6 : vérifier**

Run: `.venv/Scripts/python -m pytest tests/test_catalog.py tests/test_config.py -q`
Expected: PASS (le catalogue est encore vide : `load_config()` fonctionne sans entités).

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe (229 + nouveaux).

- [ ] **Step 7 : commit**

```bash
git checkout -b feat/vigie-socle-a
git add -A
git commit -m "feat: univers et chargement du catalogue d'entités" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2 : catalogue de départ et relations rédigées

**Files:**
- Create: `config/entities/companies.yml`, `countries.yml`, `orgs.yml`, `central_banks.yml`, `persons.yml`, `players.yml`, `drivers.yml`, `teams.yml`, `competitions.yml`, `etfs.yml`, `crypto.yml`, `indices.yml`, `rates.yml`, `commodities.yml`, `sectors.yml`, `tech.yml`, `ai_models.yml`, `topics.yml`, `config/relations.yml`
- Modify: `tests/test_catalog.py`

**Interfaces:**
- Consumes : `load_config()` (tâche 1).
- Produces : le catalogue réel (≈ 400 entités) et ≥ 100 relations, dont les identifiants sont utilisés tels quels par les sous-thèmes des univers et par les tests des tâches suivantes.

Règle des alias : **en minuscules** = insensible à la casse ; **préfixés par `=`** = casse exacte (pour les noms qui sont aussi des mots courants : `=Apple`, `=Meta`, `=Or`…). Toujours un mot entier. `link_in` restreint le rattachement à certains univers (équipes, joueurs, compétitions).

- [ ] **Step 1 : écrire les tests**

Ajouter à `tests/test_catalog.py` :

```python
def test_repo_catalog_is_large_consistent_and_aliases_are_unique():
    cfg = load_config()
    catalog = cfg["catalog"]
    assert len(catalog) >= 350
    assert {e["type"] for e in catalog.values()} == {"company", "country", "org", "person", "etf", "crypto", "index", "rate",
                                                     "commodity", "sector", "tech", "ai_model", "central_bank", "team",
                                                     "player", "driver", "competition", "topic"}
    seen = {}
    for eid, e in catalog.items():
        for a in e["aliases"]:
            key = a if a.startswith("=") else a.lower()
            assert key not in seen, f"alias {a} partagé par {seen.get(key)} et {eid}"
            seen[key] = eid
    assert len(cfg["relations"]) >= 100


def test_every_name_of_the_domain_dictionaries_is_covered_by_the_catalog():
    cfg = load_config()
    known = {a.lstrip("=").lower() for e in cfg["catalog"].values() for a in e["aliases"]}
    missing = [f"{d}:{name}" for d, dom in cfg["domains"].items() for name, aliases in dom.get("entities", {}).items()
               if not ({name.lower(), *(a.lower() for a in aliases)} & known)]
    assert missing == []


def test_subtheme_entities_exist():
    cfg = load_config()
    wanted = {i for u in cfg["universes"].values() for s in u["subthemes"] for i in s.get("entities", [])}
    assert wanted <= set(cfg["catalog"])
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_catalog.py -q`
Expected: FAIL sur les trois nouveaux tests (catalogue vide).

- [ ] **Step 3 : écrire les fichiers du catalogue**

`config/entities/companies.yml` :

```yaml
# Entreprises (type company). Alias en minuscules = insensible à la casse ; « = » = casse exacte.
- {id: company:nvidia, name: Nvidia, aliases: [nvidia, "=NVDA"], ticker: NVDA, universes: [finance, ia]}
- {id: company:microsoft, name: Microsoft, aliases: [microsoft, "=MSFT"], ticker: MSFT, universes: [finance, ia]}
- {id: company:apple, name: Apple, aliases: ["=Apple", "=AAPL", iphone], ticker: AAPL, universes: [finance]}
- {id: company:alphabet, name: Alphabet (Google), aliases: ["=Alphabet", google, "=GOOGL"], ticker: GOOGL, universes: [finance, ia]}
- {id: company:amazon, name: Amazon, aliases: ["=Amazon", aws, "amazon web services", "=AMZN"], ticker: AMZN, universes: [finance, ia]}
- {id: company:meta, name: Meta, aliases: ["=Meta", "meta platforms", "meta ai", facebook, instagram, whatsapp], ticker: META, universes: [finance, ia]}
- {id: company:tesla, name: Tesla, aliases: [tesla, "=TSLA"], ticker: TSLA, universes: [finance]}
- {id: company:broadcom, name: Broadcom, aliases: [broadcom], ticker: AVGO, universes: [finance, ia]}
- {id: company:amd, name: AMD, aliases: ["=AMD", "advanced micro devices"], ticker: AMD, universes: [finance, ia]}
- {id: company:intel, name: Intel, aliases: ["=Intel"], ticker: INTC, universes: [finance, ia]}
- {id: company:tsmc, name: TSMC, aliases: [tsmc, "taiwan semiconductor"], ticker: TSM, universes: [finance, ia, geopolitique]}
- {id: company:asml, name: ASML, aliases: [asml], ticker: ASML, universes: [finance, ia]}
- {id: company:samsung, name: Samsung Electronics, aliases: [samsung], universes: [finance, ia]}
- {id: company:sk-hynix, name: SK Hynix, aliases: ["sk hynix", hynix], universes: [finance, ia]}
- {id: company:arm, name: Arm, aliases: ["arm holdings", "=ARM"], ticker: ARM, universes: [finance, ia]}
- {id: company:qualcomm, name: Qualcomm, aliases: [qualcomm], ticker: QCOM, universes: [finance]}
- {id: company:oracle, name: Oracle, aliases: ["=Oracle"], ticker: ORCL, universes: [finance, ia]}
- {id: company:salesforce, name: Salesforce, aliases: [salesforce], ticker: CRM, universes: [finance, ia]}
- {id: company:ibm, name: IBM, aliases: ["=IBM"], ticker: IBM, universes: [finance, ia]}
- {id: company:palantir, name: Palantir, aliases: [palantir], ticker: PLTR, universes: [finance, ia]}
- {id: company:netflix, name: Netflix, aliases: [netflix], ticker: NFLX, universes: [finance]}
- {id: company:berkshire-hathaway, name: Berkshire Hathaway, aliases: ["berkshire hathaway", berkshire], universes: [finance]}
- {id: company:jpmorgan, name: JPMorgan Chase, aliases: [jpmorgan, "jp morgan", "jpmorgan chase"], ticker: JPM, universes: [finance]}
- {id: company:goldman-sachs, name: Goldman Sachs, aliases: ["goldman sachs"], ticker: GS, universes: [finance]}
- {id: company:blackrock, name: BlackRock, aliases: [blackrock], ticker: BLK, universes: [finance]}
- {id: company:visa, name: Visa, aliases: ["=Visa Inc"], ticker: V, universes: [finance]}
- {id: company:exxonmobil, name: ExxonMobil, aliases: [exxonmobil, "exxon mobil", exxon], ticker: XOM, universes: [finance, geopolitique]}
- {id: company:chevron, name: Chevron, aliases: [chevron], ticker: CVX, universes: [finance]}
- {id: company:shell, name: Shell, aliases: ["=Shell"], ticker: SHEL, universes: [finance]}
- {id: company:totalenergies, name: TotalEnergies, aliases: [totalenergies, "total energies"], ticker: TTE, universes: [finance, geopolitique]}
- {id: company:bp, name: BP, aliases: ["=BP"], ticker: BP, universes: [finance]}
- {id: company:saudi-aramco, name: Saudi Aramco, aliases: [aramco, "saudi aramco"], universes: [finance, geopolitique]}
- {id: company:lvmh, name: LVMH, aliases: [lvmh], ticker: MC.PA, universes: [finance]}
- {id: company:hermes, name: Hermès, aliases: ["=Hermès"], ticker: RMS.PA, universes: [finance]}
- {id: company:loreal, name: L'Oréal, aliases: ["l'oréal", "l’oréal", loreal], ticker: OR.PA, universes: [finance]}
- {id: company:airbus, name: Airbus, aliases: [airbus], ticker: AIR.PA, universes: [finance]}
- {id: company:boeing, name: Boeing, aliases: [boeing], ticker: BA, universes: [finance]}
- {id: company:safran, name: Safran, aliases: [safran], ticker: SAF.PA, universes: [finance]}
- {id: company:thales, name: Thales, aliases: ["=Thales"], ticker: HO.PA, universes: [finance, geopolitique]}
- {id: company:dassault-aviation, name: Dassault Aviation, aliases: ["dassault aviation", rafale], universes: [finance, geopolitique]}
- {id: company:schneider-electric, name: Schneider Electric, aliases: ["schneider electric"], ticker: SU.PA, universes: [finance]}
- {id: company:sanofi, name: Sanofi, aliases: [sanofi], ticker: SAN.PA, universes: [finance]}
- {id: company:novo-nordisk, name: Novo Nordisk, aliases: ["novo nordisk", ozempic, wegovy], ticker: NVO, universes: [finance]}
- {id: company:eli-lilly, name: Eli Lilly, aliases: ["eli lilly"], ticker: LLY, universes: [finance]}
- {id: company:bnp-paribas, name: BNP Paribas, aliases: ["bnp paribas", "=BNP"], ticker: BNP.PA, universes: [finance]}
- {id: company:axa, name: AXA, aliases: ["=AXA"], ticker: CS.PA, universes: [finance]}
- {id: company:stellantis, name: Stellantis, aliases: [stellantis], ticker: STLA, universes: [finance]}
- {id: company:renault, name: Renault, aliases: [renault], ticker: RNO.PA, universes: [finance]}
- {id: company:volkswagen, name: Volkswagen, aliases: [volkswagen], universes: [finance]}
- {id: company:byd, name: BYD, aliases: ["=BYD"], universes: [finance]}
- {id: company:toyota, name: Toyota, aliases: [toyota], universes: [finance]}
- {id: company:alibaba, name: Alibaba, aliases: [alibaba], ticker: BABA, universes: [finance, ia]}
- {id: company:tencent, name: Tencent, aliases: [tencent], universes: [finance, ia]}
- {id: company:huawei, name: Huawei, aliases: [huawei], universes: [finance, ia, geopolitique]}
- {id: company:xiaomi, name: Xiaomi, aliases: [xiaomi], universes: [finance]}
- {id: company:softbank, name: SoftBank, aliases: [softbank], universes: [finance, ia]}
- {id: company:coreweave, name: CoreWeave, aliases: [coreweave], ticker: CRWV, universes: [finance, ia]}
- {id: company:lockheed-martin, name: Lockheed Martin, aliases: ["lockheed martin", lockheed], ticker: LMT, universes: [finance, geopolitique]}
- {id: company:rheinmetall, name: Rheinmetall, aliases: [rheinmetall], universes: [finance, geopolitique]}
- {id: company:siemens, name: Siemens, aliases: [siemens], universes: [finance]}
- {id: company:sap, name: SAP, aliases: ["=SAP"], universes: [finance]}
- {id: company:coinbase, name: Coinbase, aliases: [coinbase], ticker: COIN, universes: [finance]}
- {id: company:binance, name: Binance, aliases: [binance], universes: [finance]}
- {id: company:strategy, name: Strategy (MicroStrategy), aliases: [microstrategy, "=MSTR"], ticker: MSTR, universes: [finance]}
- {id: company:openai, name: OpenAI, aliases: [openai], universes: [ia, finance]}
- {id: company:anthropic, name: Anthropic, aliases: [anthropic], universes: [ia, finance]}
- {id: company:google-deepmind, name: Google DeepMind, aliases: [deepmind, "google deepmind"], universes: [ia]}
- {id: company:xai, name: xAI, aliases: [xai], universes: [ia, finance]}
- {id: company:mistral-ai, name: Mistral AI, aliases: ["mistral ai", "=Mistral"], universes: [ia, finance]}
- {id: company:deepseek, name: DeepSeek, aliases: [deepseek], universes: [ia]}
- {id: company:perplexity, name: Perplexity, aliases: ["=Perplexity"], universes: [ia]}
- {id: company:hugging-face, name: Hugging Face, aliases: ["hugging face", huggingface], universes: [ia]}
- {id: company:cohere, name: Cohere, aliases: ["=Cohere"], universes: [ia]}
```

`config/entities/countries.yml` :

```yaml
# Pays (type country). Les capitales servent d'alias quand elles désignent couramment le gouvernement.
- {id: country:france, name: France, aliases: [france], universes: [geopolitique]}
- {id: country:etats-unis, name: États-Unis, aliases: ["états-unis", "etats-unis", "=USA", "united states", "u.s.", "maison-blanche", "maison blanche", "white house", washington], universes: [geopolitique]}
- {id: country:chine, name: Chine, aliases: [chine, china, pékin, beijing], universes: [geopolitique]}
- {id: country:russie, name: Russie, aliases: [russie, russia, moscou, moscow, kremlin], universes: [geopolitique]}
- {id: country:ukraine, name: Ukraine, aliases: [ukraine, kiev, kyiv], universes: [geopolitique]}
- {id: country:allemagne, name: Allemagne, aliases: [allemagne, germany, berlin], universes: [geopolitique]}
- {id: country:royaume-uni, name: Royaume-Uni, aliases: ["royaume-uni", "united kingdom", "=UK", britain, "grande-bretagne", "downing street"], universes: [geopolitique]}
- {id: country:italie, name: Italie, aliases: [italie, italy], universes: [geopolitique]}
- {id: country:espagne, name: Espagne, aliases: [espagne, spain], universes: [geopolitique]}
- {id: country:pologne, name: Pologne, aliases: [pologne, poland], universes: [geopolitique]}
- {id: country:japon, name: Japon, aliases: [japon, japan], universes: [geopolitique]}
- {id: country:coree-du-sud, name: Corée du Sud, aliases: ["corée du sud", "south korea", séoul, seoul], universes: [geopolitique]}
- {id: country:coree-du-nord, name: Corée du Nord, aliases: ["corée du nord", "north korea", pyongyang], universes: [geopolitique]}
- {id: country:inde, name: Inde, aliases: [inde, india, "new delhi"], universes: [geopolitique]}
- {id: country:pakistan, name: Pakistan, aliases: [pakistan], universes: [geopolitique]}
- {id: country:iran, name: Iran, aliases: [iran, téhéran, tehran], universes: [geopolitique]}
- {id: country:israel, name: Israël, aliases: [israël, israel], universes: [geopolitique]}
- {id: country:palestine, name: Palestine, aliases: [palestine, gaza, cisjordanie, "west bank", palestinien, palestiniens, palestinian, palestinians], universes: [geopolitique]}
- {id: country:liban, name: Liban, aliases: [liban, lebanon, beyrouth, beirut], universes: [geopolitique]}
- {id: country:syrie, name: Syrie, aliases: [syrie, syria, damas, damascus], universes: [geopolitique]}
- {id: country:arabie-saoudite, name: Arabie saoudite, aliases: ["arabie saoudite", "saudi arabia", riyad, riyadh], universes: [geopolitique]}
- {id: country:emirats-arabes-unis, name: Émirats arabes unis, aliases: ["émirats arabes unis", "emirats arabes unis", "united arab emirates", "=UAE", "=EAU", dubaï, dubai, "abou dhabi", "abu dhabi"], universes: [geopolitique]}
- {id: country:qatar, name: Qatar, aliases: [qatar, doha], universes: [geopolitique]}
- {id: country:turquie, name: Turquie, aliases: [turquie, turkey, türkiye, ankara], universes: [geopolitique]}
- {id: country:egypte, name: Égypte, aliases: [égypte, egypte, egypt, "le caire", cairo], universes: [geopolitique]}
- {id: country:taiwan, name: Taïwan, aliases: [taïwan, taiwan, taipei], universes: [geopolitique]}
- {id: country:bresil, name: Brésil, aliases: [brésil, bresil, brazil, brasilia], universes: [geopolitique]}
- {id: country:argentine, name: Argentine, aliases: [argentine, argentina], universes: [geopolitique]}
- {id: country:mexique, name: Mexique, aliases: [mexique, mexico], universes: [geopolitique]}
- {id: country:canada, name: Canada, aliases: [canada, ottawa], universes: [geopolitique]}
- {id: country:venezuela, name: Venezuela, aliases: [venezuela, caracas], universes: [geopolitique]}
- {id: country:afrique-du-sud, name: Afrique du Sud, aliases: ["afrique du sud", "south africa"], universes: [geopolitique]}
- {id: country:nigeria, name: Nigeria, aliases: [nigeria], universes: [geopolitique]}
- {id: country:ethiopie, name: Éthiopie, aliases: [éthiopie, ethiopie, ethiopia], universes: [geopolitique]}
- {id: country:soudan, name: Soudan, aliases: [soudan, sudan, khartoum], universes: [geopolitique]}
- {id: country:mali, name: Mali, aliases: ["=Mali", bamako], universes: [geopolitique]}
- {id: country:algerie, name: Algérie, aliases: [algérie, algerie, algeria], universes: [geopolitique]}
- {id: country:maroc, name: Maroc, aliases: [maroc, morocco], universes: [geopolitique]}
- {id: country:australie, name: Australie, aliases: [australie, australia], universes: [geopolitique]}
- {id: country:belgique, name: Belgique, aliases: [belgique, belgium], universes: [geopolitique]}
- {id: country:suisse, name: Suisse, aliases: [suisse, switzerland], universes: [geopolitique]}
- {id: country:pays-bas, name: Pays-Bas, aliases: ["pays-bas", netherlands], universes: [geopolitique]}
- {id: country:hongrie, name: Hongrie, aliases: [hongrie, hungary, budapest], universes: [geopolitique]}
- {id: country:yemen, name: Yémen, aliases: [yémen, yemen], universes: [geopolitique]}
- {id: country:danemark, name: Danemark, aliases: [danemark, denmark], universes: [geopolitique]}
- {id: country:groenland, name: Groenland, aliases: [groenland, greenland], universes: [geopolitique]}
```

`config/entities/orgs.yml` :

```yaml
- {id: org:onu, name: ONU, aliases: [onu, "nations unies", "united nations"], universes: [geopolitique]}
- {id: org:conseil-de-securite, name: Conseil de sécurité de l'ONU, aliases: ["conseil de sécurité", "security council"], universes: [geopolitique]}
- {id: org:otan, name: OTAN, aliases: [otan, nato], universes: [geopolitique]}
- {id: org:ue, name: Union européenne, aliases: ["union européenne", "european union", "=UE", "=EU"], universes: [geopolitique, finance]}
- {id: org:commission-europeenne, name: Commission européenne, aliases: ["commission européenne", "european commission"], universes: [geopolitique, finance]}
- {id: org:parlement-europeen, name: Parlement européen, aliases: ["parlement européen", "european parliament"], universes: [geopolitique]}
- {id: org:fmi, name: FMI, aliases: [fmi, "=IMF", "fonds monétaire international", "international monetary fund"], universes: [finance, geopolitique]}
- {id: org:banque-mondiale, name: Banque mondiale, aliases: ["banque mondiale", "world bank"], universes: [finance, geopolitique]}
- {id: org:omc, name: OMC, aliases: ["=OMC", "=WTO", "organisation mondiale du commerce", "world trade organization"], universes: [geopolitique, finance]}
- {id: org:opep, name: OPEP, aliases: [opep, opec, "opep+", "opec+"], universes: [finance, geopolitique]}
- {id: org:g7, name: G7, aliases: [g7], universes: [geopolitique]}
- {id: org:g20, name: G20, aliases: [g20], universes: [geopolitique]}
- {id: org:brics, name: BRICS, aliases: [brics], universes: [geopolitique]}
- {id: org:oms, name: OMS, aliases: ["=OMS", "organisation mondiale de la santé", "world health organization"], universes: [geopolitique]}
- {id: org:aiea, name: AIEA, aliases: [aiea, iaea], universes: [geopolitique]}
- {id: org:cpi, name: Cour pénale internationale, aliases: ["cour pénale internationale", "international criminal court"], universes: [geopolitique]}
- {id: org:hamas, name: Hamas, aliases: [hamas], universes: [geopolitique]}
- {id: org:hezbollah, name: Hezbollah, aliases: [hezbollah], universes: [geopolitique]}
- {id: org:houthis, name: Houthis, aliases: [houthis, houthi], universes: [geopolitique]}
- {id: org:sec, name: SEC (gendarme boursier américain), aliases: ["=SEC", "securities and exchange commission"], universes: [finance]}
- {id: org:uefa, name: UEFA, aliases: [uefa], universes: [sport], link_in: [sport]}
- {id: org:fifa, name: FIFA, aliases: [fifa], universes: [sport]}
- {id: org:cio, name: Comité international olympique, aliases: ["comité international olympique", "=CIO", "=IOC"], universes: [sport]}
- {id: org:fia, name: FIA, aliases: ["=FIA"], universes: [sport], link_in: [sport]}
- {id: org:atp, name: ATP, aliases: ["=ATP"], universes: [sport], link_in: [sport]}
- {id: org:wta, name: WTA, aliases: ["=WTA"], universes: [sport], link_in: [sport]}
```

`config/entities/central_banks.yml` :

```yaml
- {id: central_bank:fed, name: Réserve fédérale (Fed), aliases: ["=Fed", "réserve fédérale", "federal reserve", "=FOMC"], universes: [finance]}
- {id: central_bank:bce, name: Banque centrale européenne (BCE), aliases: ["=BCE", "=ECB", "banque centrale européenne", "european central bank"], universes: [finance]}
- {id: central_bank:boe, name: Banque d'Angleterre, aliases: ["=BoE", "banque d'angleterre", "bank of england"], universes: [finance]}
- {id: central_bank:boj, name: Banque du Japon, aliases: ["=BoJ", "banque du japon", "bank of japan"], universes: [finance]}
- {id: central_bank:pboc, name: Banque populaire de Chine, aliases: ["=PBOC", "banque populaire de chine", "people's bank of china"], universes: [finance]}
- {id: central_bank:bns, name: Banque nationale suisse, aliases: ["=BNS", "=SNB", "banque nationale suisse", "swiss national bank"], universes: [finance]}
```

`config/entities/persons.yml` :

```yaml
# Personnalités (type person). Les fonctions actuelles viennent de Wikidata, pas de ce fichier.
- {id: person:emmanuel-macron, name: Emmanuel Macron, aliases: [macron], universes: [geopolitique]}
- {id: person:donald-trump, name: Donald Trump, aliases: [trump], universes: [geopolitique, finance]}
- {id: person:jd-vance, name: JD Vance, aliases: [vance], universes: [geopolitique]}
- {id: person:marco-rubio, name: Marco Rubio, aliases: [rubio], universes: [geopolitique]}
- {id: person:xi-jinping, name: Xi Jinping, aliases: ["xi jinping"], universes: [geopolitique]}
- {id: person:vladimir-poutine, name: Vladimir Poutine, aliases: [poutine, putin], universes: [geopolitique]}
- {id: person:volodymyr-zelensky, name: Volodymyr Zelensky, aliases: [zelensky, zelenski, zelenskyy], universes: [geopolitique]}
- {id: person:benyamin-netanyahou, name: Benyamin Netanyahou, aliases: [netanyahou, netanyahu], universes: [geopolitique]}
- {id: person:ursula-von-der-leyen, name: Ursula von der Leyen, aliases: ["von der leyen"], universes: [geopolitique]}
- {id: person:friedrich-merz, name: Friedrich Merz, aliases: [merz], universes: [geopolitique]}
- {id: person:keir-starmer, name: Keir Starmer, aliases: [starmer], universes: [geopolitique]}
- {id: person:giorgia-meloni, name: Giorgia Meloni, aliases: [meloni], universes: [geopolitique]}
- {id: person:narendra-modi, name: Narendra Modi, aliases: [modi], universes: [geopolitique]}
- {id: person:recep-tayyip-erdogan, name: Recep Tayyip Erdoğan, aliases: [erdogan, erdoğan], universes: [geopolitique]}
- {id: person:mohammed-ben-salmane, name: Mohammed ben Salmane, aliases: ["ben salmane", "bin salman", "=MBS"], universes: [geopolitique]}
- {id: person:ali-khamenei, name: Ali Khamenei, aliases: [khamenei], universes: [geopolitique]}
- {id: person:kim-jong-un, name: Kim Jong-un, aliases: ["kim jong-un", "kim jong un"], universes: [geopolitique]}
- {id: person:lula, name: Lula da Silva, aliases: ["=Lula"], universes: [geopolitique]}
- {id: person:javier-milei, name: Javier Milei, aliases: [milei], universes: [geopolitique]}
- {id: person:antonio-guterres, name: António Guterres, aliases: [guterres], universes: [geopolitique]}
- {id: person:mark-rutte, name: Mark Rutte, aliases: [rutte], universes: [geopolitique]}
- {id: person:kaja-kallas, name: Kaja Kallas, aliases: [kallas], universes: [geopolitique]}
- {id: person:pedro-sanchez, name: Pedro Sánchez, aliases: ["pedro sánchez", "pedro sanchez"], universes: [geopolitique]}
- {id: person:marine-le-pen, name: Marine Le Pen, aliases: ["marine le pen", "le pen"], universes: [geopolitique]}
- {id: person:jordan-bardella, name: Jordan Bardella, aliases: [bardella], universes: [geopolitique]}
- {id: person:jerome-powell, name: Jerome Powell, aliases: [powell], universes: [finance]}
- {id: person:christine-lagarde, name: Christine Lagarde, aliases: [lagarde], universes: [finance]}
- {id: person:elon-musk, name: Elon Musk, aliases: [musk], universes: [finance, ia]}
- {id: person:sam-altman, name: Sam Altman, aliases: [altman], universes: [ia]}
- {id: person:dario-amodei, name: Dario Amodei, aliases: [amodei], universes: [ia]}
- {id: person:demis-hassabis, name: Demis Hassabis, aliases: [hassabis], universes: [ia]}
- {id: person:sundar-pichai, name: Sundar Pichai, aliases: [pichai], universes: [ia, finance]}
- {id: person:satya-nadella, name: Satya Nadella, aliases: [nadella], universes: [ia, finance]}
- {id: person:jensen-huang, name: Jensen Huang, aliases: ["jensen huang"], universes: [ia, finance]}
- {id: person:mark-zuckerberg, name: Mark Zuckerberg, aliases: [zuckerberg], universes: [ia, finance]}
- {id: person:tim-cook, name: Tim Cook, aliases: ["tim cook"], universes: [finance]}
- {id: person:jeff-bezos, name: Jeff Bezos, aliases: [bezos], universes: [finance]}
- {id: person:lisa-su, name: Lisa Su, aliases: ["lisa su"], universes: [ia, finance]}
- {id: person:arthur-mensch, name: Arthur Mensch, aliases: ["arthur mensch"], universes: [ia]}
- {id: person:yann-lecun, name: Yann LeCun, aliases: [lecun, "le cun"], universes: [ia]}
- {id: person:warren-buffett, name: Warren Buffett, aliases: [buffett], universes: [finance]}
- {id: person:larry-fink, name: Larry Fink, aliases: ["larry fink"], universes: [finance]}
```

`config/entities/players.yml` :

```yaml
# Joueuses et joueurs (type player), rattachés uniquement dans l'univers Sport.
- {id: player:kylian-mbappe, name: Kylian Mbappé, aliases: [mbappé, mbappe], universes: [sport], link_in: [sport]}
- {id: player:erling-haaland, name: Erling Haaland, aliases: [haaland], universes: [sport], link_in: [sport]}
- {id: player:vinicius-junior, name: Vinícius Júnior, aliases: [vinícius, vinicius], universes: [sport], link_in: [sport]}
- {id: player:jude-bellingham, name: Jude Bellingham, aliases: [bellingham], universes: [sport], link_in: [sport]}
- {id: player:lamine-yamal, name: Lamine Yamal, aliases: [yamal], universes: [sport], link_in: [sport]}
- {id: player:ousmane-dembele, name: Ousmane Dembélé, aliases: [dembélé, dembele], universes: [sport], link_in: [sport]}
- {id: player:mohamed-salah, name: Mohamed Salah, aliases: [salah], universes: [sport], link_in: [sport]}
- {id: player:harry-kane, name: Harry Kane, aliases: ["harry kane"], universes: [sport], link_in: [sport]}
- {id: player:lionel-messi, name: Lionel Messi, aliases: [messi], universes: [sport], link_in: [sport]}
- {id: player:cristiano-ronaldo, name: Cristiano Ronaldo, aliases: [ronaldo, "cristiano ronaldo"], universes: [sport], link_in: [sport]}
- {id: player:jannik-sinner, name: Jannik Sinner, aliases: [sinner], universes: [sport], link_in: [sport]}
- {id: player:carlos-alcaraz, name: Carlos Alcaraz, aliases: [alcaraz], universes: [sport], link_in: [sport]}
- {id: player:novak-djokovic, name: Novak Djokovic, aliases: [djokovic], universes: [sport], link_in: [sport]}
- {id: player:alexander-zverev, name: Alexander Zverev, aliases: [zverev], universes: [sport], link_in: [sport]}
- {id: player:daniil-medvedev, name: Daniil Medvedev, aliases: [medvedev], universes: [sport], link_in: [sport]}
- {id: player:taylor-fritz, name: Taylor Fritz, aliases: [fritz], universes: [sport], link_in: [sport]}
- {id: player:jack-draper, name: Jack Draper, aliases: [draper], universes: [sport], link_in: [sport]}
- {id: player:holger-rune, name: Holger Rune, aliases: ["=Rune"], universes: [sport], link_in: [sport]}
- {id: player:arthur-fils, name: Arthur Fils, aliases: ["arthur fils", "=Fils"], universes: [sport], link_in: [sport]}
- {id: player:giovanni-mpetshi-perricard, name: Giovanni Mpetshi Perricard, aliases: ["mpetshi perricard", mpetshi], universes: [sport], link_in: [sport]}
- {id: player:aryna-sabalenka, name: Aryna Sabalenka, aliases: [sabalenka], universes: [sport], link_in: [sport]}
- {id: player:iga-swiatek, name: Iga Świątek, aliases: [swiatek, świątek], universes: [sport], link_in: [sport]}
- {id: player:coco-gauff, name: Coco Gauff, aliases: [gauff], universes: [sport], link_in: [sport]}
- {id: player:elena-rybakina, name: Elena Rybakina, aliases: [rybakina], universes: [sport], link_in: [sport]}
- {id: player:jessica-pegula, name: Jessica Pegula, aliases: [pegula], universes: [sport], link_in: [sport]}
- {id: player:mirra-andreeva, name: Mirra Andreeva, aliases: [andreeva], universes: [sport], link_in: [sport]}
- {id: player:victor-wembanyama, name: Victor Wembanyama, aliases: [wembanyama, wemby], universes: [sport], link_in: [sport]}
- {id: player:lebron-james, name: LeBron James, aliases: [lebron], universes: [sport], link_in: [sport]}
- {id: player:stephen-curry, name: Stephen Curry, aliases: ["stephen curry", "steph curry"], universes: [sport], link_in: [sport]}
- {id: player:kevin-durant, name: Kevin Durant, aliases: [durant], universes: [sport], link_in: [sport]}
- {id: player:nikola-jokic, name: Nikola Jokić, aliases: [jokic, jokić], universes: [sport], link_in: [sport]}
- {id: player:giannis-antetokounmpo, name: Giannis Antetokounmpo, aliases: [antetokounmpo, giannis], universes: [sport], link_in: [sport]}
- {id: player:shai-gilgeous-alexander, name: Shai Gilgeous-Alexander, aliases: ["gilgeous-alexander", "=SGA"], universes: [sport], link_in: [sport]}
- {id: player:luka-doncic, name: Luka Dončić, aliases: [doncic, dončić], universes: [sport], link_in: [sport]}
- {id: player:jayson-tatum, name: Jayson Tatum, aliases: [tatum], universes: [sport], link_in: [sport]}
- {id: player:anthony-edwards, name: Anthony Edwards, aliases: ["anthony edwards"], universes: [sport], link_in: [sport]}
- {id: player:rudy-gobert, name: Rudy Gobert, aliases: [gobert], universes: [sport], link_in: [sport]}
- {id: player:earvin-ngapeth, name: Earvin Ngapeth, aliases: [ngapeth], universes: [sport], link_in: [sport]}
- {id: player:jean-patry, name: Jean Patry, aliases: [patry], universes: [sport], link_in: [sport]}
- {id: player:antoine-brizard, name: Antoine Brizard, aliases: [brizard], universes: [sport], link_in: [sport]}
- {id: player:kevin-tillie, name: Kévin Tillie, aliases: [tillie], universes: [sport], link_in: [sport]}
- {id: player:trevor-clevenot, name: Trévor Clévenot, aliases: [clevenot, clévenot], universes: [sport], link_in: [sport]}
- {id: player:stephen-boyer, name: Stephen Boyer, aliases: ["stephen boyer", "=Boyer"], universes: [sport], link_in: [sport]}
```

`config/entities/drivers.yml` :

```yaml
# Pilotes de F1, grille 2026 (à mettre à jour en début de saison).
- {id: driver:max-verstappen, name: Max Verstappen, aliases: [verstappen], universes: [sport], link_in: [sport]}
- {id: driver:isack-hadjar, name: Isack Hadjar, aliases: [hadjar], universes: [sport], link_in: [sport]}
- {id: driver:george-russell, name: George Russell, aliases: [russell], universes: [sport], link_in: [sport]}
- {id: driver:kimi-antonelli, name: Kimi Antonelli, aliases: [antonelli], universes: [sport], link_in: [sport]}
- {id: driver:charles-leclerc, name: Charles Leclerc, aliases: [leclerc], universes: [sport], link_in: [sport]}
- {id: driver:lewis-hamilton, name: Lewis Hamilton, aliases: [hamilton], universes: [sport], link_in: [sport]}
- {id: driver:lando-norris, name: Lando Norris, aliases: [norris], universes: [sport], link_in: [sport]}
- {id: driver:oscar-piastri, name: Oscar Piastri, aliases: [piastri], universes: [sport], link_in: [sport]}
- {id: driver:fernando-alonso, name: Fernando Alonso, aliases: [alonso], universes: [sport], link_in: [sport]}
- {id: driver:lance-stroll, name: Lance Stroll, aliases: [stroll], universes: [sport], link_in: [sport]}
- {id: driver:pierre-gasly, name: Pierre Gasly, aliases: [gasly], universes: [sport], link_in: [sport]}
- {id: driver:franco-colapinto, name: Franco Colapinto, aliases: [colapinto], universes: [sport], link_in: [sport]}
- {id: driver:alexander-albon, name: Alexander Albon, aliases: [albon], universes: [sport], link_in: [sport]}
- {id: driver:carlos-sainz, name: Carlos Sainz, aliases: [sainz], universes: [sport], link_in: [sport]}
- {id: driver:esteban-ocon, name: Esteban Ocon, aliases: [ocon], universes: [sport], link_in: [sport]}
- {id: driver:oliver-bearman, name: Oliver Bearman, aliases: [bearman], universes: [sport], link_in: [sport]}
- {id: driver:liam-lawson, name: Liam Lawson, aliases: [lawson], universes: [sport], link_in: [sport]}
- {id: driver:arvid-lindblad, name: Arvid Lindblad, aliases: [lindblad], universes: [sport], link_in: [sport]}
- {id: driver:nico-hulkenberg, name: Nico Hülkenberg, aliases: [hülkenberg, hulkenberg], universes: [sport], link_in: [sport]}
- {id: driver:gabriel-bortoleto, name: Gabriel Bortoleto, aliases: [bortoleto], universes: [sport], link_in: [sport]}
- {id: driver:sergio-perez, name: Sergio Pérez, aliases: ["sergio pérez", "sergio perez", checo], universes: [sport], link_in: [sport]}
- {id: driver:valtteri-bottas, name: Valtteri Bottas, aliases: [bottas], universes: [sport], link_in: [sport]}
```

`config/entities/teams.yml` :

```yaml
# Équipes (type team). Les autres équipes de football sont générées depuis les classements publiés.
- {id: team:psg, name: Paris Saint-Germain, aliases: [psg, "paris saint-germain", "paris sg"], universes: [sport], link_in: [sport]}
- {id: team:om, name: Olympique de Marseille, aliases: ["=OM", "olympique de marseille", marseille], universes: [sport], link_in: [sport]}
- {id: team:ol, name: Olympique lyonnais, aliases: ["=OL", "olympique lyonnais", "olympique lyon", lyon], universes: [sport], link_in: [sport]}
- {id: team:monaco, name: AS Monaco, aliases: ["as monaco", "=Monaco"], universes: [sport], link_in: [sport]}
- {id: team:lille, name: LOSC Lille, aliases: ["=LOSC", lille], universes: [sport], link_in: [sport]}
- {id: team:lens, name: RC Lens, aliases: ["rc lens", "=Lens"], universes: [sport], link_in: [sport]}
- {id: team:real-madrid, name: Real Madrid, aliases: ["real madrid"], universes: [sport], link_in: [sport]}
- {id: team:fc-barcelone, name: FC Barcelone, aliases: [barça, barca, "fc barcelone", barcelone, barcelona], universes: [sport], link_in: [sport]}
- {id: team:atletico-madrid, name: Atlético de Madrid, aliases: [atlético, atletico], universes: [sport], link_in: [sport]}
- {id: team:manchester-city, name: Manchester City, aliases: ["manchester city", "man city"], universes: [sport], link_in: [sport]}
- {id: team:manchester-united, name: Manchester United, aliases: ["manchester united", "man united", "man utd"], universes: [sport], link_in: [sport]}
- {id: team:liverpool, name: Liverpool FC, aliases: [liverpool], universes: [sport], link_in: [sport]}
- {id: team:arsenal, name: Arsenal, aliases: [arsenal], universes: [sport], link_in: [sport]}
- {id: team:chelsea, name: Chelsea, aliases: [chelsea], universes: [sport], link_in: [sport]}
- {id: team:tottenham, name: Tottenham Hotspur, aliases: [tottenham], universes: [sport], link_in: [sport]}
- {id: team:bayern-munich, name: Bayern Munich, aliases: [bayern], universes: [sport], link_in: [sport]}
- {id: team:dortmund, name: Borussia Dortmund, aliases: [dortmund], universes: [sport], link_in: [sport]}
- {id: team:juventus, name: Juventus, aliases: [juventus, juve], universes: [sport], link_in: [sport]}
- {id: team:inter-milan, name: Inter Milan, aliases: ["inter milan", "=Inter"], universes: [sport], link_in: [sport]}
- {id: team:ac-milan, name: AC Milan, aliases: ["milan ac", "ac milan"], universes: [sport], link_in: [sport]}
- {id: team:napoli, name: SSC Naples, aliases: [napoli, naples], universes: [sport], link_in: [sport]}
- {id: team:equipe-de-france, name: Équipe de France, aliases: ["équipe de france", "les bleus", "les bleues", "=Bleus", "=Bleues"], universes: [sport], link_in: [sport]}
- {id: team:lakers, name: Los Angeles Lakers, aliases: [lakers], universes: [sport], link_in: [sport]}
- {id: team:celtics, name: Boston Celtics, aliases: [celtics], universes: [sport], link_in: [sport]}
- {id: team:warriors, name: Golden State Warriors, aliases: [warriors], universes: [sport], link_in: [sport]}
- {id: team:knicks, name: New York Knicks, aliases: [knicks], universes: [sport], link_in: [sport]}
- {id: team:thunder, name: Oklahoma City Thunder, aliases: [thunder, "oklahoma city"], universes: [sport], link_in: [sport]}
- {id: team:spurs, name: San Antonio Spurs, aliases: ["san antonio spurs", "san antonio", "=Spurs"], universes: [sport], link_in: [sport]}
- {id: team:nuggets, name: Denver Nuggets, aliases: [nuggets], universes: [sport], link_in: [sport]}
- {id: team:bucks, name: Milwaukee Bucks, aliases: [bucks], universes: [sport], link_in: [sport]}
- {id: team:miami-heat, name: Miami Heat, aliases: ["miami heat"], universes: [sport], link_in: [sport]}
- {id: team:mavericks, name: Dallas Mavericks, aliases: [mavericks, mavs], universes: [sport], link_in: [sport]}
- {id: team:timberwolves, name: Minnesota Timberwolves, aliases: [timberwolves, wolves], universes: [sport], link_in: [sport]}
- {id: team:cavaliers, name: Cleveland Cavaliers, aliases: [cavaliers, cavs], universes: [sport], link_in: [sport]}
- {id: team:mercedes-f1, name: Mercedes (F1), aliases: ["=Mercedes"], universes: [sport], link_in: [sport]}
- {id: team:ferrari, name: Ferrari (F1), aliases: [ferrari, scuderia], universes: [sport], link_in: [sport]}
- {id: team:red-bull-racing, name: Red Bull Racing, aliases: ["red bull"], universes: [sport], link_in: [sport]}
- {id: team:racing-bulls, name: Racing Bulls, aliases: ["racing bulls"], universes: [sport], link_in: [sport]}
- {id: team:mclaren, name: McLaren, aliases: [mclaren], universes: [sport], link_in: [sport]}
- {id: team:aston-martin, name: Aston Martin (F1), aliases: ["aston martin"], universes: [sport], link_in: [sport]}
- {id: team:alpine-f1, name: Alpine (F1), aliases: ["=Alpine"], universes: [sport], link_in: [sport]}
- {id: team:williams, name: Williams, aliases: ["=Williams"], universes: [sport], link_in: [sport]}
- {id: team:audi-f1, name: Audi (F1), aliases: ["=Audi", sauber], universes: [sport], link_in: [sport]}
- {id: team:cadillac-f1, name: Cadillac (F1), aliases: ["=Cadillac"], universes: [sport], link_in: [sport]}
- {id: team:haas, name: Haas, aliases: ["=Haas"], universes: [sport], link_in: [sport]}
```

`config/entities/competitions.yml` :

```yaml
- {id: competition:ligue-des-champions, name: Ligue des champions, aliases: ["ligue des champions", "champions league", "=UCL"], universes: [sport], link_in: [sport]}
- {id: competition:ligue-europa, name: Ligue Europa, aliases: ["ligue europa", "europa league"], universes: [sport], link_in: [sport]}
- {id: competition:ligue-1, name: Ligue 1, aliases: ["ligue 1"], universes: [sport], link_in: [sport]}
- {id: competition:premier-league, name: Premier League, aliases: ["premier league"], universes: [sport], link_in: [sport]}
- {id: competition:liga, name: Liga, aliases: [laliga, "la liga", "=Liga"], universes: [sport], link_in: [sport]}
- {id: competition:serie-a, name: Serie A, aliases: ["serie a"], universes: [sport], link_in: [sport]}
- {id: competition:bundesliga, name: Bundesliga, aliases: [bundesliga], universes: [sport], link_in: [sport]}
- {id: competition:coupe-du-monde, name: Coupe du monde, aliases: ["coupe du monde", "world cup"], universes: [sport], link_in: [sport]}
- {id: competition:formule-1, name: Formule 1, aliases: ["formule 1", "formula 1", "=F1"], universes: [sport], link_in: [sport]}
- {id: competition:grands-chelems, name: Grands Chelems, aliases: ["grand chelem", "grands chelems", "grand slam"], universes: [sport], link_in: [sport]}
- {id: competition:roland-garros, name: Roland-Garros, aliases: ["roland-garros", "roland garros", "french open"], universes: [sport], link_in: [sport]}
- {id: competition:wimbledon, name: Wimbledon, aliases: [wimbledon], universes: [sport], link_in: [sport]}
- {id: competition:us-open, name: US Open, aliases: ["us open"], universes: [sport], link_in: [sport]}
- {id: competition:open-australie, name: Open d'Australie, aliases: ["open d'australie", "australian open"], universes: [sport], link_in: [sport]}
- {id: competition:masters-1000, name: Masters 1000, aliases: ["masters 1000"], universes: [sport], link_in: [sport]}
- {id: competition:finales-atp-wta, name: Finales ATP et WTA, aliases: ["atp finals", "wta finals", "finales atp"], universes: [sport], link_in: [sport]}
- {id: competition:nba, name: NBA, aliases: ["=NBA"], universes: [sport], link_in: [sport]}
- {id: competition:jeux-olympiques, name: Jeux olympiques, aliases: ["jeux olympiques", "=JO", olympics], universes: [sport], link_in: [sport]}
- {id: competition:tour-de-france, name: Tour de France, aliases: ["tour de france"], universes: [sport], link_in: [sport]}
- {id: competition:six-nations, name: Tournoi des Six Nations, aliases: ["six nations"], universes: [sport], link_in: [sport]}
- {id: competition:top-14, name: Top 14, aliases: ["top 14"], universes: [sport], link_in: [sport]}
```

`config/entities/etfs.yml` :

```yaml
# ETF (type etf) : peu cités par leur nom dans l'actualité, surtout atteints par les chaînes « Concernés ».
- {id: etf:spy, name: SPDR S&P 500 (SPY), aliases: ["=SPY"], ticker: SPY, universes: [finance]}
- {id: etf:cspx, name: iShares Core S&P 500 UCITS (CSPX), aliases: ["=CSPX", "ishares core s&p 500"], ticker: CSPX, universes: [finance]}
- {id: etf:iwda, name: iShares Core MSCI World (IWDA), aliases: ["=IWDA", "ishares core msci world"], ticker: IWDA, universes: [finance]}
- {id: etf:vwce, name: Vanguard FTSE All-World (VWCE), aliases: ["=VWCE", "vanguard ftse all-world"], ticker: VWCE, universes: [finance]}
- {id: etf:qqq, name: Invesco QQQ, aliases: ["=QQQ"], ticker: QQQ, universes: [finance]}
- {id: etf:eem, name: iShares MSCI Emerging Markets (EEM), aliases: ["=EEM"], ticker: EEM, universes: [finance]}
- {id: etf:tlt, name: iShares 20+ Year Treasury Bond (TLT), aliases: ["=TLT"], ticker: TLT, universes: [finance]}
- {id: etf:lqd, name: iShares Investment Grade Corporate Bond (LQD), aliases: ["=LQD"], ticker: LQD, universes: [finance]}
- {id: etf:hyg, name: iShares High Yield Corporate Bond (HYG), aliases: ["=HYG"], ticker: HYG, universes: [finance]}
- {id: etf:gld, name: SPDR Gold Shares (GLD), aliases: ["=GLD", "spdr gold"], ticker: GLD, universes: [finance]}
- {id: etf:xle, name: Energy Select Sector SPDR (XLE), aliases: ["=XLE"], ticker: XLE, universes: [finance]}
- {id: etf:smh, name: VanEck Semiconductor (SMH), aliases: ["=SMH"], ticker: SMH, universes: [finance, ia]}
- {id: etf:soxx, name: iShares Semiconductor (SOXX), aliases: ["=SOXX"], ticker: SOXX, universes: [finance, ia]}
- {id: etf:arkk, name: ARK Innovation (ARKK), aliases: ["=ARKK"], ticker: ARKK, universes: [finance]}
- {id: etf:ibit, name: iShares Bitcoin Trust (IBIT), aliases: ["=IBIT", "ishares bitcoin trust"], ticker: IBIT, universes: [finance]}
- {id: etf:fbtc, name: Fidelity Wise Origin Bitcoin (FBTC), aliases: ["=FBTC"], ticker: FBTC, universes: [finance]}
- {id: etf:etha, name: iShares Ethereum Trust (ETHA), aliases: ["=ETHA"], ticker: ETHA, universes: [finance]}
- {id: etf:ura, name: Global X Uranium (URA), aliases: ["=URA"], ticker: URA, universes: [finance]}
- {id: etf:ita, name: iShares U.S. Aerospace & Defense (ITA), aliases: ["=ITA"], ticker: ITA, universes: [finance, geopolitique]}
```

`config/entities/crypto.yml` :

```yaml
- {id: crypto:bitcoin, name: Bitcoin, aliases: [bitcoin, "=BTC"], universes: [finance]}
- {id: crypto:ethereum, name: Ethereum, aliases: [ethereum, ether, "=ETH"], universes: [finance]}
- {id: crypto:solana, name: Solana, aliases: [solana], universes: [finance]}
- {id: crypto:xrp, name: XRP, aliases: ["=XRP", ripple], universes: [finance]}
- {id: crypto:bnb, name: BNB, aliases: ["=BNB"], universes: [finance]}
- {id: crypto:tether, name: Tether (USDT), aliases: [tether, "=USDT"], universes: [finance]}
- {id: crypto:usdc, name: USD Coin (USDC), aliases: ["=USDC"], universes: [finance]}
- {id: crypto:dogecoin, name: Dogecoin, aliases: [dogecoin], universes: [finance]}
- {id: crypto:cardano, name: Cardano, aliases: [cardano], universes: [finance]}
```

`config/entities/indices.yml` :

```yaml
- {id: index:sp500, name: S&P 500, aliases: ["s&p 500", "s&p500", "=SPX"], universes: [finance]}
- {id: index:nasdaq, name: Nasdaq, aliases: [nasdaq], universes: [finance]}
- {id: index:dow-jones, name: Dow Jones, aliases: ["dow jones", "=Dow"], universes: [finance]}
- {id: index:cac40, name: CAC 40, aliases: ["cac 40", cac40], universes: [finance]}
- {id: index:dax, name: DAX, aliases: ["=DAX"], universes: [finance]}
- {id: index:euro-stoxx-50, name: Euro Stoxx 50, aliases: ["euro stoxx 50", eurostoxx], universes: [finance]}
- {id: index:nikkei, name: Nikkei 225, aliases: [nikkei], universes: [finance]}
- {id: index:ftse-100, name: FTSE 100, aliases: ["ftse 100", "=FTSE"], universes: [finance]}
- {id: index:hang-seng, name: Hang Seng, aliases: ["hang seng"], universes: [finance]}
- {id: index:vix, name: VIX (volatilité), aliases: ["=VIX"], universes: [finance]}
- {id: index:msci-world, name: MSCI World, aliases: ["msci world"], universes: [finance]}
```

`config/entities/rates.yml` :

```yaml
- {id: rate:us-10y, name: Taux US 10 ans, aliases: ["10-year treasury", "treasury yields", treasuries, "bons du trésor américain", "taux américain à 10 ans"], universes: [finance]}
- {id: rate:us-2y, name: Taux US 2 ans, aliases: ["2-year treasury", "taux américain à 2 ans"], universes: [finance]}
- {id: rate:bund, name: Bund allemand 10 ans, aliases: ["=Bund", "bund allemand"], universes: [finance]}
- {id: rate:oat, name: OAT française 10 ans, aliases: ["=OAT", "obligations assimilables du trésor"], universes: [finance]}
- {id: rate:spread-oat-bund, name: Écart OAT–Bund, aliases: ["spread oat", "écart oat-bund", "écart de taux franco-allemand", "spread français"], universes: [finance]}
- {id: rate:credit-spreads, name: Écarts de crédit, aliases: ["spreads de crédit", "credit spreads", "high yield", "junk bonds", "obligations à haut rendement"], universes: [finance]}
```

`config/entities/commodities.yml` :

```yaml
- {id: commodity:petrole, name: Pétrole, aliases: [pétrole, petrole, brent, "=WTI", oil, "crude oil", baril], universes: [finance, geopolitique]}
- {id: commodity:gaz, name: Gaz naturel, aliases: ["gaz naturel", "natural gas", "=GNL", "=LNG"], universes: [finance, geopolitique]}
- {id: commodity:or, name: Or, aliases: ["cours de l'or", "prix de l'or", "l'or", "l’or", gold], universes: [finance], link_in: [finance, geopolitique, ia]}
- {id: commodity:cuivre, name: Cuivre, aliases: [cuivre, copper], universes: [finance]}
- {id: commodity:lithium, name: Lithium, aliases: [lithium], universes: [finance]}
- {id: commodity:uranium, name: Uranium, aliases: [uranium], universes: [finance, geopolitique]}
- {id: commodity:terres-rares, name: Terres rares, aliases: ["terres rares", "rare earths", "rare earth"], universes: [finance, geopolitique]}
- {id: commodity:ble, name: Blé, aliases: [blé, wheat], universes: [finance, geopolitique]}
- {id: commodity:cacao, name: Cacao, aliases: [cacao, cocoa], universes: [finance]}
- {id: commodity:electricite, name: Électricité, aliases: [électricité, electricite, electricity], universes: [finance, ia]}
```

`config/entities/sectors.yml` :

```yaml
- {id: sector:semi-conducteurs, name: Semi-conducteurs, aliases: [semi-conducteurs, semiconducteurs, semiconductors, semiconductor, "puces électroniques"], universes: [finance, ia]}
- {id: sector:energie, name: Énergie, aliases: ["secteur énergétique", "energy sector", "majors pétrolières", "oil majors"], universes: [finance]}
- {id: sector:defense, name: Défense, aliases: ["industrie de défense", "valeurs de défense", "defense stocks", "dépenses militaires", "defense spending", "defence spending"], universes: [finance, geopolitique]}
- {id: sector:banques, name: Banques, aliases: ["secteur bancaire", "banking sector", "valeurs bancaires"], universes: [finance]}
- {id: sector:automobile, name: Automobile, aliases: ["secteur automobile", "constructeurs automobiles", automakers], universes: [finance]}
- {id: sector:luxe, name: Luxe, aliases: ["secteur du luxe", "luxury sector", "valeurs du luxe"], universes: [finance]}
- {id: sector:pharmacie, name: Pharmacie, aliases: ["secteur pharmaceutique", "laboratoires pharmaceutiques", "pharmaceutical industry"], universes: [finance]}
- {id: sector:immobilier, name: Immobilier, aliases: [immobilier, "real estate"], universes: [finance]}
```

`config/entities/tech.yml` :

```yaml
- {id: tech:gpu, name: GPU, aliases: ["=GPU", "=GPUs", "processeurs graphiques"], universes: [ia, finance]}
- {id: tech:puces-ia, name: Puces d'IA, aliases: ["puces ia", "puces d'ia", "ai chips", "ai chip"], universes: [ia, finance]}
- {id: tech:data-centers, name: Data centers, aliases: ["data center", "data centers", "data centres", "centres de données", "centre de données", datacenter, datacenters], universes: [ia, finance]}
- {id: tech:agents-ia, name: Agents IA, aliases: ["agents ia", "agent ia", "ai agents", "ai agent", agentic], universes: [ia]}
- {id: tech:llm, name: Grands modèles de langage, aliases: ["=LLM", "=LLMs", "large language model", "large language models", "grands modèles de langage"], universes: [ia]}
- {id: tech:robotique-humanoide, name: Robots humanoïdes, aliases: ["robot humanoïde", "robots humanoïdes", "humanoid robot", "humanoid robots"], universes: [ia]}
- {id: tech:informatique-quantique, name: Informatique quantique, aliases: ["informatique quantique", "quantum computing", "ordinateur quantique", "quantum computer"], universes: [ia, finance]}
- {id: tech:nucleaire, name: Nucléaire, aliases: [nucléaire, "nuclear power", "nuclear energy", "=SMR", "=SMRs"], universes: [finance, geopolitique]}
- {id: tech:vehicule-electrique, name: Véhicule électrique, aliases: ["véhicule électrique", "véhicules électriques", "electric vehicle", "electric vehicles", "=EV", "=EVs"], universes: [finance]}
- {id: tech:cybersecurite, name: Cybersécurité, aliases: [cybersécurité, cybersecurity, cyberattaque, cyberattack], universes: [ia, geopolitique]}
```

`config/entities/ai_models.yml` :

```yaml
- {id: ai_model:gpt, name: GPT / ChatGPT, aliases: [chatgpt, "=GPT", "gpt-4o", "gpt-5", "gpt-6"], universes: [ia]}
- {id: ai_model:sora, name: Sora, aliases: [sora], universes: [ia]}
- {id: ai_model:claude, name: Claude, aliases: ["=Claude"], universes: [ia]}
- {id: ai_model:gemini, name: Gemini, aliases: [gemini], universes: [ia]}
- {id: ai_model:veo, name: Veo, aliases: ["=Veo"], universes: [ia]}
- {id: ai_model:llama, name: Llama, aliases: ["=Llama"], universes: [ia]}
- {id: ai_model:grok, name: Grok, aliases: [grok], universes: [ia]}
- {id: ai_model:le-chat, name: Le Chat (Mistral), aliases: ["=Le Chat", "mistral large", "mistral medium", magistral], universes: [ia]}
- {id: ai_model:deepseek, name: Modèles DeepSeek, aliases: ["deepseek-r1", "deepseek-r2", "deepseek-v3", "deepseek-v4"], universes: [ia]}
- {id: ai_model:qwen, name: Qwen, aliases: [qwen], universes: [ia]}
- {id: ai_model:copilot, name: Copilot, aliases: [copilot], universes: [ia]}
```

`config/entities/topics.yml` :

```yaml
# Sujets suivis dans le temps (type topic).
- {id: topic:droits-de-douane, name: Droits de douane, aliases: ["droits de douane", tariffs, tariff, "guerre commerciale", "trade war"], universes: [geopolitique, finance]}
- {id: topic:sanctions-russie, name: Sanctions contre la Russie, aliases: ["sanctions contre la russie", "sanctions against russia", "russia sanctions"], universes: [geopolitique, finance]}
- {id: topic:guerre-ukraine, name: Guerre en Ukraine, aliases: ["guerre en ukraine", "war in ukraine", "ukraine war"], universes: [geopolitique]}
- {id: topic:guerre-gaza, name: Guerre à Gaza, aliases: ["guerre à gaza", "war in gaza", "gaza war"], universes: [geopolitique]}
- {id: topic:detroit-ormuz, name: Détroit d'Ormuz, aliases: [ormuz, hormuz], universes: [geopolitique, finance]}
- {id: topic:mer-rouge, name: Mer Rouge, aliases: ["mer rouge", "red sea"], universes: [geopolitique, finance]}
- {id: topic:sahel, name: Sahel, aliases: [sahel], universes: [geopolitique]}
- {id: topic:ai-act, name: Règlement européen sur l'IA, aliases: ["ai act", "règlement européen sur l'ia", "règlement sur l'ia"], universes: [ia]}
- {id: topic:inflation, name: Inflation, aliases: [inflation], universes: [finance]}
- {id: topic:recession, name: Récession, aliases: [récession, recession], universes: [finance]}
- {id: topic:stablecoins, name: Stablecoins, aliases: [stablecoin, stablecoins], universes: [finance]}
- {id: topic:transition-energetique, name: Transition énergétique, aliases: ["transition énergétique", "energy transition"], universes: [finance, geopolitique]}
- {id: topic:elections-mi-mandat, name: Élections de mi-mandat américaines, aliases: [midterms, "élections de mi-mandat"], universes: [geopolitique]}
- {id: topic:mercato, name: Mercato, aliases: [mercato, "transfer window"], universes: [sport], link_in: [sport]}
```

- [ ] **Step 4 : écrire `config/relations.yml`**

```yaml
# [source, verbe, cible]. Verbes : engine/catalog.py (VERBS). Appartenances et dirigeants actuels : surtout via Wikidata.
# Chaîne des semi-conducteurs et de l'IA
- [company:asml, fournit, company:tsmc]
- [company:asml, fournit, company:intel]
- [company:asml, fournit, company:samsung]
- [company:tsmc, fournit, company:nvidia]
- [company:tsmc, fournit, company:apple]
- [company:tsmc, fournit, company:amd]
- [company:tsmc, fournit, company:broadcom]
- [company:sk-hynix, fournit, company:nvidia]
- [company:samsung, fournit, company:nvidia]
- [company:nvidia, fournit, company:microsoft]
- [company:nvidia, fournit, company:amazon]
- [company:nvidia, fournit, company:alphabet]
- [company:nvidia, fournit, company:meta]
- [company:nvidia, fournit, company:oracle]
- [company:nvidia, fournit, company:coreweave]
- [company:nvidia, fournit, company:openai]
- [company:nvidia, fournit, company:xai]
- [company:amd, fournit, company:openai]
- [company:nvidia, produit, tech:gpu]
- [company:amd, produit, tech:gpu]
- [company:nvidia, produit, tech:puces-ia]
- [company:alphabet, produit, tech:puces-ia]
- [company:nvidia, secteur, sector:semi-conducteurs]
- [company:amd, secteur, sector:semi-conducteurs]
- [company:intel, secteur, sector:semi-conducteurs]
- [company:tsmc, secteur, sector:semi-conducteurs]
- [company:asml, secteur, sector:semi-conducteurs]
- [company:broadcom, secteur, sector:semi-conducteurs]
- [company:qualcomm, secteur, sector:semi-conducteurs]
- [company:arm, secteur, sector:semi-conducteurs]
- [company:sk-hynix, secteur, sector:semi-conducteurs]
- [etf:smh, suit, sector:semi-conducteurs]
- [etf:soxx, suit, sector:semi-conducteurs]
- [company:tsmc, expose, country:taiwan]
- [sector:semi-conducteurs, expose, topic:droits-de-douane]
- [company:microsoft, investit, tech:data-centers]
- [company:amazon, investit, tech:data-centers]
- [company:alphabet, investit, tech:data-centers]
- [company:meta, investit, tech:data-centers]
- [company:oracle, investit, tech:data-centers]
- [company:coreweave, investit, tech:data-centers]
- [tech:data-centers, expose, commodity:electricite]
- [tech:data-centers, expose, tech:gpu]
- [company:microsoft, investit, company:openai]
- [company:softbank, investit, company:openai]
- [company:nvidia, investit, company:openai]
- [company:amazon, investit, company:anthropic]
- [company:alphabet, investit, company:anthropic]
- [company:alphabet, detient, company:google-deepmind]
- [company:openai, produit, ai_model:gpt]
- [company:openai, produit, ai_model:sora]
- [company:anthropic, produit, ai_model:claude]
- [company:google-deepmind, produit, ai_model:gemini]
- [company:google-deepmind, produit, ai_model:veo]
- [company:meta, produit, ai_model:llama]
- [company:xai, produit, ai_model:grok]
- [company:mistral-ai, produit, ai_model:le-chat]
- [company:deepseek, produit, ai_model:deepseek]
- [company:alibaba, produit, ai_model:qwen]
- [company:microsoft, produit, ai_model:copilot]
- [company:openai, concurrent, company:anthropic]
- [company:openai, concurrent, company:google-deepmind]
- [company:anthropic, concurrent, company:google-deepmind]
- [company:nvidia, concurrent, company:amd]
- [person:sam-altman, dirige, company:openai]
- [person:dario-amodei, dirige, company:anthropic]
- [person:demis-hassabis, dirige, company:google-deepmind]
- [person:arthur-mensch, dirige, company:mistral-ai]
- [person:jensen-huang, dirige, company:nvidia]
- [person:lisa-su, dirige, company:amd]
- [person:elon-musk, dirige, company:tesla]
- [person:elon-musk, dirige, company:xai]
- [person:mark-zuckerberg, dirige, company:meta]
- [person:satya-nadella, dirige, company:microsoft]
- [person:sundar-pichai, dirige, company:alphabet]
- [person:larry-fink, dirige, company:blackrock]
- [company:berkshire-hathaway, detient, company:apple]
# Énergie, matières premières, géopolitique
- [country:arabie-saoudite, produit, commodity:petrole]
- [country:russie, produit, commodity:petrole]
- [country:iran, produit, commodity:petrole]
- [country:etats-unis, produit, commodity:petrole]
- [country:emirats-arabes-unis, produit, commodity:petrole]
- [country:venezuela, produit, commodity:petrole]
- [country:russie, produit, commodity:gaz]
- [country:qatar, produit, commodity:gaz]
- [country:etats-unis, produit, commodity:gaz]
- [country:chine, produit, commodity:terres-rares]
- [country:ukraine, produit, commodity:ble]
- [country:russie, produit, commodity:ble]
- [commodity:petrole, expose, topic:detroit-ormuz]
- [commodity:petrole, expose, topic:mer-rouge]
- [sector:energie, expose, commodity:petrole]
- [sector:energie, expose, commodity:gaz]
- [company:totalenergies, expose, commodity:petrole]
- [company:exxonmobil, expose, commodity:petrole]
- [company:chevron, expose, commodity:petrole]
- [company:shell, expose, commodity:petrole]
- [company:bp, expose, commodity:petrole]
- [company:saudi-aramco, expose, commodity:petrole]
- [company:totalenergies, secteur, sector:energie]
- [company:exxonmobil, secteur, sector:energie]
- [company:chevron, secteur, sector:energie]
- [company:shell, secteur, sector:energie]
- [company:bp, secteur, sector:energie]
- [etf:xle, suit, sector:energie]
- [etf:ura, suit, commodity:uranium]
- [etf:gld, suit, commodity:or]
- [sector:defense, expose, topic:guerre-ukraine]
- [etf:ita, suit, sector:defense]
- [company:lockheed-martin, secteur, sector:defense]
- [company:rheinmetall, secteur, sector:defense]
- [company:thales, secteur, sector:defense]
- [company:dassault-aviation, secteur, sector:defense]
- [company:safran, secteur, sector:defense]
- [country:ukraine, voisin, country:russie]
- [country:israel, voisin, country:liban]
- [country:israel, voisin, country:syrie]
# Marchés, taux, crypto
- [etf:ibit, suit, crypto:bitcoin]
- [etf:fbtc, suit, crypto:bitcoin]
- [etf:etha, suit, crypto:ethereum]
- [company:strategy, detient, crypto:bitcoin]
- [company:coinbase, expose, crypto:bitcoin]
- [etf:cspx, suit, index:sp500]
- [etf:spy, suit, index:sp500]
- [etf:iwda, suit, index:msci-world]
- [etf:qqq, suit, index:nasdaq]
- [etf:tlt, expose, rate:us-10y]
- [etf:lqd, expose, rate:credit-spreads]
- [etf:hyg, expose, rate:credit-spreads]
- [rate:us-10y, expose, central_bank:fed]
- [rate:us-2y, expose, central_bank:fed]
- [rate:bund, expose, central_bank:bce]
- [rate:oat, expose, central_bank:bce]
- [rate:spread-oat-bund, expose, country:france]
- [sector:automobile, expose, topic:droits-de-douane]
- [sector:luxe, expose, country:chine]
- [company:lvmh, secteur, sector:luxe]
- [company:hermes, secteur, sector:luxe]
- [company:stellantis, secteur, sector:automobile]
- [company:renault, secteur, sector:automobile]
- [company:volkswagen, secteur, sector:automobile]
- [company:tesla, secteur, sector:automobile]
- [company:byd, secteur, sector:automobile]
- [company:toyota, secteur, sector:automobile]
- [company:bnp-paribas, secteur, sector:banques]
- [company:jpmorgan, secteur, sector:banques]
- [company:goldman-sachs, secteur, sector:banques]
- [company:sanofi, secteur, sector:pharmacie]
- [company:novo-nordisk, secteur, sector:pharmacie]
- [company:eli-lilly, secteur, sector:pharmacie]
```

- [ ] **Step 5 : vérifier**

Run: `.venv/Scripts/python -m pytest tests/test_catalog.py -q`
Expected: PASS. Si `test_every_name_of_the_domain_dictionaries_is_covered_by_the_catalog` liste un nom manquant (`rubrique:Nom`), ajouter une entité portant ce nom en alias dans le fichier du type correspondant, puis relancer ; si le test d'unicité signale un alias partagé, garder l'alias sur l'entité la plus probable et le retirer de l'autre.

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe.

- [ ] **Step 6 : commit**

```bash
git add -A
git commit -m "feat: catalogue de départ de 400 entités et relations rédigées" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3 : rattachement par alias

**Files:**
- Create: `engine/linker.py`, `tests/test_linker.py`

**Interfaces:**
- Consumes : catalogue `{id: {"aliases": [...], "link_in"?: [...]}}` (tâches 1-2).
- Produces : `build_matcher(catalog, universe=None) -> dict`, `link(text, matcher) -> list[str]` (identifiants dans l'ordre de première mention), `event_text(ev) -> str`, `final_ids(ev) -> list[str]` (lit `candidates`, `llm_offered`, `llm_entities`).

- [ ] **Step 1 : écrire les tests**

`tests/test_linker.py` :

```python
from engine.linker import build_matcher, event_text, final_ids, link
from tests.helpers import mk_event, mk_item

CATALOG = {
    "company:apple": {"aliases": ["=Apple", "iphone"]},
    "company:meta": {"aliases": ["=Meta", "meta ai"]},
    "tech:data-centers": {"aliases": ["data center", "data centers"]},
    "country:france": {"aliases": ["france"]},
    "team:lille": {"aliases": ["lille"], "link_in": ["sport"]},
}


def test_whole_words_only_and_case_sensitive_aliases():
    m = build_matcher(CATALOG)
    assert link("Apple sort un nouvel iPhone", m) == ["company:apple"]
    assert link("une recette d'apple pie", m) == []
    assert link("Le metaverse ne sauve pas Meta", m) == ["company:meta"]


def test_order_follows_the_first_mention():
    assert link("Des data centers en France pour Meta", build_matcher(CATALOG)) == ["tech:data-centers", "country:france", "company:meta"]


def test_the_longest_alias_wins_at_the_same_position():
    m = build_matcher({"tech:data": {"aliases": ["data"]}, "tech:data-centers": {"aliases": ["data centers"]}})
    assert link("Les data centers consomment", m) == ["tech:data-centers"]


def test_link_in_restricts_an_entity_to_its_universes():
    assert link("Lille bat Lens", build_matcher(CATALOG, "sport")) == ["team:lille"]
    assert link("Le maire de Lille", build_matcher(CATALOG, "geopolitique")) == []
    assert link("Le maire de Lille", build_matcher(CATALOG)) == ["team:lille"]      # sans univers : tout le catalogue


def test_empty_catalog_links_nothing():
    assert link("Apple", build_matcher({})) == []


def test_event_text_puts_the_event_title_first():
    ev = mk_event([mk_item("a", "La France et Apple", snippet="Meta aussi")], title="Apple en tête")
    assert link(event_text(ev), build_matcher(CATALOG)) == ["company:apple", "country:france", "company:meta"]


def test_final_ids_keeps_confirmed_and_never_offered_candidates_in_order():
    ev = {"candidates": ["a", "b", "c"], "llm_offered": ["a", "b"], "llm_entities": ["b"]}
    assert final_ids(ev) == ["b", "c"]
    assert final_ids({"candidates": ["a"]}) == ["a"]
    assert final_ids({}) == []
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_linker.py -q`
Expected: FAIL, `No module named 'engine.linker'`.

- [ ] **Step 3 : écrire `engine/linker.py`**

```python
"""Rattachement des événements aux entités du catalogue par alias (mot entier)."""
import re

_Pattern = tuple[re.Pattern | None, dict[str, list[str]]]


def _pattern(keys: dict, flags: int) -> re.Pattern | None:
    if not keys:
        return None
    alternatives = "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))   # le plus long d'abord
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", flags)


def build_matcher(catalog: dict, universe: str | None = None) -> dict[str, _Pattern]:
    """Deux expressions : alias en minuscules (insensibles à la casse) et alias « = » (casse exacte)."""
    loose, strict = {}, {}
    for eid, e in catalog.items():
        if universe and e.get("link_in") and universe not in e["link_in"]:
            continue
        for alias in map(str, e["aliases"]):
            if alias.startswith("="):
                strict.setdefault(alias[1:], []).append(eid)
            else:
                loose.setdefault(alias.lower(), []).append(eid)
    return {"loose": (_pattern(loose, re.IGNORECASE), loose), "strict": (_pattern(strict, 0), strict)}


def link(text: str, matcher: dict[str, _Pattern]) -> list[str]:
    first = {}
    for mode, (pattern, table) in matcher.items():
        if pattern is None:
            continue
        for m in pattern.finditer(text):
            key = m.group(0).lower() if mode == "loose" else m.group(0)
            for eid in table.get(key, []):
                first[eid] = min(first.get(eid, m.start()), m.start())
    return sorted(first, key=lambda eid: (first[eid], eid))


def event_text(ev: dict) -> str:
    return " ".join([ev["title"], *(f"{i['title']} {i['snippet'][:300]}" for i in ev["items"])])


def final_ids(ev: dict) -> list[str]:
    """Candidats confirmés par le LLM, plus ceux qui ne lui ont jamais été proposés (catalogue enrichi depuis)."""
    offered, kept = set(ev.get("llm_offered", [])), set(ev.get("llm_entities", []))
    return [c for c in ev.get("candidates", []) if c in kept or c not in offered]
```

- [ ] **Step 4 : vérifier**

Run: `.venv/Scripts/python -m pytest tests/test_linker.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5 : commit**

```bash
git add -A
git commit -m "feat: rattachement des événements aux entités par alias" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4 : photos des articles

**Files:**
- Modify: `engine/collect.py`, `engine/normalize.py`, `engine/enrich.py`
- Test: `tests/test_collect.py`, `tests/test_normalize.py`, `tests/test_enrich.py`

**Interfaces:**
- Produces : clé facultative `image` sur les éléments bruts et normalisés (uniquement `https://`, 500 caractères max) ; `event_image(ev) -> str | None` dans `engine/enrich.py`.

- [ ] **Step 1 : écrire les tests**

Ajouter à `tests/test_collect.py` :

```python
MEDIA = b"""<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><title>t</title>
<item><title>A</title><link>https://ex.com/a</link><media:content url="https://img.ex.com/a.jpg" medium="image"/></item>
<item><title>B</title><link>https://ex.com/b</link><enclosure url="https://img.ex.com/b.png" type="image/png" length="1"/></item>
<item><title>C</title><link>https://ex.com/c</link><description>&lt;img src="https://img.ex.com/c.webp"&gt; texte</description></item>
<item><title>D</title><link>https://ex.com/d</link><description>sans image</description></item>
</channel></rss>"""


def test_rss_images_come_from_media_enclosure_or_the_first_img_tag():
    raws, health = collect_rss({"id": "s", "url": "mem://"}, lambda url: MEDIA)
    assert health["ok"]
    assert [r.get("image") for r in raws] == ["https://img.ex.com/a.jpg", "https://img.ex.com/b.png",
                                              "https://img.ex.com/c.webp", None]
```

Ajouter à `tests/test_normalize.py` :

```python
def test_only_https_images_are_kept():
    source = {"id": "s", "name": "S", "tier": 2, "domain": "ia"}
    base = {"title": "T", "url": "https://ex.com/1", "published_at": "2026-09-26T10:00:00+00:00"}
    assert normalize({**base, "image": "https://i.ex.com/x.jpg"}, source)["image"] == "https://i.ex.com/x.jpg"
    assert "image" not in normalize({**base, "image": "http://i.ex.com/x.jpg"}, source)
    assert "image" not in normalize({**base, "image": "javascript:alert(1)"}, source)
    assert "image" not in normalize({**base, "image": "https://i.ex.com/" + "x" * 600}, source)
    assert "image" not in normalize(base, source)
```

Ajouter à `tests/test_enrich.py` :

```python
from engine.enrich import event_image
from tests.helpers import mk_event, mk_item


def test_event_image_prefers_the_best_tier_then_the_most_recent():
    items = [{**mk_item("a", "A", tier=3, minutes_ago=5), "image": "https://i/a.jpg"},
             {**mk_item("b", "B", tier=2, minutes_ago=60), "image": "https://i/b.jpg"},
             {**mk_item("c", "C", tier=2, minutes_ago=10), "image": "https://i/c.jpg"},
             mk_item("d", "D", tier=1)]
    assert event_image(mk_event(items)) == "https://i/c.jpg"
    assert event_image(mk_event([mk_item("x", "X")])) is None
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py tests/test_normalize.py tests/test_enrich.py -q`
Expected: FAIL sur les trois nouveaux tests (`KeyError`/`AssertionError`, `ImportError: cannot import name 'event_image'`).

- [ ] **Step 3 : implémenter**

Dans `engine/collect.py`, ajouter `import re` en tête, puis après `_entry_time` :

```python
_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def _image(entry: dict) -> str | None:
    """Photo de l'article : media:content ou media:thumbnail, pièce jointe image, sinon première balise <img>."""
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            url = m.get("url")
            if url and (key == "media_thumbnail" or m.get("medium") == "image"
                        or str(m.get("type", "")).startswith("image/")):
                return url
    for enc in entry.get("enclosures") or []:
        if str(enc.get("type", "")).startswith("image/") and enc.get("href"):
            return enc["href"]
    m = _IMG.search(entry.get("summary", "") or "")
    return m.group(1) if m else None
```

et dans `collect_rss`, remplacer la construction de `raw` par :

```python
            raw = {"title": e["title"], "url": e["link"], "snippet": e.get("summary", ""),
                   "published_at": iso(_entry_time(e)), "image": _image(e)}
```

Dans `engine/normalize.py`, remplacer le `return` de `normalize` par :

```python
    image = str(raw.get("image") or "")
    item = {
        "id": item_id(raw["url"]), "source": pub or source["name"], "tier": tier,
        "origin": origin_of(default_origin, title, snippet), "title": title, "snippet": snippet,
        "url": raw["url"], "published_at": raw["published_at"], "domain": source["domain"],
    }
    # https uniquement : ni contenu mixte ni schéma exécutable dans la page
    return {**item, "image": image} if image.startswith("https://") and len(image) <= 500 else item
```

Dans `engine/enrich.py`, ajouter :

```python
def event_image(ev: dict) -> str | None:
    """Photo de l'événement : celle de la meilleure source (tier le plus bas), la plus récente à tier égal."""
    with_image = sorted((i for i in ev["items"] if i.get("image")), key=lambda i: i["published_at"], reverse=True)
    return min(with_image, key=lambda i: i["tier"])["image"] if with_image else None
```

- [ ] **Step 4 : vérifier**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe (les tests existants de `collect_rss` comparent des champs précis : si l'un compare un dictionnaire entier, y ajouter `"image": None`).

- [ ] **Step 5 : commit**

```bash
git add -A
git commit -m "feat: photos des articles (flux RSS, https uniquement)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5 : titre en français, entités confirmées et noms inconnus

**Files:**
- Modify: `engine/summarize.py`
- Create: `engine/candidates.py`, `tests/test_candidates.py`
- Test: `tests/test_summarize.py`

**Interfaces:**
- Consumes : `ev["candidates"]` (liste d'identifiants, tâche 11 la remplit avant le résumé).
- Produces : le résumé LLM peut porter en plus `title_fr: str`, `entities_llm: list[str]` (sous-ensemble des candidats), `unknown: list[str]` (≤ 3) ; `fingerprint` préfixé `v2|` ; `update_candidates(old, names, is_known, now, keep_days=30) -> dict`, `top_candidates(data, n=30) -> list[dict]`.

- [ ] **Step 1 : écrire les tests**

Ajouter à `tests/test_summarize.py` :

```python
def test_prompt_lists_the_candidates_and_asks_for_a_french_title():
    e = {**ev("ev_1", "OpenAI launches GPT-6"), "candidates": ["company:openai", "ai_model:gpt"]}
    prompts = []
    summarize([e], lambda p: prompts.append(p) or json.dumps({"ev_1": GOOD}))
    assert "Entités candidates : company:openai, ai_model:gpt" in prompts[0] and "« titre »" in prompts[0]


def test_extras_are_parsed_and_entities_outside_the_offer_are_dropped():
    e = {**ev("ev_1", "OpenAI launches GPT-6"), "candidates": ["company:openai", "ai_model:gpt"]}
    answer = {"ev_1": {**GOOD, "titre": " OpenAI lance GPT-6 ", "entites": ["ai_model:gpt", "company:inventee", 3],
                       "inconnus": ["Sam Altman", "", 7, "A", "B", "C"]}}
    results, _ = summarize([e], lambda p: json.dumps(answer))
    summary, mode = results["ev_1"]
    assert mode == "llm" and summary["title_fr"] == "OpenAI lance GPT-6"
    assert summary["entities_llm"] == ["ai_model:gpt"] and summary["unknown"] == ["Sam Altman", "A", "B"]
    assert {k: summary[k] for k in KEYS} == GOOD


def test_malformed_extras_are_ignored_without_losing_the_summary():
    answer = {"ev_1": {**GOOD, "titre": 42, "entites": "company:openai", "inconnus": None}}
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(answer))
    assert results["ev_1"] == (GOOD, "llm")


def test_fingerprint_is_versioned():
    assert fingerprint(ev("ev_1", "T")) != fingerprint({**ev("ev_1", "T"), "items": []})
    import hashlib
    ids = "|".join(sorted(i["id"] for i in ev("ev_1", "T")["items"]))
    assert fingerprint(ev("ev_1", "T")) == hashlib.sha1(("v2|" + ids).encode("utf-8")).hexdigest()[:16]
```

`tests/test_candidates.py` :

```python
from datetime import timedelta

from engine.candidates import top_candidates, update_candidates
from engine.timeutil import iso
from tests.helpers import NOW


def test_unknown_names_are_counted_by_lowercase_key_and_known_names_are_skipped():
    data = update_candidates({}, [("Sam Altman", "ia"), ("sam altman", "finance"), ("OpenAI", "ia"), ("  ", "ia")],
                             lambda name: name == "OpenAI", NOW)
    assert data == {"sam altman": {"name": "Sam Altman", "count": 2, "last_seen": iso(NOW), "domains": ["finance", "ia"]}}


def test_old_candidates_are_forgotten_and_the_top_is_sorted_by_count():
    old = {"vieux": {"name": "Vieux", "count": 9, "last_seen": iso(NOW - timedelta(days=31)), "domains": ["ia"]}}
    data = update_candidates(old, [("B", "ia"), ("A", "ia"), ("B", "ia")], lambda name: False, NOW)
    assert "vieux" not in data
    assert [c["name"] for c in top_candidates(data)] == ["B", "A"]
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_summarize.py tests/test_candidates.py -q`
Expected: FAIL (nouveaux tests ; `No module named 'engine.candidates'`).

- [ ] **Step 3 : implémenter `engine/summarize.py`**

Après `GEOPOLITICS_EXTRA`, ajouter :

```python
ENTITY_EXTRA = (
    "Pour chaque événement, ajoute aussi : « titre » : le titre de l'événement en français, fidèle aux sources, "
    "120 caractères au plus ; « entites » : la liste des identifiants, choisis UNIQUEMENT dans la ligne "
    "« Entités candidates » de l'événement, des entités réellement concernées (retire les homonymes et les mentions "
    "accessoires) ; « inconnus » : 0 à 3 noms propres importants (personnes, entreprises, pays, organisations) "
    "cités par les sources et absents des candidats."
)
```

Remplacer `fingerprint` :

```python
def fingerprint(ev: dict) -> str:
    # « v2| » : titres traduits et entités confirmées (lot 1A). Changer le préfixe fait résumer à nouveau, par lots.
    ids = "|".join(sorted(i["id"] for i in ev["items"]))
    return hashlib.sha1(f"v2|{ids}".encode("utf-8")).hexdigest()[:16]
```

Remplacer `_prompt` :

```python
def _prompt(events: list, profile: str = "default") -> str:
    extra = PROFILES[profile]["extra"]
    blocks = []
    for ev in events:
        lines = "\n".join(f"- [tier {i['tier']}] {i['source']} (publié le {i['published_at'][:10]}) : {i['title']} — {i['snippet'][:300]}"
                          for i in sorted(ev["items"], key=lambda i: i["tier"])[:6])
        cands = f"\nEntités candidates : {', '.join(ev['candidates'])}" if ev.get("candidates") else ""
        blocks.append(f"## {ev['id']}\nSujet : {ev['title']}\nFiabilité : {ev.get('reliability', '?')}{cands}\n{lines}")
    return f"{SYSTEM}{' ' + extra if extra else ''} {ENTITY_EXTRA}\n\n" + "\n\n".join(blocks)
```

Ajouter avant `_parse` :

```python
def _extras(s: dict, offered: set) -> dict:
    """Titre français, entités confirmées (parmi les candidats seulement) et noms inconnus ; tout champ mal formé est ignoré."""
    out = {}
    title = s.get("titre")
    if isinstance(title, str) and title.strip():
        out["title_fr"] = title.strip()[:200]
    chosen = s.get("entites")
    if isinstance(chosen, list):
        out["entities_llm"] = [x for x in chosen if isinstance(x, str) and x in offered]
    unknown = s.get("inconnus")
    if isinstance(unknown, list):
        out["unknown"] = [x.strip()[:80] for x in unknown if isinstance(x, str) and x.strip()][:3]
    return out
```

Remplacer `_parse` et `_ask` :

```python
def _parse(text: str, ids: list[str], profile: str = "default", offered: dict | None = None) -> dict:
    text = text.strip().removeprefix(_FENCE + "json").removeprefix(_FENCE).removesuffix(_FENCE).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("la réponse n'est pas un objet JSON")
    ok = {}
    for i in ids:
        s = data.get(i)
        if not (isinstance(s, dict) and all(isinstance(s.get(k), str) and s[k].strip() for k in KEYS)):
            continue
        summary = {k: s[k].strip() for k in KEYS}
        layers = _layers(s.get("layers")) if PROFILES[profile]["layers"] else None
        if has_advice(summary, layers):
            continue
        ok[i] = {**summary, **({"layers": layers} if layers else {}), **_extras(s, (offered or {}).get(i, set()))}
    return ok


def _ask(batch: list, call: Callable[[str], str], profile: str = "default") -> tuple[dict, str | None]:
    prompt, error = _prompt(batch, profile), None
    offered = {e["id"]: set(e.get("candidates", [])) for e in batch}
    for _ in range(2):
        try:
            return _parse(call(prompt), [e["id"] for e in batch], profile, offered), None
        except Exception as exc:  # le repli extractif couvre tous les échecs, l'erreur est remontée
            msg = f"{type(exc).__name__}: {exc}"
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                return {}, "quota"
            error = msg
    return {}, error
```

- [ ] **Step 4 : écrire `engine/candidates.py`**

```python
"""Noms propres importants absents du catalogue, proposés par le LLM : jamais ajoutés sans validation (spec §5.3)."""
from collections.abc import Callable
from datetime import datetime, timedelta

from .timeutil import iso, parse


def update_candidates(old: dict, names: list[tuple[str, str]], is_known: Callable[[str], bool],
                      now: datetime, keep_days: int = 30) -> dict:
    data = dict(old)
    for raw, domain in names:
        name = raw.strip()
        if not name or is_known(name):
            continue
        key = name.lower()
        cur = data.get(key, {"name": name, "count": 0, "domains": []})
        data[key] = {"name": cur["name"], "count": cur["count"] + 1, "last_seen": iso(now),
                     "domains": sorted({*cur["domains"], domain})}
    cutoff = now - timedelta(days=keep_days)
    return {k: v for k, v in sorted(data.items()) if parse(v["last_seen"]) >= cutoff}


def top_candidates(data: dict, n: int = 30) -> list[dict]:
    return sorted(data.values(), key=lambda c: (-c["count"], c["name"]))[:n]
```

- [ ] **Step 5 : vérifier**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe.

- [ ] **Step 6 : commit**

```bash
git add -A
git commit -m "feat: titre en français, entités confirmées et noms inconnus dans l'appel de résumé" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6 : graphe et chaînes « Concernés »

**Files:**
- Create: `engine/graph.py`, `tests/test_graph.py`

**Interfaces:**
- Consumes : `VERBS`, `EXPOSURE` (tâche 1) ; relations `[(src, verb, dst)]`.
- Produces : `cooccurrence(events, min_events=3) -> list[dict]`, `build_edges(relations, fact_edges, events, min_events=3) -> list[dict]` (arête = `{"src","verb","dst","weight","origin"}`), `adjacency(edges) -> dict[str, list[dict]]` (voisin = `{"id","verb","label","weight","origin"}`), `concerned(start_ids, adj, catalog, limit=6) -> list[list[dict]]` (étape = `{"from","to","label"}`).

- [ ] **Step 1 : écrire les tests**

`tests/test_graph.py` :

```python
from engine.graph import adjacency, build_edges, concerned, cooccurrence

CAT = {i: {"name": n, "type": i.split(":")[0], **extra} for i, n, extra in [
    ("country:iran", "Iran", {}), ("commodity:petrole", "Pétrole", {}), ("sector:energie", "Énergie", {}),
    ("etf:xle", "XLE", {"ticker": "XLE"}), ("company:total", "TotalEnergies", {"ticker": "TTE"}), ("org:onu", "ONU", {})]}
REL = [("country:iran", "produit", "commodity:petrole"), ("sector:energie", "expose", "commodity:petrole"),
       ("etf:xle", "suit", "sector:energie"), ("company:total", "expose", "commodity:petrole"),
       ("country:iran", "membre_de", "org:onu")]


def test_cooccurrence_needs_three_shared_events():
    evs = [{"entity_ids": ["a", "b"]}] * 3 + [{"entity_ids": ["a", "c"]}] * 2 + [{}]
    assert cooccurrence(evs) == [{"src": "a", "verb": "lie_a", "dst": "b", "weight": 3, "origin": "cooccurrence"}]


def test_edges_are_deduplicated_and_readable_in_both_directions():
    edges = build_edges([*REL, REL[0]], [{"src": "org:onu", "verb": "membre_de", "dst": "country:iran", "weight": 1, "origin": "wikidata"}], [])
    assert len(edges) == len(REL) + 1
    adj = adjacency(edges)
    assert {"id": "country:iran", "verb": "produit", "label": "produit par", "weight": 1, "origin": "config"} in adj["commodity:petrole"]
    assert {"id": "commodity:petrole", "verb": "produit", "label": "produit", "weight": 1, "origin": "config"} in adj["country:iran"]


def test_concerned_follows_only_exposure_links_up_to_two_hops_and_ranks_tradable_assets_first():
    chains = concerned(["country:iran"], adjacency(build_edges(REL, [], [])), CAT)
    assert [[s["to"] for s in c] for c in chains] == [["commodity:petrole"], ["commodity:petrole", "company:total"],
                                                     ["commodity:petrole", "sector:energie"]]
    assert chains[1][1] == {"from": "commodity:petrole", "to": "company:total", "label": "influence"}


def test_an_event_about_oil_reaches_the_energy_etf():
    chains = concerned(["commodity:petrole"], adjacency(build_edges(REL, [], [])), CAT)
    assert ["sector:energie", "etf:xle"] in [[s["to"] for s in c] for c in chains]
    assert all(c[-1]["to"] != "commodity:petrole" for c in chains)          # jamais une entité de départ


def test_concerned_is_limited_and_ignores_unknown_entities():
    adj = adjacency(build_edges(REL, [{"src": "company:total", "verb": "expose", "dst": "company:inconnue", "weight": 1, "origin": "wikidata"}], []))
    chains = concerned(["commodity:petrole"], adj, CAT, limit=2)
    assert len(chains) == 2 and all(c[-1]["to"] in CAT for c in chains)
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_graph.py -q`
Expected: FAIL, `No module named 'engine.graph'`.

- [ ] **Step 3 : écrire `engine/graph.py`**

```python
"""Graphe des entités : relations rédigées, faits Wikidata, co-occurrences ; chaînes « Concernés » (spec §5.5)."""
from collections import Counter, defaultdict
from itertools import combinations

from .catalog import EXPOSURE, VERBS

_TRADABLE = {"etf", "index", "commodity", "crypto", "rate"}


def cooccurrence(events: list, min_events: int = 3) -> list[dict]:
    pairs = Counter()
    for e in events:
        pairs.update(combinations(sorted(set(e.get("entity_ids", []))), 2))
    return [{"src": a, "verb": "lie_a", "dst": b, "weight": n, "origin": "cooccurrence"}
            for (a, b), n in sorted(pairs.items()) if n >= min_events]


def build_edges(relations: list, fact_edges: list, events: list, min_events: int = 3) -> list[dict]:
    curated = [{"src": s, "verb": v, "dst": d, "weight": 1, "origin": "config"} for s, v, d in relations]
    out, seen = [], set()
    for edge in [*curated, *fact_edges, *cooccurrence(events, min_events)]:
        key = (edge["src"], edge["verb"], edge["dst"])
        if key not in seen:
            seen.add(key)
            out.append(edge)
    return out


def adjacency(edges: list) -> dict[str, list[dict]]:
    adj = defaultdict(list)
    for e in edges:
        forward, backward = VERBS[e["verb"]]
        adj[e["src"]].append({"id": e["dst"], "verb": e["verb"], "label": forward, "weight": e["weight"], "origin": e["origin"]})
        adj[e["dst"]].append({"id": e["src"], "verb": e["verb"], "label": backward, "weight": e["weight"], "origin": e["origin"]})
    return dict(adj)


def _tradable(entity: dict) -> bool:
    return bool(entity.get("ticker")) or entity.get("type") in _TRADABLE


def concerned(start_ids: list[str], adj: dict, catalog: dict, limit: int = 6) -> list[list[dict]]:
    """Parcours en largeur, 2 sauts au plus, par les seuls liens d'exposition ; actifs cotés d'abord."""
    seen, chains = set(start_ids), []
    queue = [(s, []) for s in start_ids]
    while queue:
        node, steps = queue.pop(0)
        if len(steps) == 2:
            continue
        for nb in adj.get(node, []):
            if nb["verb"] not in EXPOSURE or nb["id"] in seen or nb["id"] not in catalog:
                continue
            seen.add(nb["id"])
            chain = [*steps, {"from": node, "to": nb["id"], "label": nb["label"]}]
            chains.append(chain)
            queue.append((nb["id"], chain))
    end = lambda c: catalog[c[-1]["to"]]
    return sorted(chains, key=lambda c: (not _tradable(end(c)), len(c), end(c)["name"]))[:limit]
```

- [ ] **Step 4 : vérifier**

Run: `.venv/Scripts/python -m pytest tests/test_graph.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5 : commit**

```bash
git add -A
git commit -m "feat: graphe des entités et chaînes Concernés" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7 : contrat, sélection du jour et fichiers d'univers

**Files:**
- Modify: `schemas/public.schema.json`, `engine/publish.py`, `engine/search.py`
- Create: `engine/today.py`, `tests/test_today.py`, `tests/test_publish_socle.py`

**Interfaces:**
- Consumes : événements portant `universe`, `entity_ids`, `title_fr`, `image`, `concerned` (facultatifs).
- Produces : contrat `step`, `searchEntry`, `todayBand`, `universeFile`, `entityIndex`, `entityFile`, `band` ; `project()` publie les champs facultatifs ; `day_score(ev, now, t)`, `build_today(events, universes, g, now) -> list[dict]` ; `build_home` ajoute `today` si des univers existent ; `build_universe(uni, domains, events_by_domain, now, agendas=None, limit=150) -> dict` ; `publish(root, home, domain_files, universe_files=())` ; `search._entry` publie les champs facultatifs.

- [ ] **Step 1 : étendre le contrat**

Dans `schemas/public.schema.json`, dans `$defs.event.properties`, ajouter après `"entities"` :

```json
        "universe": {"type": "string"},
        "entity_ids": {"type": "array", "items": {"type": "string"}},
        "title_fr": {"type": "string"},
        "image": {"type": "string", "pattern": "^https://"},
        "concerned": {"type": "array", "maxItems": 6,
                      "items": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"$ref": "#/$defs/step"}}},
```

Dans `$defs.home.properties`, ajouter après `"events"` :

```json
        "today": {"type": "array", "items": {"$ref": "#/$defs/todayBand"}}
```

Dans `$defs.search.properties.events`, remplacer l'objet `items` entier par `{"$ref": "#/$defs/searchEntry"}`.

Ajouter dans `$defs` (après `"football"`) :

```json
    "step": {
      "type": "object",
      "required": ["from", "to", "label"],
      "properties": {"from": {"type": "string"}, "to": {"type": "string"}, "label": {"type": "string"}}
    },
    "searchEntry": {
      "type": "object",
      "required": ["id", "domain", "title", "retenir", "entities", "date", "level", "reliability", "source", "url"],
      "properties": {
        "id": {"type": "string"}, "domain": {"type": "string"}, "title": {"type": "string"}, "retenir": {"type": "string"},
        "entities": {"type": "array", "items": {"type": "string"}}, "date": {"type": "string"},
        "level": {"type": "integer", "enum": [1, 2, 3]}, "reliability": {"type": "string"},
        "source": {"type": "string"}, "url": {"type": "string"},
        "universe": {"type": "string"}, "entity_ids": {"type": "array", "items": {"type": "string"}},
        "title_fr": {"type": "string"}, "image": {"type": "string", "pattern": "^https://"}
      }
    },
    "todayBand": {
      "type": "object",
      "required": ["id", "name", "short", "color", "ids"],
      "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "short": {"type": "string"},
                     "color": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}}
    },
    "universeFile": {
      "type": "object",
      "required": ["generated_at", "universe", "domains", "events", "upcoming"],
      "properties": {
        "generated_at": {"type": "string"},
        "universe": {
          "type": "object",
          "required": ["id", "name", "short", "color", "order", "subthemes"],
          "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "short": {"type": "string"},
                         "color": {"type": "string"}, "order": {"type": "integer"},
                         "subthemes": {"type": "array", "items": {"type": "object", "required": ["id", "name"]}}}
        },
        "domains": {"type": "array", "items": {"type": "object", "required": ["id", "name"]}},
        "events": {"type": "array", "items": {"$ref": "#/$defs/event"}},
        "upcoming": {"$ref": "#/$defs/upcoming"}
      }
    },
    "entityIndex": {
      "type": "object",
      "required": ["generated_at", "types", "entities"],
      "properties": {
        "generated_at": {"type": "string"},
        "types": {"type": "object", "additionalProperties": {"type": "string"}},
        "entities": {"type": "array", "items": {
          "type": "object",
          "required": ["id", "name", "type", "universes", "aliases", "n30"],
          "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"},
                         "universes": {"type": "array", "items": {"type": "string"}},
                         "aliases": {"type": "array", "items": {"type": "string"}},
                         "n30": {"type": "integer", "minimum": 0},
                         "image": {"type": "string", "pattern": "^https://"}}
        }}
      }
    },
    "entityFile": {
      "type": "object",
      "required": ["generated_at", "entity", "description", "image", "facts", "relations", "events"],
      "properties": {
        "generated_at": {"type": "string"},
        "entity": {"type": "object", "required": ["id", "name", "type", "type_label", "universes"]},
        "description": {"type": ["string", "null"]},
        "image": {"type": ["string", "null"], "pattern": "^https://"},
        "facts": {"type": "array", "items": {"type": "object", "required": ["label", "value"],
                  "properties": {"label": {"type": "string"}, "value": {"type": "string"}}}},
        "relations": {"type": "array", "items": {"type": "object", "required": ["id", "name", "type", "label", "origin", "weight"]}},
        "events": {"type": "array", "items": {"$ref": "#/$defs/searchEntry"}},
        "quote": {"type": "object", "required": ["price", "change_pct", "currency", "as_of", "stale"]}
      }
    },
    "band": {
      "type": "object",
      "required": ["generated_at", "items"],
      "properties": {
        "generated_at": {"type": "string"},
        "items": {"type": "array", "items": {
          "type": "object",
          "required": ["universe", "kind", "label", "value", "delta", "unit", "at", "href"],
          "properties": {"universe": {"type": "string"}, "kind": {"enum": ["new", "agenda", "match", "race", "quote"]},
                         "label": {"type": "string"}, "value": {"type": ["number", "string", "null"]},
                         "delta": {"type": ["number", "null"]}, "unit": {"type": ["string", "null"]},
                         "at": {"type": ["string", "null"]}, "href": {"type": ["string", "null"]}}
        }}
      }
    }
```

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe (champs uniquement facultatifs ; `test_sample_data` reste vert).

- [ ] **Step 2 : écrire les tests**

`tests/test_today.py` :

```python
from datetime import timedelta

from engine.timeutil import iso
from engine.today import build_today, day_score
from tests.helpers import NOW

G = {"today": {"window_hours": 36, "floor": 2, "total": 7, "max_per_entity": 2, "novelty_bonus": 8, "evolution_bonus": 5}}
UNIS = {u: {"id": u, "name": u.upper(), "short": u, "color": u} for u in ("finance", "ia", "sport")}


def ev(id, universe, imp, ents=(), level=1, hours=2, rev=1, first_hours=None):
    return {"id": id, "universe": universe, "importance": imp, "level": level, "entity_ids": list(ents), "rev": rev,
            "updated_at": iso(NOW - timedelta(hours=hours)),
            "first_seen": iso(NOW - timedelta(hours=hours if first_hours is None else first_hours))}


def ids(result):
    return {r["id"]: r["ids"] for r in result}


def test_each_universe_gets_its_floor_then_the_best_scores_fill_the_total():
    evs = [ev("f1", "finance", 90), ev("f2", "finance", 85), ev("f3", "finance", 80), ev("f4", "finance", 79),
           ev("f5", "finance", 78), ev("i1", "ia", 50), ev("i2", "ia", 40), ev("s1", "sport", 30)]
    assert ids(build_today(evs, UNIS, G, NOW)) == {"finance": ["f1", "f2", "f3", "f4"], "ia": ["i1", "i2"], "sport": ["s1"]}


def test_at_most_two_events_per_lead_entity_and_old_or_level_zero_events_are_ignored():
    evs = [ev("a", "ia", 90, ["company:openai"]), ev("b", "ia", 89, ["company:openai"]), ev("c", "ia", 88, ["company:openai"]),
           ev("old", "ia", 99, hours=40), ev("l0", "ia", 99, level=0), ev("x", "espace", 99)]
    assert ids(build_today(evs, UNIS, G, NOW))["ia"] == ["a", "b"]


def test_novelty_and_evolution_bonuses():
    t = G["today"]
    assert day_score(ev("n", "ia", 50, first_hours=2), NOW, t) == 58
    assert day_score(ev("o", "ia", 50, hours=2, first_hours=30, rev=2), NOW, t) == 55
    assert day_score(ev("p", "ia", 50, hours=20, first_hours=30, rev=2), NOW, t) == 50


def test_universes_keep_their_order_and_metadata_even_when_empty():
    result = build_today([], UNIS, G, NOW)
    assert [r["id"] for r in result] == ["finance", "ia", "sport"] and result[0] == {"id": "finance", "name": "FINANCE", "short": "finance", "color": "finance", "ids": []}
```

`tests/test_publish_socle.py` :

```python
import json
from datetime import timedelta

from engine.contract import validate
from engine.publish import build_home, build_universe, project, publish
from engine.search import _entry
from engine.timeutil import iso
from tests.helpers import DOM, G, NOW, mk_event, mk_item

UNI = {"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "order": 2, "domains": ["ia"],
       "subthemes": [{"id": "modeles", "name": "Modèles", "kinds": ["model_release"]}]}
TODAY = {"window_hours": 36, "floor": 3, "total": 18, "max_per_entity": 2, "novelty_bonus": 8, "evolution_bonus": 5}


def pub(id, imp=80, level=1, **extra):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}")], id=id)
    return {**e, "importance": imp, "level": level, "reliability": "confirmé", "reliability_reason": "r", **extra}


def cfg(universes=True):
    return {"global": {**G, "today": TODAY}, "domains": {"ia": DOM}, "universes": {"ia": UNI} if universes else {}}


def test_project_adds_the_new_optional_fields_only_when_set():
    p = project(pub("a", universe="ia", entity_ids=["company:openai"], title_fr="Titre FR", image="https://i/x.jpg",
                    concerned=[[{"from": "company:openai", "to": "ai_model:gpt", "label": "produit"}]], unknown=["X"]))
    validate("event", p)
    assert p["title_fr"] == "Titre FR" and p["entity_ids"] == ["company:openai"] and "unknown" not in p
    assert "title_fr" not in project(pub("b", title_fr=None))


def test_search_entries_carry_the_optional_fields():
    entry = _entry(pub("a", universe="ia", entity_ids=["company:openai"], title_fr="Titre FR"))
    validate("searchEntry", entry)
    assert entry["universe"] == "ia" and entry["title_fr"] == "Titre FR" and "image" not in entry


def test_home_carries_today_with_its_events():
    home = build_home(cfg(), {"ia": [pub("a", universe="ia"), pub("b", 60, level=2, universe="ia")]}, NOW)
    validate("home", home)
    assert home["today"] == [{"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "ids": ["a", "b"]}]
    assert set(home["today"][0]["ids"]) <= set(home["events"])


def test_home_without_universes_has_no_today():
    assert "today" not in build_home(cfg(universes=False), {"ia": [pub("a")]}, NOW)


def test_universe_file_lists_recent_events_by_importance_and_is_published(tmp_path):
    old = pub("old", 99, updated_at=iso(NOW - timedelta(days=8)))
    f = build_universe(UNI, {"ia": DOM}, {"ia": [pub("a", 60, universe="ia"), pub("b", 90, universe="ia"), old, pub("z", 99, level=0)]}, NOW)
    validate("universeFile", f)
    assert [e["id"] for e in f["events"]] == ["b", "a"] and f["universe"]["subthemes"][0]["id"] == "modeles"
    assert f["domains"] == [{"id": "ia", "name": DOM["name"]}]
    publish(tmp_path, build_home(cfg(), {"ia": []}, NOW), [], [f])
    assert json.loads((tmp_path / "site" / "data" / "universes" / "ia.json").read_text("utf-8"))["events"][0]["id"] == "b"
```

- [ ] **Step 3 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_today.py tests/test_publish_socle.py -q`
Expected: FAIL (`No module named 'engine.today'`, `cannot import name 'build_universe'`).

- [ ] **Step 4 : écrire `engine/today.py`**

```python
"""« Ce qu'il faut savoir aujourd'hui » : plancher par univers, puis meilleurs scores du jour (spec §6)."""
from collections import Counter
from datetime import datetime, timedelta

from .timeutil import parse


def day_score(ev: dict, now: datetime, t: dict) -> float:
    score = ev["importance"]
    if now - parse(ev["first_seen"]) <= timedelta(hours=24):
        score += t["novelty_bonus"]
    if ev["rev"] > 1 and now - parse(ev["updated_at"]) <= timedelta(hours=12):
        score += t["evolution_bonus"]
    return score


def build_today(events: list, universes: dict, g: dict, now: datetime) -> list[dict]:
    t = g["today"]
    cutoff = now - timedelta(hours=t["window_hours"])
    pool = sorted((e for e in events if e.get("level", 0) >= 1 and e.get("universe") in universes
                   and parse(e["updated_at"]) >= cutoff), key=lambda e: (-day_score(e, now, t), e["id"]))
    picked = {u: [] for u in universes}
    per_entity, chosen = Counter(), set()

    def take(e: dict) -> None:
        lead = (e.get("entity_ids") or [None])[0]
        if e["id"] in chosen or (lead and per_entity[lead] >= t["max_per_entity"]):
            return
        chosen.add(e["id"])
        picked[e["universe"]].append(e["id"])
        if lead:
            per_entity[lead] += 1

    for u in universes:
        for e in pool:
            if len(picked[u]) >= t["floor"]:
                break
            if e["universe"] == u:
                take(e)
    for e in pool:
        if len(chosen) >= t["total"]:
            break
        take(e)
    rank = {e["id"]: n for n, e in enumerate(pool)}
    return [{"id": u, "name": uni["name"], "short": uni["short"], "color": uni["color"],
             "ids": sorted(picked[u], key=rank.__getitem__)} for u, uni in universes.items()]
```

- [ ] **Step 5 : modifier `engine/publish.py`**

Ajouter l'import `from .today import build_today`. Après `_PUBLIC`, ajouter :

```python
_OPTIONAL = ("universe", "entity_ids", "title_fr", "image", "concerned")
```

Dans `project`, juste avant `return p`, ajouter :

```python
    p.update({k: ev[k] for k in _OPTIONAL if ev.get(k) is not None})
```

Remplacer la fin de `build_home` (à partir de `level_one = ...`) par :

```python
    level_one = sorted((e for e in events.values() if e["level"] == 1), key=lambda e: -e["importance"])
    out = {"generated_at": iso(now), "sample": False, "domains": domains,
           "retain": [e["id"] for e in level_one[: h["retain_max"]]], "events": events}
    if cfg.get("universes"):
        flat = [e for evs in events_by_domain.values() for e in evs]
        by_id = {e["id"]: e for e in flat}
        today = build_today(flat, cfg["universes"], cfg["global"], now)
        events.update({i: project(by_id[i]) for band in today for i in band["ids"]})
        out["today"] = today
    return out
```

Après `learn_card`, ajouter :

```python
def build_universe(uni: dict, domains: dict, events_by_domain: dict, now: datetime,
                   agendas: dict | None = None, limit: int = 150) -> dict:
    cutoff = now - timedelta(days=7)
    evs = sorted((e for d in uni["domains"] for e in events_by_domain.get(d, [])
                  if e["level"] >= 1 and parse(e["updated_at"]) >= cutoff), key=lambda e: (-e["importance"], e["id"]))
    upcoming = sorted(({**u, "domain": d} for d in uni["domains"] if d in domains
                       for u in upcoming_events(domains[d], now, (agendas or {}).get(d))),
                      key=lambda u: (u["date"], u["title"]))[:12]
    meta = {k: uni[k] for k in ("id", "name", "short", "color", "order")}
    return {"generated_at": iso(now), "universe": {**meta, "subthemes": uni.get("subthemes", [])},
            "domains": [{"id": d, "name": domains[d]["name"]} for d in uni["domains"] if d in domains],
            "events": [project(e) for e in evs[:limit]], "upcoming": upcoming}
```

Remplacer `publish` :

```python
def publish(root: Path, home: dict, domain_files: list, universe_files: list | tuple = ()) -> None:
    validate("home", home)
    for d in domain_files:
        validate("domainFile", d)
    for u in universe_files:
        validate("universeFile", u)
    out = root / "site" / "data"
    write_if_changed(out / "home.json", home)
    for d in domain_files:
        write_if_changed(out / "domains" / f"{d['domain']['id']}.json", d)
    for u in universe_files:
        write_if_changed(out / "universes" / f"{u['universe']['id']}.json", u)
```

Dans `engine/search.py`, remplacer `_entry` :

```python
def _entry(ev: dict) -> dict:
    best = min(ev["items"], key=lambda i: (i["tier"], i["published_at"]))
    entry = {"id": ev["id"], "domain": ev["domain"], "title": ev["title"],
             "retenir": (ev.get("summary") or {}).get("retenir", ""), "entities": ev.get("entities", []),
             "date": ev["updated_at"], "level": ev["level"], "reliability": ev["reliability"],
             "source": best["source"], "url": best["url"]}
    return {**entry, **{k: ev[k] for k in ("universe", "entity_ids", "title_fr", "image") if ev.get(k) is not None}}
```

- [ ] **Step 6 : vérifier**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe.

- [ ] **Step 7 : commit**

```bash
git add -A
git commit -m "feat: contrat étendu, sélection du jour et fichiers d'univers" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8 : fiches entités et index

**Files:**
- Create: `engine/entity_pages.py`, `tests/test_entity_pages.py`
- Modify: `engine/publish.py`

**Interfaces:**
- Consumes : `TYPES` (tâche 1), `adjacency` (tâche 6), `search._entry` (tâche 7), faits `{id: {"description","image","facts","edges"}}` (tâche 9, dictionnaire vide avant).
- Produces : `build_entity_pages(catalog, facts, adj, events, quotes, now, days=30, max_events=40, max_relations=40) -> tuple[dict, dict]` ; `publish_entities(root, index, pages)` écrit `site/data/entities/index.json` et `site/data/entities/<type>/<slug>.json`.

- [ ] **Step 1 : écrire les tests**

`tests/test_entity_pages.py` :

```python
import json
from datetime import timedelta

from engine.contract import validate
from engine.entity_pages import build_entity_pages
from engine.graph import adjacency, build_edges
from engine.publish import publish_entities
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item

CAT = {
    "company:openai": {"id": "company:openai", "name": "OpenAI", "type": "company", "aliases": ["openai"], "universes": ["ia"], "wikidata": "Q1"},
    "ai_model:gpt": {"id": "ai_model:gpt", "name": "GPT", "type": "ai_model", "aliases": ["=GPT", "chatgpt"], "universes": ["ia"], "quote": "GPT-X"},
}
QUOTES = {"quotes": [{"symbol": "GPT-X", "name": "x", "group": "g", "price": 1.5, "change": 0.1, "change_pct": 2.0,
                      "currency": "USD", "as_of": iso(NOW), "stale": False}]}


def ev(id, ids, hours=1, level=1):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}")], id=id, updated_at=iso(NOW - timedelta(hours=hours)))
    return {**e, "importance": 70, "level": level, "reliability": "confirmé", "entity_ids": ids, "universe": "ia"}


def test_index_and_pages_gather_events_relations_facts_and_quote():
    adj = adjacency(build_edges([("company:openai", "produit", "ai_model:gpt")], [], []))
    facts = {"company:openai": {"description": "entreprise d'IA", "image": "https://commons.wikimedia.org/x.png",
                                "facts": [{"label": "Création", "value": "2015"}], "edges": []}}
    events = [ev("a", ["company:openai"], hours=5), ev("b", ["company:openai", "ai_model:gpt"], hours=1),
              ev("old", ["company:openai"], hours=24 * 40), ev("l0", ["company:openai"], level=0)]
    index, pages = build_entity_pages(CAT, facts, adj, events, QUOTES, NOW)
    validate("entityIndex", index)
    assert {e["id"]: e["n30"] for e in index["entities"]} == {"ai_model:gpt": 1, "company:openai": 2}
    assert next(e for e in index["entities"] if e["id"] == "ai_model:gpt")["aliases"] == ["GPT", "chatgpt"]
    assert next(e for e in index["entities"] if e["id"] == "company:openai")["image"] == "https://commons.wikimedia.org/x.png"
    page = pages["company:openai"]
    validate("entityFile", page)
    assert [e["id"] for e in page["events"]] == ["b", "a"]
    assert page["relations"] == [{"id": "ai_model:gpt", "name": "GPT", "type": "ai_model", "label": "produit", "origin": "config", "weight": 1}]
    assert page["description"] == "entreprise d'IA" and page["facts"][0]["value"] == "2015"
    assert page["entity"] == {"id": "company:openai", "name": "OpenAI", "type": "company", "type_label": "Entreprise", "universes": ["ia"], "wikidata": "Q1"}
    gpt = pages["ai_model:gpt"]
    validate("entityFile", gpt)
    assert gpt["quote"]["change_pct"] == 2.0 and gpt["relations"][0]["label"] == "produit par" and gpt["image"] is None


def test_cooccurrence_relations_come_after_written_ones_and_unknown_neighbours_are_dropped():
    edges = build_edges([("company:openai", "produit", "ai_model:gpt")],
                        [{"src": "company:openai", "verb": "lie_a", "dst": "company:inconnue", "weight": 9, "origin": "cooccurrence"}], [])
    _, pages = build_entity_pages(CAT, {}, adjacency(edges), [], None, NOW)
    assert [r["id"] for r in pages["company:openai"]["relations"]] == ["ai_model:gpt"]


def test_pages_are_written_by_type_and_slug(tmp_path):
    index, pages = build_entity_pages(CAT, {}, {}, [], None, NOW)
    publish_entities(tmp_path, index, pages)
    data = tmp_path / "site" / "data" / "entities"
    assert json.loads((data / "company" / "openai.json").read_text("utf-8"))["entity"]["name"] == "OpenAI"
    assert len(json.loads((data / "index.json").read_text("utf-8"))["entities"]) == 2
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_entity_pages.py -q`
Expected: FAIL, `No module named 'engine.entity_pages'`.

- [ ] **Step 3 : écrire `engine/entity_pages.py`**

```python
"""Index des entités (recherche, pastilles) et fiche de chaque entité (spec §7)."""
from collections import defaultdict
from datetime import datetime, timedelta

from .catalog import TYPES
from .search import _entry
from .timeutil import iso, parse


def _page(eid: str, ent: dict, fact: dict, rels: list, evs: list, catalog: dict, now: datetime) -> dict:
    return {
        "generated_at": iso(now),
        "entity": {"id": eid, "name": ent["name"], "type": ent["type"], "type_label": TYPES[ent["type"]],
                   "universes": ent["universes"], **{k: ent[k] for k in ("ticker", "wikidata") if ent.get(k)}},
        "description": fact.get("description"), "image": fact.get("image"), "facts": fact.get("facts", []),
        "relations": [{"id": r["id"], "name": catalog[r["id"]]["name"], "type": catalog[r["id"]]["type"],
                       "label": r["label"], "origin": r["origin"], "weight": r["weight"]} for r in rels],
        "events": [_entry(e) for e in evs],
    }


def build_entity_pages(catalog: dict, facts: dict, adj: dict, events: list, quotes: dict | None, now: datetime,
                       days: int = 30, max_events: int = 40, max_relations: int = 40) -> tuple[dict, dict]:
    cutoff = now - timedelta(days=days)
    recent = sorted((e for e in events if e.get("level", 0) >= 1 and parse(e["updated_at"]) >= cutoff),
                    key=lambda e: e["updated_at"], reverse=True)
    by_entity = defaultdict(list)
    for e in recent:
        for eid in e.get("entity_ids", []):
            by_entity[eid].append(e)
    by_symbol = {q["symbol"]: q for q in (quotes or {}).get("quotes", [])}
    index, pages = [], {}
    for eid, ent in sorted(catalog.items()):
        fact, evs = (facts or {}).get(eid, {}), by_entity.get(eid, [])
        index.append({"id": eid, "name": ent["name"], "type": ent["type"], "universes": ent["universes"],
                      "aliases": [str(a).lstrip("=") for a in ent["aliases"][:4]], "n30": len(evs),
                      **({"image": fact["image"]} if fact.get("image") else {})})
        rels = sorted((r for r in adj.get(eid, []) if r["id"] in catalog),
                      key=lambda r: (r["origin"] == "cooccurrence", -r["weight"], r["id"]))[:max_relations]
        page = _page(eid, ent, fact, rels, evs[:max_events], catalog, now)
        quote = by_symbol.get(ent.get("quote"))
        if quote:
            page["quote"] = {k: quote[k] for k in ("price", "change_pct", "currency", "as_of", "stale")}
        pages[eid] = page
    return {"generated_at": iso(now), "types": TYPES, "entities": index}, pages
```

- [ ] **Step 4 : ajouter `publish_entities` à `engine/publish.py`**

```python
def publish_entities(root: Path, index: dict, pages: dict) -> None:
    validate("entityIndex", index)
    for page in pages.values():
        validate("entityFile", page)
    out = root / "site" / "data" / "entities"
    write_if_changed(out / "index.json", index)
    for eid, page in pages.items():
        etype, name = eid.split(":", 1)
        write_if_changed(out / etype / f"{name}.json", page)
```

- [ ] **Step 5 : vérifier**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe.

- [ ] **Step 6 : commit**

```bash
git add -A
git commit -m "feat: fiches entités et index des entités" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9 : faits Wikidata et PIB, identifiants du catalogue

**Files:**
- Create: `engine/facts.py`, `engine/wikidata_ids.py`, `tools/resolve_wikidata.py`, `tests/test_facts.py`, `tests/test_wikidata_ids.py`
- Modify: `config/entities/*.yml` (ajout des `wikidata:` par l'outil)

**Interfaces:**
- Consumes : catalogue (tâches 1-2).
- Produces : `WIKIDATA`, `fetch_json(url, params=None)`, `collect_facts(catalog, fetch=fetch_json) -> dict`, `with_gdp(facts, fetch=fetch_json) -> tuple[dict, list[str]]`, `refresh_facts(root, catalog, now, fetch=fetch_json) -> tuple[dict, dict | None]`, `load_facts(root) -> dict`. Fichier `data/facts/entities.json` = `{"checked_at", "qids", "entities": {id: {"description","image","facts","edges","iso2"?}}}`. `pick(results, etype)`, `insert_qid(text, eid, qid)`, `HINTS`.

- [ ] **Step 1 : écrire les tests**

`tests/test_facts.py` :

```python
import json
from datetime import timedelta

from engine.facts import collect_facts, load_facts, refresh_facts, with_gdp
from tests.helpers import NOW

CAT = {
    "country:france": {"type": "country", "wikidata": "Q142"},
    "person:emmanuel-macron": {"type": "person", "wikidata": "Q3052772"},
    "org:otan": {"type": "org", "wikidata": "Q7184"},
    "company:sans-qid": {"type": "company"},
    "company:disparue": {"type": "company", "wikidata": "Q999"},
}


def ref(q, rank="normal", end=False):
    claim = {"rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"type": "wikibase-entityid", "value": {"id": q}}}}
    return {**claim, "qualifiers": {"P582": [{}]}} if end else claim


def val(kind, value, rank="normal"):
    return {"rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"type": kind, "value": value}}}


def item(label, claims=None, desc=None):
    return {"labels": {"fr": {"value": label}}, "descriptions": {"fr": {"value": desc}} if desc else {}, "claims": claims or {}}


ENTITIES = {
    "Q142": item("France", desc="pays d'Europe de l'Ouest", claims={
        "P36": [ref("Q90")],
        "P1082": [val("quantity", {"amount": "+68400000"})],
        "P35": [ref("Q1", end=True), ref("Q3052772")],
        "P38": [ref("Q4916"), ref("Q181", rank="deprecated")],
        "P463": [ref("Q7184")],
        "P41": [val("string", "Flag of France.svg")],
        "P297": [val("string", "FR")],
        "P6": [{"rank": "normal", "mainsnak": {"snaktype": "somevalue"}}],
    }),
    "Q3052772": item("Emmanuel Macron", claims={"P569": [val("time", {"time": "+1977-12-21T00:00:00Z", "precision": 11})],
                                                "P27": [ref("Q142")]}),
    "Q7184": item("OTAN", claims={"P571": [val("time", {"time": "+1949-04-04T00:00:00Z", "precision": 9})]}),
    "Q90": item("Paris"), "Q4916": item("euro"), "Q1": item("Ancien président"), "Q181": item("franc"),
}


def fake(entities=ENTITIES, calls=None):
    def fetch(url, params=None):
        if calls is not None:
            calls.append(url)
        if "wikidata" in url:
            return {"entities": {i: entities.get(i, {"id": i, "missing": ""}) for i in params["ids"].split("|")}}
        raise ConnectionError(url)
    return fetch


def test_facts_are_labelled_formatted_current_and_linked():
    facts = collect_facts(CAT, fake())
    fr = facts["country:france"]
    assert fr["description"] == "pays d'Europe de l'Ouest" and fr["iso2"] == "FR"
    assert fr["image"] == "https://commons.wikimedia.org/wiki/Special:FilePath/Flag_of_France.svg?width=480"
    values = {f["label"]: f["value"] for f in fr["facts"]}
    assert values == {"Capitale": "Paris", "Population": "68,4 millions", "Chef de l'État": "Emmanuel Macron", "Monnaie": "euro"}
    assert {"src": "person:emmanuel-macron", "verb": "dirige", "dst": "country:france", "weight": 1, "origin": "wikidata"} in fr["edges"]
    assert {"src": "country:france", "verb": "membre_de", "dst": "org:otan", "weight": 1, "origin": "wikidata"} in fr["edges"]
    macron = {f["label"]: f["value"] for f in facts["person:emmanuel-macron"]["facts"]}
    assert macron == {"Naissance": "21 décembre 1977", "Nationalité": "France"}
    assert {f["label"]: f["value"] for f in facts["org:otan"]["facts"]} == {"Création": "1949"}
    assert "company:disparue" not in facts and "company:sans-qid" not in facts


def test_gdp_is_added_and_failures_are_reported():
    base = {"country:france": {"facts": [], "iso2": "FR", "edges": []}}
    def bank(url, params=None):
        assert params["mrnev"] == 1
        return [{"page": 1}, [{"value": 3.05e12, "date": "2024"}]]
    facts, errors = with_gdp(base, bank)
    assert facts["country:france"]["facts"] == [{"label": "PIB", "value": "3 050 Md$ (2024)"}] and errors == []
    facts, errors = with_gdp(base, fake())
    assert facts == base and len(errors) == 1


def test_refresh_is_weekly_and_keeps_the_old_facts_when_wikidata_fails(tmp_path):
    calls = []
    facts, health = refresh_facts(tmp_path, CAT, NOW, fake(calls=calls))
    assert "country:france" in facts and health["ok"] is False          # la Banque mondiale échoue ici (faux réseau)
    n = len(calls)
    assert refresh_facts(tmp_path, CAT, NOW + timedelta(days=1), fake(calls=calls))[0] == facts and len(calls) == n
    def down(url, params=None):
        raise ConnectionError("Wikidata injoignable")
    kept, health = refresh_facts(tmp_path, CAT, NOW + timedelta(days=8), down)
    assert kept == facts and health["ok"] is False and "injoignable" in health["error"]
    assert load_facts(tmp_path) == facts
    stored = json.loads((tmp_path / "data" / "facts" / "entities.json").read_text("utf-8"))
    assert stored["qids"] == ["Q142", "Q3052772", "Q7184", "Q999"]


def test_no_wikidata_id_means_no_network_call(tmp_path):
    def never(url, params=None):
        raise AssertionError("aucun appel attendu")
    assert refresh_facts(tmp_path, {"company:x": {"type": "company"}}, NOW, never) == ({}, None)
```

`tests/test_wikidata_ids.py` :

```python
from engine.wikidata_ids import insert_qid, pick


def test_pick_takes_the_first_result_whose_description_fits_the_type():
    results = [{"id": "Q1", "description": "fruit"}, {"id": "Q312", "description": "entreprise américaine"}]
    assert pick(results, "company") == "Q312" and pick(results, "country") is None and pick([], "company") is None


def test_insert_qid_adds_the_id_once_after_the_entity_id():
    text = "- {id: company:apple, name: Apple, aliases: [x]}\n- {id: company:applex, name: X, aliases: [y]}\n"
    once = insert_qid(text, "company:apple", "Q312")
    assert once.splitlines()[0] == "- {id: company:apple, wikidata: Q312, name: Apple, aliases: [x]}"
    assert once.splitlines()[1] == "- {id: company:applex, name: X, aliases: [y]}"
    assert insert_qid(once, "company:apple", "Q999") == once
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_facts.py tests/test_wikidata_ids.py -q`
Expected: FAIL (`No module named 'engine.facts'`, `'engine.wikidata_ids'`).

- [ ] **Step 3 : écrire `engine/facts.py`**

```python
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
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
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
        eid = by_qid[qid]
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
        if f.get("iso2"):
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
```

- [ ] **Step 4 : écrire `engine/wikidata_ids.py` et `tools/resolve_wikidata.py`**

`engine/wikidata_ids.py` :

```python
"""Aide ponctuelle pour renseigner les identifiants Wikidata du catalogue (hors cycle)."""
import re

# Mots attendus dans la description Wikidata (fr ou en), par type d'entité.
HINTS = {
    "company": ("entreprise", "société", "company", "groupe", "constructeur", "fabricant", "manufacturer", "corporation",
                "conglomérat", "banque", "bank", "multinational", "start-up", "startup", "laboratoire", "business"),
    "country": ("pays", "country", "état", "state", "république", "republic", "royaume", "kingdom", "territoire", "territory"),
    "org": ("organisation", "organization", "organisme", "alliance", "union", "fonds", "fund", "banque", "bank", "cour",
            "court", "agence", "agency", "groupe", "group", "mouvement", "movement", "parti", "commission", "parlement",
            "parliament", "comité", "committee", "fédération", "federation", "association", "forum", "conseil",
            "council", "institution", "régulateur", "regulator"),
    "central_bank": ("banque centrale", "central bank", "réserve", "reserve"),
    "person": ("homme", "femme", "politique", "politician", "président", "president", "entrepreneur", "businessman",
               "businesswoman", "chef", "dirigeant", "économiste", "economist", "informaticien", "computer scientist",
               "investisseur", "investor", "diplomate", "diplomat", "ministre", "minister", "ingénieur", "engineer",
               "banquier", "banker", "juriste", "lawyer", "monarque", "leader", "guide suprême", "supreme leader"),
    "player": ("joueur", "joueuse", "player", "footballeur", "footballer", "tennisman", "tennis", "basketteur",
               "basketball", "volleyeur", "volleyball"),
    "driver": ("pilote", "racing driver", "driver"),
    "team": ("club", "équipe", "team", "écurie", "franchise", "constructor"),
    "competition": ("compétition", "competition", "championnat", "championship", "tournoi", "tournament", "coupe", "cup",
                    "ligue", "league", "grand chelem", "grand slam", "jeux", "games", "course", "race", "series"),
    "crypto": ("cryptomonnaie", "cryptocurrency", "monnaie", "currency", "blockchain", "stablecoin", "jeton", "token"),
    "ai_model": ("modèle", "model", "chatbot", "agent conversationnel", "logiciel", "software", "intelligence artificielle",
                 "artificial intelligence", "assistant", "générat", "generat"),
    "index": ("indice", "index", "stock market"),
}


def pick(results: list[dict], etype: str) -> str | None:
    hints = HINTS.get(etype, ())
    return next((r["id"] for r in results if any(h in str(r.get("description", "")).lower() for h in hints)), None)


def insert_qid(text: str, eid: str, qid: str) -> str:
    return re.sub(rf"\{{id: {re.escape(eid)}, (?!wikidata)", "{id: " + eid + ", wikidata: " + qid + ", ", text, count=1)
```

`tools/resolve_wikidata.py` :

```python
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
```

- [ ] **Step 5 : vérifier les tests**

Run: `.venv/Scripts/python -m pytest tests/test_facts.py tests/test_wikidata_ids.py -q`
Expected: PASS.

- [ ] **Step 6 : renseigner les identifiants du catalogue**

Run: `.venv/Scripts/python tools/resolve_wikidata.py`
Expected: une ligne par entité (`identifiant  Qxxx  description`). Relire chaque description : elle doit correspondre à l'entité (ex. `country:mali` → « pays d'Afrique de l'Ouest », pas une ville ; `team:om` → le club de football). Noter les erreurs.

Run: `.venv/Scripts/python tools/resolve_wikidata.py --write`
Puis, dans `config/entities/*.yml`, corriger à la main chaque identifiant erroné noté, et ajouter celui des entités non résolues quand il s'agit d'un pays, d'une organisation, d'une personne, d'une entreprise ou d'une banque centrale (recherche sur wikidata.org). Les équipes, joueurs, pilotes et compétitions non résolus peuvent rester sans identifiant (lot Sport).

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe (un identifiant mal formé ferait échouer `load_config`).

- [ ] **Step 7 : commit**

```bash
git add -A
git commit -m "feat: faits Wikidata et PIB hebdomadaires, identifiants Wikidata du catalogue" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10 : bandeau Vigie

**Files:**
- Create: `engine/band.py`, `tests/test_band.py`

**Interfaces:**
- Consumes : `quotes.json`, `football.json`, `f1.json` publiés, `home` (avec `events` portant `universe`, `title_fr`), `uni_of: {domaine: univers}`, `g["band"]`.
- Produces : `build_band(quotes, football, f1, home, uni_of, g, now) -> dict` conforme à `band`.

- [ ] **Step 1 : écrire les tests**

`tests/test_band.py` :

```python
from datetime import timedelta

from engine.band import build_band
from engine.contract import validate
from engine.timeutil import iso
from tests.helpers import NOW

G = {"band": {"quotes": ["^FCHI", "^TNX", "ABSENT"], "new_hours": 6, "max_new": 4, "agenda_days": 3, "max_agenda": 4, "max_matches": 6}}


def quote(symbol, name, group, change, pct):
    return {"symbol": symbol, "name": name, "group": group, "price": 1.0, "change": change, "change_pct": pct,
            "currency": "EUR", "as_of": iso(NOW), "stale": False}


def test_band_orders_news_agenda_matches_race_then_markets():
    home = {"events": {"n": {"id": "n", "level": 1, "universe": "ia", "title": "T", "title_fr": "Titre", "first_seen": iso(NOW - timedelta(hours=1))},
                       "old": {"id": "old", "level": 1, "universe": "ia", "title": "Vieux", "first_seen": iso(NOW - timedelta(hours=10))},
                       "l2": {"id": "l2", "level": 2, "universe": "ia", "title": "Moins", "first_seen": iso(NOW)}},
            "domains": [{"id": "finance", "upcoming": [{"date": "2026-09-28", "title": "Réunion BCE"}, {"date": "2026-10-20", "title": "Loin"}]},
                        {"id": "inconnu", "upcoming": [{"date": "2026-09-27", "title": "Hors univers"}]}]}
    football = {"fixtures": [{"home": "PSG", "away": "OM", "date": iso(NOW + timedelta(hours=8))},
                             {"home": "A", "away": "B", "date": iso(NOW + timedelta(days=4))}],
                "results": [{"home": "Lens", "away": "Lille", "date": iso(NOW - timedelta(hours=3)), "home_score": 2, "away_score": 1}]}
    f1 = {"next": {"name": "GP", "sessions": [{"name": "Qualifications", "start": iso(NOW + timedelta(days=1))},
                                              {"name": "Course", "start": iso(NOW + timedelta(days=2))}]}}
    quotes = {"quotes": [quote("^FCHI", "CAC 40", "Indices", 30.0, 0.4), quote("^TNX", "Taux US 10 ans", "Taux", -0.05, -1.2)]}
    band = build_band(quotes, football, f1, home, {"finance": "finance"}, G, NOW)
    validate("band", band)
    assert [(i["kind"], i["label"]) for i in band["items"]] == [
        ("new", "Titre"), ("agenda", "Réunion BCE"), ("match", "PSG – OM"), ("match", "Lens – Lille"),
        ("race", "GP"), ("quote", "CAC 40"), ("quote", "Taux US 10 ans")]
    items = band["items"]
    assert items[0]["href"] == "#/e/n" and items[3]["value"] == "2–1"
    assert (items[5]["delta"], items[5]["unit"]) == (0.4, "%") and (items[6]["delta"], items[6]["unit"]) == (-0.05, "pt")


def test_band_survives_missing_data():
    band = build_band(None, None, None, {"events": {}, "domains": []}, {}, G, NOW)
    validate("band", band)
    assert band["items"] == []
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_band.py -q`
Expected: FAIL, `No module named 'engine.band'`.

- [ ] **Step 3 : écrire `engine/band.py`**

```python
"""Bandeau Vigie : une ligne de repères, tous univers confondus (nouveautés, agenda, matchs, Grand Prix, marchés)."""
from datetime import datetime, timedelta

from .timeutil import iso, parse


def _item(universe: str, kind: str, label: str, value: object = None, delta: float | None = None,
          unit: str | None = None, at: str | None = None, href: str | None = None) -> dict:
    return {"universe": universe, "kind": kind, "label": label, "value": value, "delta": delta, "unit": unit, "at": at, "href": href}


def _news(home: dict, cfg: dict, now: datetime) -> list[dict]:
    fresh = sorted((e for e in home.get("events", {}).values() if e["level"] == 1 and e.get("universe")
                    and now - parse(e["first_seen"]) <= timedelta(hours=cfg["new_hours"])),
                   key=lambda e: e["first_seen"], reverse=True)
    return [_item(e["universe"], "new", e.get("title_fr") or e["title"], href=f"#/e/{e['id']}") for e in fresh][: cfg["max_new"]]


def _agenda(home: dict, uni_of: dict, cfg: dict, now: datetime) -> list[dict]:
    horizon = (now + timedelta(days=cfg["agenda_days"])).date().isoformat()
    rows = sorted(((u, d["id"]) for d in home.get("domains", []) if d["id"] in uni_of for u in d.get("upcoming", [])
                   if u["date"] <= horizon), key=lambda x: (x[0]["date"], x[0]["title"]))
    return [_item(uni_of[dom], "agenda", u["title"], at=u["date"]) for u, dom in rows][: cfg["max_agenda"]]


def _matches(football: dict | None, cfg: dict, now: datetime) -> list[dict]:
    fb = football or {}
    upcoming = [_item("sport", "match", f"{m['home']} – {m['away']}", at=m["date"], href="#/u/sport/foot")
                for m in fb.get("fixtures", []) if now <= parse(m["date"]) <= now + timedelta(hours=36)]
    played = [_item("sport", "match", f"{m['home']} – {m['away']}", value=f"{m['home_score']}–{m['away_score']}",
                    at=m["date"], href="#/u/sport/foot")
              for m in fb.get("results", []) if m.get("home_score") is not None
              and now - timedelta(hours=18) <= parse(m["date"]) <= now]
    return [*upcoming, *played][: cfg["max_matches"]]


def _race(f1: dict | None, now: datetime) -> list[dict]:
    nxt = (f1 or {}).get("next") or {}
    race = next((s for s in nxt.get("sessions", []) if s["name"] == "Course"), None)
    if race and now <= parse(race["start"]) <= now + timedelta(days=7):
        return [_item("sport", "race", nxt["name"], at=race["start"], href="#/u/sport/f1")]
    return []


def _quotes(quotes: dict | None, cfg: dict) -> list[dict]:
    by_symbol = {q["symbol"]: q for q in (quotes or {}).get("quotes", [])}
    out = []
    for q in (by_symbol[s] for s in cfg["quotes"] if s in by_symbol):
        rate = q["group"] == "Taux"
        out.append(_item("finance", "quote", q["name"], value=q["price"], delta=q["change"] if rate else q["change_pct"],
                         unit="pt" if rate else "%", at=q["as_of"], href="#/u/finance"))
    return out


def build_band(quotes: dict | None, football: dict | None, f1: dict | None, home: dict, uni_of: dict,
               g: dict, now: datetime) -> dict:
    cfg = g["band"]
    items = [*_news(home, cfg, now), *_agenda(home, uni_of, cfg, now), *_matches(football, cfg, now),
             *_race(f1, now), *_quotes(quotes, cfg)]
    return {"generated_at": iso(now), "items": items}
```

- [ ] **Step 4 : vérifier**

Run: `.venv/Scripts/python -m pytest tests/test_band.py -q`
Expected: PASS.

- [ ] **Step 5 : commit**

```bash
git add -A
git commit -m "feat: bandeau Vigie" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11 : branchement dans le cycle

**Files:**
- Modify: `engine/run.py`
- Create: `tests/test_run_socle.py`

**Interfaces:**
- Consumes : tout ce qui précède.
- Produces : `annotate(ev, universe, matcher) -> dict` ; `add_summaries` qui renseigne `title_fr`, `llm_offered`, `llm_entities`, `unknown` et **ne remplace jamais un résumé LLM par un extractif** ; `run(..., facts_fetch=fetch_json)` qui publie `universes/*.json`, `entities/**`, `band.json`, `home.today`, `data/candidates.json`, `data/facts/entities.json` ; `report["entities"] = {"linked_pct": int, "candidates": int}` ; `health.json` gagne `candidates`.

- [ ] **Step 1 : écrire les tests**

`tests/test_run_socle.py` :

```python
import json

import yaml

from engine.contract import validate
from engine.run import add_summaries, run
from tests.helpers import DOM, G, NOW, mk_event, mk_item
from tests.test_run import fake_fetch, setup

UNI = {"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "order": 1, "domains": ["ia"], "subthemes": []}
ENTITIES = [{"id": "company:openai", "name": "OpenAI", "aliases": ["openai"], "universes": ["ia"], "wikidata": "Q1"},
            {"id": "ai_model:gpt", "name": "GPT", "aliases": ["gpt-6"], "universes": ["ia"]}]
KEYS = ("quoi", "qui", "quand", "pourquoi", "retenir")


def setup_socle(tmp_path):
    setup(tmp_path)
    for rel, data in (("universes/ia.yml", UNI), ("entities/ia.yml", ENTITIES),
                      ("relations.yml", [["company:openai", "produit", "ai_model:gpt"]])):
        path = tmp_path / "config" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")


def no_facts(url, params=None):
    raise ConnectionError("Wikidata injoignable")


def data(tmp_path, name):
    return json.loads((tmp_path / "site" / "data" / name).read_text("utf-8"))


def test_run_publishes_universes_entities_band_and_today(tmp_path):
    setup_socle(tmp_path)
    report = run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    uni = data(tmp_path, "universes/ia.json")
    validate("universeFile", uni)
    ev = uni["events"][0]
    assert ev["universe"] == "ia" and ev["entity_ids"] == ["company:openai", "ai_model:gpt"] and "concerned" not in ev
    home = data(tmp_path, "home.json")
    validate("home", home)
    assert home["today"][0]["ids"] == [ev["id"]]
    page = data(tmp_path, "entities/company/openai.json")
    validate("entityFile", page)
    assert page["events"][0]["id"] == ev["id"] and page["relations"][0]["id"] == "ai_model:gpt"
    validate("entityIndex", data(tmp_path, "entities/index.json"))
    validate("band", data(tmp_path, "band.json"))
    health = data(tmp_path, "health.json")
    assert any(s["source"] == "facts:wikidata" and not s["ok"] for s in health["sources"]) and health["candidates"] == []
    assert report["entities"] == {"linked_pct": 100, "candidates": 0}


def test_llm_title_confirmed_entities_and_unknown_names(tmp_path):
    setup_socle(tmp_path)

    def call(prompt):
        ev_id = prompt.split("## ")[1].split("\n")[0]
        assert "Entités candidates : company:openai, ai_model:gpt" in prompt
        return json.dumps({ev_id: {**{k: f"llm {k}" for k in KEYS}, "titre": "OpenAI lance GPT-6",
                                   "entites": ["ai_model:gpt"], "inconnus": ["Sam Altman", "OpenAI"]}})

    run(tmp_path, now=NOW, fetch=fake_fetch, call=call, facts_fetch=no_facts)
    ev = data(tmp_path, "universes/ia.json")["events"][0]
    assert ev["title_fr"] == "OpenAI lance GPT-6" and ev["entity_ids"] == ["ai_model:gpt"]
    candidates = json.loads((tmp_path / "data" / "candidates.json").read_text("utf-8"))["candidates"]
    assert list(candidates) == ["sam altman"]                   # « OpenAI » est déjà dans le catalogue
    assert data(tmp_path, "health.json")["candidates"][0]["name"] == "Sam Altman"


def test_second_identical_run_rewrites_no_published_file(tmp_path):
    setup_socle(tmp_path)
    run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    files = sorted((tmp_path / "site" / "data").rglob("*.json"))
    before = {p: p.read_bytes() for p in files}
    run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    assert {p: p.read_bytes() for p in files} == before


def test_a_quota_failure_keeps_the_previous_llm_summary():
    e = {**mk_event([mk_item("a", "T")], id="ev_q"), "importance": 80, "level": 1, "reliability": "confirmé",
         "summary": {"quoi": "ancien"}, "summary_mode": "llm", "summary_fp": "vieux", "title_fr": "Ancien titre"}

    def quota(prompt):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    events, touched, errors = add_summaries([e], DOM, G, quota)
    assert events[0] == e and touched == set() and errors == ["quota"]
```

- [ ] **Step 2 : vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_run_socle.py -q`
Expected: FAIL (`run()` ne connaît pas `facts_fetch`).

- [ ] **Step 3 : modifier `engine/run.py`**

Remplacer le bloc d'imports par :

```python
import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from .agenda import fetch_points
from .alerts import prune_sent, select_alerts, send_ntfy
from .band import build_band
from .candidates import top_candidates, update_candidates
from .catalog import football_teams
from .cluster import cluster, merge_events
from .collect import collect_source, fetch_bytes
from .config import ROOT, load_config
from .enrich import event_image, is_relevant
from .entity_pages import build_entity_pages
from .f1_data import collect_f1
from .f1_data import fetch_json as fetch_f1
from .facts import fetch_json as fetch_facts
from .facts import load_facts, refresh_facts
from .football_data import collect_football, fetch_fd
from .graph import adjacency, build_edges, concerned
from .linker import build_matcher, event_text, final_ids, link
from .normalize import dedupe, excluded, normalize, recent
from .publish import (build_domain, build_home, build_universe, publish, publish_entities, publish_football,
                      publish_json, publish_quotes, write_if_changed)
from .quotes import collect_quotes, fetch_relay
from .reliability import classify
from .score import assign_levels, importance
from .search import FULL_DAYS, build_index
from .store import append, load_recent
from .summarize import fingerprint, gemini_call, summarize
from .timeutil import iso, now_utc
```

Après `rescore`, ajouter :

```python
def annotate(ev: dict, universe: str | None, matcher: dict | None) -> dict:
    """Univers, entités candidates et photo : recalculés à chaque cycle à partir des articles de l'événement."""
    if universe is None or matcher is None:
        return ev
    image = event_image(ev)
    return {**ev, "universe": universe, "candidates": link(event_text(ev), matcher), **({"image": image} if image else {})}
```

Remplacer `add_summaries` :

```python
def add_summaries(events: list, dom: dict, g: dict, call: Callable[[str], str] | None) -> tuple[list, set, list]:
    need = sorted((e for e in events if e["level"] in (1, 2) and e.get("summary_fp") != fingerprint(e)),
                  key=lambda e: -e["importance"])[: g["ai"]["max_events_per_run"]]
    results, errors = summarize(need, call, profile=dom.get("summary_profile", "default"))
    done, touched = {}, set()
    for e in need:
        summary, mode = results[e["id"]]
        if mode == "extractif" and e.get("summary_mode") == "llm":
            continue                        # échec ou quota : on garde le résumé LLM, nouvel essai au cycle suivant
        summary = dict(summary)
        layers = summary.pop("layers", None)
        title_fr = summary.pop("title_fr", None)
        chosen = summary.pop("entities_llm", None)
        unknown = summary.pop("unknown", [])
        upd = {**e, "summary": summary, "summary_mode": mode, "layers": layers,
               "summary_fp": fingerprint(e) if mode == "llm" else None}
        if mode == "llm":
            offered = e.get("candidates", [])
            upd = {**upd, "title_fr": title_fr, "llm_offered": offered,
                   "llm_entities": offered if chosen is None else chosen, "unknown": unknown}
        done[e["id"]] = upd
        if (summary, mode, layers, upd.get("title_fr")) != (e.get("summary"), e.get("summary_mode"), e.get("layers"), e.get("title_fr")):
            touched.add(e["id"])
    return [done.get(e["id"], e) for e in events], touched, errors
```

Après `_read_json`, ajouter :

```python
def _with_concerned(ev: dict, adj: dict, catalog: dict) -> dict:
    if ev.get("level") in (1, 2) and ev.get("entity_ids"):
        chains = concerned(ev["entity_ids"], adj, catalog)
        if chains:
            return {**ev, "concerned": chains}
    return ev


def _facts(root: Path, catalog: dict, now: datetime, only: list[str] | None, fetch: Callable, health: list) -> dict:
    if only is not None:
        return load_facts(root)
    facts, entry = refresh_facts(root, catalog, now, fetch)
    if entry:
        health.append(entry)
    return facts


def _update_candidates(root: Path, unknown: list, catalog: dict, now: datetime) -> dict:
    path = root / "data" / "candidates.json"
    everything = build_matcher(catalog)
    data = update_candidates((_read_json(path) or {}).get("candidates", {}), unknown,
                             lambda name: bool(link(name, everything)), now)
    write_if_changed(path, {"candidates": data})
    return data


def _linked_pct(by_domain: dict) -> int:
    shown = [e for evs in by_domain.values() for e in evs if e.get("level", 0) >= 1 and "candidates" in e]
    return round(100 * sum(1 for e in shown if e.get("entity_ids")) / len(shown)) if shown else 0
```

Remplacer la fonction `run` entière par :

```python
def run(root: Path = ROOT, now: datetime | None = None, only: list[str] | None = None,
        call: Callable[[str], str] | None = None, fetch: Callable[[str], bytes] = fetch_bytes,
        quote_fetch: Callable[[str], dict] = fetch_relay,
        agenda_fetch: Callable[[str], list[str]] = fetch_points,
        football_token: str | None = None,
        football_fetch: Callable[[str, str], dict] = fetch_fd,
        f1_fetch: Callable[[str], dict] = fetch_f1,
        ntfy_topic: str | None = None,
        ntfy_post: Callable[..., object] = requests.post,
        facts_fetch: Callable[..., object] = fetch_facts) -> dict:
    now = now or now_utc()
    cfg = load_config(root)
    g, universes = cfg["global"], cfg["universes"]
    catalog = {**cfg["catalog"], **football_teams(_previous(root, "football.json"), cfg["catalog"], universes)}
    uni_of = {d: u for u, uni in universes.items() for d in uni["domains"]}
    matchers = {u: build_matcher(catalog, u) for u in universes}
    stored = load_recent(root, now)
    report = {"collected": 0, "new_items": 0, "events": {"1": 0, "2": 0, "3": 0}, "reliability": {},
              "ai": {"llm": 0, "extractif": 0, "errors": []}, "quotes": {"ok": 0, "failed": 0},
              "football": {"ok": 0, "failed": 0}, "f1": {"ok": 0, "failed": 0}, "alerts": 0,
              "entities": {"linked_pct": 0, "candidates": 0}, "sources_failed": []}
    health, by_domain, unknown = [], {}, []
    for dom in sorted(cfg["domains"].values(), key=lambda d: d["order"]):
        mine = [e for e in stored if e["domain"] == dom["id"]]
        changed, merges = set(), []
        if only is None or dom["id"] in only:
            items, h = collect_domain(dom, g, now, fetch)
            health += h
            fresh = dedupe(items, {i["id"] for e in mine for i in e["items"]})
            report["collected"] += len(items)
            report["new_items"] += len(fresh)
            mine, changed = cluster(fresh, mine, dom, g, now)
            mine, merges = merge_events(mine, dom, g, now)
            changed = (changed - {d["id"] for d, _ in merges}) | {sid for _, sid in merges}
        universe = uni_of.get(dom["id"])
        mine = [annotate(e, universe, matchers.get(universe)) for e in mine]
        mine = rescore(mine, dom, g, now)
        mine, touched, errors = add_summaries(mine, dom, g, call)
        mine = [{**e, "entity_ids": final_ids(e)} if "candidates" in e else e for e in mine]
        unknown += [(name, dom["id"]) for e in mine if e["id"] in touched for name in e.get("unknown", [])]
        append(root, [{**d, "merged_into": sid} for d, sid in merges]          # marqueur : l'absorbé ne revient pas
               + [e for e in mine if e["id"] in changed | touched], now)
        by_domain[dom["id"]] = mine
        _tally(report, mine, errors)
    history = {e["id"]: e for e in load_recent(root, now, days=FULL_DAYS)}
    history.update({e["id"]: e for evs in by_domain.values() for e in evs})       # niveaux du cycle en cours
    facts = _facts(root, catalog, now, only, facts_fetch, health)
    adj = adjacency(build_edges(cfg["relations"], [e for f in facts.values() for e in f.get("edges", [])],
                                list(history.values()), g.get("links", {}).get("cooccurrence_min", 3)))
    by_domain = {d: [_with_concerned(e, adj, catalog) for e in evs] for d, evs in by_domain.items()}
    agendas = _import_agendas(cfg, only, agenda_fetch, health)
    home = build_home(cfg, by_domain, now, agendas)
    publish(root, home, [build_domain(cfg["domains"][d], evs, now, agendas.get(d)) for d, evs in by_domain.items()],
            [build_universe(u, cfg["domains"], by_domain, now, agendas) for u in universes.values()])
    if cfg["quotes"] and (only is None or "quotes" in only):
        quotes, qhealth = collect_quotes(cfg["quotes"], _previous(root, "quotes.json"), now, quote_fetch)
        publish_quotes(root, quotes)
        health += qhealth
        symbols = [h for h in qhealth if h["source"] != "quote-relay"]
        report["quotes"] = {"ok": sum(h["ok"] for h in symbols), "failed": sum(not h["ok"] for h in qhealth)}
    publish_json(root, "search", "search.json", build_index(list(history.values()), cfg["domains"], now))
    if "f1" in cfg["domains"] and (only is None or "f1-data" in only or "f1" in only):
        f1, f1health = collect_f1(_previous(root, "f1.json"), now, f1_fetch)
        if f1 is not None:
            publish_json(root, "f1", "f1.json", f1)
        health += f1health
        report["f1"] = {"ok": sum(h["ok"] for h in f1health), "failed": sum(not h["ok"] for h in f1health)}
    if cfg["football"] and (only is None or "football-data" in only):
        data, fhealth = collect_football(cfg["football"], football_token, _previous(root, "football.json"), now, football_fetch)
        if data is not None:
            publish_football(root, data)
        health += fhealth
        report["football"] = {"ok": sum(h["ok"] for h in fhealth), "failed": sum(not h["ok"] for h in fhealth)}
    if universes:
        index, pages = build_entity_pages(catalog, facts, adj, list(history.values()), _previous(root, "quotes.json"), now)
        publish_entities(root, index, pages)
        publish_json(root, "band", "band.json", build_band(_previous(root, "quotes.json"), _previous(root, "football.json"),
                                                           _previous(root, "f1.json"), home, uni_of, g, now))
    candidates = _update_candidates(root, unknown, catalog, now)
    report["entities"] = {"linked_pct": _linked_pct(by_domain), "candidates": len(candidates)}
    if ntfy_topic and g.get("alerts"):
        report["alerts"] = _send_alerts(root, cfg, by_domain, now, ntfy_topic, ntfy_post, health)
    report["sources_failed"] = [h["source"] for h in health if not h["ok"]]
    write_if_changed(root / "site" / "data" / "health.json",
                     {"checked_at": iso(now), "sources": health, "ai": report["ai"], "candidates": top_candidates(candidates)},
                     now, max_age_min=55)
    return report
```

- [ ] **Step 4 : vérifier**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe, y compris `tests/test_run.py` inchangé (sans univers ni catalogue dans sa config temporaire, aucun nouveau fichier publié et aucun appel réseau).

Run: `cd site && node --test "tests/*.test.mjs"`
Expected: 0 échec (site inchangé).

- [ ] **Step 5 : essai local sans IA sur les vraies sources, sans football-data**

Run: `.venv/Scripts/python -m engine.run --no-ai --only ia finance geopolitique quotes`
Expected : rapport JSON avec `"entities": {"linked_pct": ...}` ; fichiers `site/data/universes/*.json`, `site/data/entities/index.json`, `site/data/band.json` présents. Ouvrir `site/data/universes/finance.json` et vérifier à l'œil 5 événements (entités plausibles, `concerned` présent sur au moins un événement pétrole ou puces si l'actualité en contient).
Puis annuler les données locales : `git checkout -- site/data data && git clean -fd site/data data`

- [ ] **Step 6 : commit**

```bash
git add -A
git commit -m "feat: univers, entités, faits, Concernés et bandeau dans le cycle" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12 : mesure sur données réelles et mise à jour de la spec

**Files:**
- Create: `tools/measure_links.py`, `docs/superpowers/measurements/lot-1a.md`
- Modify: `docs/superpowers/specs/2026-09-27-vigie-2-design.md`

- [ ] **Step 1 : écrire `tools/measure_links.py`**

```python
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
```

- [ ] **Step 2 : demander l'accord de mise en production**

Arrêt obligatoire : présenter à l'utilisateur le résumé des tâches 1 à 11 (tests verts, essai local) et **demander son accord** pour fusionner `feat/vigie-socle-a` dans `main` et pousser. Le site visible ne change pas ; seuls de nouveaux fichiers de données apparaissent. Sans accord, s'arrêter ici.

- [ ] **Step 3 : mise en production (après accord)**

```bash
git checkout main
git pull --rebase origin main
git merge --no-ff feat/vigie-socle-a -m "merge: socle de données Vigie 2 (lot 1A)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/Scripts/python -m pytest -q
git push origin main
gh workflow run pipeline.yml -R Adam2328/veille-plateforme
```

Attendre la fin du cycle (`gh run watch`), puis 2 à 3 cycles supplémentaires : le préfixe `v2|` fait résumer à nouveau les événements par lots de 30 par rubrique, et les faits Wikidata sont collectés au premier cycle. En cas de conflit sur `site/data/` ou `data/`, garder la version du robot.

- [ ] **Step 4 : mesurer**

```bash
git pull origin main
.venv/Scripts/python tools/measure_links.py > docs/superpowers/measurements/lot-1a-brut.txt
```

Relire les 50 lignes de l'échantillon et compter les rattachements faux (entité citée qui n'a rien à voir avec l'événement). Écrire `docs/superpowers/measurements/lot-1a.md` avec : date, taux de liaison des niveaux 1-2 (objectif ≥ 80 %), taux de faux rattachements sur l'échantillon (objectif ≤ 5 %), part des titres traduits, des photos et des Concernés, dix premiers candidats inconnus, poids de `site/data/entities/` (`du -sh site/data/entities`), état `facts:wikidata` dans `health.json`, et pour chaque faux rattachement la correction apportée (alias passé en casse exacte `=`, `link_in` ajouté, alias retiré). Supprimer `lot-1a-brut.txt`.

Si un objectif n'est pas atteint : corriger les alias concernés dans `config/entities/*.yml` (sur une branche `fix/alias-lot-1a`, tests verts, accord de l'utilisateur avant fusion) et remesurer au cycle suivant.

- [ ] **Step 5 : mettre la spec à jour**

Dans `docs/superpowers/specs/2026-09-27-vigie-2-design.md` :
- §3 « Supprimé » : retirer « dictionnaires `entities` par rubrique (migrés dans le catalogue) » et ajouter à « Conservé » : « dictionnaires `entities` des rubriques, pour le score et le filtre de pertinence (calibrés) ; le catalogue les couvre tous ».
- §5.1 : ajouter le type `index` à la liste des types ; §5.4 : ajouter le verbe `secteur` (appartient au secteur / regroupe).
- §7 : retirer la ligne `site/data/graph.json` ; ajouter `site/data/band.json` ; préciser que les événements gagnent `entity_ids` (le champ `entities` garde les noms).
- §12 lot 1 : préciser « partie A (données, ce plan) puis partie B (interface) ».

- [ ] **Step 6 : commit**

```bash
git add -A
git commit -m "docs: mesures du lot 1A et spec mise à jour" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git pull --rebase origin main
git push origin main
```

(Le push de ce commit de documentation est couvert par l'accord de l'étape 2 s'il a été donné pour tout le lot ; sinon, demander.)
