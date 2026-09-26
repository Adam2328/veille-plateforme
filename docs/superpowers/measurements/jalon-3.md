# Mesures du jalon 3 (Finance & Marchés)

Date : 2026-09-26. Exécution : `python -m engine.run --no-ai` sur les vraies sources, historique vide au départ.

| Mesure | Valeur | Objectif |
|---|---|---|
| Sources Finance actives / configurées | 15 / 15 | ≥ 10 |
| Articles bruts collectés (Finance) | 352 | |
| Cours obtenus via le relais `ticker-relay` | 18 / 18, 0 périmé | 18 |
| Agenda importé de l'ancien pipeline | 158 points lus, 6 retenus dans les 21 jours | |
| Événements Finance affichés (niveaux 1 à 3) | 20 (3 / 4 / 13) sur la fenêtre de 7 jours | 2-4 / 5-8 |
| Sur l'Accueil (quota de 12) | 3 en niveau 1, 4 en niveau 2, 5 en niveau 3 | |
| Rumeurs en niveau 1 | 0 | 0 |
| Doublons visibles | aucun repéré sur les 20 événements | ≤ 3 sur 30 |
| Durée d'un cycle complet (IA + Finance + cours + agenda) | ~11 s | < 3 min |
| Synthèses en couches (Gemini) | non mesurées en local (pas de clé) : à vérifier en production (tâche 8) | |

## Réglages retenus après mesure

- **Filtre de pertinence** (`relevance: true`, nouveau, testé) : sans lui, 82 événements dont beaucoup de bruit (finance personnelle, retraite, météo, quiz, « Birding apps ») venaient de CNBC, MarketWatch et Bloomberg, au même score que de vraies nouvelles. Un article n'est gardé que s'il cite une entité de la veille ou un mot-clé d'un type d'événement. Résultat : 20 événements, tous liés aux marchés. Effet de bord assumé : la géopolitique sans lien direct avec un mot-clé financier (« Iran War Endgame ») n'apparaît plus dans Finance, elle relèvera de la veille Géopolitique.
- **Seuils** : 62/45/30 (plan) puis 53/50/44. Les scores observés vont de 43 à 56 : à 62 aucun événement n'atteignait le niveau 1. Les articles de type `other` plafonnent à 43, donc `l3 = 44` les écarte.
- **Exclusions** : « approval of application », « enforcement action » (communiqués administratifs de la Fed, qui prenaient 51 points comme source officielle), « in common stock » et « insider » (transactions d'initiés qui ressortaient en fusion-acquisition).
- **Mots-clés `markets`** élargis (bonds, yields, investors, dollar, central bank, marchés...) pour ne pas perdre des articles obligataires ; l'ordre des `agenda_keywords` va du plus spécifique au plus général car il sert aussi de clé de dédoublonnage (JOLTS apparaissait deux fois sous les clés « emploi » et « jolts »).
- **Agenda** : `agenda_exclude` (discours, panel, conférence, forum, non-monétaire) pour écarter les interventions de faible valeur, mots-clés « résultats » et « earnings » retirés (ils faisaient remonter des sociétés inconnues comme « SODITECH »).
- **Aucun changement de `cluster.threshold`** : la veille Finance ne montre pas de doublons ; la veille IA n'a pas été modifiée.

## Limites connues

- **Classement approximatif** : le premier événement de niveau 1 est un article pédagogique sur l'inflation (« these charts show ») plutôt que la vraie nouvelle du jour, parce que le score ne distingue pas un explicatif d'une décision. Le nombre de sources indépendantes pèse peu en Finance car chaque média publie son propre angle.
- **Peu de fiabilité « confirmé »** : sur 20 événements, 11 sont « rapporté » (une source reconnue) et 9 « non confirmé » (sources d'agrégateur sans tier connu). Aucun n'est « officiel » : les communiqués de la Fed et de la BCE restants sont trop administratifs pour passer les filtres. Une décision de taux réelle sera « officielle » car ces flux sont en tier 1.
- **Cours** : le relais arrondit à 2 décimales (EUR/USD s'affiche « 1,14 ») et peut mettre jusqu'à 60 s à se réveiller après une période d'inactivité.
- **Agenda** : dépend du dépôt `mon-brief-quotidien` ; s'il s'arrête, seul le calendrier officiel vérifié de `finance.yml` (Fed et BCE jusqu'en septembre 2027) reste affiché.
- **Regroupement en 2 événements d'une même histoire** (limite héritée du jalon 2) : non traité, fusion événement-à-événement reportée.

## Décision

Le socle Finance est utilisable au quotidien. Restent à valider en production (tâche 8) : les synthèses Gemini en couches (qualité, part rejetée par le garde-fou anti-conseil), la disponibilité du relais et de l'agenda depuis GitHub Actions, et la durée d'un cycle avec le réveil du relais.
