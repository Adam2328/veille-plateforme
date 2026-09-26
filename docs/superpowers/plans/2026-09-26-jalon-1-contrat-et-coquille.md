# Jalon 1 : contrat de données et coquille du site, plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un site statique complet (navigation, Accueil, page de veille, fiche événement, « depuis ma dernière visite ») qui lit des JSON conformes à un contrat versionné, alimenté ici par des données d'exemple, ouvert dans Live Preview.

**Architecture:** Un schéma JSON (`schemas/public.schema.json`) est le contrat entre le futur pipeline Python et le site. Le site est du HTML + CSS + modules JS natifs, sans build ; la logique pure (état de lecture, rendu en chaînes) est testée avec `node --test`, le contrat avec `pytest`. Un script génère des données d'exemple conformes au contrat.

**Tech Stack:** HTML/CSS/JS (ES modules, Node 24 pour les tests), Python 3.11 + `jsonschema` + `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-26-plateforme-veille-design.md` (sections 3, 4, 10, 14 jalon 1).

**Suite :** `2026-09-26-jalon-2-moteur-et-veille-ia.md` (produit les vrais JSON). Les jalons 3 à 5 auront leurs plans après les mesures du jalon 2.

## Global Constraints

- Python 3.11, Node 24 ; aucune dépendance front, aucun build, aucun CDN de scripts (seules les polices Google Fonts sont chargées).
- Coût d'exploitation 0 € ; dépôt destiné à être public : aucun secret dans le code.
- Toute donnée issue du contrat qui est insérée dans du HTML passe par `esc()` (leçon XSS du 22/07/2026 sur l'ancien site). Les URL de sources passent par `safeUrl()` (http/https uniquement). Les couleurs d'accent passent par `color()` (regex hexadécimale).
- Design : tokens « Ledger » (Playfair Display / IBM Plex Sans / IBM Plex Mono ; accent `#1A3A6B` clair, `#467CC8` sombre ; fond `#F8F6F1` / `#0B0B09` ; carte `#FFFFFF` / `#15150F` ; vert `#006633` / `#00A854` ; rouge `#CC0000` / `#DD2222` ; rayon 2 px ; aucune ombre portée ; filets fins).
- Interface en français ; pas d'emoji.
- Niveaux d'événements : 1, 2, 3. Fiabilités : `officiel`, `confirmé`, `rapporté`, `en_développement`, `non_confirmé`, `rumeur`.
- **Écart avec la spec initiale** : le pipeline publie directement dans `site/data/` (et non `data/public/`) car Vercel ne sert que le dossier `site/`. La spec a été corrigée en conséquence.
- Chaque commit se termine par la ligne `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- Tous les chemins sont relatifs à `veille-générale/plateforme/`.

## Review Focus

1. Titre d'événement ou nom de source contenant du HTML, des guillemets ou `<script>` : rendu inerte (test `render`).
2. URL de source en `javascript:` ou invalide : aucun lien cliquable créé (test `render`).
3. `localStorage` absent, bloqué ou contenant du JSON corrompu ou de mauvais types : le site démarre avec un état vide, sans exception (test `state`).
4. Veille sans aucun événement (cas normal de Sport-L'essentiel) : message explicite, pas de bloc vide (test `render`).
5. Fichier `data/domains/<id>.json` absent ou `home.json` illisible : message d'erreur avec bouton « Réessayer », pas d'écran blanc (vérification manuelle à la tâche 5).

---

### Task 1: Scaffold du dépôt et contrat de données

**Files:**
- Create: `.gitignore`, `pytest.ini`, `requirements.txt`, `engine/__init__.py`, `tests/__init__.py`
- Create: `schemas/public.schema.json`
- Create: `engine/contract.py`
- Test: `tests/test_contract.py`

**Interfaces:**
- Produces: `engine.contract.validate(kind: str, instance: dict) -> None`, avec `kind` dans `{"event", "home", "domainFile"}` ; lève `jsonschema.ValidationError` si non conforme.
- Produces (contrat JSON) :
  - `event` : `id, rev, domain, kind, title, first_seen, updated_at, importance, level, reliability, reliability_reason, summary, summary_mode, entities, sources`. `summary` vaut `null` ou `{quoi, qui, quand, pourquoi, retenir}` ; `summary_mode` vaut `llm | extractif | aucun` ; `sources[]` = `{name, tier, url, title, published_at}`.
  - `home` : `{generated_at, sample, domains[{id, name, accent, levels{"1":[id],"2":[id],"3":[id]}, upcoming[{date,title}]}], retain[id], events{id: event}}`.
  - `domainFile` : `{generated_at, domain{id,name,accent}, events[event], upcoming[{date,title}]}`.

- [ ] **Step 1: Créer les fichiers de base**

`.gitignore` :
```
.env
__pycache__/
.pytest_cache/
node_modules/
*.tmp
```

`pytest.ini` :
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`requirements.txt` :
```
jsonschema>=4.22
pytest>=8
```

`engine/__init__.py` et `tests/__init__.py` : fichiers vides.

- [ ] **Step 2: Installer les dépendances**

Run: `python -m pip install -r requirements.txt`
Expected: `Successfully installed ...` (ou `already satisfied`).

- [ ] **Step 3: Écrire le test qui échoue**

`tests/test_contract.py` :
```python
import pytest
from jsonschema import ValidationError

from engine.contract import validate

EVENT = {
    "id": "ev_1", "rev": 1, "domain": "ia", "kind": "model_release", "title": "Titre",
    "first_seen": "2026-09-26T10:00:00+00:00", "updated_at": "2026-09-26T11:00:00+00:00",
    "importance": 80.5, "level": 1, "reliability": "confirmé", "reliability_reason": "2 origines",
    "summary": {"quoi": "q", "qui": "w", "quand": "n", "pourquoi": "p", "retenir": "r"},
    "summary_mode": "llm", "entities": ["OpenAI"],
    "sources": [{"name": "S", "tier": 2, "url": "https://ex.com/a", "title": "t",
                 "published_at": "2026-09-26T10:30:00+00:00"}],
}
HOME = {
    "generated_at": "2026-09-26T12:00:00+00:00", "sample": False,
    "domains": [{"id": "ia", "name": "IA", "accent": "#5B3FA8",
                 "levels": {"1": ["ev_1"], "2": [], "3": []}, "upcoming": []}],
    "retain": ["ev_1"], "events": {"ev_1": EVENT},
}
DOMAIN_FILE = {
    "generated_at": "2026-09-26T12:00:00+00:00",
    "domain": {"id": "ia", "name": "IA", "accent": "#5B3FA8"},
    "events": [EVENT], "upcoming": [{"date": "2026-10-01", "title": "Conférence"}],
}


def test_valid_event_home_and_domain_file_pass():
    validate("event", EVENT)
    validate("home", HOME)
    validate("domainFile", DOMAIN_FILE)


def test_level_three_event_may_have_no_summary():
    validate("event", {**EVENT, "level": 3, "summary": None, "summary_mode": "aucun"})


@pytest.mark.parametrize("field", ["id", "rev", "level", "reliability", "sources", "summary_mode"])
def test_event_missing_required_field_fails(field):
    bad = {k: v for k, v in EVENT.items() if k != field}
    with pytest.raises(ValidationError):
        validate("event", bad)


@pytest.mark.parametrize("patch", [
    {"reliability": "certain"},
    {"level": 4},
    {"level": 0},
    {"importance": 101},
    {"sources": []},
    {"summary_mode": "magie"},
])
def test_event_invalid_value_fails(patch):
    with pytest.raises(ValidationError):
        validate("event", {**EVENT, **patch})


def test_home_without_levels_key_fails():
    bad = {**HOME, "domains": [{**HOME["domains"][0], "levels": {"1": [], "2": []}}]}
    with pytest.raises(ValidationError):
        validate("home", bad)
```

- [ ] **Step 4: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_contract.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'engine.contract'`.

- [ ] **Step 5: Écrire le schéma et le validateur**

`schemas/public.schema.json` :
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "source": {
      "type": "object",
      "required": ["name", "tier", "url", "title", "published_at"],
      "properties": {
        "name": {"type": "string"},
        "tier": {"type": "integer", "minimum": 1, "maximum": 5},
        "url": {"type": "string"},
        "title": {"type": "string"},
        "published_at": {"type": "string"}
      }
    },
    "summary": {
      "type": ["object", "null"],
      "required": ["quoi", "qui", "quand", "pourquoi", "retenir"],
      "properties": {
        "quoi": {"type": "string"}, "qui": {"type": "string"}, "quand": {"type": "string"},
        "pourquoi": {"type": "string"}, "retenir": {"type": "string"}
      }
    },
    "upcoming": {
      "type": "array",
      "items": {"type": "object", "required": ["date", "title"],
                "properties": {"date": {"type": "string"}, "title": {"type": "string"}}}
    },
    "event": {
      "type": "object",
      "required": ["id", "rev", "domain", "kind", "title", "first_seen", "updated_at", "importance",
                   "level", "reliability", "reliability_reason", "summary", "summary_mode",
                   "entities", "sources"],
      "properties": {
        "id": {"type": "string"},
        "rev": {"type": "integer", "minimum": 1},
        "domain": {"type": "string"},
        "kind": {"type": "string"},
        "title": {"type": "string"},
        "first_seen": {"type": "string"},
        "updated_at": {"type": "string"},
        "importance": {"type": "number", "minimum": 0, "maximum": 100},
        "level": {"type": "integer", "enum": [1, 2, 3]},
        "reliability": {"enum": ["officiel", "confirmé", "rapporté", "en_développement", "non_confirmé", "rumeur"]},
        "reliability_reason": {"type": "string"},
        "summary": {"$ref": "#/$defs/summary"},
        "summary_mode": {"enum": ["llm", "extractif", "aucun"]},
        "entities": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/source"}}
      }
    },
    "domainRef": {
      "type": "object",
      "required": ["id", "name", "accent"],
      "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "accent": {"type": "string"}}
    },
    "home": {
      "type": "object",
      "required": ["generated_at", "sample", "domains", "retain", "events"],
      "properties": {
        "generated_at": {"type": "string"},
        "sample": {"type": "boolean"},
        "domains": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "name", "accent", "levels", "upcoming"],
            "properties": {
              "id": {"type": "string"}, "name": {"type": "string"}, "accent": {"type": "string"},
              "levels": {
                "type": "object",
                "required": ["1", "2", "3"],
                "properties": {
                  "1": {"type": "array", "items": {"type": "string"}},
                  "2": {"type": "array", "items": {"type": "string"}},
                  "3": {"type": "array", "items": {"type": "string"}}
                }
              },
              "upcoming": {"$ref": "#/$defs/upcoming"}
            }
          }
        },
        "retain": {"type": "array", "items": {"type": "string"}},
        "events": {"type": "object", "additionalProperties": {"$ref": "#/$defs/event"}}
      }
    },
    "domainFile": {
      "type": "object",
      "required": ["generated_at", "domain", "events", "upcoming"],
      "properties": {
        "generated_at": {"type": "string"},
        "domain": {"$ref": "#/$defs/domainRef"},
        "events": {"type": "array", "items": {"$ref": "#/$defs/event"}},
        "upcoming": {"$ref": "#/$defs/upcoming"}
      }
    }
  }
}
```

`engine/contract.py` :
```python
import json
import pathlib

