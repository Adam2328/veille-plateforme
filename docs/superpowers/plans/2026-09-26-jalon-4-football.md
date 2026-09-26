# Jalon 4 : Football, plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la veille Football, la plus profonde : actualité et mercato issus de 12 sources testées, avec des rumeurs de transfert étiquetées comme telles (jamais présentées comme des faits), plus des données structurées (classements, résultats, calendrier des 5 grands championnats et de la Ligue des champions) et une page Football à onglets Actu / Résultats / Classements / Calendrier / Mercato.

**Architecture:** Aucune nouvelle brique de collecte pour l'actualité : une configuration `config/domains/football.yml` sur le moteur existant. Trois ajouts : (1) une règle de fiabilité pilotée par la config qui classe en « rumeur » les événements à source unique formulés comme des pistes (« serait intéressé », « dans le viseur »), sauf marqueur de confirmation (« officiel », « here we go ») ; (2) une étape `structured` `football-data` qui publie `site/data/football.json` depuis l'API gratuite football-data.org, avec conservation des dernières valeurs en cas d'échec et arrêt propre si la clé est absente ; (3) une page Football à onglets et une bande résultats/prochains matchs sur l'Accueil.

**Tech Stack:** Python 3.11 (`requests`, `PyYAML`, `scikit-learn`, `jsonschema`, `pytest`), HTML/CSS/JS natifs, `node --test`.

**Spec:** `docs/superpowers/specs/2026-09-26-plateforme-veille-design.md` (sections 5 à 7, 10, 11 « Football », 14 jalon 4). **Prérequis :** jalons 1 à 3 terminés et déployés.

## Sources retenues après test (26/09/2026)

| Source | État | Décision |
|---|---|---|
| L'Équipe, RMC Sport, Le Figaro Sport, Foot Mercato (`/flux-rss/`), BBC Sport, Sky Sports, ESPN, The Guardian, Marca, La Gazzetta dello Sport, Kicker, Reddit r/soccer | flux RSS valides | **Retenus** (Reddit en tier 5) |
| Google Actualités par thème (mercato, blessures, Ligue 1, Ligue des champions, équipe de France, football féminin) | valide | **Retenus** (tier 4, éditeur reconnu via `publishers`) |
| Eurosport (404), UEFA (connexion impossible), FIFA (page HTML sans flux) | inutilisables | Écartés |
| ESPN API JSON | 403 « Access Denied » (blocage anti-robots) | Écartée |
| TheSportsDB (clé publique gratuite) | répond, mais classement limité à 5 lignes et 1 seul match par requête | Écartée pour les classements |
| **football-data.org** (v4) | répond 403 sans jeton ; le plan gratuit couvre Ligue 1, Premier League, Liga, Serie A, Bundesliga, Ligue des champions, Euro et Coupe du monde, à 10 requêtes par minute | **Retenue, exige une clé gratuite créée par l'utilisateur** (tâche 7) |
| Comptes X d'actualité (Actu Foot, BeFootball) | pas d'API gratuite fiable | Non couverts (voir spec §11) ; Reddit et Google Actualités assurent la détection rapide |

Le plan gratuit de football-data.org **ne couvre pas** la Ligue Europa, la Ligue Conférence, la Ligue des nations ni les compétitions féminines : leurs actualités passent par les flux RSS uniquement.

## Global Constraints

