# Vigie 2 — poste d'observation personnel de l'information

Statut : validé en conversation le 2026-09-27 (socle, identité visuelle A, esquisse Finance, clé FRED), puis précisé par questionnaire (usage, accueil, lecture, langue, univers, ordre des lots).
Remplace la navigation de la spec du 2026-09-26 ; le moteur de cette spec (collecte → regroupement → fiabilité → score → résumé → publication) reste la base.

## 1. But

Passer d'un agrégateur par rubriques à un système de veille où chaque information est reliée à des **entités** (entreprise, pays, joueur, ETF, modèle d'IA…) et où l'on peut **explorer** : événement → entité → autres événements → entités voisines → autre univers.

Principe : Observer → Détecter → Comprendre → Explorer. Critère de réussite : en ouvrant Vigie, « voici ce que je dois savoir aujourd'hui », puis pouvoir comprendre pourquoi et aller plus loin en un ou deux gestes.

Les quatre univers ont **la même importance** : aucun n'est prioritaire, chacun reçoit le même niveau de soin.

Usage visé : coups d'œil de 2 à 5 minutes plusieurs fois par jour, surtout sur téléphone, et de temps en temps une séance d'exploration de 20 à 30 minutes.

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

| Univers | Rubriques | Angles prioritaires |
|---|---|---|
| Sport | football, tennis, f1 (couverture riche) ; nba, volley, rugby (nouvelle), sport-essentiel (actualités seulement) | d'abord les équipes, joueurs et compétitions suivis |
| Géopolitique | geopolitique | grandes puissances, conflits en cours, France et Europe, économie et ressources |
| Finance & Marchés | finance | investisseur long terme : tendances de fond, résultats, stratégie, macro, ETF |
| IA | ia | produits et modèles, business et argent, infrastructure, société et régulation |

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

Score du jour = importance + bonus nouveauté (< 24 h) + bonus évolution (révision récente avec nouvelles sources) ; bonus suivis appliqué côté navigateur.

Répartition : **plancher de 3 événements par univers**, puis les places restantes (total visé 16 à 20) vont aux meilleurs scores du jour, tous univers confondus ; un univers peut donc prendre plus de place un jour de forte actualité. Diversité : au plus 2 événements par entité dominante. Réglages dans `config/global.yml` (`today: {floor: 3, total: 18}`).

Ordre des bandes : fixe, **Finance · IA · Géopolitique · Sport** par défaut, modifiable dans le site (préférence gardée dans le navigateur).

