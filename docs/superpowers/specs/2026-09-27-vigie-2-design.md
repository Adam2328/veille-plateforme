# Vigie 2 — poste d'observation personnel de l'information

Statut : validé en conversation le 2026-09-27 (socle, identité visuelle A, Finance, clé FRED).
Remplace la navigation de la spec du 2026-09-26 ; le moteur de cette spec (collecte → regroupement → fiabilité → score → résumé → publication) reste la base.

## 1. But

Passer d'un agrégateur par rubriques à un système de veille où chaque information est reliée à des **entités** (entreprise, pays, joueur, ETF, modèle d'IA…) et où l'on peut **explorer** : événement → entité → autres événements → entités voisines → autre univers.

Principe : Observer → Détecter → Comprendre → Explorer. Critère de réussite : en ouvrant Vigie, « voici ce que je dois savoir aujourd'hui », puis pouvoir comprendre pourquoi et aller plus loin en un ou deux gestes.

## 2. Contraintes globales

- Coût ≈ 0 € : Vercel (site statique), GitHub Actions (cycle 30 min), API gratuites uniquement. Clés gratuites en secrets GitHub : `GEMINI_API_KEY`, `FOOTBALL_DATA_TOKEN`, `NTFY_TOPIC`, `FRED_API_KEY` (nouvelle).
- Site sans étape de build : modules ES natifs, pas de framework. Bibliothèque graphique externe seulement si le SVG fait main ne suffit plus.
- Moteur Python 3.11, tests pytest ; site testé par `node --test` + smoke Playwright.
- Chaque fichier publié est validé par un schéma JSON avant publication (contrat existant étendu).
- Pas de temps réel : cycle de 30 min, faits Wikidata hebdomadaires.
- Jamais de conseil d'achat/vente (filtre `has_advice` conservé sur tout texte généré). Une rumeur reste une rumeur (étiquettes de fiabilité conservées).
- Mobile d'abord ; `prefers-reduced-motion` respecté ; accessible au clavier.
- Les anciennes adresses `#/d/...` redirigent vers les nouvelles (liens des alertes déjà envoyées).
- Aucune entité créée automatiquement sans validation (voir §5.3).

## 3. Ce qui est conservé / supprimé / refactorisé

Conservé : collecte des 147 sources, `normalize`, `cluster`/`merge_events`, `reliability`, `score`, `summarize` (couches Faits/Analyse/Interprétation/Incertitude), `store` (historique jsonl), connecteurs football-data, Jolpica F1, relais de cours, agenda, alertes ntfy ; côté site : état « depuis ma dernière visite », suivis, garde contre les rendus périmés, PWA, service worker.

Supprimé : navigation par 9 rubriques, dictionnaires `entities` par rubrique (migrés dans le catalogue), `app.css` et la mise en page actuelle, cartes « À connaître » sous leur forme actuelle (deviennent contenu de fiche), rubrique « Sport, l'essentiel » comme page (fondue dans l'accueil Sport).

Refactorisé : `render.js` découpé en vues et composants ; `enrich.extract_entities` renvoie des identifiants d'entités ; `publish` produit fiches entités et graphe ; `search` indexe entités + événements.

## 4. Univers