from jsonschema import Draft202012Validator

_SCHEMA = json.loads(
    (pathlib.Path(__file__).resolve().parent.parent / "schemas" / "public.schema.json").read_text("utf-8")
)


def validate(kind, instance):
    """Lève jsonschema.ValidationError si `instance` ne respecte pas le contrat `kind`."""
    Draft202012Validator({"$ref": f"#/$defs/{kind}", "$defs": _SCHEMA["$defs"]}).validate(instance)
```

- [ ] **Step 6: Lancer les tests**

Run: `python -m pytest tests/test_contract.py -v`
Expected: PASS (tous les tests).

- [ ] **Step 7: Commit**

```bash
git add .gitignore pytest.ini requirements.txt engine tests schemas docs
git commit -m "feat: contrat de données JSON et validateur" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Données d'exemple conformes au contrat

**Files:**
- Create: `site/tools/make-sample.mjs`
- Create (générés, versionnés) : `site/data/home.json`, `site/data/domains/ia.json`, `site/data/domains/finance.json`, `site/data/domains/football.json`
- Create: `site/package.json`
- Test: `tests/test_sample_data.py`

**Interfaces:**
- Consumes: `engine.contract.validate` (tâche 1).
- Produces: `site/data/home.json` et `site/data/domains/{ia,finance,football}.json` (`sample: true`, 14 événements). Ces fichiers servent au développement du site. Le pipeline du jalon 2 les écrasera aux mêmes chemins.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_sample_data.py` :
```python
import json
import pathlib

from engine.contract import validate

DATA = pathlib.Path(__file__).resolve().parent.parent / "site" / "data"


def test_sample_home_matches_contract():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    validate("home", home)
    assert home["sample"] is True
    ids = {i for d in home["domains"] for n in "123" for i in d["levels"][n]}
    assert ids <= set(home["events"])          # aucune référence orpheline
    assert set(home["retain"]) <= set(home["events"])


def test_sample_covers_every_reliability_and_level():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    evs = home["events"].values()
    assert {e["reliability"] for e in evs} >= {"officiel", "confirmé", "rapporté", "en_développement", "rumeur"}
    assert {e["level"] for e in evs} == {1, 2, 3}


def test_sample_domain_files_match_contract():
    for name in ("ia", "finance", "football"):
        validate("domainFile", json.loads((DATA / "domains" / f"{name}.json").read_text("utf-8")))


def test_rumors_never_reach_level_one():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    assert all(e["level"] > 1 for e in home["events"].values() if e["reliability"] in ("rumeur", "non_confirmé"))
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_sample_data.py -v`
Expected: FAIL (`FileNotFoundError` sur `site/data/home.json`).

- [ ] **Step 3: Écrire le générateur**

`site/package.json` :
```json
{
  "name": "veille-site",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test \"tests/*.test.mjs\"",
    "sample": "node tools/make-sample.mjs"
  }
}
```

`site/tools/make-sample.mjs` :
```js
// Génère des données d'exemple conformes à schemas/public.schema.json (usage : design du site).
import { mkdirSync, writeFileSync } from 'node:fs';

const now = new Date();
const ago = (h) => new Date(now - h * 3600e3).toISOString();
const src = (name, tier, title, h) => ({
  name, tier, url: `https://example.com/${encodeURIComponent(name)}`, title, published_at: ago(h),
});
const S = (quoi, qui, quand, pourquoi, retenir) => ({ quoi, qui, quand, pourquoi, retenir });
let n = 0;
const ev = (domain, level, importance, reliability, reason, kind, title, summary, entities, sources, rev = 1) => ({
  id: `sample_${++n}`, rev, domain, kind, title, first_seen: ago(7), updated_at: ago(1 + n / 4),
  importance, level, reliability, reliability_reason: reason,
  summary, summary_mode: summary ? 'llm' : 'aucun', entities, sources,
});

const DOMAINS = [
  { id: 'ia', name: 'IA', accent: '#5B3FA8' },
  { id: 'finance', name: 'Finance & Marchés', accent: '#1A3A6B' },
  { id: 'football', name: 'Football', accent: '#0B6E4F' },
];

