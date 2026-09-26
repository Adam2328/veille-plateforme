# Mesures du jalon 2

Date : 2026-09-26. Exécution : `python -m engine.run --only ia --no-ai` sur les vraies sources, historique vide au départ.

| Mesure | Valeur | Objectif |
|---|---|---|
| Sources actives / configurées | 16 / 16 | ≥ 10 |
| Articles collectés (moins de 36 h) | 146 | |
| Articles nouveaux après dédoublonnage | 144 | |
| Événements affichés (niveaux 1 à 3) | 42 | |
| Rapport articles / événements | 3,4 | ≥ 3 |
| Événements niveau 1 / niveau 2 / niveau 3 | 4 / 11 / 27 | 2-4 / 5-8 / le reste |
| Rumeurs en niveau 1 | 0 | 0 |
| Fusions abusives (événements à 3 sources et plus) | 0 observée | 0 |
| Doublons visibles | 3 paires (Pentagone/Anthropic 11+7 sources, agents OpenAI, DeepSeek) sur 42 événements | ≤ 3 sur 30 |
| Synthèses llm / extractif | 0 / 15 (exécution sans clé Gemini) | à mesurer avec la clé |
| Durée d'un cycle | ~27 s | < 3 min |

## Réglages retenus après mesure

- `cluster.threshold` : 0,45 (plan) puis 0,25. À 0,45, l'affaire Pentagone/Anthropic était éclatée en 5 événements ; à 0,25 elle tombe à 2 (11 et 7 sources).
- **Bonus d'entités supprimé du regroupement.** À 0,30 avec bonus (+0,15/+0,25), un événement « rogue AI attacks » absorbait des articles sur Meta et sur les modèles chinois, parce que tout ce qui cite OpenAI et Anthropic se rapprochait. Les noms d'entités sont déjà des tokens du TF-IDF, le bonus double-comptait. Test de non-régression : `test_two_stories_sharing_only_big_names_do_not_merge`.
- `thresholds` IA : 70/50/30 (plan) puis 58/45/30. Les scores observés vont de 43 à 79 ; à 70 aucun événement n'atteignait le niveau 1 sur les articles à source unique.
- Mots-clés de `regulation` et `funding_acquisition` élargis (court, ruling, ban, billion, ipo...) : le type `other` (poids 5) était trop fréquent sur des événements clairement importants.
- **Fiabilité** : ajout d'une règle « 3 éditeurs distincts (tier ≤ 4) sans formulation au conditionnel = rapporté ». Sans elle, une décision de justice reprise par 7 éditeurs de Google Actualités était étiquetée « non confirmé ». Les réseaux sociaux (tier 5) ne comptent pas, et le conditionnel reste prioritaire (`rumeur`). Écart assumé avec la spec §7 (« rapporté = 1 origine fiable ») : la spec visait à empêcher qu'une rumeur devienne un fait, ce que la règle préserve.
- **Filtre `exclude`** par veille (promotions « TechCrunch Disrupt » qui ressortaient comme actualités).
- Sources retirées : VentureBeat (HTTP 429, bloque les robots), Hacker News via hnrss.org (HTTP 502). Source remplacée : flux Microsoft AI (410) par `news.microsoft.com/source/topics/ai/feed/`. Anthropic n'a pas de flux RSS officiel (404) : couvert par Google Actualités.

## Limites connues (à traiter aux jalons suivants)

- Le regroupement reste par paraphrase lexicale : une même histoire peut rester en 2 événements (fusion événement-à-événement non implémentée). Piste : second passage comparant les centroïdes des événements ouverts, ou embeddings multilingues locaux (option prévue par la spec).
- Google Actualités impose un éditeur par article mais son tier est 4 par défaut : seuls les éditeurs de la liste `publishers` (`config/global.yml`) ont un tier 2/3.
- Les synthèses Gemini n'ont pas encore été mesurées (pas de clé dans l'environnement local) : qualité, nombre d'appels et quota restent à vérifier.

## Décision

Le socle est assez bon pour poursuivre. Avant le jalon 3 : mesurer les synthèses avec la clé Gemini, puis décider si le second passage de fusion est nécessaire.
