# Mesures du lot 1A (socle de données Vigie 2)

Date : 2026-09-27, après 3 cycles de production avec Gemini (runs 36338816778, 36339156814, 36339313087).
Outil : `.venv/Scripts/python tools/measure_links.py`.

| Mesure | Résultat | Objectif |
|---|---|---|
| Événements de niveau 1-2 reliés à au moins une entité | 91 / 98 (**93 %**) | ≥ 80 % ✅ |
| Rattachements faux sur un échantillon de 50 | **2 / 50 (4 %)** | ≤ 5 % ✅ |
| Titres traduits en français (niveaux 1-2) | 83 / 98 (85 %) | — (le reste : résumés en attente de reprise v2) |
| Événements avec photo d'article | 3 / 98 (3 %) | — (les flux RSS en fournissent très rarement) |
| Événements avec chaînes « Concernés » | 31 / 98 (32 %) | — |
| Faits Wikidata | 354 entités, `facts:wikidata` ok | — |
| Poids de `site/data/entities/` | 2,0 Mo | — |
| Cycle de production | 3 cycles verts, aucune source en échec | — |

Rattachements faux relevés dans l'échantillon :
- « Popularité du Premier ministre thaïlandais en baisse » → Pétrole (mention accessoire des prix de l'énergie dans l'extrait).
- « Dernière sortie de Tadej Pogačar avec le maillot arc-en-ciel » → France (lieu de course). Pays cités comme lieu : limite connue du rattachement par alias, sans correction pour l'instant.

Candidats inconnus les plus cités (à valider pour le catalogue) : Zinédine Zidane (7), Finlande (3), Luis de la Fuente (3), Bradley Barcola (2), Désiré Doué (2), Eduardo Camavinga (2), Slovénie (2), Thomas Tuchel (2), UBS (2).

Constats pour la partie B :
- Les photos d'articles sont rares : l'illustration générée par le site sera la présentation la plus fréquente.
- Les pays sont très présents dans les actualités sportives (« France », « Belgique » pour les matchs de l'équipe de France) : utile pour la navigation, à ne pas mettre en avant dans les pastilles d'une carte sportive.