const events = [
  ev('ia', 1, 92, 'officiel', 'Source officielle : blog du laboratoire', 'model_release',
    'Un laboratoire majeur publie un nouveau modèle de raisonnement',
    S('Publication d’un modèle de raisonnement avec une fenêtre de contexte élargie.', 'Exemple Labs', 'Aujourd’hui', 'Le modèle est disponible dans l’API dès aujourd’hui, à prix inchangé.', 'Disponible tout de suite en API, sans surcoût.'),
    ['Exemple Labs'], [src('Exemple Labs (blog officiel)', 1, 'Présentation du nouveau modèle', 3), src('Exemple Tech Media', 2, 'Ce que change le nouveau modèle', 2), src('Exemple Agrégateur', 4, 'Nouveau modèle : tout ce qu’il faut savoir', 1)], 3),
  ev('ia', 1, 84, 'confirmé', '3 origines indépendantes dont 2 médias reconnus', 'funding_acquisition',
    'Un accord de fourniture de puces d’IA de plusieurs milliards annoncé',
    S('Accord pluriannuel de fourniture de puces pour l’entraînement de modèles.', 'Un fabricant de puces et un laboratoire', 'Cette semaine', 'Il sécurise la capacité de calcul du laboratoire pour les prochains modèles.', 'Le calcul reste le facteur limitant de la course aux modèles.'),
    ['Exemple Puces'], [src('Exemple Business', 2, 'Accord de puces à plusieurs milliards', 4), src('Exemple Presse Éco', 2, 'Le laboratoire assure son calcul', 3), src('Exemple Généraliste', 3, 'Un contrat record dans les puces', 2)]),
  ev('ia', 2, 61, 'rapporté', '1 origine fiable (média spécialisé)', 'regulation',
    'Règlement européen sur l’IA : nouvelle étape du calendrier d’application',
    S('Publication du calendrier de la prochaine phase d’application.', 'Commission européenne (selon un média spécialisé)', 'Dans les prochains mois', 'Les fournisseurs de modèles à usage général devront documenter leurs données d’entraînement.', 'Prévoir la mise en conformité documentaire.'),
    ['UE'], [src('Exemple Tech Media', 2, 'Le calendrier d’application se précise', 5)]),
  ev('ia', 2, 55, 'en_développement', 'Croissance rapide du nombre de sources', 'product_launch',
    'Panne de plusieurs heures sur une API d’IA très utilisée',
    S('Interruption de service de l’API, en cours de rétablissement.', 'Un fournisseur d’API', 'Ce matin', 'Des applications tierces sont indisponibles.', 'Situation en évolution, à suivre.'),
    [], [src('Exemple Statut', 1, 'Incident en cours d’investigation', 1), src('Exemple Forum', 5, 'Tout est down chez moi', 0.5), src('Exemple Tech Media', 2, 'Panne sur une API majeure', 0.7)], 2),
  ev('ia', 3, 38, 'rapporté', '1 origine fiable (média spécialisé)', 'research',
    'Un benchmark ouvert classe dix nouveaux modèles', null, [], [src('Exemple Recherche', 2, 'Résultats du benchmark', 9)]),

  ev('finance', 1, 90, 'officiel', 'Source officielle : communiqué de la banque centrale', 'central_bank',
    'La banque centrale maintient ses taux directeurs',
    S('Maintien des taux directeurs, ton attentif sur l’inflation.', 'Banque centrale', 'Hier soir', 'Les marchés obligataires ajustent leurs anticipations de baisse.', 'Pas de changement de taux, le débat se déplace sur le calendrier.'),
    ['Banque centrale'], [src('Banque centrale (communiqué)', 1, 'Décision de politique monétaire', 5), src('Exemple Marchés', 2, 'Taux inchangés, ton prudent', 4)]),
  ev('finance', 2, 66, 'confirmé', '2 origines indépendantes de tier 2', 'earnings',
    'Un géant de la tech relève sa prévision annuelle',
    S('Relèvement de la prévision de chiffre d’affaires annuel après un trimestre supérieur aux attentes.', 'Un groupe technologique', 'Après la clôture', 'Le titre progresse dans les échanges hors séance.', 'Attention à la réaction à l’ouverture.'),
    ['Groupe Tech'], [src('Exemple Marchés', 2, 'Prévision relevée', 6), src('Exemple Business', 2, 'Résultats supérieurs aux attentes', 6)]),
  ev('finance', 2, 52, 'rumeur', 'Formulation au conditionnel, sources tier 4-5 uniquement', 'm_and_a',
    'Un rapprochement dans la banque serait à l’étude',
    S('Des sources non identifiées évoquent une discussion préliminaire.', 'Deux banques (non confirmé)', 'Non précisé', 'Aucune confirmation officielle : à traiter comme une rumeur.', 'Ne pas considérer l’opération comme acquise.'),
    [], [src('Exemple Agrégateur', 4, 'Une fusion serait envisagée', 3), src('Exemple Forum', 5, 'Il paraît que…', 2)]),
  ev('finance', 3, 34, 'rapporté', '1 origine fiable', 'commodities', 'Le pétrole recule après la hausse des stocks', null, [], [src('Exemple Marchés', 2, 'Pétrole en baisse', 8)]),

  ev('football', 1, 91, 'officiel', 'Source officielle : site de la compétition', 'result',
    'Finale de la coupe : victoire 2-1 après prolongation',
    S('Victoire 2-1 après prolongation en finale.', 'Le vainqueur et le finaliste', 'Hier soir', 'Premier titre de la décennie pour le vainqueur.', 'Score 2-1 a.p., but décisif à la 116e minute.'),
    ['Le vainqueur'], [src('Exemple Compétition (officiel)', 1, 'Résultat final', 12), src('Exemple Sport', 2, 'Le récit de la finale', 11), src('Exemple Sport 2', 2, 'Les notes du match', 10)]),
  ev('football', 1, 80, 'confirmé', '2 origines indépendantes de tier 2', 'transfer',
    'Transfert : un attaquant signe pour cinq saisons',
    S('Signature d’un attaquant pour cinq saisons.', 'Un attaquant et son nouveau club', 'Aujourd’hui', 'Le club renforce son secteur offensif avant la reprise.', 'Contrat de cinq ans, visite médicale passée.'),
    ['Le club'], [src('Exemple Sport', 2, 'C’est fait pour l’attaquant', 3), src('Exemple Mercato', 2, 'Signature officialisée', 2.5)]),
  ev('football', 2, 57, 'rumeur', 'Formulation au conditionnel, sources tier 4-5 uniquement', 'transfer',
    'Un milieu de terrain serait proche d’un départ',
    S('Un départ serait envisagé selon des sources non confirmées.', 'Un milieu de terrain', 'Non précisé', 'Aucune confirmation du joueur ni du club.', 'Rumeur : ne rien conclure avant confirmation.'),
    [], [src('Exemple Réseau', 5, 'Il pourrait partir', 4), src('Exemple Agrégateur', 4, 'Départ possible', 3)]),
  ev('football', 2, 54, 'rapporté', '1 origine fiable (média spécialisé)', 'injury',
    'Blessure : un titulaire absent trois semaines',
    S('Absence estimée à trois semaines après un examen.', 'Un joueur titulaire', 'Cette semaine', 'Il manquera les deux prochains matchs de championnat.', 'Retour attendu dans trois semaines.'),
    [], [src('Exemple Sport', 2, 'Trois semaines d’absence', 6)], 2),
  ev('football', 3, 33, 'rapporté', '1 origine fiable', 'fixtures', 'Le calendrier de la prochaine journée est dévoilé', null, [], [src('Exemple Compétition (officiel)', 1, 'Calendrier de la journée', 20)]),
];

const byDomain = (id) => events.filter((e) => e.domain === id);
const upcoming = { ia: [{ date: ago(-72), title: 'Conférence développeurs d’un grand laboratoire' }], finance: [{ date: ago(-48), title: 'Publication de l’inflation mensuelle' }, { date: ago(-120), title: 'Réunion de la banque centrale' }], football: [{ date: ago(-24), title: 'Journée de championnat' }] };

