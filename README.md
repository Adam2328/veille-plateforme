# Plateforme de veille

Centre de contrôle personnel de l'information : un moteur commun (collecte, regroupement, fiabilité, importance, synthèse) et une configuration par veille.

- Spec : `docs/superpowers/specs/`. Plans : `docs/superpowers/plans/`. Mesures : `docs/superpowers/measurements/`.
- Environnement : `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt` (Windows) ou `.venv/bin/python` (Linux/macOS).
- Veilles en service : IA (`config/domains/ia.yml`) et Finance & Marchés (`config/domains/finance.yml`, avec synthèses en couches et garde-fou anti-conseil).
- Lancer le pipeline en local : `python -m engine.run --only ia finance quotes --no-ai` (`--only` accepte des ids de veilles et `quotes` ; ajouter `GEMINI_API_KEY` dans `.env`, ignoré par Git, pour les synthèses Gemini).
- Dépendances externes reprises de l'ancien projet `mon-brief-quotidien` : le relais de cours `ticker-relay` (Render, jusqu'à 60 s de réveil) pour `site/data/quotes.json`, et son `agenda_events.json` (dépôt `Adam2328/mon-brief-quotidien`) pour l'agenda Finance. Si l'ancien projet s'arrête, l'agenda importé disparaît et seul le calendrier officiel de `finance.yml` reste (Fed et BCE jusqu'en septembre 2027, à renouveler chaque année).
- Déploiement Vercel : « Root Directory » = `site` (config dans `site/vercel.json`). Voir le site en local : `python -m http.server 8934 --directory site`, ou Live Preview sur `site/index.html`. Paramètre `?reset` : efface l'état de lecture.
- Données d'exemple pour le design : `node site/tools/make-sample.mjs` (écrase `site/data/`, à ne pas commiter).
- Tests : `python -m pytest -q` et `cd site && node --test "tests/*.test.mjs"`.
- Ajouter une veille : créer `config/domains/<id>.yml` (voir `ia.yml`), aucun code.
- Sorties versionnées : `site/data/` (lu par le site) et `data/events/` (historique).
