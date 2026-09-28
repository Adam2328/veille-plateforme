# Lot 1, partie B : nouvelle interface de Vigie 2, plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'interface actuelle (9 rubriques en cartes empilées) par l'interface Vigie 2 validée : direction A « Poste d'observation », accueil en 4 bandes d'univers faites de cartes illustrées, pages univers avec sous-thèmes, pages événement (court puis déplié, Concernés), fiches entités (grand visuel, constellation), pastilles et panneau d'aperçu, bandeau défilant, recherche par catégorie, thème clair/sombre, redirections des anciennes adresses.

**Architecture:** Site statique sans étape de build (modules ES natifs), inchangé côté hébergement. Les vues produisent des chaînes HTML (toute donnée passe par `esc()`, toute URL par `safeUrl()`), `app.js` route et gère les interactions. Données lues : `home.json` (aujourd'hui), `universes/<id>.json`, `entities/index.json` (chargé au démarrage), `entities/<type>/<slug>.json` (à la demande), `band.json`, `search.json`, plus `quotes.json`, `football.json`, `f1.json` déjà publiés. Les blocs de données existants (cours, matchs, classements, week-end F1, couches Faits/Analyse) sont conservés et restylés.

**Tech Stack:** HTML/CSS/JS natifs, `node --test`, Playwright (smoke, dans `.venv`).

**Spec:** `docs/superpowers/specs/2026-09-27-vigie-2-design.md` §6, §8, §9. **Prérequis :** partie A en production (fait le 2026-09-27, mesures dans `docs/superpowers/measurements/lot-1a.md`).

**Forme du plan (écart assumé) :** l'utilisateur a demandé d'enchaîner sans pause et la conception visuelle est validée dans la spec. Ce plan fixe donc précisément les fichiers, les interfaces, les comportements et **les cas de test** de chaque tâche ; le code d'implémentation est écrit directement pendant l'exécution, sous TDD (test écrit et vu en échec d'abord). Coût si c'est faux : un relecteur a moins de code de référence, compensé par la relecture finale de la branche.

## Global Constraints

- Aucune dépendance, aucun build ; modules ES dans `site/js/`. Fichiers < 800 lignes.
- Sécurité : toute donnée injectée dans le HTML passe par `esc()` ; toute URL (source, image) par `safeUrl()` ; images tierces avec `referrerpolicy="no-referrer"`, `loading="lazy"`, repli sur l'illustration en cas d'erreur (sans gestionnaire `onerror` inline : délégation depuis `app.js`).
- Tout en français. Pas de conseil d'achat/vente ajouté par l'interface.
- Badge de fiabilité sur les cartes **uniquement** pour `rumeur`, `non_confirmé`, `en_développement` ; détail complet sur la page événement.
- Thème : sombre bleu nuit ou clair selon l'appareil, bouton pour forcer (préférence dans `localStorage`). Un seul accent ambre (signal). Couleurs d'univers : Sport vert, Géo brique, Finance bleu acier, IA violet.
- Polices : Newsreader (titres), IBM Plex Mono (chiffres) via Google Fonts ; texte en sans-serif système.
- Mouvement présent mais utile, entièrement coupé sous `prefers-reduced-motion`.
- Mobile d'abord : barre de navigation basse ; pas de défilement horizontal de page (sauf le bandeau, volontaire) ; accessible au clavier (liens et boutons réels, focus visible).
- Les anciennes adresses `#/d/<rubrique>[/…]` redirigent vers l'univers correspondant.
- Commits conventionnels terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` ; branche `feat/vigie-interface` ; **aucune fusion dans `main` sans accord explicite**.

## Review Focus

1. Titre, nom d'entité, source ou URL malveillants (`<img onerror>`, `javascript:`) → rendus inertes partout (cartes, pastilles, panneau, fiche, bandeau, recherche).
2. Donnée absente (pas d'image, pas de résumé, entité inconnue de l'index, fichier d'univers ou de fiche indisponible) → affichage dégradé propre, jamais d'exception.
3. Navigation rapide (clic pendant un chargement) → la vue la plus récente gagne (garde `routeToken` conservée).
4. Préférences corrompues dans `localStorage` (ordre des univers, thème) → valeurs par défaut.
5. Ancienne adresse ou lien d'alerte (`#/e/<id>` d'un événement archivé, `#/d/football/mercato`) → page utile, pas une erreur.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `site/js/blocks.js` (ex-`render.js`, renommé et allégé) | Utilitaires (`esc`, `safeUrl`, `timeAgo`, dates, nombres) et blocs de données conservés : `renderQuotes`, `matchLine`, `renderMatches`, `renderStandings`, `f1Weekend`, `f1Strip`, `f1Tables`, `layersBlock`, `linksBlock` |
| `site/js/art.js` | Illustrations SVG générées (événement, entité) |
| `site/js/ui.js` | Composants : `pill`, `pills`, `relBadge`, `card`, `chains`, `bandHtml`, `panelHtml`, `constellation` |
| `site/js/views.js` | Vues : `viewToday`, `viewUniverse`, `viewEvent`, `viewEntity`, `viewSearch`, `viewError`, `navHtml` |
| `site/js/search.js` | + `searchEntities` |
| `site/js/state.js` | + préférences `theme`, `order` ; suivis par identifiant d'entité |
| `site/js/data.js` | + `loadUniverse`, `loadEntityIndex`, `loadEntity`, `loadBand` |
| `site/js/app.js` | Routeur, redirections, panneau, thème, bandeau, animations |
| `site/index.html`, `site/css/app.css`, `site/sw.js` | Coquille, design complet, version du cache |
| `site/tests/*.test.mjs` | Tests par module ; suppression des tests des vues retirées |
| `site/tests/e2e_smoke.py` | Smoke Playwright réécrit |

---

### Task 1 : socle JS (blocks, state, data, search)

- Renommer `render.js` en `blocks.js` ; retirer `renderHome`, `domainBlock`, `renderDomain`, `renderFootball`, `renderF1`, `renderEvent`, `renderNav`, `renderSearch`, `renderResults`, `renderArchived`, `followsBlock`, `card`, `row`, `badges`, `learnBlock`, `upcomingList`, `eventSections`, `fbTabs`, `footballStrip` (remplacés) ; exporter `layersBlock`, `linksBlock`, `fmtDate`, `fmtDateTime`, `parisDay`, `parisTime`, `nf`, `signed`, `plural`, et `f1Tables(f1)` (tableaux pilotes/constructeurs extraits de `renderF1`).
- `layersBlock(layers, domain, names = {})` : une puce égale à un identifiant d'entité connu (`rate:us-10y`) s'affiche avec le nom de l'entité.
- `state.js` : `defaultState()` gagne `prefs: {theme: 'auto', order: null}` ; `sanitize` ne garde que `theme ∈ {auto, dark, light}` et un `order` tableau de chaînes ; les suivis non conformes à `type:slug` sont ignorés ; `setTheme(state, t)`, `setOrder(state, ids)`, `orderedUniverses(state, bands)`.
- `data.js` : `loadUniverse(id)`, `loadEntityIndex()`, `loadEntity(id)` (`data/entities/<type>/<slug>.json`), `loadBand()`.
- `search.js` : `searchEntities(index, query)` → groupes `[{type, label, items}]` (nom ou alias, sans accents, 8 par type, tri par `n30` décroissant).
- Tests : mettre à jour les imports (`../js/blocks.js`) ; supprimer les tests des fonctions retirées ; ajouter : `layersBlock` remplace un identifiant par un nom et échappe ; préférences corrompues → défaut ; suivi « Nvidia » (ancien format) ignoré, `company:nvidia` gardé ; `orderedUniverses` applique l'ordre et complète les univers manquants ; `searchEntities` trouve « nvda » via alias, « etats unis » sans accent, groupe par type.

### Task 2 : illustrations et cartes

- `art.js` : `artFor(seed, universe, label, kind)` → SVG 16:9 déterministe (même graine → même dessin) : dégradé aux couleurs de l'univers (variables CSS `--u-*`), motif choisi par hachage (lignes d'horizon, anneaux, grille de points, relèvements), pictogramme du type d'événement (`kind`), étiquette courte (`label`) échappée ; `artEntity(entity)` même principe avec l'initiale.
- `ui.js` : `relBadge(ev)` (vide sauf rumeur / non confirmé / en développement) ; `pill(id, index)` (bouton `data-entity`, icône du type, nom ; identifiant inconnu → rien) ; `pills(ids, index, max = 3, skipTypes = [])` ; `card(ev, status, index)` : `article.card` avec lien étiré vers `#/e/<id>`, visuel (photo `https` avec `data-fallback` = illustration, sinon illustration), titre (`title_fr` sinon `title`), une ligne (`summary.pourquoi` sinon `summary.retenir`, rien sinon), 2 à 3 pastilles (sans les pays pour l'univers Sport), point « nouveau » si statut `new`/`updated`, badge de fiabilité selon la règle.
- Tests : même graine → même SVG, graines différentes → SVG différents ; étiquette malveillante échappée ; `relBadge` vide pour officiel/confirmé/rapporté ; carte sans image → illustration, image `http:` → illustration ; titre `<img onerror>` inerte ; pastilles limitées à 3 et pays exclus en Sport ; point « nouveau ».

### Task 3 : bandeau, pastilles, panneau d'aperçu, chaînes, constellation

- `bandHtml(band)` : segments (point couleur univers, libellé, valeur, variation +/−, heure pour matchs et agenda), liste dupliquée pour le défilement continu, liens `href` internes seulement (`#/…`).
- `panelHtml(page, index, state)` : grand visuel, type, nom, description, 4 faits, cours si présent, 3 dernières actualités, 6 relations en pastilles, bouton « Suivre », lien « Ouvrir la fiche ».
- `chains(concerned, index)` : chaînes « Concernés » lisibles (« Iran → produit → Pétrole → influence → Énergie »), maillons cliquables.
- `constellation(page, index)` : SVG radial, entité au centre, jusqu'à 12 voisins (écrits d'abord, puis co-occurrences), liens `#/x/<type>/<slug>`, libellé de relation au survol (`<title>`).
- Tests : bandeau vide → rien ; lien externe dans `href` ignoré ; variation négative marquée `down` ; panneau sans image → illustration ; chaîne avec identifiant inconnu → maillon textuel ; constellation limitée à 12 et nœuds liés.

### Task 4 : vues

- `viewToday(ctx)` : date, compteur « N nouveaux depuis HH h MM » (événements `new`/`updated` de `home.today`), 4 bandes dans l'ordre des préférences (titre, filet couleur, nombre, lien « Tout voir »), grille de cartes ; colonne Radar (suivis avec leurs dernières actualités tirées de l'index de recherche, entités en hausse = top `n30`, marchés résumés, prochains matchs) ; réglages : ordre des univers (monter/descendre) et thème.
- `viewUniverse(ctx, file, sub)` : en-tête, onglets « Tout » + sous-thèmes (filtre : rubrique, type d'événement, type d'entité ou entité listée), cartes niveaux 1-2, liste compacte niveau 3, blocs de données selon l'univers (Finance : tableau des cours ; Sport/foot : derniers résultats, prochains matchs, classements repliables ; Sport/f1 : week-end, dernier GP, championnats), agenda de l'univers, liens « Approfondir » des rubriques.
- `viewEvent(ctx, ev)` : grande image en tête (photo ou illustration), rangée de visuels des entités (image de l'index ou initiale), titre, « Ce qui s'est passé » (`quoi`), « Pourquoi c'est important » (`pourquoi`), bloc repliable « Aller plus loin » (qui, quand, à retenir, couches, Concernés, chronologie des sources), fiabilité détaillée, suivis par entité.
- `viewEntity(ctx, page)` : grand visuel, nom, type, ligne de chiffres clés, description, bouton « Suivre », constellation, relations groupées par libellé, chronologie des actualités (30 jours), lien vers l'univers.
- `viewSearch(ctx, query)` : champ, résultats entités par catégorie puis actualités (index 30 jours, titre français si disponible).
- `navHtml(active)` : liens Aujourd'hui · Sport · Géo · Finance · IA + recherche.
- Tests : ordre des bandes suivant les préférences ; compteur de nouveautés ; filtre de sous-thème (par rubrique, par type d'entité) ; page événement sans résumé → sources seulement ; actifs identifiants → noms ; fiche sans relations → pas de constellation ; recherche vide → invite.

### Task 5 : coquille, routeur, design, service worker, smoke

- `index.html` : bandeau, en-tête (marque Vigie, recherche, thème), `main`, colonne Radar, panneau (`<aside role="dialog">`), barre basse ; polices Newsreader + IBM Plex Mono.
- `app.js` : routes `#/`, `#/u/<id>[/<sub>]`, `#/e/<id>`, `#/x/<type>/<slug>`, `#/s/<q>` ; redirections `#/d/…` (`football→sport/foot`, `tennis→sport/tennis`, `f1→sport/f1`, `nba→sport/basket`, `volley→sport/volley`, `sport-essentiel→sport/autres`, autres → univers du même nom) ; événement introuvable → recherche dans les 4 univers puis archive ; clics : pastille → panneau, fermer (Échap, fond, bouton), suivre, thème, ordre ; images en erreur → illustration ; apparition des cartes (IntersectionObserver) ; `markSeen` à l'ouverture d'un événement.
- `app.css` : jetons (sombre/clair, couleurs d'univers, accent ambre), mise en page mobile/ordinateur, cartes, bandeau défilant (pause au survol/toucher, glissable), panneau, fiche, constellation, animations et `prefers-reduced-motion`.
- `sw.js` : cache `vigie-v2`.
- `e2e_smoke.py` : accueil (4 bandes, cartes, pas de défilement horizontal, mobile et ordinateur), univers et sous-thème, événement, pastille → panneau → fiche, recherche entité, ancienne adresse redirigée, thème forcé, hors ligne.
- Vérification : `node --test`, `pytest` (échantillon), smoke local sur les vraies données, captures d'écran relues.

### Task 6 : mise en production (après accord)

Relecture finale de la branche, corrections, demande d'accord, fusion, cycle, smoke en production.