- Python 3.11 ; commandes Python via `.venv/Scripts/python` ; **annotations de types sur toutes les fonctions** ; aucune dépendance nouvelle.
- Coût 0 € ; dépôt public : **aucun secret dans le code, les tests, les JSON ni les messages**. La clé football-data.org s'appelle `FOOTBALL_DATA_TOKEN` (variable d'environnement, `.env` local ignoré par Git, secret GitHub). Ne jamais l'afficher ni la demander dans la conversation.
- Aucun conseil de pari : les articles de pronostics, cotes et bookmakers sont exclus par la config.
- Le LLM ne décide jamais de la fiabilité, de l'importance ni du niveau. La classification « rumeur » est une règle déterministe sur des marqueurs de la config.
- Toute donnée insérée dans du HTML passe par `esc()` (y compris les noms d'équipes et de compétitions) ; les couleurs par `color()` ; les URL par `safeUrl()`.
- Aucune publication d'un JSON non conforme au contrat : validation avant écriture. Une source ou un appel d'API qui échoue ne bloque jamais le cycle ; l'échec apparaît dans `site/data/health.json` (`football:...`).
- Limite de football-data.org : 10 requêtes par minute. Un cycle en fait 8 (6 classements + 2 fenêtres de matchs). Ne pas en ajouter sans revoir ce budget.
- Réécriture conditionnelle des JSON (ignorer les horodatages) pour rester sous les 100 déploiements Vercel par jour.
- Les fichiers de code s'écrivent avec les outils d'écriture et d'édition de fichiers, jamais avec des scripts Python en ligne contenant des `\` (un `\b` y est devenu un caractère de contrôle lors du jalon 3). Utiliser `git add -A` (sans exclusion de chemin).
- Chaque commit se termine par `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Travail sur la branche `feat/jalon-4`. **Aucun push ni fusion dans `main` sans l'accord explicite de l'utilisateur** (le robot pousse sur `main` toutes les 30 minutes : `git pull --rebase origin main` avant de pousser ; en cas de conflit sur `site/data/` ou `data/events/`, garder la version du robot).
- Tous les chemins sont relatifs à `veille-générale/plateforme/`.

## Review Focus

1. **Rumeurs de mercato** : une piste « serait intéressé » relayée par un seul média reconnu est une `rumeur`, jamais `rapporté` ni `confirmé` ; un « officiel » ou « here we go » dans le titre l'emporte ; deux origines fiables indépendantes restent `confirmé` ; un mot qui contient seulement le début d'un marqueur (« désintéressement ») ne déclenche rien (tests `reliability`).
2. **Clé absente ou invalide, quota dépassé (HTTP 429), réponse mal formée** : le site garde les dernières données marquées non actualisées, le pipeline continue, l'échec est dans `health.json` ; sans clé, aucun appel n'est fait et aucun fichier vide n'est publié (tests `football_data`, `run`).
3. **Page Football** : données de matchs absentes, équipe au nom hostile (`<img onerror>`), match non joué (score nul), onglet ou compétition inconnus : aucune erreur, aucun HTML injecté, message clair (tests `render`).
4. **Mercato** : les rumeurs sont masquées par défaut avec un décompte et un lien pour les afficher ; les informations `officiel` et `confirmé` restent visibles ; aucun événement de type `transfer` n'apparaît dans l'onglet Actu (tests `render`).
5. **Bruit** : pronostics, cotes, paris sportifs, jeux vidéo (EA FC) et jeux concours n'entrent pas dans la veille (test de config et mesure de la tâche 6).

---

### Task 1: Contrat : données football

**Files:**
- Modify: `schemas/public.schema.json` (ajout de définitions)
- Test: `tests/test_contract.py` (ajouts)

**Interfaces:**
- Produces: `engine.contract.validate("football", instance)` avec `instance = {checked_at: str, competitions: [{code, name, stale: bool, standings: [{position, team, played, won, draw, lost, gf, ga, gd, points: int, form: str}]}], results: [match], fixtures: [match]}` et `match = {id: int, competition: str, date: str, home: str, away: str, home_score: int|null, away_score: int|null, status: str, matchday: int|null}`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_contract.py` :
```python
MATCH = {"id": 501, "competition": "FL1", "date": "2026-09-20T18:45:00+00:00", "home": "Marseille", "away": "PSG",
         "home_score": 1, "away_score": 2, "status": "FINISHED", "matchday": 5}
ROW = {"position": 1, "team": "Monaco", "played": 5, "won": 4, "draw": 1, "lost": 0, "gf": 8, "ga": 3, "gd": 5, "points": 13, "form": "WDWWW"}
FOOTBALL = {"checked_at": "2026-09-26T12:00:00+00:00",
            "competitions": [{"code": "FL1", "name": "Ligue 1", "stale": False, "standings": [ROW]}],
            "results": [MATCH], "fixtures": [{**MATCH, "id": 502, "home_score": None, "away_score": None, "status": "SCHEDULED", "matchday": None}]}


def test_football_file_is_valid_with_unplayed_matches_and_empty_lists():
    validate("football", FOOTBALL)
    validate("football", {"checked_at": "t", "competitions": [], "results": [], "fixtures": []})


def test_football_rejects_missing_fields_and_wrong_types():
    bad_row = {**ROW, "points": "13"}
    bad_match = {k: v for k, v in MATCH.items() if k != "home"}
    for bad in ({"competitions": [], "results": [], "fixtures": []},
                {**FOOTBALL, "competitions": [{"code": "FL1", "name": "L1", "stale": False, "standings": [bad_row]}]},
                {**FOOTBALL, "results": [bad_match]},
                {**FOOTBALL, "results": [{**MATCH, "home_score": "1"}]},
                {**FOOTBALL, "competitions": [{"code": "FL1", "name": "L1", "standings": []}]}):
        with pytest.raises(ValidationError):
            validate("football", bad)
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_contract.py -q`
Expected: FAIL (`football` inconnu).

- [ ] **Step 3: Ajouter les définitions au schéma**

Dans `schemas/public.schema.json`, dans l'objet `"$defs"`, après la définition `"quotes"` (ajouter une virgule après son accolade fermante), insérer :
```json
    "standingRow": {
      "type": "object",
      "required": ["position", "team", "played", "won", "draw", "lost", "gf", "ga", "gd", "points", "form"],
      "properties": {
        "position": {"type": "integer"}, "team": {"type": "string"}, "played": {"type": "integer"},
        "won": {"type": "integer"}, "draw": {"type": "integer"}, "lost": {"type": "integer"},
        "gf": {"type": "integer"}, "ga": {"type": "integer"}, "gd": {"type": "integer"},
        "points": {"type": "integer"}, "form": {"type": "string"}
      }
    },
    "match": {
      "type": "object",
      "required": ["id", "competition", "date", "home", "away", "home_score", "away_score", "status", "matchday"],
      "properties": {
        "id": {"type": "integer"}, "competition": {"type": "string"}, "date": {"type": "string"},
        "home": {"type": "string"}, "away": {"type": "string"},
        "home_score": {"type": ["integer", "null"]}, "away_score": {"type": ["integer", "null"]},
        "status": {"type": "string"}, "matchday": {"type": ["integer", "null"]}
      }
    },
    "football": {
      "type": "object",
      "required": ["checked_at", "competitions", "results", "fixtures"],
      "properties": {
        "checked_at": {"type": "string"},
        "competitions": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["code", "name", "stale", "standings"],
            "properties": {
              "code": {"type": "string"}, "name": {"type": "string"}, "stale": {"type": "boolean"},
              "standings": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/standingRow"}}
            }
          }
        },
        "results": {"type": "array", "items": {"$ref": "#/$defs/match"}},
        "fixtures": {"type": "array", "items": {"$ref": "#/$defs/match"}}
      }
    }
```

- [ ] **Step 4: Lancer toute la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout PASS.

- [ ] **Step 5: Commit**

```bash
git checkout feat/jalon-4 2>/dev/null || git checkout -b feat/jalon-4
git add -A
git commit -m "feat(contrat): données football (classements, résultats, calendrier)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Client football-data.org et publication

**Files:**
- Create: `engine/football_data.py`, `config/football.yml`
- Modify: `engine/config.py` (clé `football`), `engine/publish.py` (ajout `publish_football`), `engine/run.py` (import, paramètres, bloc de collecte, `main`)
- Test: `tests/test_football_data.py`, `tests/test_config.py`, `tests/test_run.py` (ajouts)

**Interfaces:**
- Consumes: contrat `football` (tâche 1), `publish.write_if_changed`, `timeutil.{iso, parse}`.
- Produces :
  - `football_data.fetch_fd(url: str, token: str) -> dict` (GET avec l'en-tête `X-Auth-Token`, délai 15 s, `raise_for_status`).
  - `football_data.parse_standings(payload: dict) -> list[dict]` : tableau `type == "TOTAL"` converti en lignes du contrat ; `ValueError` si absent ou vide.
  - `football_data.parse_matches(payload: dict, statuses: set[str]) -> list[dict]` : matchs dont `status` est dans `statuses`, au format `match` du contrat (date normalisée en ISO UTC, score `None` si non joué).
  - `football_data.collect_football(cfg: dict, token: str | None, previous: dict | None, now: datetime, fetch=fetch_fd) -> (football_file | None, health: list[dict])`. Sans jeton : aucun appel, `(None, [échec « FOOTBALL_DATA_TOKEN absent »])`. Sinon 6 appels de classements (un par compétition de `cfg["competitions"]`) puis 2 appels `/matches` (fenêtres passée et future, sans filtre de statut, filtrés localement). En cas d'échec : classement précédent conservé avec `stale: True`, listes de matchs précédentes conservées, échec dans `health` (`football:standings:<code>`, `football:matches:results`, `football:matches:fixtures`). Résultats triés du plus récent au plus ancien, calendrier du plus proche au plus lointain, 40 entrées au plus chacun.
  - `publish.publish_football(root: Path, data: dict) -> None`.
  - `config.load_config(...)["football"]` : contenu de `config/football.yml` ou `None`.
  - `run.run(..., football_token=None, football_fetch=fetch_fd)` ; collecte quand `cfg["football"]` existe et `only is None or "football-data" in only`. `main()` lit `FOOTBALL_DATA_TOKEN`. Le rapport gagne `"football": {"ok": int, "failed": int}`.

- [ ] **Step 1: Écrire les tests qui échouent**

`tests/test_football_data.py` :
```python
import pytest

from engine.contract import validate
from engine.football_data import collect_football, parse_matches, parse_standings
from tests.helpers import NOW

CFG = {"competitions": [{"code": "FL1", "name": "Ligue 1"}, {"code": "PL", "name": "Premier League"}]}


def row(pos, name, played=5, w=4, d=1, l=0, gf=8, ga=3, pts=13, form="W,D,W,W,W"):
    return {"position": pos, "team": {"name": f"{name} FC", "shortName": name}, "playedGames": played, "won": w, "draw": d,
            "lost": l, "goalsFor": gf, "goalsAgainst": ga, "goalDifference": gf - ga, "points": pts, "form": form}


def standings(*rows):
    return {"standings": [{"stage": "REGULAR_SEASON", "type": "HOME", "table": [row(1, "Domicile")]},
                          {"stage": "REGULAR_SEASON", "type": "TOTAL", "table": list(rows)}]}


def match(id, status, home, away, hs=None, aws=None, date="2026-09-20T18:45:00Z", comp="FL1", md=5):
    return {"id": id, "utcDate": date, "status": status, "matchday": md, "competition": {"code": comp},
            "homeTeam": {"shortName": home}, "awayTeam": {"shortName": away},
            "score": {"fullTime": {"home": hs, "away": aws}}}


MATCHES = {"matches": [
    match(1, "FINISHED", "Marseille", "PSG", 1, 2, "2026-09-20T18:45:00Z"),
    match(2, "FINISHED", "Lens", "Lille", 0, 0, "2026-09-25T18:45:00Z"),
    match(3, "TIMED", "Nice", "Brest", None, None, "2026-09-28T18:45:00Z", md=6),
    match(4, "SCHEDULED", "Lyon", "Metz", None, None, "2026-09-27T15:00:00Z", md=6),
    match(5, "CANCELLED", "Nantes", "Reims", None, None, "2026-09-29T15:00:00Z"),
]}


def fake(url, token):
    assert token == "secret"
    return standings(row(1, "Monaco"), row(2, "PSG", pts=12)) if "/standings" in url else MATCHES


def test_parse_standings_reads_the_total_table_only():
    rows = parse_standings(standings(row(1, "Monaco"), row(2, "PSG", pts=12)))
    assert [(r["position"], r["team"], r["points"]) for r in rows] == [(1, "Monaco", 13), (2, "PSG", 12)]
    assert rows[0] == {"position": 1, "team": "Monaco", "played": 5, "won": 4, "draw": 1, "lost": 0, "gf": 8, "ga": 3,
                       "gd": 5, "points": 13, "form": "WDWWW"}


@pytest.mark.parametrize("bad", [{}, {"standings": []}, {"standings": [{"type": "HOME", "table": [row(1, "X")]}]},
                                 {"standings": [{"type": "TOTAL", "table": []}]}])
def test_parse_standings_rejects_missing_or_empty_tables(bad):
    with pytest.raises(ValueError):
        parse_standings(bad)


def test_parse_matches_filters_by_status_and_maps_scores_and_dates():
    played = parse_matches(MATCHES, {"FINISHED"})
    assert [m["id"] for m in played] == [1, 2]
    assert played[0] == {"id": 1, "competition": "FL1", "date": "2026-09-20T18:45:00+00:00", "home": "Marseille",
                         "away": "PSG", "home_score": 1, "away_score": 2, "status": "FINISHED", "matchday": 5}
    upcoming = parse_matches(MATCHES, {"SCHEDULED", "TIMED"})
    assert [m["id"] for m in upcoming] == [3, 4] and upcoming[0]["home_score"] is None
    assert parse_matches({}, {"FINISHED"}) == []


def test_collect_builds_a_valid_sorted_file_with_one_request_per_call():
    calls = []
    data, health = collect_football(CFG, "secret", None, NOW, lambda url, t: calls.append(url) or fake(url, t))
    validate("football", data)
    assert len(calls) == 4                                      # 2 classements + 2 fenêtres de matchs
    assert [c["code"] for c in data["competitions"]] == ["FL1", "PL"] and not any(c["stale"] for c in data["competitions"])
    assert [m["id"] for m in data["results"]] == [2, 1]         # du plus récent au plus ancien
    assert [m["id"] for m in data["fixtures"]] == [4, 3]        # du plus proche au plus lointain
    assert all(h["ok"] for h in health)
    assert {h["source"] for h in health} == {"football:standings:FL1", "football:standings:PL",
                                             "football:matches:results", "football:matches:fixtures"}


def test_match_windows_respect_the_ten_day_limit_of_the_free_plan():
    urls = []
    collect_football(CFG, "secret", None, NOW, lambda url, t: urls.append(url) or fake(url, t))
    windows = [u for u in urls if "/matches" in u]
    assert len(windows) == 2 and all("competitions=FL1,PL" in u for u in windows)
    assert "dateFrom=2026-09-17" in windows[0] and "dateTo=2026-09-26" in windows[0]
    assert "dateFrom=2026-09-26" in windows[1] and "dateTo=2026-10-05" in windows[1]


def test_without_a_token_nothing_is_requested_and_nothing_is_published():
    def never(url, t):
        raise AssertionError("aucun appel attendu")
    data, health = collect_football(CFG, None, None, NOW, never)
    assert data is None and len(health) == 1 and health[0]["ok"] is False and "FOOTBALL_DATA_TOKEN" in health[0]["error"]
    assert collect_football(CFG, "", None, NOW, never)[0] is None


def test_failures_keep_the_previous_values_marked_stale():
    first, _ = collect_football(CFG, "secret", None, NOW, fake)

    def flaky(url, t):
        if "/standings" in url and "/FL1/" in url:
            raise TimeoutError("boom")
        if "/matches" in url:
            raise RuntimeError("429 Too Many Requests")
        return fake(url, t)

    second, health = collect_football(CFG, "secret", first, NOW, flaky)
    by = {c["code"]: c for c in second["competitions"]}
    assert by["FL1"]["stale"] is True and by["FL1"]["standings"] == first["competitions"][0]["standings"]
    assert by["PL"]["stale"] is False
    assert second["results"] == first["results"] and second["fixtures"] == first["fixtures"]
    assert [h["ok"] for h in health] == [False, True, False, False]
    validate("football", second)


def test_failure_without_history_omits_the_competition_and_keeps_going():
    def only_pl(url, t):
        if "/FL1/" in url:
            raise ValueError("boom")
        return fake(url, t)
    data, _ = collect_football(CFG, "secret", None, NOW, only_pl)
    assert [c["code"] for c in data["competitions"]] == ["PL"]
    validate("football", data)


def test_malformed_answers_are_handled_like_failures():
    data, health = collect_football(CFG, "secret", None, NOW, lambda url, t: {"unexpected": True})
    assert data["competitions"] == [] and data["results"] == [] and data["fixtures"] == []
    assert not any(h["ok"] for h in health)


def test_lists_are_capped_at_forty_entries():
    many = {"matches": [match(i, "FINISHED", "A", "B", 1, 0, f"2026-09-{(i % 9) + 17:02d}T18:00:00Z") for i in range(60)]}
    data, _ = collect_football(CFG, "secret", None, NOW, lambda url, t: standings(row(1, "X")) if "/standings" in url else many)
    assert len(data["results"]) == 40
```

Ajouter à la fin de `tests/test_config.py` :
```python
def test_football_config_is_optional_and_the_real_one_is_well_formed(tmp_path):
    (tmp_path / "config" / "domains").mkdir(parents=True)
    (tmp_path / "config" / "global.yml").write_text("cluster: {threshold: 0.5}\n", "utf-8")
    assert load_config(tmp_path)["football"] is None
    real = load_config()["football"]
    codes = [c["code"] for c in real["competitions"]]
    assert len(codes) == len(set(codes)) and 1 <= len(codes) <= 6      # budget : 6 classements + 2 fenêtres = 8 requêtes par minute
    assert all(c["name"].strip() for c in real["competitions"])
    assert 1 <= real["results_days"] <= 9 and 1 <= real["fixtures_days"] <= 9      # limite de 10 jours du plan gratuit
```

Ajouter à la fin de `tests/test_run.py` :
```python
FB_CFG = {"competitions": [{"code": "FL1", "name": "Ligue 1"}], "results_days": 9, "fixtures_days": 9}


def fb_fetch(url, token):
    if "/standings" in url:
        return {"standings": [{"type": "TOTAL", "table": [{"position": 1, "team": {"shortName": "Monaco"}, "playedGames": 5,
                "won": 4, "draw": 1, "lost": 0, "goalsFor": 8, "goalsAgainst": 3, "goalDifference": 5, "points": 13, "form": "W,D"}]}]}
    return {"matches": [{"id": 1, "utcDate": "2026-09-25T18:45:00Z", "status": "FINISHED", "matchday": 5, "competition": {"code": "FL1"},
                         "homeTeam": {"shortName": "Lens"}, "awayTeam": {"shortName": "Lille"}, "score": {"fullTime": {"home": 0, "away": 0}}}]}


def test_run_publishes_football_data_when_a_token_is_given(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "football.yml").write_text(yaml.safe_dump(FB_CFG), "utf-8")
    report = run(tmp_path, now=NOW, fetch=fake_fetch, football_token="secret", football_fetch=fb_fetch)
    data = json.loads((tmp_path / "site" / "data" / "football.json").read_text("utf-8"))
    validate("football", data)
    assert data["competitions"][0]["standings"][0]["team"] == "Monaco" and data["results"][0]["home"] == "Lens"
    assert report["football"] == {"ok": 3, "failed": 0}


def test_run_without_a_token_reports_it_and_publishes_nothing(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "football.yml").write_text(yaml.safe_dump(FB_CFG), "utf-8")
    report = run(tmp_path, now=NOW, fetch=fake_fetch, football_token=None, football_fetch=fb_fetch)
    assert not (tmp_path / "site" / "data" / "football.json").exists()
    assert "football-data" in report["sources_failed"] and report["football"] == {"ok": 0, "failed": 1}


def test_football_data_is_skipped_when_only_names_other_domains(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "football.yml").write_text(yaml.safe_dump(FB_CFG), "utf-8")
    run(tmp_path, now=NOW, fetch=fake_fetch, only=["ia"], football_token="secret", football_fetch=fb_fetch)
    assert not (tmp_path / "site" / "data" / "football.json").exists()


def test_football_file_is_not_rewritten_when_nothing_changed(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "football.yml").write_text(yaml.safe_dump(FB_CFG), "utf-8")
    path = tmp_path / "site" / "data" / "football.json"
    run(tmp_path, now=NOW, fetch=fake_fetch, football_token="secret", football_fetch=fb_fetch)
    first = path.read_bytes()
    run(tmp_path, now=NOW.replace(hour=13), fetch=fake_fetch, football_token="secret", football_fetch=fb_fetch)
    assert path.read_bytes() == first
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_football_data.py tests/test_config.py tests/test_run.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'engine.football_data'`).

- [ ] **Step 3: Écrire `config/football.yml`**

```yaml
competitions:                  # plan gratuit de football-data.org : 10 requêtes par minute, donc 6 classements + 2 fenêtres de matchs
  - {code: FL1, name: "Ligue 1"}
  - {code: PL, name: "Premier League"}
  - {code: PD, name: "Liga"}
  - {code: SA, name: "Serie A"}
  - {code: BL1, name: "Bundesliga"}
  - {code: CL, name: "Ligue des champions"}
results_days: 9                # les fenêtres de /matches sont limitées à 10 jours par le plan gratuit
fixtures_days: 9
```

- [ ] **Step 4: Écrire `engine/football_data.py`**

```python
from collections.abc import Callable
from datetime import datetime, timedelta

import requests

from .timeutil import iso, parse

_BASE = "https://api.football-data.org/v4"
_FIXTURE_STATUSES = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "POSTPONED"}
_KEEP = 40


