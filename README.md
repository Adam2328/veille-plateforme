# Plateforme de veille

Centre de contrôle personnel de l'information : un moteur commun (collecte, regroupement, fiabilité, importance, synthèse) et une configuration par veille.

- Spec : `docs/superpowers/specs/`. Plans : `docs/superpowers/plans/`. Mesures : `docs/superpowers/measurements/`.
- Environnement : `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt` (Windows) ou `.venv/bin/python` (Linux/macOS).
- Veilles en service : IA (`config/domains/ia.yml`), Finance & Marchés (`config/domains/finance.yml`, avec synthèses en couches et garde-fou anti-conseil) et Football (`config/domains/football.yml`, rumeurs de mercato étiquetées, liens « Voir sur Flashscore »).
- Lancer le pipeline en local : `python -m engine.run --only ia finance football quotes football-data --no-ai` (`--only` accepte des ids de veilles, `quotes` et `football-data`). Secrets dans `.env` (ignoré par Git) et dans les secrets GitHub : `GEMINI_API_KEY` (synthèses) et `FOOTBALL_DATA_TOKEN` (classements, résultats, calendrier via football-data.org, plan gratuit : 10 requêtes par minute, fenêtres de 10 jours ; un cycle en fait 8 ou 9 ; Ligue Europa, Conférence, Ligue des nations et compétitions féminines non couvertes).
- Dépendances externes reprises de l'ancien projet `mon-brief-quotidien` : le relais de cours `ticker-relay` (Render, jusqu'à 60 s de réveil) pour `site/data/quotes.json`, et son `agenda_events.json` (dépôt `Adam2328/mon-brief-quotidien`) pour l'agenda Finance. Si l'ancien projet s'arrête, l'agenda importé disparaît et seul le calendrier officiel de `finance.yml` reste (Fed et BCE jusqu'en septembre 2027, à renouveler chaque année).
- Déploiement Vercel : « Root Directory » = `site` (config dans `site/vercel.json`). Voir le site en local : `python -m http.server 8934 --directory site`, ou Live Preview sur `site/index.html`. Paramètre `?reset` : efface l'état de lecture.
- Données d'exemple pour le design : `node site/tools/make-sample.mjs` (écrase `site/data/`, à ne pas commiter).
- Tests : `python -m pytest -q` et `cd site && node --test "tests/*.test.mjs"`. Vérification de bout en bout (bureau et mobile, Chromium sans fenêtre) : servir `site/` sur le port 8934 puis `.venv/Scripts/python site/tests/e2e_smoke.py` (Playwright installé dans `.venv` uniquement).
- Recherche et archives : `site/data/search.json` (30 jours), chargé à la demande ; `Ctrl+K` ou `/`. Suivis : bouton « Suivre » sur les entités d’Ne fiche, section « Vos suivis » sur l’Accueil (stockés dans le navigateur).
- Ajouter une veille : créer `config/domains/<id>.yml` (voir `ia.yml`), aucun code.
- Sorties versionnées : `site/data/` (lu par le site) et `data/events/` (historique).