Quatre univers au-dessus des rubriques de collecte existantes (qui restent l'unité de collecte et de calibrage).

```yaml
# config/universes/<id>.yml
id: finance
name: Finance & Marchés
color: steel            # jeton de couleur de l'univers
domains: [finance]      # rubriques collectées rattachées
quota_today: 7
subthemes:
  - {id: actions, name: Actions, entity_types: [company]}
  - {id: taux, name: Taux & obligations, kinds: [central_bank, rates], entity_types: [rate, central_bank]}
  - {id: etf, name: ETF, entity_types: [etf]}
  - {id: crypto, name: Crypto, kinds: [crypto], entity_types: [crypto]}
  - {id: macro, name: Macro & banques centrales, kinds: [macro_data, central_bank]}
```

Un sous-thème est un filtre (types d'événement ou types d'entités) ; il ne crée pas de collecte.

| Univers | Rubriques | Quota « aujourd'hui » (défaut) |
|---|---|---|
| Sport | football, tennis, nba, f1, volley, sport-essentiel, rugby (nouvelle) | 3 |
| Géopolitique | geopolitique | 5 |
| Finance & Marchés | finance | 7 |
| IA | ia | 4 |

## 5. Entités et relations

### 5.1 Catalogue

```yaml
# config/entities/<type>.yml
- id: company:nvidia
  name: Nvidia
  aliases: [Nvidia, NVDA]
  wikidata: Q182477        # facultatif
  ticker: NVDA             # facultatif, types cotés
  universes: [finance, ia]
```

Types : `company, country, org, person, etf, crypto, rate, commodity, sector, tech, ai_model, central_bank, team, player, driver, competition, topic`. Identifiant `type:slug`, unique. Ajouter un type = ajouter un fichier et un gabarit de fiche.

Amorce rédigée (~400) : ~60 entreprises, ~40 pays, ~25 organisations, ~40 personnes, ~20 ETF, ~15 crypto, ~30 labos/modèles IA, ~30 technologies/sujets, ~20 matières premières/taux. Les 160 entrées des dictionnaires actuels y sont migrées.
Générées automatiquement : équipes et joueurs (football-data), pilotes et écuries (Jolpica).

### 5.2 Faits

Tâche hebdomadaire `facts` : Wikidata (drapeau, capitale, population, dirigeant, régime, monnaie, appartenances, secteur, siège, dirigeants, date de naissance, nationalité…) et Banque mondiale (PIB, population) → `data/facts/<type>.json`. En cas d'échec, la version précédente est conservée et l'échec apparaît dans `health.json`.

### 5.3 Rattachement événement → entités

1. Correspondance d'alias (mot entier, insensible à la casse) sur titre + extraits → liste de candidats.
2. L'appel Gemini de résumé existant reçoit cette liste et renvoie `entities` : sous-ensemble **de la liste**, jamais d'identifiant hors liste (vérifié par le code ; un identifiant inconnu est ignoré). Pas d'appel supplémentaire.
3. Sans IA (repli extractif) : les candidats d'alias sont gardés tels quels.
4. Gemini renvoie aussi `unknown` (noms propres importants absents du catalogue) → `data/candidates.json` avec compteur ; affiché dans la page santé. Entrée dans le catalogue uniquement par modification de la config.

### 5.4 Relations

Vocabulaire fixe, chaque verbe a un libellé dans les deux sens :

| verbe | sens direct | sens inverse |
|---|---|---|
| membre_de | membre de | a pour membre |
| dirige | dirige | dirigé par |
| fournit | fournisseur de | client de |
| concurrent | concurrent de | concurrent de |
| detient | détient | détenu par |
| suit | suit l'indice / le secteur | suivi par |
| expose | exposé à | expose |
| produit | produit | produit par |
| joue_pour | joue pour | effectif |
| participe | participe à | participants |
| investit | investit dans | financé par |
| voisin | frontalier de | frontalier de |

Sources : `config/relations.yml` (triplets rédigés), faits Wikidata (appartenances, dirigeants), données sportives (effectifs), et **co-occurrence** : deux entités présentes ensemble dans ≥ 3 événements sur 30 jours → lien `lie_a` pondéré, recalculé à chaque cycle.

### 5.5 « Concernés »

Pour chaque événement de niveau 1 ou 2 : parcours en largeur sur 2 sauts maximum en suivant uniquement `expose`, `fournit`, `detient`, `suit`, `produit`, `investit`, à partir de ses entités. Résultat : chaînes avec la raison de chaque maillon, limitées à 6, priorité aux entités cotées. Présentées comme contexte, jamais comme recommandation.

## 6. Sélection « Ce qu'il faut savoir aujourd'hui »

Score du jour = importance + bonus nouveauté (< 24 h) + bonus évolution (révision récente avec nouvelles sources) ; bonus suivis appliqué côté navigateur. Quotas par univers (§4). Diversité : au plus 2 événements par entité dominante. Les réglages sont dans `config/global.yml` (`today:`).

## 7. Données publiées

```
site/data/home.json                 aujourd'hui + bandeau
site/data/universes/<id>.json       page univers : chaud, sous-thèmes, blocs de données
site/data/entities/index.json       id, nom, type, alias, univers (recherche + pastilles)
site/data/entities/<type>/<slug>.json  fiche : faits, données, relations, événements récents (30 j)
site/data/graph.json                arêtes (source, verbe, cible, poids, origine)
site/data/markets.json              tableau Marchés (remplace quotes.json)
site/data/search.json               événements 30 j (existant)
football.json, f1.json, health.json (existants)
```

Les événements gagnent `entities: [ids]`, `concerned: [[ids…]]`, `universe`.

## 8. Pages et adresses

| Vue | Adresse |
|---|---|
| Aujourd'hui | `#/` |
| Univers / sous-thème | `#/u/<univers>[/<sous-thème>]` |
| Fiche entité | `#/x/<type>/<slug>` |
| Événement | `#/e/<id>` |
| Match | `#/m/<id>` (lot Sport) |
| Recherche | `#/s/<requête>` (résultats par catégorie) |
| Santé | `#/sante` |

## 9. Identité visuelle (direction A « Poste d'observation »)

- Sombre bleu nuit par défaut, variante claire selon le système. Un seul accent ambre, réservé au signal (nouveau, important, alerte).
- Couleurs d'univers en filets et points, jamais en aplats : Sport vert, Géopolitique brique, Finance bleu acier, IA violet.
- Typographies : titres en Newsreader, données en IBM Plex Mono, texte en sans-serif système. Deux polices Google Fonts, pas plus.
- Accueil : quatre bandes éditoriales (une info principale en grand + lignes compactes), pas de grille de cartes. Colonne « Radar » (suivis, entités en hausse) sur grand écran.
- Navigation basse sur mobile : Aujourd'hui · Sport · Géo · Finance · IA ; recherche en haut.
- **Pastille d'entité** : nom souligné pointillé + icône de type ; toucher → panneau (bas sur mobile, droite sur ordinateur) avec faits clés, 3 dernières actualités, relations, « Ouvrir la fiche ».
- **Fiche entité** : en-tête (nom, type, ligne de données clés), constellation SVG radiale des voisins cliquables, chronologie, bloc de données propre au type.
- **Événement** : ce qui s'est passé → pourquoi c'est important → Concernés (chaînes) → chronologie → sources et fiabilité.
- **Bandeau Vigie** : une ligne en haut, défilement lent, pause au survol/toucher, segments marqués de la couleur de l'univers (marchés, matchs du jour, agenda, alertes, nouveautés).
- Mouvement utile uniquement : transitions 150 ms, glissement des panneaux, marqueur « nouveau » qui s'allume brièvement, mini-graphiques réactifs au survol ; tout coupé sous `prefers-reduced-motion`.

## 10. Finance & Marchés (détaillé)

Page univers :
1. **Chaud (24 h)** : événements Finance de niveau 1-2 + événements des autres univers dont une chaîne « Concernés » atteint une entité cotée ; chaque actif concerné montre sa variation du jour. Couches Faits/Analyse/Interprétation/Incertitude conservées.
2. **Marchés** : indices (S&P 500, Nasdaq, CAC 40, DAX, Euro Stoxx 50, Nikkei), taux (US 2 et 10 ans, Bund 10 ans, OAT 10 ans, écart OAT–Bund), EUR/USD, USD/JPY, pétrole, gaz, or, cuivre, VIX, BTC, ETH, écarts de crédit IG et HY ; mini-graphique par ligne.
3. **Agenda** : banques centrales + publications macro (existant).
4. Onglets : Actions · Taux & obligations · ETF · Crypto · Macro.

Sources :
| Donnée | Source | Rythme |
|---|---|---|
| Cours actions, indices, devises, matières premières, ETF | relais existant | 30 min |
| Rendements US, courbe | FRED (DGS2, DGS10, …) | quotidien |
| Écarts de crédit | FRED (BAMLC0A0CM, BAMLH0A0HYM2) | quotidien |
| Courbe zone euro (AAA) | BCE, API de données sans clé | quotidien |
| Bund 10 ans, OAT 10 ans, écart | Bundesbank et Banque de France si leurs API gratuites donnent le quotidien, sinon FRED (mensuel) ; vérifié en première tâche du lot 2 | quotidien ou mensuel |
| Inflation, emploi, croissance | FRED | à publication |
| Résultats trimestriels (US) | SEC EDGAR companyfacts | quotidien, seulement si nouveau dépôt |
| Crypto | CoinGecko (API publique) | 30 min |
| Faits entreprise | Wikidata | hebdomadaire |
| ETF (indice, zone, frais, 10 positions) | catalogue rédigé | trimestriel, à la main |

Historique de cours pour les mini-graphiques : constitué par Vigie (un point par jour et par actif dans `data/prices/<annee>.jsonl`), complété si le relais fournit un historique.

Fiches : entreprise (cours + graphique 1 an, faits, chiffres clés trimestriels US, événements classés par nature, constellation concurrents/fournisseurs/clients, ETF détenteurs), taux (courbes, écarts, décisions), ETF, crypto (cours, capitalisation, 24 h/7 j, dominance BTC).

Détection d'information chaude : nouveaux types d'événement `guidance`, `buyback_dividend`, `management_change`, `contract`, `litigation` (mots-clés FR/EN) en plus de l'existant ; signal « mouvement anormal » quand un actif du catalogue varie de plus de ±5 % le jour d'un événement qui le concerne.

Limites assumées : pas de chiffres trimestriels pour les entreprises non américaines ; pas de calendrier prévisionnel de résultats (publication détectée le jour même) ; positions d'ETF à rafraîchir à la main.

## 11. Géopolitique, Sport, IA (grandes lignes, détaillés avant leur lot)

- **Géopolitique** : fiches pays (drapeau, capitale, population, dirigeant, régime, monnaie, PIB, appartenances, partenaires, sujets en cours, actualités), organisations, personnes ; sujets suivis dans le temps (`topic`) avec chronologie ; ponts vers Finance via `expose` (pays → matières premières → secteurs → entreprises/ETF).
- **Sport** : accueil (aujourd'hui, à venir, résultats, compétitions, actualités), fiches match avant/après, équipes, joueurs, rugby. Préalable : essai des offres gratuites (football-data, API-Football, TheSportsDB, balldontlie) pour savoir quelles données de match (compositions, buteurs, cartons, statistiques) sont réellement accessibles ; la fiche après match sera limitée à ce que ces sources fournissent. Pas de données tennis structurées gratuites connues : actualités + liens Flashscore.
- **IA** : labos, modèles, financements, infrastructures (GPU, data centers, énergie), réglementation ; ponts IA → infrastructure → entreprises cotées → marchés.

## 12. Découpage en lots

Chaque lot est mis en production à sa fin et a son propre plan d'implémentation.

1. **Socle** : univers, catalogue + faits Wikidata, rattachement, relations, « Concernés », sélection du jour, nouvelles pages (Aujourd'hui, univers, fiche entité générique, événement), pastilles et panneau, bandeau Vigie, recherche par catégorie, identité visuelle A, redirections.
2. **Finance** : §10.
3. **Géopolitique** : §11.
4. **Sport** : essai des sources puis §11.
5. **IA** : §11 et ponts inter-univers.

## 13. Tests et mesures

- Moteur : tests unitaires par module (rattachement contraint au catalogue, relations, parcours « Concernés », sélection du jour, schémas), test d'intégration du cycle complet sur données factices.
- Site : tests `node --test` des vues et composants, smoke Playwright en production (navigation entre univers, pastille → panneau → fiche → événement, recherche par catégorie, ancienne adresse redirigée).
- Mesures après chaque lot sur données réelles : part des événements de niveau 1-2 reliés à au moins une entité (objectif ≥ 80 %), taux de faux rattachements sur un échantillon de 50 (objectif ≤ 5 %), nombre de candidats inconnus, poids des fichiers publiés, temps d'affichage de l'accueil sur mobile.