def fetch_fd(url: str, token: str) -> dict:
    r = requests.get(url, headers={"X-Auth-Token": token}, timeout=15)
    r.raise_for_status()
    return r.json()


def _team(team: dict) -> str:
    return team.get("shortName") or team.get("name") or "?"


def parse_standings(payload: dict) -> list[dict]:
    tables = [s for s in payload.get("standings", []) if s.get("type") == "TOTAL" and s.get("table")]
    if not tables:
        raise ValueError("aucun classement TOTAL dans la réponse")
    return [{
        "position": r["position"], "team": _team(r["team"]), "played": r["playedGames"], "won": r["won"],
        "draw": r["draw"], "lost": r["lost"], "gf": r["goalsFor"], "ga": r["goalsAgainst"],
        "gd": r["goalDifference"], "points": r["points"], "form": (r.get("form") or "").replace(",", ""),
    } for r in tables[0]["table"]]


def parse_matches(payload: dict, statuses: set[str]) -> list[dict]:
    out = []
    for m in payload.get("matches", []):
        if m.get("status") not in statuses:
            continue
        full = (m.get("score") or {}).get("fullTime") or {}
        out.append({
            "id": m["id"], "competition": m["competition"]["code"], "date": iso(parse(m["utcDate"])),
            "home": _team(m["homeTeam"]), "away": _team(m["awayTeam"]),
            "home_score": full.get("home"), "away_score": full.get("away"),
            "status": m["status"], "matchday": m.get("matchday"),
        })
    return out


def _try(health: list, source: str, action: Callable[[], object]) -> object | None:
    try:
        result = action()
        health.append({"source": source, "ok": True, "count": len(result) if hasattr(result, "__len__") else 1, "error": None})
        return result
    except Exception as exc:  # un appel défaillant ne doit jamais arrêter le cycle
        health.append({"source": source, "ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"})
        return None


def collect_football(cfg: dict, token: str | None, previous: dict | None, now: datetime,
                     fetch: Callable[[str, str], dict] = fetch_fd) -> tuple[dict | None, list[dict]]:
    if not token:
        return None, [{"source": "football-data", "ok": False, "count": 0,
                       "error": "FOOTBALL_DATA_TOKEN absent : classements, résultats et calendrier non mis à jour"}]
    old = previous or {}
    old_comps = {c["code"]: c for c in old.get("competitions", [])}
    health, comps = [], []
    for c in cfg["competitions"]:
        rows = _try(health, f"football:standings:{c['code']}",
                    lambda c=c: parse_standings(fetch(f"{_BASE}/competitions/{c['code']}/standings", token)))
        if rows:
            comps.append({"code": c["code"], "name": c["name"], "standings": rows, "stale": False})
        elif c["code"] in old_comps:
            comps.append({**old_comps[c["code"]], "name": c["name"], "stale": True})
    codes = ",".join(c["code"] for c in cfg["competitions"])
    today = now.date()

    def window(start, end):
        return f"{_BASE}/matches?competitions={codes}&dateFrom={start.isoformat()}&dateTo={end.isoformat()}"

    played = _try(health, "football:matches:results", lambda: sorted(parse_matches(
        fetch(window(today - timedelta(days=cfg.get("results_days", 9)), today), token), {"FINISHED"}),
        key=lambda m: m["date"], reverse=True)[:_KEEP])
    upcoming = _try(health, "football:matches:fixtures", lambda: sorted(parse_matches(
        fetch(window(today, today + timedelta(days=cfg.get("fixtures_days", 9))), token), _FIXTURE_STATUSES),
        key=lambda m: m["date"])[:_KEEP])
    return {"checked_at": iso(now), "competitions": comps,
            "results": played if played is not None else old.get("results", []),
            "fixtures": upcoming if upcoming is not None else old.get("fixtures", [])}, health
```

- [ ] **Step 5: Adapter `engine/config.py`**

Remplacer la fonction `load_config` par :
```python
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
    return {"global": g, "domains": domains, "quotes": quotes, "football": football}
```

- [ ] **Step 6: Ajouter `publish_football` à `engine/publish.py`**

À la fin du fichier :
```python
def publish_football(root: Path, data: dict) -> None:
    validate("football", data)
    write_if_changed(root / "site" / "data" / "football.json", data)