const home = {
  generated_at: now.toISOString(),
  sample: true,
  domains: DOMAINS.map((d) => ({
    ...d,
    levels: Object.fromEntries([1, 2, 3].map((l) => [String(l), byDomain(d.id).filter((e) => e.level === l).map((e) => e.id)])),
    upcoming: upcoming[d.id],
  })),
  retain: events.filter((e) => e.level === 1).sort((a, b) => b.importance - a.importance).slice(0, 7).map((e) => e.id),
  events: Object.fromEntries(events.map((e) => [e.id, e])),
};

mkdirSync(new URL('../data/domains/', import.meta.url), { recursive: true });
const write = (rel, obj) => writeFileSync(new URL(`../data/${rel}`, import.meta.url), JSON.stringify(obj, null, 1) + '\n');
write('home.json', home);
for (const d of DOMAINS) {
  write(`domains/${d.id}.json`, { generated_at: home.generated_at, domain: d, events: byDomain(d.id), upcoming: upcoming[d.id] });
}
console.log(`${events.length} événements d’exemple écrits dans site/data/`);
```

- [ ] **Step 4: Générer les données**

Run: `node site/tools/make-sample.mjs`
Expected: `14 événements d’exemple écrits dans site/data/`

- [ ] **Step 5: Lancer les tests**

Run: `python -m pytest tests/test_sample_data.py -v`
Expected: PASS (4 tests). Si `test_rumors_never_reach_level_one` ou la couverture échoue, corriger les données du script (pas le test) puis régénérer.

- [ ] **Step 6: Commit**

```bash
git add site tests/test_sample_data.py
git commit -m "feat: générateur de données d'exemple conformes au contrat" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: État de lecture (« depuis ma dernière visite »)

**Files:**
- Create: `site/js/state.js`
- Test: `site/tests/state.test.mjs`

