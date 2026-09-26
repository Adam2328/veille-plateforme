# Plateforme de veille

Centre de contrôle personnel de l'information : un moteur commun (collecte, regroupement, fiabilité, importance, synthèse) et une configuration par veille.

- Spec : `docs/superpowers/specs/`. Plans : `docs/superpowers/plans/`. Mesures : `docs/superpowers/measurements/`.
- Environnement : `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt` (Windows) ou `.venv/bin/python` (Linux/macOS).
- Lancer le pipeline en local : `python -m engine.run --only ia --no-ai` (ajouter `GEMINI_API_KEY` dans `.env`, ignoré par Git, pour les synthèses Gemini).
- Voir le site : `python -m http.server 8934 --directory site`, ou Live Preview sur `site/index.html`. Paramètre `?reset` : efface l'état de lecture.
- Données d'exemple pour le design : `node site/tools/make-sample.mjs` (écrase `site/data/`, à ne pas commiter).
- Tests : `python -m pytest -q` et `cd site && node --test "tests/*.test.mjs"`.
- Ajouter une veille : créer `config/domains/<id>.yml` (voir `ia.yml`), aucun code.
- Sorties versionnées : `site/data/` (lu par le site) et `data/events/` (historique).