Suivis : bouton « suivre » sur toute entité (comme aujourd'hui) ; pas de liste personnelle à gérer.

Nouveau depuis la dernière visite : point ambre sur les événements nouveaux ou mis à jour + compteur en tête (« 7 nouveaux depuis 8 h 12 »). Pas de section dédiée.

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

Les événements gagnent `entities: [ids]`, `concerned: [[ids…]]`, `universe`, `title_fr` (niveaux 1-2) et `image` (URL de la photo de l'article, si fournie). Les éléments collectés gagnent `image`.

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

- Thème sombre bleu nuit ou clair selon le réglage de l'appareil, avec un bouton pour forcer l'un ou l'autre (choix gardé dans le navigateur). Un seul accent ambre, réservé au signal (nouveau, important, alerte).
- **Tout en français** : titres et résumés traduits si la source est étrangère, lien vers l'article original. La traduction du titre est faite dans l'appel Gemini de résumé existant (niveaux 1 et 2) ; les événements de niveau 3, sans résumé, gardent leur titre d'origine (limite du quota gratuit).
- **Lecture courte puis dépliée** : un événement montre d'abord 2 à 3 phrases (ce qui s'est passé, pourquoi c'est important) ; un geste déplie l'analyse, le contexte, la chronologie, les Concernés.
- **Chaque information a une image.** Ordre : photo de l'article source si le flux en fournit une (champ `image` des éléments collectés) ; sinon **illustration générée** par le site en SVG (aucun coût) : fond aux couleurs de l'univers, motif, icône du type d'événement, chiffre clé si l'événement en porte un. Même format pour toutes les cartes.
- Couleurs d'univers en filets, points et fonds d'illustration : Sport vert, Géopolitique brique, Finance bleu acier, IA violet.
- Typographies : titres en Newsreader, données en IBM Plex Mono, texte en sans-serif système. Deux polices Google Fonts, pas plus.
- Densité équilibrée : environ deux univers visibles par écran de téléphone.
- **Accueil** : quatre bandes d'univers ; chaque bande est une **grille de cartes de même taille** (2 colonnes sur téléphone, 3 à 4 sur ordinateur), la plus importante en premier.
- **Carte** : photo au-dessus, titre, résumé d'une ligne (« pourquoi c'est important »), 2 à 3 pastilles d'entités. Pas de source ni d'heure sur la carte. Badge de fiabilité **uniquement** pour « Rumeur », « Non confirmé » et « En développement » (une rumeur ne doit jamais passer pour un fait) ; officiel/confirmé/rapporté sans badge. Point ambre si nouveau ou mis à jour depuis la dernière visite.
- **Ordinateur** : pleine largeur + colonne « Radar » à droite (suivis, entités en hausse, marchés, prochains matchs).
- **Téléphone** : barre de navigation en bas (Aujourd'hui · Sport · Géo · Finance · IA), recherche en haut.
- **Pastille d'entité** : nom souligné pointillé + icône de type ; toucher → panneau d'aperçu (bas sur mobile, droite sur ordinateur) avec faits clés, 3 dernières actualités, relations, « Ouvrir la fiche ».
- **Fiche entité** : en-tête dominé par un **grand visuel** (photo, logo, drapeau, sinon illustration) avec le nom, le type et une ligne de chiffres clés ; puis constellation SVG radiale des voisins cliquables, chronologie, bloc de données propre au type.
- **Événement** : grande photo en tête, puis rangée de visuels de données (visages/logos des entités concernées, mini-graphique, carte si pertinent) ; ensuite ce qui s'est passé → pourquoi c'est important → [déplier] analyse, Concernés (chaînes), chronologie → sources et fiabilité détaillée.
- **Bandeau Vigie** : une ligne en haut qui défile lentement en continu **et** se fait glisser au doigt ; pause au survol/toucher ; segments marqués de la couleur de l'univers (marchés, matchs du jour, agenda, alertes, nouveautés).
- **Mouvement présent mais utile** : transitions de page courtes, panneaux qui glissent, apparition des cartes au défilement, léger effet de profondeur sur les images, constellation animée, marqueur « nouveau » qui s'allume brièvement, mini-graphiques réactifs au survol. Tout est coupé sous `prefers-reduced-motion`.

## 10. Finance & Marchés (esquisse validée, détaillée avant son lot comme les autres univers)

Angle : investisseur long terme. Les tendances de fond, résultats, stratégie, macro et ETF passent avant les mouvements de court terme.

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
- **Sport** : accueil centré d'abord sur les équipes, joueurs et compétitions suivis, puis aujourd'hui, à venir, résultats, actualités. Couverture riche pour football, tennis et F1 (fiches match avant/après, équipes, joueurs, pilotes, classements) ; NBA, rugby et volley en actualités et entités simples. Préalable : essai des offres gratuites (football-data, API-Football, TheSportsDB, sources tennis) pour savoir quelles données de match (compositions, buteurs, cartons, statistiques, tableaux de tournoi) sont réellement accessibles ; les fiches seront limitées à ce que ces sources fournissent. À défaut de données tennis structurées gratuites : actualités, fiches joueurs, liens Flashscore.
- **IA** : labos, modèles, financements, infrastructures (GPU, data centers, énergie), réglementation ; ponts IA → infrastructure → entreprises cotées → marchés.

## 12. Découpage en lots

Un univers après l'autre, après un socle commun. Chaque lot est mis en production à sa fin, a sa propre section détaillée ajoutée à cette spec puis son propre plan d'implémentation.

1. **Socle** : univers, catalogue + faits Wikidata, rattachement, relations, « Concernés », sélection du jour, traduction des titres, images, nouvelles pages (Aujourd'hui, univers, fiche entité générique, événement), pastilles et panneau d'aperçu, bandeau Vigie, recherche par catégorie, identité visuelle A, thème, redirections. Les quatre univers y sont au même niveau.
2. **Sport** : essai des sources puis §11.
3. à 5. **Géopolitique, Finance, IA** : ordre choisi par l'utilisateur à la fin du lot Sport.

## 13. Tests et mesures

- Moteur : tests unitaires par module (rattachement contraint au catalogue, relations, parcours « Concernés », sélection du jour, schémas), test d'intégration du cycle complet sur données factices.
- Site : tests `node --test` des vues et composants, smoke Playwright en production (navigation entre univers, pastille → panneau → fiche → événement, recherche par catégorie, ancienne adresse redirigée).
- Mesures après chaque lot sur données réelles : part des événements de niveau 1-2 reliés à au moins une entité (objectif ≥ 80 %), taux de faux rattachements sur un échantillon de 50 (objectif ≤ 5 %), nombre de candidats inconnus, poids des fichiers publiés, temps d'affichage de l'accueil sur mobile.