**Interfaces:**
- Produces (module ES `site/js/state.js`) :
  - `defaultState() -> {lastVisit: null, seen: {}, follows: [], favorites: [], weights: {}}`
  - `loadState(storage) -> state` (n'échoue jamais ; état vide si stockage absent, illisible ou de mauvais types)
  - `saveState(storage, state) -> boolean` (`false` si l'écriture échoue)
  - `resetState(storage) -> void`
  - `eventStatus(state, ev) -> 'new' | 'updated' | 'seen'`
  - `markSeen(state, events) -> state` (immuable ; conserve la plus grande `rev`)
  - `countChanges(state, events) -> {fresh: number, updated: number}`
  - `pruneSeen(state, max = 3000) -> state`

- [ ] **Step 1: Écrire les tests qui échouent**

`site/tests/state.test.mjs` :
```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, loadState, saveState, resetState, eventStatus, markSeen, countChanges, pruneSeen } from '../js/state.js';

const memory = (initial = null) => {
  let v = initial;
  return { getItem: () => v, setItem: (_k, x) => { v = x; }, removeItem: () => { v = null; } };
};
const ev = (id, rev = 1) => ({ id, rev });

test('un événement absent de seen est nouveau', () => {
  assert.equal(eventStatus(defaultState(), ev('a')), 'new');
});

test('un événement vu à la même révision est vu', () => {
  assert.equal(eventStatus({ ...defaultState(), seen: { a: 2 } }, ev('a', 2)), 'seen');
});

test('un événement dont la révision a augmenté est mis à jour', () => {
  assert.equal(eventStatus({ ...defaultState(), seen: { a: 1 } }, ev('a', 2)), 'updated');
});

test('markSeen est immuable et garde la plus grande révision', () => {
  const s0 = { ...defaultState(), seen: { a: 5 } };
  const s1 = markSeen(s0, [ev('a', 2), ev('b', 1)]);
  assert.deepEqual(s1.seen, { a: 5, b: 1 });
  assert.deepEqual(s0.seen, { a: 5 });
});

test('countChanges distingue nouveautés et mises à jour', () => {
  const s = { ...defaultState(), seen: { a: 1, c: 1 } };
  assert.deepEqual(countChanges(s, [ev('a', 2), ev('b'), ev('c')]), { fresh: 1, updated: 1 });
});

test('loadState : stockage vide, JSON corrompu ou null donnent un état vide', () => {
  for (const raw of [null, '{corrompu', 'null', '42', '[]']) {
    assert.deepEqual(loadState(memory(raw)), defaultState());
  }
});

test('loadState : stockage qui lève une exception donne un état vide', () => {
  const throwing = { getItem() { throw new Error('SecurityError'); } };
  assert.deepEqual(loadState(throwing), defaultState());
});

test('loadState : mauvais types corrigés sans exception', () => {
  const s = loadState(memory(JSON.stringify({ seen: 5, follows: 'x', weights: [], lastVisit: 'd' })));
  assert.deepEqual(s.seen, {});
  assert.deepEqual(s.follows, []);
  assert.deepEqual(s.weights, {});
  assert.equal(s.lastVisit, 'd');
});

test('saveState renvoie false si l’écriture échoue et true sinon', () => {
  assert.equal(saveState({ setItem() { throw new Error('Quota'); } }, defaultState()), false);
  const m = memory();
  assert.equal(saveState(m, { ...defaultState(), seen: { a: 1 } }), true);
  assert.deepEqual(loadState(m).seen, { a: 1 });
});

test('resetState vide le stockage et ne lève jamais', () => {
  const m = memory('{"seen":{"a":1}}');
  resetState(m);
  assert.deepEqual(loadState(m), defaultState());
  resetState({ removeItem() { throw new Error('x'); } });
});

test('pruneSeen garde les entrées les plus récentes', () => {
  const s = { ...defaultState(), seen: { a: 1, b: 1, c: 1, d: 1, e: 1 } };
  assert.deepEqual(Object.keys(pruneSeen(s, 3).seen), ['c', 'd', 'e']);
  assert.equal(pruneSeen(s, 10), s);
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `cd site && node --test "tests/*.test.mjs"`
Expected: FAIL (`Cannot find module '.../js/state.js'`).

- [ ] **Step 3: Écrire l'implémentation**

`site/js/state.js` :
```js
const KEY = 'veille.state.v1';

export const defaultState = () => ({ lastVisit: null, seen: {}, follows: [], favorites: [], weights: {} });

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function sanitize(raw) {
  const s = { ...defaultState(), ...(isPlainObject(raw) ? raw : {}) };
  if (!isPlainObject(s.seen)) s.seen = {};
  if (!isPlainObject(s.weights)) s.weights = {};
  for (const k of ['follows', 'favorites']) if (!Array.isArray(s[k])) s[k] = [];
  return s;
}

export function loadState(storage) {
  try { return sanitize(JSON.parse(storage.getItem(KEY))); } catch { return defaultState(); }
}

export function saveState(storage, state) {
  try { storage.setItem(KEY, JSON.stringify(state)); return true; } catch { return false; }
}

export function resetState(storage) {
  try { storage.removeItem(KEY); } catch { /* stockage indisponible : rien à effacer */ }
}

export function eventStatus(state, ev) {
  const seenRev = state.seen[ev.id];
  if (seenRev === undefined) return 'new';
  return ev.rev > seenRev ? 'updated' : 'seen';
}

export function markSeen(state, events) {
  const seen = { ...state.seen };
  for (const ev of events) seen[ev.id] = Math.max(seen[ev.id] ?? 0, ev.rev);
  return { ...state, seen };
}

export function countChanges(state, events) {
  let fresh = 0;
  let updated = 0;
  for (const ev of events) {
    const status = eventStatus(state, ev);
    if (status === 'new') fresh++;
    else if (status === 'updated') updated++;
  }
  return { fresh, updated };
}

export function pruneSeen(state, max = 3000) {
  const keys = Object.keys(state.seen);
  if (keys.length <= max) return state;
  return { ...state, seen: Object.fromEntries(keys.slice(keys.length - max).map((k) => [k, state.seen[k]])) };
}
```

- [ ] **Step 4: Lancer les tests**

Run: `cd site && node --test "tests/*.test.mjs"`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add site/js/state.js site/tests/state.test.mjs
git commit -m "feat(site): état de lecture nouveau/mis à jour/vu, résistant aux stockages défaillants" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Rendu HTML (cartes, blocs, fiche, navigation)

**Files:**
- Create: `site/js/render.js`
- Test: `site/tests/render.test.mjs`

**Interfaces:**
- Consumes: `eventStatus`, `countChanges` de `state.js` (tâche 3) ; contrat `event`, `home`, `domainFile` (tâche 1).
- Produces (module ES `site/js/render.js`), toutes les fonctions renvoient une chaîne HTML :
  - `esc(s)`, `safeUrl(u) -> string | null`, `timeAgo(iso, now = Date.now()) -> string`
  - `badges(ev, status)`, `card(ev, status, now)`, `row(ev, status, now)`
  - `domainBlock(dom, events, state, now)` (dom = entrée `home.domains[]` ; events = `home.events`)
  - `renderHome(home, state, now, since = null)`
  - `renderDomain(file, state, now)`
  - `renderEvent(ev, state, now)`
  - `renderNav(home, state, activeHash)`
  - `renderError(message, canRetry = false)`
- Hooks DOM : `data-action="mark-all"`, `data-action="retry"`. Routes : `#/`, `#/d/<id>`, `#/e/<id>`.

- [ ] **Step 1: Écrire les tests qui échouent**

`site/tests/render.test.mjs` :
```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { esc, safeUrl, timeAgo, badges, card, domainBlock, renderHome, renderEvent, renderNav } from '../js/render.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const SRC = { name: 'S', tier: 2, url: 'https://ex.com/a', title: 'x', published_at: '2026-09-26T10:30:00Z' };
const ev = (o = {}) => ({
  id: 'e1', rev: 1, domain: 'ia', kind: 'other', title: 'T', first_seen: '2026-09-26T10:00:00Z',
  updated_at: '2026-09-26T11:00:00Z', importance: 80, level: 1, reliability: 'confirmé', reliability_reason: 'r',
  summary: { quoi: 'q', qui: 'w', quand: 'n', pourquoi: 'p', retenir: 'ret' }, summary_mode: 'llm',
  entities: [], sources: [SRC], ...o,
});
const dom = (o = {}) => ({ id: 'ia', name: 'IA', accent: '#5B3FA8', levels: { 1: [], 2: [], 3: [] }, upcoming: [], ...o });

test('esc neutralise HTML, guillemets et apostrophes', () => {
  assert.equal(esc(`<a href="x" onclick='y'>&`), '&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;');
  assert.equal(esc(null), '');
});

test('un titre malveillant est rendu inerte dans une carte', () => {
  const html = card(ev({ title: '<img src=x onerror=alert(1)>' }), 'seen', NOW);
  assert.ok(!html.includes('<img'));
  assert.match(html, /&lt;img/);
});

test('un nom de source malveillant est rendu inerte dans la fiche', () => {
  const html = renderEvent(ev({ sources: [{ ...SRC, name: '"><script>x</script>' }] }), defaultState(), NOW);
  assert.ok(!html.includes('<script>'));
});

test('safeUrl refuse javascript:, data: et les URL invalides', () => {
  assert.equal(safeUrl('javascript:alert(1)'), null);
  assert.equal(safeUrl('data:text/html,x'), null);
  assert.equal(safeUrl('pas une url'), null);
  assert.equal(safeUrl('https://ex.com/a'), 'https://ex.com/a');
});

test('la fiche ne crée aucun lien pour une source en javascript:', () => {
  const html = renderEvent(ev({ sources: [{ ...SRC, url: 'javascript:alert(1)' }] }), defaultState(), NOW);
  assert.ok(!html.includes('javascript:'));
  assert.ok(html.includes('S'));
});

test('la fiche affiche les 5 champs de la synthèse et sépare les sources sociales', () => {
  const html = renderEvent(ev({ sources: [SRC, { ...SRC, name: 'Forum', tier: 5 }] }), defaultState(), NOW);
  for (const label of ['Quoi', 'Qui', 'Quand', 'Pourquoi', 'À retenir']) assert.ok(html.includes(label));
  assert.match(html, /<details[^>]*>[\s\S]*Forum/);
});

test('un résumé extractif est signalé', () => {
  assert.match(renderEvent(ev({ summary_mode: 'extractif' }), defaultState(), NOW), /Résumé automatique simple/);
});

test('badge Nouveau présent pour un événement nouveau, absent pour un événement vu', () => {
  assert.match(badges(ev(), 'new'), /Nouveau/);
  assert.match(badges(ev(), 'updated'), /Mis à jour/);
  assert.ok(!/Nouveau|Mis à jour/.test(badges(ev(), 'seen')));
});

test('une fiabilité inconnue retombe sur « Non confirmé » sans injecter de classe', () => {
  const html = badges(ev({ reliability: 'x" onmouseover="y' }), 'seen');
  assert.match(html, /Non confirmé/);
  assert.ok(!html.includes('onmouseover'));
});

test('timeAgo tolère une date invalide', () => {
  assert.equal(timeAgo('nope', NOW), '');
  assert.equal(timeAgo('2026-09-26T11:30:00Z', NOW), 'il y a 30 min');
  assert.equal(timeAgo('2026-09-26T08:00:00Z', NOW), 'il y a 4 h');
});

test('une veille sans événement affiche un message explicite', () => {
  assert.match(domainBlock(dom(), {}, defaultState(), NOW), /Rien d’important/);
});

test('un accent invalide ne peut pas injecter de CSS', () => {
  const html = domainBlock(dom({ accent: 'red;}body{display:none' }), {}, defaultState(), NOW);
  assert.ok(!html.includes('display:none'));
});

test('renderHome compte les nouveautés et propose « Tout marquer comme vu »', () => {
  const e = ev();
  const home = { generated_at: '2026-09-26T11:00:00Z', sample: true, domains: [dom({ levels: { 1: ['e1'], 2: [], 3: [] } })], retain: ['e1'], events: { e1: e } };
  const html = renderHome(home, defaultState(), NOW);
  assert.match(html, /<b>1<\/b> nouveauté/);
  assert.match(html, /data-action="mark-all"/);
  assert.match(html, /Données d’exemple/);
  assert.match(html, /À retenir aujourd’hui/);
  const seen = renderHome(home, { ...defaultState(), seen: { e1: 1 } }, NOW);
  assert.ok(!seen.includes('mark-all'));
});

test('renderNav affiche un compteur par veille et marque la page active', () => {
  const home = { domains: [dom({ levels: { 1: ['e1'], 2: [], 3: [] } })], events: { e1: ev() } };
  const html = renderNav(home, defaultState(), '#/d/ia');
  assert.match(html, /class="count">1</);
  assert.match(html, /href="#\/d\/ia" aria-current="page"/);
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `cd site && node --test "tests/*.test.mjs"`
Expected: FAIL (`Cannot find module '.../js/render.js'`).

- [ ] **Step 3: Écrire l'implémentation**

`site/js/render.js` :
```js
import { eventStatus, countChanges } from './state.js';

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function safeUrl(u) {
  try {
    const x = new URL(u);
    return x.protocol === 'http:' || x.protocol === 'https:' ? x.href : null;
  } catch {
    return null;
  }
}

const color = (c) => (/^#[0-9a-f]{3,8}$/i.test(c) ? c : '#1A3A6B');
const plural = (n, word) => `${n} ${word}${n > 1 ? 's' : ''}`;
const enc = encodeURIComponent;

const REL = { officiel: 'Officiel', 'confirmé': 'Confirmé', 'rapporté': 'Rapporté', 'en_développement': 'En développement', 'non_confirmé': 'Non confirmé', rumeur: 'Rumeur' };
const REL_CLASS = { officiel: 'officiel', 'confirmé': 'confirme', 'rapporté': 'rapporte', 'en_développement': 'dev', 'non_confirmé': 'nc', rumeur: 'rumeur' };
const STATUS = { new: 'Nouveau', updated: 'Mis à jour' };
const relLabel = (r) => REL[r] ?? REL['non_confirmé'];
const relClass = (r) => REL_CLASS[r] ?? 'nc';

export function timeAgo(iso, now = Date.now()) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const m = Math.max(0, Math.round((now - t) / 60000));
  if (m < 60) return `il y a ${m} min`;
  const h = Math.round(m / 60);
  return h < 24 ? `il y a ${h} h` : `il y a ${Math.round(h / 24)} j`;
}

const fmtDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
};
const fmtDateTime = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

export function badges(ev, status) {
  const st = STATUS[status] ? `<span class="badge st-${status}">${STATUS[status]}</span>` : '';
  return `${st}<span class="badge rel-${relClass(ev.reliability)}" title="${esc(ev.reliability_reason)}">${esc(relLabel(ev.reliability))}</span>`;
}

const href = (ev) => `#/e/${enc(ev.id)}`;

export function card(ev, status, now) {
  return `<a class="card" href="${href(ev)}">
    <div>${badges(ev, status)}</div>
    <h3>${esc(ev.title)}</h3>
    ${ev.summary ? `<p>${esc(ev.summary.retenir)}</p>` : ''}
    <div class="meta">${esc(plural(ev.sources.length, 'source'))} · ${esc(timeAgo(ev.updated_at, now))}</div>
  </a>`;
}

export function row(ev, status, now) {
  return `<a class="row" href="${href(ev)}">${badges(ev, status)}<span class="t">${esc(ev.title)}</span><span class="meta">${esc(timeAgo(ev.updated_at, now))}</span></a>`;
}

const upcomingList = (items) =>
  items && items.length
    ? `<ul class="upcoming">${items.map((u) => `<li><b>${esc(fmtDate(u.date))}</b> ${esc(u.title)}</li>`).join('')}</ul>`
    : '';

export function domainBlock(dom, events, state, now) {
  const pick = (n) => (dom.levels[n] ?? []).map((id) => events[id]).filter(Boolean);
  const [l1, l2, l3] = [pick(1), pick(2), pick(3)];
  const st = (e) => eventStatus(state, e);
  const empty = !l1.length && !l2.length && !l3.length;
  const more = l3.length
    ? `<details class="more"><summary>Voir ${plural(l3.length, 'autre')}</summary>${l3.map((e) => `<a href="${href(e)}">${esc(e.title)}</a>`).join('')}</details>`
    : '';
  return `<section class="block" style="--dom:${color(dom.accent)}">
    <h2><a href="#/d/${enc(dom.id)}">${esc(dom.name)}</a></h2>
    ${empty ? '<p class="meta">Rien d’important pour l’instant.</p>' : ''}
    ${l1.map((e) => card(e, st(e), now)).join('')}
    ${l2.map((e) => row(e, st(e), now)).join('')}
    ${more}
    ${upcomingList(dom.upcoming)}
  </section>`;
}

export function renderHome(home, state, now, since = null) {
  const { fresh, updated } = countChanges(state, Object.values(home.events));
  const retain = home.retain.map((id) => home.events[id]).filter(Boolean);
  const sinceTxt = since && fmtDateTime(since) ? ` (dernière visite : ${esc(fmtDateTime(since))})` : '';
  return `${home.sample ? '<div class="sample-banner">Données d’exemple</div>' : ''}
    <h1>Aujourd’hui</h1>
    <p class="meta">Dernier changement de contenu : ${esc(timeAgo(home.generated_at, now))}</p>
    <div class="since"><span>Depuis ta dernière visite${sinceTxt} : <b>${fresh}</b> nouveauté${fresh > 1 ? 's' : ''} · <b>${updated}</b> mise${updated > 1 ? 's' : ''} à jour</span>${fresh + updated ? '<button class="link" data-action="mark-all">Tout marquer comme vu</button>' : ''}</div>
    ${retain.length ? `<section class="retain"><h2>À retenir aujourd’hui</h2><ol>${retain.map((e) => `<li>${badges(e, eventStatus(state, e))}<a href="${href(e)}">${esc(e.title)}</a><div class="meta">${esc(e.summary?.retenir ?? '')}</div></li>`).join('')}</ol></section>` : ''}
    ${home.domains.map((d) => domainBlock(d, home.events, state, now)).join('')}`;
}

export function renderDomain(file, state, now) {
  const by = (n) => file.events.filter((e) => e.level === n);
  const st = (e) => eventStatus(state, e);
  const section = (title, list, fn) => (list.length ? `<h2>${title}</h2>${list.map((e) => fn(e, st(e), now)).join('')}` : '');
  const empty = !file.events.length;
  return `<div style="--dom:${color(file.domain.accent)}"><a class="back" href="#/">← Accueil</a>
    <h1>${esc(file.domain.name)}</h1>
    ${empty ? '<p class="meta">Rien d’important pour l’instant.</p>' : ''}
    ${section('Incontournable', by(1), card)}
    ${section('Important', by(2), row)}
    ${section('À savoir', by(3), row)}
    ${upcomingList(file.upcoming)}</div>`;
}

export function renderEvent(ev, state, now) {
  const s = ev.summary;
  const fields = s ? [['Quoi', s.quoi], ['Qui', s.qui], ['Quand', s.quand], ['Pourquoi c’est important', s.pourquoi], ['À retenir', s.retenir]] : [];
  const sorted = [...ev.sources].sort((a, b) => a.tier - b.tier || Date.parse(b.published_at) - Date.parse(a.published_at));
  const li = (x) => {
    const url = safeUrl(x.url);
    const label = `${esc(x.name)} — ${esc(x.title)}`;
    return `<li><span class="badge">tier ${esc(x.tier)}</span>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label}<span class="meta"> ${esc(timeAgo(x.published_at, now))}</span></li>`;
  };
  const main = sorted.filter((x) => x.tier < 5);
  const social = sorted.filter((x) => x.tier >= 5);
  return `<article class="detail"><a class="back" href="#/">← Accueil</a>
    <div>${badges(ev, eventStatus(state, ev))}${ev.summary_mode === 'extractif' ? '<span class="badge">Résumé automatique simple</span>' : ''}</div>
    <h1>${esc(ev.title)}</h1>
    <p class="meta">Fiabilité : ${esc(ev.reliability_reason)} · première détection ${esc(timeAgo(ev.first_seen, now))} · mis à jour ${esc(timeAgo(ev.updated_at, now))}</p>
    ${fields.length ? `<dl>${fields.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` : '<p class="meta">Événement secondaire : pas de synthèse, voir les sources.</p>'}
    <h2>Sources (${sorted.length})</h2>
    <ul class="sources">${main.map(li).join('')}</ul>
    ${social.length ? `<details class="more"><summary>Réseaux sociaux (${social.length})</summary><ul class="sources">${social.map(li).join('')}</ul></details>` : ''}
  </article>`;
}

export function renderNav(home, state, activeHash) {
  const changed = (d) =>
    [1, 2, 3].flatMap((n) => d.levels[n] ?? []).map((id) => home.events[id]).filter((e) => e && eventStatus(state, e) !== 'seen').length;
  const link = (h, label, n) =>
    `<a href="${h}"${activeHash === h ? ' aria-current="page"' : ''}><span>${esc(label)}</span>${n ? `<span class="count">${n}</span>` : ''}</a>`;
  return `<div class="brand">Veille</div>${link('#/', 'Accueil', 0)}${home.domains.map((d) => link(`#/d/${enc(d.id)}`, d.name, changed(d))).join('')}`;
}

export function renderError(message, canRetry = false) {
  return `<div class="err"><p>${esc(message)}</p>${canRetry ? '<button class="link" data-action="retry">Réessayer</button>' : ''}</div>`;
}
```

- [ ] **Step 4: Lancer les tests**

Run: `cd site && node --test "tests/*.test.mjs"`
Expected: PASS (state + render). Si `renderNav` échoue sur `class="count">1<`, vérifier le gabarit `link()` : le compteur doit être exactement `<span class="count">1</span>`.

- [ ] **Step 5: Commit**

```bash
git add site/js/render.js site/tests/render.test.mjs
git commit -m "feat(site): rendu HTML échappé (accueil, veille, fiche, navigation)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Coquille du site, ouverture dans Live Preview, vérification visuelle

**Files:**
- Create: `site/index.html`, `site/css/app.css`, `site/js/data.js`, `site/js/app.js`
- Create: `vercel.json` (racine de `plateforme/`)

**Interfaces:**
- Consumes: `state.js` (tâche 3), `render.js` (tâche 4), `site/data/*.json` (tâche 2).
- Produces: le site complet à `site/index.html`. Routes `#/`, `#/d/<id>`, `#/e/<id>`. Paramètre de développement `?reset` : efface l'état de lecture. Sur des données `sample: true`, la première visite ne masque pas les nouveautés ; sur de vraies données, la première visite les marque toutes comme vues (référence de départ).

- [ ] **Step 1: Écrire `site/index.html`**

```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Veille</title>
  <meta name="description" content="Centre de contrôle personnel de l'information">
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/app.css">
</head>
<body>
  <div class="shell">
    <nav id="nav" aria-label="Veilles"></nav>
    <main id="main" tabindex="-1"><p class="meta">Chargement…</p></main>
  </div>
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Écrire `site/css/app.css`**

```css
:root {
  --serif: 'Playfair Display', Georgia, serif;
  --sans: 'IBM Plex Sans', system-ui, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, monospace;
  --bg: #F8F6F1; --card: #FFFFFF; --text: #1B1B18; --soft: #5E5E56; --line: #E2DED3;
  --accent: #1A3A6B; --green: #006633; --red: #CC0000; --amber: #8A5A00;
  --radius: 2px;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0B0B09; --card: #15150F; --text: #ECEAE2; --soft: #A3A196; --line: #2A2A22;
          --accent: #467CC8; --green: #00A854; --red: #DD2222; --amber: #D6A23A; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 var(--sans); }
a { color: inherit; }
.shell { display: grid; grid-template-columns: 232px minmax(0, 1fr); min-height: 100vh; }

nav { position: sticky; top: 0; height: 100vh; padding: 20px 12px; border-right: 1px solid var(--line); display: flex; flex-direction: column; gap: 2px; }
nav .brand { font: 700 20px var(--serif); padding: 4px 10px 16px; }
nav a { display: flex; justify-content: space-between; align-items: center; padding: 9px 10px; border-radius: var(--radius); text-decoration: none; }
nav a:hover { background: color-mix(in srgb, var(--text) 6%, transparent); }
nav a[aria-current="page"] { background: color-mix(in srgb, var(--accent) 12%, transparent); font-weight: 600; }
.count { font: 500 12px var(--mono); background: var(--accent); color: var(--bg); border-radius: 99px; padding: 1px 7px; }

main { padding: 28px clamp(16px, 4vw, 48px) 64px; width: 100%; max-width: 980px; outline: none; }
h1 { font: 700 30px/1.15 var(--serif); margin: 0 0 4px; }
h2 { font: 700 21px var(--serif); margin: 36px 0 12px; }
h2 a { text-decoration: none; }
h2 a:hover { text-decoration: underline; }
.meta { font: 400 12px var(--mono); color: var(--soft); margin: 6px 0 0; }
button.link { background: none; border: 0; color: var(--accent); font: inherit; cursor: pointer; text-decoration: underline; padding: 0; }

.sample-banner { background: var(--amber); color: var(--bg); font: 500 12px var(--mono); padding: 6px 12px; text-align: center; margin: -28px calc(-1 * clamp(16px, 4vw, 48px)) 20px; }
.since { display: flex; justify-content: space-between; gap: 12px; align-items: center; border: 1px solid var(--line); background: var(--card); padding: 10px 14px; margin: 16px 0 8px; border-radius: var(--radius); }
.since b { font: 500 14px var(--mono); }
.retain { background: var(--card); border: 1px solid var(--line); border-top: 3px solid var(--accent); padding: 4px 16px 6px; margin: 20px 0; border-radius: var(--radius); }
.retain h2 { margin: 12px 0 6px; font-size: 18px; }
.retain ol { margin: 0; padding: 0; list-style: none; }
.retain li { padding: 10px 0; border-bottom: 1px solid var(--line); }
.retain li:last-child { border: 0; }
.retain li a { font-weight: 600; text-decoration: none; }

.block { --dom: var(--accent); }
.card { display: block; background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--dom, var(--accent)); padding: 14px 16px; margin: 0 0 10px; color: inherit; text-decoration: none; border-radius: var(--radius); }
.card h3 { font: 600 17px/1.3 var(--sans); margin: 6px 0 4px; }
.card p { margin: 0; color: var(--soft); }
.row { display: flex; gap: 10px; align-items: baseline; padding: 8px 12px; border: 1px solid var(--line); background: var(--card); margin-bottom: 6px; color: inherit; text-decoration: none; border-radius: var(--radius); }
.row .t { flex: 1; }
.card:hover, .row:hover { border-color: var(--dom, var(--accent)); }
.more { margin-top: 8px; }
.more summary { cursor: pointer; color: var(--soft); }
.more a { display: block; padding: 6px 2px; text-decoration: none; }
.upcoming { display: flex; gap: 8px; overflow-x: auto; padding: 0; list-style: none; margin: 12px 0 0; }
.upcoming li { white-space: nowrap; font-size: 13px; border: 1px dashed var(--line); padding: 4px 10px; }

.badge { display: inline-block; font: 500 11px var(--mono); letter-spacing: .02em; text-transform: uppercase; padding: 2px 6px; border-radius: var(--radius); margin-right: 6px; border: 1px solid var(--line); color: var(--soft); }
.st-new { background: var(--accent); border-color: var(--accent); color: var(--bg); }
.st-updated { background: var(--amber); border-color: var(--amber); color: var(--bg); }
.rel-officiel, .rel-confirme { color: var(--green); border-color: var(--green); }
.rel-rapporte { color: var(--accent); border-color: var(--accent); }
.rel-dev { color: var(--amber); border-color: var(--amber); }
.rel-nc, .rel-rumeur { color: var(--red); border-color: var(--red); }

.back { display: inline-block; margin-bottom: 12px; color: var(--soft); text-decoration: none; }
.detail dl { display: grid; grid-template-columns: 170px 1fr; gap: 10px 16px; margin: 20px 0; }
.detail dt { color: var(--soft); font-size: 13px; }
.detail dd { margin: 0; }
.sources { list-style: none; padding: 0; margin: 0; }
.sources li { padding: 8px 0; border-bottom: 1px solid var(--line); }
.err { border: 1px solid var(--red); padding: 16px; border-radius: var(--radius); }

@media (max-width: 768px) {
  .shell { grid-template-columns: 1fr; }
  nav { position: fixed; top: auto; bottom: 0; left: 0; right: 0; height: auto; flex-direction: row; justify-content: space-around; border-right: 0; border-top: 1px solid var(--line); background: var(--bg); padding: 6px; z-index: 5; }
  nav .brand { display: none; }
  nav a { flex-direction: column; font-size: 12px; gap: 2px; padding: 6px 4px; text-align: center; }
  main { padding-bottom: 96px; }
  .since { flex-direction: column; align-items: flex-start; }
  .detail dl { grid-template-columns: 1fr; gap: 2px; }
  .detail dd { margin-bottom: 10px; }
}
@media (prefers-reduced-motion: no-preference) { .card, .row { transition: border-color .12s; } }
```

- [ ] **Step 3: Écrire `site/js/data.js` et `site/js/app.js`**

`site/js/data.js` :
```js
async function get(path) {
  const r = await fetch(path, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${path} : HTTP ${r.status}`);
  return r.json();
}

export const loadHome = () => get('data/home.json');
export const loadDomain = (id) => get(`data/domains/${encodeURIComponent(id)}.json`);
```

`site/js/app.js` :
```js
import { loadState, saveState, resetState, markSeen, pruneSeen, defaultState } from './state.js';
import { loadHome, loadDomain } from './data.js';
import { renderHome, renderDomain, renderEvent, renderNav, renderError } from './render.js';

const storage = (() => {
  try { return window.localStorage; } catch { return { getItem: () => null, setItem: () => {}, removeItem: () => {} }; }
})();

const $main = document.getElementById('main');
const $nav = document.getElementById('nav');
const domains = new Map();
let home = null;
let state = defaultState();
let previousVisit = null;

const persist = (next) => { state = next; saveState(storage, state); };

async function domainFile(id) {
  if (!domains.has(id)) domains.set(id, await loadDomain(id));
  return domains.get(id);
}

async function findEvent(id) {
  if (home.events[id]) return home.events[id];
  for (const d of home.domains) {
    const hit = (await domainFile(d.id)).events.find((e) => e.id === id);
    if (hit) return hit;
  }
  return null;
}

async function route() {
  const hash = location.hash || '#/';
  const now = Date.now();
  try {
    if (hash.startsWith('#/d/')) {
      $main.innerHTML = renderDomain(await domainFile(decodeURIComponent(hash.slice(4))), state, now);
    } else if (hash.startsWith('#/e/')) {
      const ev = await findEvent(decodeURIComponent(hash.slice(4)));
      if (!ev) {
        $main.innerHTML = renderError('Événement introuvable ou archivé.');
      } else {
        $main.innerHTML = renderEvent(ev, state, now);
        persist(markSeen(state, [ev]));
      }
    } else {
      $main.innerHTML = renderHome(home, state, now, previousVisit);
    }
  } catch (err) {
    $main.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
  }
  $nav.innerHTML = renderNav(home, state, hash);
  window.scrollTo(0, 0);
}

async function init() {
  try {
    home = await loadHome();
  } catch (err) {
    $main.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
    return;
  }
  if (new URLSearchParams(location.search).has('reset')) resetState(storage);
  state = loadState(storage);
  previousVisit = state.lastVisit;
  // Première visite sur de vraies données : tout est marqué vu, seules les nouveautés à venir seront signalées.
  if (!state.lastVisit && !home.sample) state = markSeen(state, Object.values(home.events));
  persist(pruneSeen({ ...state, lastVisit: new Date().toISOString() }));
  route();
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  if (btn.dataset.action === 'mark-all') { persist(markSeen(state, Object.values(home.events))); route(); }
  if (btn.dataset.action === 'retry') location.reload();
});
window.addEventListener('hashchange', route);
init();
```

`vercel.json` (racine de `plateforme/`) :
```json
{
  "outputDirectory": "site",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains" }
      ]
    }
  ]
}
```

- [ ] **Step 4: Lancer tous les tests**

Run: `cd site && node --test "tests/*.test.mjs" && cd .. && python -m pytest -q`
Expected: tout PASS.

- [ ] **Step 5: Ouvrir dans Live Preview**

Ouvrir `site/index.html` dans l'éditeur. Sur cette machine `code` est le binaire de Cursor :

Run: `"C:/Users/rouas/AppData/Local/Programs/cursor/resources/app/codeBin/code" site/index.html`

Puis, dans l'éditeur, palette de commandes (`Ctrl+Maj+P`) : `Live Preview: Show Preview (External Browser)` (ou clic droit sur `index.html` > `Show Preview`). La commande ne peut pas être lancée depuis la ligne de commande : demander à l'utilisateur de l'exécuter si elle ne s'ouvre pas seule. Live Preview sert le dossier de travail ; vérifier que l'URL ouverte se termine par `/site/index.html` (sinon les chemins relatifs `data/...` seront corrects quand même, car ils sont relatifs à la page).

En parallèle, pour la vérification automatisée, servir `site/` :

Run (en arrière-plan) : `python -m http.server 8934 --bind 127.0.0.1 --directory site`
Expected: le site répond sur `http://127.0.0.1:8934/`.

- [ ] **Step 6: Vérification visuelle et fonctionnelle (navigateur)**

Avec les outils de navigateur, ouvrir `http://127.0.0.1:8934/?reset` puis contrôler, en desktop (≥ 1200 px) et mobile (390 px de large) :

1. Accueil : bandeau « Données d'exemple », bloc « À retenir aujourd'hui » (5 événements de niveau 1 maximum, triés par importance), 3 blocs de veilles, bandeau « Depuis ta dernière visite : 14 nouveautés · 0 mise à jour ».
2. Le badge Rumeur est rouge, Officiel et Confirmé sont verts, aucune rumeur dans les cartes de niveau 1.
3. Clic sur une carte : la fiche affiche Quoi/Qui/Quand/Pourquoi/À retenir, la fiabilité avec sa raison, les sources triées par tier (les sources tier 5 repliées).
4. Retour à l'Accueil : l'événement ouvert n'a plus le badge Nouveau, le compteur de la barre latérale a baissé de 1.
5. « Tout marquer comme vu » : tous les badges Nouveau disparaissent, le bouton disparaît.
6. Simuler « Mis à jour » : dans la console, exécuter `const s = JSON.parse(localStorage['veille.state.v1']); s.seen.sample_4 = 1; localStorage['veille.state.v1'] = JSON.stringify(s); location.reload()` ; l'événement `sample_4` (rev 2) doit afficher « Mis à jour ».
7. Page veille (`#/d/football`) : Incontournable / Important / À savoir, et bande « À venir ».
8. Erreur : ouvrir `#/d/inconnu` : message d'erreur avec « Réessayer », pas d'écran blanc. Arrêter le serveur et recharger : idem.
9. Mode sombre : activer `prefers-color-scheme: dark` (émulation des outils de développement) ; le texte des badges et du compteur reste lisible.
10. Console : aucune erreur JavaScript.

Corriger tout défaut constaté dans `app.css` ou `render.js` (et compléter les tests si la cause est logique), puis relancer les tests.

- [ ] **Step 7: Demander l'avis de l'utilisateur sur le design**

Laisser Live Preview ouvert, résumer ce qui est visible et demander : hiérarchie, densité, couleurs, mobile. Noter les retours ; les changements de design demandés sont faits avant le commit final (ils touchent seulement `app.css` et `render.js`).

- [ ] **Step 8: Commit**

```bash
git add site vercel.json
git commit -m "feat(site): coquille complète (accueil, veille, fiche, depuis ma dernière visite)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-review (jalon 1 contre la spec)

- Spec §3 structure : `schemas/`, `site/`, `engine/`, `tests/` créés ; `config/`, `data/`, workflow : jalon 2.
- Spec §4 contrat : événement, home, domainFile, état utilisateur (`state.js`) couverts. `Structured`, `Agenda` complets (jalon 3-4) ; `upcoming` présent dès maintenant dans le contrat.
- Spec §10 : navigation latérale et barre basse mobile, Accueil (bandeau depuis la dernière visite, À retenir, blocs par niveaux, badges), fiche événement (synthèse, fiabilité + raison, sources triées, sociales repliées), modes clair/sombre, échappement. Recherche `Ctrl+K`, suivis, favoris, PWA, alertes, modules par veille : jalon 5 et phase 2 (hors de ce plan).
- Critère « Live Preview » de l'utilisateur : tâche 5, étape 5.
- Types et noms : `eventStatus/markSeen/countChanges/pruneSeen/resetState` définis à la tâche 3 et utilisés à l'identique aux tâches 4 et 5 ; `renderHome(home, state, now, since)` défini tâche 4, appelé à l'identique tâche 5.
- Pas de placeholder.
