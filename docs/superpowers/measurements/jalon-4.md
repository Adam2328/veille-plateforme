# Mesures du jalon 4 (Football)

Date : 2026-09-26 (semaine de Ligue des nations : Turquie-France, première de Zinédine Zidane, blessure de Kylian Mbappé). Exécution : `python -m engine.run --no-ai`, historique vide au départ, sans clé football-data.org.

| Mesure | Valeur | Objectif |
|---|---|---|
| Sources Football actives / configurées | 19 / 19 | ≥ 12 |
| Articles collectés (moins de 36 h) | ~340 | |
| Événements Football affichés | 51 (4 / 11 / 36) | 2-4 / 5-8 / le reste |
| Rapport articles / événements | ~6,5 | ≥ 3 |
| Rumeurs en niveau 1 | 0 | 0 |
| Rumeurs de mercato : faux positifs (fait classé rumeur) | 2 avant réglage → 0 après | 0 |
| Rumeurs de mercato : faux négatifs (piste non étiquetée) | 1 avant réglage (« Transfer rumors… » classé confirmé) → 0 après | 0 |
| Pages-dossiers sans contenu (« Real Madrid », « Ousmane Dembélé ») | 4 → 0 | 0 |
| Classements, résultats, calendrier | non collectés : clé football-data.org absente (attendu) | validés à la tâche 7 |
| Durée d'un cycle complet (IA + Finance + Football + cours + agenda) | ~19 s | < 3 min |

Échantillon de mercato petit (5 événements `transfer` ce jour-là, semaine internationale) : les taux de faux positifs et négatifs sont à revérifier un jour de mercato ouvert.

## Réglages retenus après mesure

- **Seuils** : 60/50/40 (plan) puis 76/70/60. Les scores observés vont de 41 à 84 : à 50, 98 événements étaient en niveau 2.
- **Marqueurs de rumeur** : « would », « could », « aurait », « pourrait » et « tenter » retirés. Ils faisaient classer en rumeur des faits ou des récits (« Pavel Šulc révèle pourquoi son transfert a échoué », « Gakpo reflects on a tough summer »).
- **Nouvelle règle (code et tests)** : `explicit_rumor_markers`. Un titre qui se présente lui-même comme une rumeur (« Transfer rumors… », « Transfer news LIVE », « gossip ») reste une rumeur même repris par plusieurs médias, conformément à la spec (« une rumeur reprise par 15 agrégateurs reste une rumeur »). Seul un statut « officiel » l'emporte.
- **Exclusion par URL (code et tests)** : le filtre `exclude` porte aussi sur l'adresse de l'article ; `_dn-` écarte les pages-dossiers de RMC Sport.
- **Types d'événements** : « offre », « signe », « prêt », « recrue » retirés du type `transfer` (« s'offre l'Angleterre », « un signe ») ; « directeur sportif » et « sporting director » ajoutés.

## Limites connues

- **Même histoire en plusieurs événements (principale limite)** : la victoire en Turquie et la blessure de Mbappé occupent 8 à 10 événements (angles différents : résultat, blessure, communiqué du Real, réaction de Zidane, audiences). La fusion événement-à-événement, reportée depuis le jalon 2, devient la prochaine amélioration la plus utile.
- **Types approximatifs** : « Lamine Yamal marque dès la 2e minute » est classé `injury` (mot « blessure » dans l'extrait). Le type sert au score et à l'onglet Mercato, pas à la fiabilité.
- **Comptes X** (Actu Foot, BeFootball) non couverts ; Reddit et Google Actualités assurent la détection rapide.
- **Flashscore** : pas de collecte (aucune API, signature privée, `robots.txt`) ; utilisé comme lien « approfondir » par compétition.
- **Données structurées** : Ligue Europa, Conférence, Ligue des nations et compétitions féminines hors plan gratuit de football-data.org.

## Décision

L'actualité Football est utilisable. Il reste à valider les classements, résultats et calendrier avec la clé football-data.org de l'utilisateur (tâche 7), puis à mettre en production.