```

- [ ] **Step 7: Adapter `engine/run.py`**

Ajouter les imports (à leur place alphabétique) : `from .football_data import collect_football, fetch_fd` et compléter `from .publish import ...` avec `publish_football`. Ajouter avant `def run(` la fonction :
```python
def _previous_football(root: Path) -> dict | None:
    path = root / "site" / "data" / "football.json"
    try:
        return json.loads(path.read_text("utf-8")) if path.exists() else None
    except ValueError:
        return None
```
Remplacer la signature de `run` par :
```python
def run(root: Path = ROOT, now: datetime | None = None, only: list[str] | None = None,
        call: Callable[[str], str] | None = None, fetch: Callable[[str], bytes] = fetch_bytes,
        quote_fetch: Callable[[str], dict] = fetch_relay,
        agenda_fetch: Callable[[str], list[str]] = fetch_points,
        football_token: str | None = None,
        football_fetch: Callable[[str, str], dict] = fetch_fd) -> dict:
```
Dans le dictionnaire `report`, ajouter la clé `"football": {"ok": 0, "failed": 0},` après `"quotes"`. Après le bloc `if cfg["quotes"] and (...)` et avant `report["sources_failed"] = ...`, ajouter :
```python
    if cfg["football"] and (only is None or "football-data" in only):
        data, fhealth = collect_football(cfg["football"], football_token, _previous_football(root), now, football_fetch)
        if data is not None:
            publish_football(root, data)
        health += fhealth
        report["football"] = {"ok": sum(h["ok"] for h in fhealth), "failed": sum(not h["ok"] for h in fhealth)}
```
Dans `main()`, remplacer la ligne `print(json.dumps(run(only=args.only, call=call), ensure_ascii=False, indent=2))` par :
```python
    report = run(only=args.only, call=call, football_token=os.environ.get("FOOTBALL_DATA_TOKEN"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
```
et mettre à jour l'aide de `--only` : `« quotes » ou « football-data »`.

- [ ] **Step 8: Lancer toute la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout PASS.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(engine): classements, résultats et calendrier via football-data.org (clé optionnelle)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Rumeurs de mercato (règle de fiabilité pilotée par la config)

**Files:**
- Modify: `engine/reliability.py`, `engine/run.py` (fonction `rescore`)
- Test: `tests/test_reliability.py` (ajouts)

**Interfaces:**
- Consumes: `classify` du jalon 2.
- Produces: `reliability.classify(items: list, now: datetime, dom: dict | None = None) -> (label, reason)`. Sans `dom`, comportement inchangé. Avec `dom`, si l'étiquette calculée est `rapporté` ou `non_confirmé` **et** que le texte (titres et extraits) contient un marqueur de `dom["rumor_markers"]` **et** aucun marqueur de `dom["confirm_markers"]`, l'étiquette devient `rumeur`. Un marqueur correspond au **début d'un mot** (insensible à la casse ; `intéress` correspond à « intéressé », pas à « désintéressement »). Les événements `officiel`, `confirmé` et `en_développement` ne sont jamais modifiés.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_reliability.py` :
```python
DOM_FB = {"rumor_markers": ["serait", "intéress", "dans le viseur"], "confirm_markers": ["officiel", "here we go"]}


def test_hedged_single_source_transfer_is_a_rumor_even_from_a_reliable_outlet():
    items = [mk_item("a", "Mbappé serait dans le viseur du Real", tier=2)]
    assert classify(items, NOW, DOM_FB)[0] == "rumeur"
    assert classify(items, NOW)[0] == "rapporté"                       # sans config, comportement inchangé
    assert classify([mk_item("a", "Un joueur intéressé par un départ", tier=3)], NOW, DOM_FB)[0] == "rumeur"


def test_confirmation_markers_win_over_rumor_markers():
    items = [mk_item("a", "Officiel : le Real annonce l'arrivée, le PSG était intéressé", tier=2)]
    assert classify(items, NOW, DOM_FB)[0] == "rapporté"
    assert classify([mk_item("a", "Here we go, il serait proche de signer", tier=2)], NOW, DOM_FB)[0] == "rapporté"


def test_strong_labels_are_never_downgraded_by_rumor_markers():
    two = [mk_item("a", "Il serait intéressé", tier=2), mk_item("b", "Il serait intéressé", tier=2)]
    assert classify(two, NOW, DOM_FB)[0] == "confirmé"
    assert classify([mk_item("a", "Il serait intéressé", tier=1)], NOW, DOM_FB)[0] == "officiel"


def test_markers_match_word_starts_only():
    assert classify([mk_item("a", "Le désintéressement du club est total", tier=2)], NOW, DOM_FB)[0] == "rapporté"
    assert classify([mk_item("a", "SERAIT-il prêt ?", tier=2)], NOW, DOM_FB)[0] == "rumeur"


def test_missing_marker_lists_change_nothing():
    items = [mk_item("a", "Il serait intéressé", tier=2)]
    assert classify(items, NOW, {})[0] == "rapporté"
    assert classify(items, NOW, {"rumor_markers": ["serait"]})[0] == "rumeur"


def test_rescore_passes_the_domain_markers_to_the_classifier():
    from engine.run import rescore
    from tests.helpers import DOM, G, mk_event
    ev = mk_event([mk_item("a", "Le club serait intéressé par le joueur", tier=2)], id="ev_r", entities=[])
    assert rescore([ev], {**DOM, "rumor_markers": ["serait"]}, G, NOW)[0]["reliability"] == "rumeur"
    assert rescore([ev], DOM, G, NOW)[0]["reliability"] == "rapporté"
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_reliability.py -q`
Expected: FAIL (`classify() takes 2 positional arguments but 3 were given`).

- [ ] **Step 3: Implémenter**

Dans `engine/reliability.py` : renommer la fonction existante `def classify(items: list, now: datetime) -> tuple[str, str]:` en `def _classify(items: list, now: datetime) -> tuple[str, str]:`, puis ajouter à la fin du fichier :
```python
def _matches(text: str, markers: list[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"(?<!\w){re.escape(m.lower())}", low) for m in markers)


def classify(items: list, now: datetime, dom: dict | None = None) -> tuple[str, str]:
    label, reason = _classify(items, now)
    if dom and label in ("rapporté", "non_confirmé"):
        text = " ".join(f"{i['title']} {i['snippet']}" for i in items)
        if _matches(text, dom.get("rumor_markers", [])) and not _matches(text, dom.get("confirm_markers", [])):
            return "rumeur", "formulation de piste ou de rumeur (« serait », « intéressé »...) sans confirmation"
    return label, reason
```
Dans `engine/run.py`, dans `rescore`, remplacer `label, reason = classify(ev["items"], now)` par `label, reason = classify(ev["items"], now, dom)`.

- [ ] **Step 4: Lancer toute la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(reliability): rumeurs de mercato détectées par marqueurs de la config de veille" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Site : page Football à onglets et bande de l'Accueil

**Files:**
- Modify: `site/js/render.js`, `site/js/data.js`, `site/js/app.js`, `site/css/app.css`, `site/tools/make-sample.mjs`, `tests/test_sample_data.py`
- Test: `site/tests/render.test.mjs` (ajouts)

**Interfaces:**
- Consumes: `data/football.json` (contrat `football`), événements de kind `transfer`.
- Produces (module `render.js`) :
  - `matchLine(m) -> string` (`<li class="match">`; score « 1 – 2 » si les deux scores sont des entiers, sinon date et heure du coup d'envoi).
  - `renderMatches(list, football) -> string` (groupé par compétition, nom lu dans `football.competitions`).
  - `renderStandings(comp) -> string` (tableau `#, Équipe, J, G, N, P, Diff, Pts, Forme` ; mention « non actualisé » si `comp.stale`).
  - `footballStrip(football) -> string` (`<div class="fb-strip">` : 6 derniers résultats et 6 prochains matchs ; vide si rien).
  - `renderFootball(file, football, tab, arg, state, now) -> string` : onglets `actu` (défaut), `resultats`, `classements` (`arg` = code de compétition), `calendrier`, `mercato` (`arg === 'rumeurs'` affiche aussi les événements `rumeur` et `non_confirmé`).
  - `renderDomain(file, state, now, quotes = null, football = null, tab = 'actu', arg = null)` : délègue à `renderFootball` quand `file.domain.id === 'football'`.
  - `domainBlock(dom, events, state, now, quotes = null, football = null)` et `renderHome(home, state, now, since = null, quotes = null, football = null)` : la bande apparaît dans le bloc `football`.
  - `renderNav` marque la veille active aussi pour les sous-routes (`#/d/football/resultats`).
- Routes : `#/d/football`, `#/d/football/<tab>`, `#/d/football/classements/<code>`, `#/d/football/mercato/rumeurs`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `site/tests/render.test.mjs` (et ajouter `matchLine, renderMatches, renderStandings, footballStrip, renderFootball` à l'import de `../js/render.js`) :
```js
const M = (o = {}) => ({ id: 1, competition: 'FL1', date: '2026-09-20T18:45:00Z', home: 'Marseille', away: 'PSG', home_score: 1, away_score: 2, status: 'FINISHED', matchday: 5, ...o });
const ROW = (o = {}) => ({ position: 1, team: 'Monaco', played: 5, won: 4, draw: 1, lost: 0, gf: 8, ga: 3, gd: 5, points: 13, form: 'WDWWW', ...o });
const FB = (o = {}) => ({
  checked_at: 'x',
  competitions: [{ code: 'FL1', name: 'Ligue 1', stale: false, standings: [ROW(), ROW({ position: 2, team: 'PSG', points: 12 })] },
                 { code: 'PL', name: 'Premier League', stale: true, standings: [ROW({ team: 'Arsenal' })] }],
  results: [M(), M({ id: 2, home: 'Lens', away: 'Lille', home_score: 0, away_score: 0 })],
  fixtures: [M({ id: 3, home: 'Nice', away: 'Brest', home_score: null, away_score: null, status: 'TIMED', date: '2026-09-28T18:45:00Z' })],
  ...o,
});
const fbFile = (events = []) => ({ domain: { id: 'football', name: 'Football', accent: '#0B6E4F' }, events, upcoming: [] });
const fbEv = (id, o = {}) => ev({ id, domain: 'football', kind: 'other', ...o });

test('un match joué affiche son score, un match à venir sa date', () => {
  assert.match(matchLine(M()), /1 – 2/);
  assert.match(matchLine(M({ home_score: 0, away_score: 0 })), /0 – 0/);
  const next = matchLine(M({ home_score: null, away_score: null, date: '2026-09-28T18:45:00Z' }));
  assert.ok(!next.includes('–'));
  assert.match(next, /class="match next"/);
});

test('les noms d’équipes et de compétitions sont échappés', () => {
  const html = renderMatches([M({ home: '<img src=x onerror=alert(1)>', competition: 'X"><script>' })], FB());
  assert.ok(!html.includes('<img') && !html.includes('<script>'));
  const table = renderStandings({ code: 'A', name: 'A', stale: false, standings: [ROW({ team: '<b onmouseover=x>' })] });
  assert.ok(!table.includes('<b onmouseover'));
});

test('les matchs sont groupés par compétition avec le nom lu dans les données', () => {
  const html = renderMatches(FB().results, FB());
  assert.match(html, /Ligue 1/);
  assert.equal((html.match(/<h3/g) || []).length, 1);
  assert.match(renderMatches([], FB()), /Aucun match/);
});

test('le classement affiche les colonnes et signale un classement périmé', () => {
  const html = renderStandings(FB().competitions[1]);
  for (const col of ['Équipe', 'Pts', 'Diff', 'Forme']) assert.ok(html.includes(col), col);
  assert.match(html, /Arsenal/);
  assert.match(html, /non actualisé/);
  assert.ok(!renderStandings(FB().competitions[0]).includes('non actualisé'));
});

test('la page Football propose les cinq onglets et marque l’onglet actif', () => {
  const html = renderFootball(fbFile(), FB(), 'resultats', null, defaultState(), NOW);
  for (const t of ['Actu', 'Résultats', 'Classements', 'Calendrier', 'Mercato']) assert.ok(html.includes(t), t);
  assert.match(html, /href="#\/d\/football\/resultats" aria-current="page"/);
  assert.match(html, /Marseille/);
});

test('onglets résultats, calendrier et classements sans données affichent un message', () => {
  for (const tab of ['resultats', 'calendrier', 'classements']) {
    assert.match(renderFootball(fbFile(), null, tab, null, defaultState(), NOW), /Données indisponibles/);
  }
  assert.match(renderFootball(fbFile(), FB({ competitions: [] }), 'classements', null, defaultState(), NOW), /Données indisponibles/);
});

test('l’onglet classements choisit la compétition demandée, sinon la première, sans planter sur un code inconnu', () => {
  const pl = renderFootball(fbFile(), FB(), 'classements', 'PL', defaultState(), NOW);
  assert.match(pl, /Arsenal/);
  assert.ok(!pl.includes('>Monaco<'));
  assert.match(renderFootball(fbFile(), FB(), 'classements', 'ZZZ', defaultState(), NOW), /Monaco/);
  assert.match(renderFootball(fbFile(), FB(), 'inconnu', null, defaultState(), NOW), /Rien d’important/);
});

test('le mercato masque les rumeurs par défaut avec un décompte et un lien, et les affiche à la demande', () => {
  const events = [fbEv('t1', { kind: 'transfer', title: 'Transfert acté', reliability: 'officiel' }),
                  fbEv('t2', { kind: 'transfer', title: 'Piste évoquée', reliability: 'rumeur' }),
                  fbEv('t3', { kind: 'transfer', title: 'Autre piste', reliability: 'non_confirmé' }),
                  fbEv('n1', { title: 'Résultat du week-end' })];
  const hidden = renderFootball(fbFile(events), FB(), 'mercato', null, defaultState(), NOW);
  assert.match(hidden, /Transfert acté/);
  assert.ok(!hidden.includes('Piste évoquée') && !hidden.includes('Résultat du week-end'));
  assert.match(hidden, /Afficher les rumeurs \(2 masquées\)/);
  const all = renderFootball(fbFile(events), FB(), 'mercato', 'rumeurs', defaultState(), NOW);
  assert.match(all, /Piste évoquée/);
  assert.match(all, /Masquer les rumeurs/);
  assert.match(renderFootball(fbFile([]), FB(), 'mercato', null, defaultState(), NOW), /Aucune information de mercato/);
});

test('l’onglet Actu exclut les transferts', () => {
  const events = [fbEv('t1', { kind: 'transfer', title: 'Transfert acté' }), fbEv('n1', { title: 'Résultat du week-end' })];
  const html = renderFootball(fbFile(events), FB(), 'actu', null, defaultState(), NOW);
  assert.match(html, /Résultat du week-end/);
  assert.ok(!html.includes('Transfert acté'));
});

test('renderDomain délègue à la page Football uniquement pour la veille football', () => {
  const file = fbFile();
  assert.match(renderDomain(file, defaultState(), NOW, null, FB(), 'calendrier'), /Nice/);
  const other = renderDomain({ domain: { id: 'ia', name: 'IA', accent: '#5B3FA8' }, events: [], upcoming: [] }, defaultState(), NOW, null, FB());
  assert.ok(!other.includes('Calendrier'));
});

test('la bande de l’Accueil n’apparaît que dans le bloc football, avec 6 lignes au plus par colonne', () => {
  const many = FB({ results: Array.from({ length: 9 }, (_, i) => M({ id: i, home: `H${i}` })) });
  const strip = footballStrip(many);
  assert.match(strip, /Derniers résultats/);
  assert.match(strip, /Prochains matchs/);
  assert.equal((strip.match(/class="match"/g) || []).length, 6);
  assert.equal(footballStrip(null), '');
  assert.equal(footballStrip(FB({ results: [], fixtures: [] })), '');
  const block = domainBlock(dom({ id: 'football', name: 'Football' }), {}, defaultState(), NOW, null, FB());
  assert.match(block, /fb-strip/);
  assert.ok(!domainBlock(dom(), {}, defaultState(), NOW, null, FB()).includes('fb-strip'));
});

test('la veille active reste marquée dans la navigation sur une sous-route', () => {
  const home = { domains: [dom({ id: 'football', name: 'Football' })], events: {} };
  assert.match(renderNav(home, defaultState(), '#/d/football/classements/PL'), /href="#\/d\/football" aria-current="page"/);
  assert.ok(!renderNav(home, defaultState(), '#/d/footballeur').includes('aria-current="page"><span>Football'));
});
```

Ajouter à la fin de `tests/test_sample_data.py` :
```python
def test_sample_includes_valid_football_data(data):
    football = json.loads((data / "football.json").read_text("utf-8"))
    validate("football", football)
    assert any(c["stale"] for c in football["competitions"]) and football["results"] and football["fixtures"]
    assert any(m["home_score"] is None for m in football["fixtures"])
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `(cd site && node --test "tests/*.test.mjs") ; .venv/Scripts/python -m pytest tests/test_sample_data.py -q`
Expected: FAIL (`matchLine` n'existe pas ; `football.json` absent de l'exemple).

- [ ] **Step 3: Modifier `site/js/render.js`**

1. Ajouter, après la fonction `layersBlock`, le code suivant :
```js
const FB_TABS = [['actu', 'Actu'], ['resultats', 'Résultats'], ['classements', 'Classements'], ['calendrier', 'Calendrier'], ['mercato', 'Mercato']];
const HIDDEN_IN_MERCATO = ['rumeur', 'non_confirmé'];
const compName = (football, code) => football?.competitions?.find((c) => c.code === code)?.name ?? code;
const fmtKickoff = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

export function matchLine(m) {
  const played = Number.isInteger(m.home_score) && Number.isInteger(m.away_score);
  const middle = played ? `${m.home_score} – ${m.away_score}` : fmtKickoff(m.date);
  return `<li class="match${played ? '' : ' next'}"><span class="mh">${esc(m.home)}</span><span class="ms">${esc(middle)}</span><span class="ma">${esc(m.away)}</span></li>`;
}

export function renderMatches(list, football) {
  if (!list || !list.length) return '<p class="meta">Aucun match à afficher.</p>';
  const codes = [...new Set(list.map((m) => m.competition))];
  return codes
    .map((code) => `<h3 class="cmp">${esc(compName(football, code))}</h3><ul class="matches">${list.filter((m) => m.competition === code).map(matchLine).join('')}</ul>`)
    .join('');
}

export function renderStandings(comp) {
  const rows = comp.standings
    .map((r) => `<tr><td>${esc(r.position)}</td><td class="tn">${esc(r.team)}</td><td>${esc(r.played)}</td><td>${esc(r.won)}</td><td>${esc(r.draw)}</td><td>${esc(r.lost)}</td><td>${esc(r.gd)}</td><td><b>${esc(r.points)}</b></td><td class="form">${esc(r.form)}</td></tr>`)
    .join('');
  return `<table class="standings"><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>Diff</th><th>Pts</th><th>Forme</th></tr></thead><tbody>${rows}</tbody></table>${comp.stale ? '<p class="meta">Classement non actualisé.</p>' : ''}`;
}

export function footballStrip(football) {
  if (!football) return '';
  const last = (football.results ?? []).slice(0, 6);
  const next = (football.fixtures ?? []).slice(0, 6);
  if (!last.length && !next.length) return '';
  const col = (title, list) => (list.length ? `<div><h3 class="cmp">${title}</h3><ul class="matches">${list.map(matchLine).join('')}</ul></div>` : '');
  return `<div class="fb-strip">${col('Derniers résultats', last)}${col('Prochains matchs', next)}</div>`;
}

function eventSections(events, state, now) {
  const by = (n) => events.filter((e) => e.level === n);
  const st = (e) => eventStatus(state, e);
  const section = (title, list, fn) => (list.length ? `<h2>${title}</h2>${list.map((e) => fn(e, st(e), now)).join('')}` : '');
  return `${section('Incontournable', by(1), card)}${section('Important', by(2), row)}${section('À savoir', by(3), row)}`;
}

const fbTabs = (tab) =>
  `<div class="tabs">${FB_TABS.map(([k, t]) => `<a href="#/d/football${k === 'actu' ? '' : `/${k}`}"${k === tab ? ' aria-current="page"' : ''}>${t}</a>`).join('')}</div>`;

export function renderFootball(file, football, tab, arg, state, now) {
  const unavailable = '<p class="meta">Données indisponibles pour le moment.</p>';
  let body;
  if (tab === 'resultats') {
    body = football ? `<h2>Résultats récents</h2>${renderMatches(football.results, football)}` : unavailable;
  } else if (tab === 'calendrier') {
    body = football ? `<h2>Prochains matchs</h2>${renderMatches(football.fixtures, football)}` : unavailable;
  } else if (tab === 'classements') {
    const comps = football?.competitions ?? [];
    if (!comps.length) {
      body = unavailable;
    } else {
      const cur = comps.find((c) => c.code === arg) ?? comps[0];
      const subtabs = comps.map((c) => `<a href="#/d/football/classements/${enc(c.code)}"${c.code === cur.code ? ' aria-current="page"' : ''}>${esc(c.name)}</a>`).join('');
      body = `<div class="tabs sub">${subtabs}</div><h2>${esc(cur.name)}</h2>${renderStandings(cur)}`;
    }
  } else if (tab === 'mercato') {
    const all = file.events.filter((e) => e.kind === 'transfer');
    const showAll = arg === 'rumeurs';
    const shown = showAll ? all : all.filter((e) => !HIDDEN_IN_MERCATO.includes(e.reliability));
    const hidden = all.length - shown.length;
    const toggle = hidden
      ? `<p class="meta"><a href="#/d/football/mercato/rumeurs">Afficher les rumeurs (${plural(hidden, 'masquée')})</a></p>`
      : showAll ? '<p class="meta"><a href="#/d/football/mercato">Masquer les rumeurs</a></p>' : '';
    body = `${toggle}${shown.length ? eventSections(shown, state, now) : '<p class="meta">Aucune information de mercato pour l’instant.</p>'}`;
  } else {
    const news = file.events.filter((e) => e.kind !== 'transfer');
    body = `${news.length ? eventSections(news, state, now) : '<p class="meta">Rien d’important pour l’instant.</p>'}${upcomingList(file.upcoming)}`;
  }
  const tabName = FB_TABS.some(([k]) => k === tab) ? tab : 'actu';
  return `<div style="--dom:${color(file.domain.accent)}"><a class="back" href="#/">← Accueil</a><h1>${esc(file.domain.name)}</h1>${fbTabs(tabName)}${body}</div>`;
}
```
2. Remplacer la signature `export function domainBlock(dom, events, state, now, quotes = null) {` par `export function domainBlock(dom, events, state, now, quotes = null, football = null) {` et, dans son gabarit, remplacer la ligne `    ${more}` par :
```js
    ${more}
    ${dom.id === 'football' ? footballStrip(football) : ''}
```
3. Remplacer `export function renderHome(home, state, now, since = null, quotes = null) {` par `export function renderHome(home, state, now, since = null, quotes = null, football = null) {` et l'appel `domainBlock(d, home.events, state, now, quotes)` par `domainBlock(d, home.events, state, now, quotes, football)`.
4. Remplacer la fonction `renderDomain` par :
```js
export function renderDomain(file, state, now, quotes = null, football = null, tab = 'actu', arg = null) {
  if (file.domain.id === 'football') return renderFootball(file, football, tab, arg, state, now);
  const empty = !file.events.length;
  return `<div style="--dom:${color(file.domain.accent)}"><a class="back" href="#/">← Accueil</a>
    <h1>${esc(file.domain.name)}</h1>
    ${file.domain.id === 'finance' ? renderQuotes(quotes, now) : ''}
    ${empty ? '<p class="meta">Rien d’important pour l’instant.</p>' : ''}
    ${eventSections(file.events, state, now)}
    ${upcomingList(file.upcoming)}</div>`;
}
```
5. Dans `renderNav`, remplacer la fonction `link` par :
```js
  const isActive = (h) => (h === '#/' ? activeHash === h : activeHash === h || activeHash.startsWith(`${h}/`));
  const link = (h, label, n) =>
    `<a href="${h}"${isActive(h) ? ' aria-current="page"' : ''}><span>${esc(label)}</span>${n ? `<span class="count">${n}</span>` : ''}</a>`;
```

- [ ] **Step 4: Modifier `site/js/data.js` et `site/js/app.js`**

Ajouter à la fin de `site/js/data.js` : `export const loadFootball = () => get('data/football.json');`.
Dans `site/js/app.js` : importer `loadFootball` (`import { loadHome, loadDomain, loadQuotes, loadFootball } from './data.js';`), déclarer `let football = null;`, remplacer la ligne de la route veille par :
```js
    if (hash.startsWith('#/d/')) {
      const [id, tab = 'actu', arg = null] = hash.slice(4).split('/').map(decodeURIComponent);
      $main.innerHTML = renderDomain(await domainFile(id), state, now, quotes, football, tab, arg);
    } else if (hash.startsWith('#/e/')) {
```
(en supprimant l'ancienne ligne `if (hash.startsWith('#/d/')) {` et son corps d'une ligne), remplacer `renderHome(home, state, now, previousVisit, quotes)` par `renderHome(home, state, now, previousVisit, quotes, football)`, et dans `init()`, après `quotes = await loadQuotes().catch(() => null);`, ajouter `football = await loadFootball().catch(() => null);`.

- [ ] **Step 5: Ajouter le style à `site/css/app.css`**

```css
.tabs { display: flex; gap: 4px; overflow-x: auto; margin: 10px 0 18px; border-bottom: 1px solid var(--line); scrollbar-width: thin; }
.tabs a { flex: none; padding: 8px 12px; text-decoration: none; color: var(--soft); border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tabs a[aria-current="page"] { color: var(--text); border-bottom-color: var(--dom, var(--accent)); font-weight: 600; }
.tabs.sub { border-bottom: 0; margin-top: 0; }
.tabs.sub a { border: 1px solid var(--line); border-radius: var(--radius); margin: 0; }
.tabs.sub a[aria-current="page"] { border-color: var(--dom, var(--accent)); }

.cmp { font: 600 12px var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--soft); margin: 18px 0 6px; }
.matches { list-style: none; padding: 0; margin: 0; }
.match { display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: baseline; padding: 7px 10px; border: 1px solid var(--line); background: var(--card); margin-bottom: 4px; border-radius: var(--radius); }
.match .mh { text-align: right; }
.match .ms { font: 500 13px var(--mono); min-width: 84px; text-align: center; }
.match.next .ms { color: var(--soft); font-weight: 400; font-size: 12px; }
.fb-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0 20px; margin-top: 10px; }

.standings { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--line); font-size: 14px; }
.standings th, .standings td { padding: 6px 8px; text-align: center; border-bottom: 1px solid var(--line); }
.standings th { font: 500 11px var(--mono); text-transform: uppercase; color: var(--soft); }
.standings .tn { text-align: left; }
.standings .form { font-family: var(--mono); letter-spacing: 1px; color: var(--soft); }
@media (max-width: 768px) { .standings .form { display: none; } .standings th:last-child { display: none; } .match .ms { min-width: 70px; } }
```

- [ ] **Step 6: Étendre `site/tools/make-sample.mjs`**

Ajouter avant la ligne `const home = {` :
```js
const row = (position, team, played, won, draw, lost, gf, ga, points, form) => ({ position, team, played, won, draw, lost, gf, ga, gd: gf - ga, points, form });
const mtch = (id, competition, home, away, hs, as, h, status = 'FINISHED') => ({
  id, competition, date: ago(h), home, away, home_score: hs, away_score: as, status, matchday: 7,
});
const football = {
  checked_at: now.toISOString(),
  competitions: [
    { code: 'FL1', name: 'Ligue 1', stale: false, standings: [row(1, 'Monaco', 5, 4, 1, 0, 8, 3, 13, 'WDWWW'), row(2, 'PSG', 5, 4, 0, 1, 11, 4, 12, 'WWLWW'), row(3, 'Lens', 5, 3, 2, 0, 7, 2, 11, 'DWWDW'), row(4, 'Marseille', 5, 3, 1, 1, 9, 6, 10, 'WLDWW')] },
    { code: 'PL', name: 'Premier League', stale: true, standings: [row(1, 'Arsenal', 6, 5, 1, 0, 14, 3, 16, 'WWDWW'), row(2, 'Liverpool', 6, 5, 0, 1, 12, 5, 15, 'WWWLW')] },
  ],
  results: [mtch(1, 'FL1', 'Marseille', 'PSG', 1, 2, 20), mtch(2, 'FL1', 'Lens', 'Lille', 0, 0, 44), mtch(3, 'PL', 'Arsenal', 'Chelsea', 2, 1, 30)],
  fixtures: [mtch(4, 'FL1', 'Nice', 'Brest', null, null, -30, 'TIMED'), mtch(5, 'FL1', 'Lyon', 'Metz', null, null, -54, 'SCHEDULED'), mtch(6, 'PL', 'Liverpool', 'Spurs', null, null, -60, 'TIMED')],
};

```
et, dans la partie écriture, après `write('quotes.json', quotes);`, ajouter `write('football.json', football);`.

- [ ] **Step 7: Lancer les tests**

Run: `(cd site && node --test "tests/*.test.mjs") ; .venv/Scripts/python -m pytest -q`
Expected: tout PASS.

- [ ] **Step 8: Vérification visuelle sur les données d'exemple (sans toucher aux vraies données)**

Copier le site dans le dossier temporaire et y générer l'exemple :
```bash
SP="C:/Users/rouas/AppData/Local/Temp/claude/C--Users-rouas-Documents-Cerveau-Projets-Code-veille-g-n-rale/00ebcd9e-bf08-405c-9b41-fc6472d5ae53/scratchpad"
rm -rf "$SP/site-preview" && cp -r site "$SP/site-preview" && node site/tools/make-sample.mjs "$SP/site-preview/data"
(cd "$SP/site-preview" && python -m http.server 8935 --bind 127.0.0.1 > /dev/null 2>&1 &)
```
Avec l'outil de navigateur (ouvrir un **nouvel onglet** si le précédent ne répond plus), contrôler sur `http://127.0.0.1:8935/#/d/football` et ses sous-routes : les 5 onglets, l'onglet actif souligné, l'onglet Mercato qui masque les rumeurs avec son décompte et son lien (les événements d'exemple `sample_12` sont de kind `transfer` et de fiabilité `rumeur`), Résultats et Calendrier groupés par compétition, Classements avec le sélecteur de compétitions (la Premier League porte la mention « non actualisé »), la bande « Derniers résultats / Prochains matchs » dans le bloc Football de l'Accueil, pas de débordement horizontal à 390 px (iframe), lisibilité en mode sombre, aucune erreur console. Ouvrir `site-preview/index.html` dans l'éditeur (Live Preview) pour que l'utilisateur juge le design, puis arrêter le serveur.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(site): page Football à onglets, classements, résultats, mercato et bande d'Accueil" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Configuration de la veille Football et première exécution réelle

**Files:**
- Create: `config/domains/football.yml`
- Modify: `config/global.yml` (liste `publishers`), `tests/test_config_domains.py`
- Test: `tests/test_config_domains.py`

**Interfaces:**
- Consumes: format de config de veille (jalon 2), `relevance` (jalon 3), `rumor_markers` / `confirm_markers` (tâche 3).
- Produces: la veille `football` (ordre 3), 19 sources, types d'événements, entités, marqueurs de rumeur et de confirmation, exclusions.

- [ ] **Step 1: Étendre le test de configuration (échoue)**

Ajouter à la fin de `tests/test_config_domains.py` :
```python
def test_football_domain_is_configured_with_rumor_rules_and_noise_filters():
    cfg = load_config()
    fb = cfg["domains"]["football"]
    assert fb["order"] > cfg["domains"]["finance"]["order"] and fb["relevance"] is True
    assert {"transfer", "injury", "suspension", "result", "coach"} <= set(fb["kinds"])
    assert len({s["tier"] for s in fb["sources"]}) >= 3 and len(fb["sources"]) >= 12
    assert fb["rumor_markers"] and fb["confirm_markers"]
    assert not set(m.lower() for m in fb["rumor_markers"]) & set(m.lower() for m in fb["confirm_markers"])
    for word in ("pronostic", "bookmaker", "ea fc"):
        assert any(word in e.lower() for e in fb["exclude"]), word


def test_publishers_cover_the_main_football_outlets():
    publishers = load_config()["global"]["publishers"]
    assert {"rmc sport", "eurosport", "sky sports", "bbc sport", "espn", "marca"} <= set(publishers)
```
Run: `.venv/Scripts/python -m pytest tests/test_config_domains.py -q`
Expected: FAIL (`KeyError: 'football'`).

- [ ] **Step 2: Ajouter les éditeurs à `config/global.yml`**

À la fin de la liste `publishers:` (lignes indentées de deux espaces), ajouter :
```yaml
  rmc sport: 2
  eurosport: 2
  sky sports: 2
  bbc sport: 2
  espn: 2
  the athletic: 2
  marca: 2
  france football: 2
  la gazzetta dello sport: 2
  kicker: 2
  as.com: 3
  goal.com: 3
  onefootball: 3
  transfermarkt: 3
  foot mercato: 3
  footmercato: 3
  so foot: 3
  le parisien: 3
  ouest-france: 3
  foot01: 4
```

- [ ] **Step 3: Écrire `config/domains/football.yml`**

```yaml
id: football
name: Football
accent: "#0B6E4F"
order: 3
quota: 12
max_l1: 4
thresholds: {l1: 60, l2: 50, l3: 40}   # valeurs de départ, calibrées à la tâche 6
relevance: true

exclude: ["pronostic", "prono ", "cote ", "cotes ", "bookmaker", "paris sportifs", "betting", "betclic", "winamax", "unibet", "odds",
          "jeu concours", "quiz", "ea fc", "ea sports fc", "fifa 2", "fantasy", "promo code", "sponsored"]      # paris, jeux vidéo, promotions

# Rumeurs de mercato : un événement à source unique formulé comme une piste est une rumeur, sauf marqueur de confirmation.
# Un marqueur correspond au début d'un mot (« intéress » couvre « intéressé », « intéresse »).
rumor_markers: ["serait", "seraient", "aurait", "pourrait", "pourraient", "piste", "pisteur", "intéress", "dans le viseur", "sur les tablettes",
                "envisage", "tenterait", "tenter", "courtise", "convoit", "souhaite recruter", "would", "could", "reportedly", "linked with",
                "interested in", "eyeing", "considering", "target", "monitoring", "keen on", "rumour", "rumor"]
confirm_markers: ["officiel", "officialise", "officialisé", "official", "here we go", "a signé", "vient de signer", "signs", "signed",
                  "confirme", "confirmed", "présenté", "unveiled", "prolonge", "extends his contract"]

entities:                               # entités majeures : un événement qui en cite une reçoit le bonus d'entité
  PSG: [psg, "paris saint-germain", "paris sg"]
  OM: ["olympique de marseille", "om "]
  OL: ["olympique lyonnais"]
  Monaco: ["as monaco"]
  Lille: [losc]
  Lens: ["rc lens"]
  Real Madrid: ["real madrid"]
  FC Barcelone: [barça, barca, "fc barcelona", "fc barcelone"]
  Atlético: ["atlético", "atletico madrid"]
  Manchester City: ["manchester city", "man city"]
  Manchester United: ["manchester united", "man united", "man utd"]
  Liverpool: [liverpool]
  Arsenal: [arsenal]
  Chelsea: [chelsea]
  Tottenham: [tottenham, spurs]
  Bayern: ["bayern munich", "bayern munchen", "bayern münchen"]
  Dortmund: ["borussia dortmund"]
  Juventus: [juventus, juve]
  Inter: ["inter milan", "inter de milan"]
  Milan AC: ["ac milan"]
  Napoli: [napoli, naples]
  Équipe de France: ["équipe de france", "bleus", "les bleus", "france team", "france national team"]
  Mbappé: [mbappé, mbappe]
  Haaland: [haaland]
  Messi: [messi]
  Ronaldo: [ronaldo]
  Vinícius: [vinicius, vinícius]
  Bellingham: [bellingham]
  Yamal: [yamal]
  Dembélé: [dembélé, dembele]
  Salah: [salah]
  Ligue des champions: ["ligue des champions", "champions league"]
  Coupe du monde: ["coupe du monde", "world cup"]

kinds:
  result:
    weight: 22
    keywords: [victoire, défaite, "match nul", "s'impose", "s'incline", "l'emporte", wins, beat, beats, draw, defeat, "full-time", "full time", triumph]
  competition:
    weight: 20
    keywords: ["ligue des champions", "champions league", "coupe du monde", "world cup", euro, "ligue des nations", "nations league", "europa league", "conference league", "tirage au sort", "coupe de france", "fa cup", "copa"]
  transfer:
    weight: 20
    keywords: [transfert, transfer, mercato, recrue, prêt, loan, "here we go", officialise, prolonge, prolongation, "release clause", "clause libératoire", signe, signs, signing, "va signer", "bid", offre]
  injury:
    weight: 18
    keywords: [blessure, blessé, blessés, injury, injured, forfait, indisponible, "out for", ligaments, "rupture"]
  suspension:
    weight: 18
    keywords: [suspendu, suspension, "carton rouge", "red card", disciplinaire, "commission de discipline", "banned", "suspended"]
  coach:
    weight: 15
    keywords: [entraîneur, coach, limogé, limogeage, sacked, "appointed", "nommé", "manager"]
  national_team:
    weight: 15
    keywords: ["équipe de france", bleus, "sélection", "national team", "convoqué", "liste des"]
  record:
    weight: 12
    keywords: [record, historique, "all-time", "meilleur buteur", "plus jeune", "plus ancien"]
  women:
    weight: 10
    keywords: [féminin, féminine, "women's", "women’s", "wsl", "d1 arkema"]
  statement:
    weight: 10
    keywords: [polémique, controversy, "dénonce", "réagit", "déclaration", "critique"]

sources:                                # flux testés le 26/09/2026 ; Eurosport (404), UEFA (injoignable), FIFA (HTML) écartés
  - {id: lequipe-foot, name: "L'Équipe (football)", tier: 2, origin: "l'équipe", type: rss, url: "https://dwh.lequipe.fr/api/edito/rss?path=/Football/"}
  - {id: rmc-foot, name: "RMC Sport (football)", tier: 2, origin: rmc sport, type: rss, url: "https://rmcsport.bfmtv.com/rss/football/"}
  - {id: figaro-foot, name: "Le Figaro (football)", tier: 2, origin: le figaro, type: rss, url: "https://www.lefigaro.fr/rss/figaro_football.xml"}
  - {id: footmercato, name: "Foot Mercato", tier: 3, origin: foot mercato, type: rss, url: "https://www.footmercato.net/flux-rss/"}
  - {id: bbc-foot, name: "BBC Sport (football)", tier: 2, origin: bbc sport, type: rss, url: "https://feeds.bbci.co.uk/sport/football/rss.xml"}
  - {id: sky-foot, name: "Sky Sports (football)", tier: 2, origin: sky sports, type: rss, url: "https://www.skysports.com/rss/12040"}
  - {id: espn-foot, name: "ESPN (football)", tier: 2, origin: espn, type: rss, url: "https://www.espn.com/espn/rss/soccer/news"}
  - {id: guardian-foot, name: "The Guardian (football)", tier: 2, origin: the guardian, type: rss, url: "https://www.theguardian.com/football/rss"}
  - {id: marca-liga, name: "Marca (Liga)", tier: 2, origin: marca, type: rss, url: "https://e00-marca.uecdn.es/rss/futbol/primera-division.xml"}
  - {id: gazzetta-calcio, name: "La Gazzetta dello Sport (calcio)", tier: 2, origin: la gazzetta dello sport, type: rss, url: "https://www.gazzetta.it/rss/calcio.xml"}
  - {id: kicker-foot, name: "Kicker (Fussball)", tier: 2, origin: kicker, type: rss, url: "https://newsfeed.kicker.de/news/fussball"}
  - {id: reddit-soccer, name: "Reddit r/soccer", tier: 5, origin: reddit, type: rss, url: "https://www.reddit.com/r/soccer/.rss"}
  - {id: gn-mercato-fr, name: "Google Actualités : mercato", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=mercato+transfert+football+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
  - {id: gn-transfers-en, name: "Google Actualités : transfers", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=football+transfer+news+when:1d&hl=en-GB&gl=GB&ceid=GB:en"}
  - {id: gn-blessures, name: "Google Actualités : blessures et suspensions", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=football+blessure+OR+suspension+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
  - {id: gn-ligue1, name: "Google Actualités : Ligue 1", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=Ligue+1+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
  - {id: gn-champions, name: "Google Actualités : Ligue des champions", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=Ligue+des+champions+OR+Champions+League+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
  - {id: gn-bleus, name: "Google Actualités : équipe de France", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=%C3%A9quipe+de+France+football+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
  - {id: gn-feminin, name: "Google Actualités : football féminin", tier: 4, type: rss, publisher_suffix: true, url: "https://news.google.com/rss/search?q=football+f%C3%A9minin+when:1d&hl=fr&gl=FR&ceid=FR:fr"}
```

- [ ] **Step 4: Lancer les tests**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout PASS. Si YAML refuse un mot-clé (`no`, `on`, `off` non guillemetés), le guillemeter.

- [ ] **Step 5: Première exécution réelle (sans IA, sans clé)**

Run: `.venv/Scripts/python -m engine.run --only football football-data --no-ai`
Expected: rapport JSON ; `sources_failed` contient `football-data` (pas de clé, attendu) et aucune des 19 sources RSS (sinon `curl -sI <url>` pour diagnostiquer, corriger ou retirer la source). Vérifier que `site/data/domains/football.json` existe et que `home.json` contient les trois veilles ; `site/data/football.json` n'existe pas (aucune clé).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: veille Football (19 sources, types d'événements, règles de rumeur de mercato)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Calibrage et mesures

**Files:**
- Modify: `config/domains/football.yml`, `config/global.yml` (si nécessaire)
- Create: `docs/superpowers/measurements/jalon-4.md`

**Interfaces:**
- Consumes: tout ce qui précède. Produces: valeurs de réglage retenues et un document de mesures.

Cette tâche est **pilotée par les mesures** : elle se termine quand les objectifs sont atteints ou que l'écart est expliqué.

- [ ] **Step 1: Historique propre et exécution réelle**

Run: `rm -rf data/events && .venv/Scripts/python -m engine.run --no-ai | tr -d '\n '; echo`
Noter : sources Football actives/configurées, articles collectés, événements par niveau, fiabilités, durée (`time`).

- [ ] **Step 2: Lister les événements de Football**

Run: `.venv/Scripts/python "<scratchpad>/list_events.py" football 60` (le script `list_events.py` de la session : il lit `site/data/domains/<veille>.json` et affiche niveaux, fiabilités, types et 60 événements ; le recréer si absent : il charge le JSON, compte `level`, `reliability` et `kind`, puis imprime `level importance fiabilité nb_sources kind | titre`).
Contrôler à la main et régler **dans la configuration** :
1. **Rumeurs de mercato** : ouvrir tous les événements `transfer` et vérifier que les pistes (« serait », « intéressé », « would », « linked with ») sont `rumeur` et que les annonces « officiel » / « here we go » ne le sont pas. Ajuster `rumor_markers` / `confirm_markers` (ajouter les tournures manquantes, retirer celles qui classent à tort des faits en rumeur). Compter faux positifs et faux négatifs sur ~20 événements de mercato.
2. **Niveaux** : viser 2 à 4 événements de niveau 1 et 5 à 8 de niveau 2. Ajuster `thresholds`.
3. **Bruit** : pronostics, paris, jeux vidéo, articles sans rapport avec le football : compléter `exclude` ; vérifier que `relevance: true` ne retire pas d'actualités utiles (compter, sur un échantillon de 20 articles écartés, combien étaient légitimes ; si plus de 3, élargir les mots-clés de `kinds` ou les entités).
4. **Doublons** : noter le nombre d'histoires en plusieurs événements (limite connue, fusion événement-à-événement reportée) et les fusions abusives (aucune tolérée : si un événement mélange deux histoires, revoir `cluster.threshold` pour cette veille uniquement avec l'accord de l'utilisateur, car ce seuil est global).
5. **Reddit r/soccer** (tier 5) : vérifier qu'il n'introduit pas de rumeurs en niveau 1 ; sinon abaisser son poids en le retirant.

- [ ] **Step 3: Vérifier le site sur les vraies données**

Servir `site/` (`python -m http.server 8934 --bind 127.0.0.1 --directory site`), ouvrir `http://127.0.0.1:8934/?reset` (nouvel onglet) : trois veilles dans la navigation, bloc Football sur l'Accueil (sans bande, puisque pas de clé), page Football avec ses onglets ; les onglets Résultats, Classements et Calendrier affichent « Données indisponibles pour le moment » tant que la clé n'existe pas ; Mercato masque les rumeurs avec décompte ; aucune erreur console. Arrêter le serveur.

- [ ] **Step 4: Écrire `docs/superpowers/measurements/jalon-4.md`**

Reprendre le format de `jalon-3.md` : tableau des mesures (sources actives, articles, événements par niveau, rapport articles/événements, rumeurs de mercato correctement étiquetées avec faux positifs et faux négatifs comptés, rumeurs en niveau 1, doublons, bruit écarté, durée d'un cycle), « Réglages retenus après mesure », « Limites connues » (dont : données structurées non validées faute de clé, comptes X non couverts, Ligue Europa et Conférence hors plan gratuit), « Décision ». Les valeurs doivent être celles réellement observées.

- [ ] **Step 5: Lancer toute la suite puis commiter**

Run: `.venv/Scripts/python -m pytest -q && (cd site && node --test "tests/*.test.mjs")`
Expected: tout PASS.

```bash
git add -A
git commit -m "feat: calibrage de la veille Football et mesures du jalon 4" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Clé football-data.org, validation de l'API réelle et mise en production (accord de l'utilisateur requis)

**Files:**
- Modify: `.github/workflows/pipeline.yml`, `README.md`, `docs/superpowers/measurements/jalon-4.md`, éventuellement `engine/football_data.py`
- Create: `tests/fixtures/football_data_standings.json`, `tests/fixtures/football_data_matches.json` (réponses réelles anonymisées)
- Test: `tests/test_football_data.py` (ajouts)

**Interfaces:**
- Consumes: `FOOTBALL_DATA_TOKEN`, workflow `pipeline.yml`, secret GitHub, projet Vercel.
- Produces: classements, résultats et calendrier réels en production.

**Cette tâche demande deux actions de l'utilisateur** (création d'un compte, saisie d'un secret) **et son accord avant toute poussée sur `main`.** Ne jamais demander ni afficher la clé dans la conversation.

- [ ] **Step 1: L'utilisateur crée sa clé gratuite (action de l'utilisateur)**

Lui donner ces étapes exactes : (1) ouvrir https://www.football-data.org/client/register, (2) s'inscrire avec son adresse email (plan « Free »), (3) ouvrir le mail de confirmation et récupérer le jeton d'API (« API Token »), (4) créer le secret GitHub sur https://github.com/Adam2328/veille-plateforme/settings/secrets/actions : **Name** `FOOTBALL_DATA_TOKEN`, **Secret** = le jeton, **Add secret**, (5) ajouter la ligne `FOOTBALL_DATA_TOKEN=<le jeton>` dans le fichier `plateforme/.env` (ignoré par Git) pour les essais locaux. Attendre son « c'est fait ».

- [ ] **Step 2: Valider l'API réelle en local**

Run: `.venv/Scripts/python -m engine.run --only football-data --no-ai`
Expected: `football.ok` égal à 8 et `failed` égal à 0. Sinon lire `site/data/health.json` (`football:...`) : une erreur HTTP 403 indique un jeton invalide ou une compétition non couverte par le plan gratuit ; 429 un dépassement de 10 requêtes par minute ; une `KeyError` ou `ValueError` un format de réponse différent de celui supposé (`standings[].type == "TOTAL"`, `table[].team.shortName`, `matches[].score.fullTime`, `matches[].competition.code`).

- [ ] **Step 3: Figer un cas réel en test (TDD sur le format réel)**

Si le format réel diffère de l'hypothèse, écrire d'abord un test rouge à partir d'une réponse réelle : enregistrer un classement et une liste de matchs réels (tronqués à 3 lignes, sans donnée personnelle) dans `tests/fixtures/`, ajouter à `tests/test_football_data.py` des tests qui chargent ces fichiers et vérifient `parse_standings` / `parse_matches`, constater l'échec, corriger `engine/football_data.py`, relancer. Même si le format est conforme, ajouter les deux tests d'intégrité sur les fixtures réelles (ils protègent contre un futur changement de l'API).

- [ ] **Step 4: Vérifier les données et le site**

Contrôler dans `site/data/football.json` : 6 compétitions avec 18 à 20 équipes (Ligue des champions : phase de ligue de 36 équipes), positions et points cohérents avec un classement officiel consulté sur un site de référence, résultats des 9 derniers jours, calendrier des 9 prochains jours, noms d'équipes lisibles (`shortName`). Servir `site/` (nouvel onglet du navigateur) : bande sur l'Accueil, onglets Résultats, Classements (sélecteur des 6 compétitions), Calendrier ; aucune erreur console ; mobile sans débordement.

- [ ] **Step 5: Ajouter la clé au workflow**

Dans `.github/workflows/pipeline.yml`, dans le bloc `env:` de l'étape `python -m engine.run`, ajouter la ligne `FOOTBALL_DATA_TOKEN: ${{ secrets.FOOTBALL_DATA_TOKEN }}`. Mettre à jour `README.md` : veille Football, secret `FOOTBALL_DATA_TOKEN`, `--only football-data`, limites (10 requêtes par minute ; Ligue Europa, Conférence, Ligue des nations et compétitions féminines hors plan gratuit).

- [ ] **Step 6: Fusionner et pousser (accord de l'utilisateur requis)**

```bash
git add -A && git commit -m "feat: football-data.org en production (clé dans le workflow, fixtures réelles)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git checkout main && git pull --rebase origin main && git merge feat/jalon-4 -m "merge: jalon 4 (Football)"
```
En cas de conflit sur `site/data/` ou `data/events/`, garder la version du robot (`git checkout --ours <chemins>` puis `git add`). Relancer toute la suite de tests, puis `git push origin main`.

- [ ] **Step 7: Lancer le pipeline dans le cloud et vérifier**

Run: `gh workflow run pipeline.yml -R Adam2328/veille-plateforme`, attendre la fin (`gh run watch <id> -R Adam2328/veille-plateforme --exit-status`), `git pull --rebase origin main`.
Vérifier dans `site/data/health.json` : `football:*` tous `ok`, synthèses Gemini sans erreur de quota avec trois veilles (`ai.errors` vide, sinon voir `max_events_per_run` dans `global.yml`), durée du workflow. Relire 5 événements de mercato : les rumeurs sont étiquetées, les annonces officielles ne le sont pas. Vérifier la production (`curl -s https://veille-plateforme.vercel.app/data/football.json | head -c 300`, puis le site dans le navigateur : trois veilles, onglets, classements).

- [ ] **Step 8: Consigner et pousser la documentation**

Compléter `docs/superpowers/measurements/jalon-4.md` avec les résultats de production (disponibilité de l'API depuis GitHub, quota Gemini, durée d'un cycle, qualité des étiquettes de rumeur), commiter et pousser (`git pull --rebase origin main` avant).

---

## Self-review (jalon 4 contre la spec)

- **Spec §11 Football** : presse sportive (L'Équipe, RMC Sport, Le Figaro, BBC, Sky, ESPN, Guardian, Marca, Gazzetta, Kicker, Foot Mercato), réseaux sociaux au mieux (Reddit r/soccer, Google Actualités ; comptes X non couverts, assumé), compétitions (Ligue 1, PL, Liga, Serie A, Bundesliga, Ligue des champions : classements, résultats, calendrier ; Europa, Conférence, Ligue des nations, féminines, sélections : actualité seulement), types d'information (résultats, transferts, blessures, suspensions, entraîneurs, sélections, records, polémiques), Coupe du monde / Euro : couverts par l'actualité, et par les données structurées seulement si ajoutés à `football.yml` (budget de requêtes à revoir).
- **Spec §7 fiabilité** : « une rumeur sans source fiable ne doit pas avoir la même importance qu'une information confirmée » : règle `rumor_markers` déterministe (tâche 3), plafond de niveau 2 déjà en place, onglet Mercato qui masque les rumeurs par défaut (tâche 4). Les étiquettes officiel / confirmé / rapporté / en développement / rumeur sont visibles sur chaque carte.
- **Spec §10 UX** : onglets Actu, Résultats, Classements, Calendrier, Mercato, blessures et suspensions visibles dans Actu (kinds `injury` et `suspension`), bande résultats/prochains matchs sur l'Accueil. Non couverts : onglet « Compétitions » séparé, filtres par équipe et suivis (jalon 5).
- **Spec §12 erreurs** : clé absente, quota, API en panne, format inattendu : dernières valeurs conservées et marquées non actualisées, échec dans `health.json`, jamais de fichier vide publié, jamais de blocage du cycle.
- **Risque assumé** : le format de football-data.org est supposé d'après sa documentation et n'a pas pu être testé sans clé ; la tâche 7 impose une validation sur la réponse réelle et des fixtures réelles avant toute mise en production.
- **Types et noms** : `collect_football(cfg, token, previous, now, fetch)`, `parse_standings`, `parse_matches`, `fetch_fd`, `publish_football`, `football_token`, `football_fetch` (tâche 2) ; `classify(items, now, dom)` et `rescore` (tâche 3) ; `renderFootball`, `renderMatches`, `renderStandings`, `matchLine`, `footballStrip`, `renderDomain(..., football, tab, arg)`, `domainBlock(..., quotes, football)`, `renderHome(..., quotes, football)` (tâche 4), cohérents avec le `run.py` du jalon 3.
- **Pas de placeholder** : les seuils sont des valeurs de départ avec procédure de calibrage chiffrée (tâche 6) ; les deux actions de l'utilisateur (clé, secret) et l'accord de poussée sont explicites (tâche 7).
