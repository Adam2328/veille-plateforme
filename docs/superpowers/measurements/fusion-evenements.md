# Fusion d'événements (second passage) : mesures

Date : 2026-09-27. Méthode : un même lot d'articles réels (IA 116, Finance 148, Football 309), 3 cycles par seuil (une fusion par événement et par cycle, comme en production où les cycles se succèdent toutes les 30 minutes).

| Seuil `merge_threshold` | IA | Finance | Football | Mbappé / Turquie-France (Football) |
|---|---|---|---|---|
| désactivé | 23 | 13 | 43 | 13 événements |
| 0,50 | 23 | 13 | 42 | 12 |
| 0,40 | 23 | 13 | 42 | 12 |
| 0,35 | 23 | 13 | 41 | 12 |
| **0,30 (retenu)** | 23 | 13 → 12* | 38 → 37* | **9** |

\* avec l'exclusion des pages de cotation (voir plus bas).

## Contrôle des fusions à 0,30

- Blessure de Mbappé : un seul événement de 25 sources, toutes sur la blessure (communiqué du Real, diagnostic, forfait, remplaçant). Correct.
- Irlande et Israël (boycott, vote des joueurs, gardien) : 10 sources, une seule histoire. Correct.
- Taux américains au plus haut depuis 20 ans : 3 sources. Correct.
- Cas limite : 9 sources qui réunissent la victoire en Turquie et la préparation du match contre la Belgique (« les Bleus de Zidane », même semaine). Acceptable, à surveiller.
- Aucune fusion entre histoires sans rapport observée.

## Constat annexe corrigé

La veille Finance contenait un faux événement de 17 « sources » : des pages de cotation Boursorama (« ORANGE Cours Action ORA, Cotation Bourse Euronext Paris ») remontées par Google Actualités et regroupées sur leur gabarit commun. Exclues par `cours action` et `cotation bourse` dans `finance.yml`.

## Limites

- Gain modeste : les angles restants de l'histoire Turquie-France (audiences, polémique sur la Marseillaise, analyses tactiques) sont lexicalement différents. Aller plus loin demanderait des embeddings sémantiques (modèle local), prévus en option par la spec.
- La fusion ne s'applique qu'aux événements encore ouverts (48 h).
- Une fusion par événement et par cycle : une histoire éclatée en 10 morceaux converge sur plusieurs cycles.
