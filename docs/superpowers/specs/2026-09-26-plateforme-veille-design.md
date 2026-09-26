# Plateforme de veille multi-domaines : spécification de conception

Date : 2026-09-26. Statut : à relire avant plan d'implémentation.

## 1. Objectif

Un centre de contrôle personnel de l'information : un seul site, plusieurs veilles spécialisées, un moteur commun de collecte, regroupement, hiérarchisation et synthèse, une logique éditoriale par domaine. Usage quotidien de 5 à 15 minutes, avec deux niveaux : compréhension de l'essentiel à l'Accueil, profondeur à la demande dans chaque veille.

Critères de réussite :
- En ouvrant le site, savoir « ce que je dois absolument savoir aujourd'hui » en quelques minutes.
- Une actualité reprise par 15 médias = 1 événement + 15 sources.
- Une rumeur n'est jamais présentée comme un fait.
- Distinguer ce qui est nouveau, déjà vu et mis à jour depuis la dernière visite.
- Coût d'exploitation proche de 0 €, entièrement automatisé.
- Ajouter une veille = ajouter un fichier de configuration, pas du code.

Hors périmètre : recommandations d'achat ou de vente, comptes utilisateurs multi-personnes, application native.

## 2. Décisions d'architecture

**Approche retenue (A)** : site statique + pipeline Python planifié sur GitHub Actions + fichiers JSON versionnés dans le dépôt. Vercel sert le site. Aucun serveur, aucune base hébergée.

Alternatives écartées :
- Supabase Postgres + Next.js : surdimensionné, plan gratuit mis en pause, c'est le projet « News IA » existant.
- Ajout d'un état utilisateur côté Cloudflare : prématuré. L'état utilisateur est isolé côté navigateur, donc ajoutable plus tard sans rien casser.

Le pipeline et le site sont découplés par un contrat de données (schémas JSON versionnés). Changer l'un n'impose pas de changer l'autre.

**Emplacement** : `veille-générale/plateforme/`, dépôt Git dédié. `mon-brief-quotidien/` reste intact et en production jusqu'à la bascule.

**Repris de l'existant** : principe Actions + fichiers versionnés + Vercel, quota Gemini gratuit, sources RSS Finance (Bloomberg Markets, The Economist), agenda, tokens de design « Ledger » (à relire dans `mon-brief-quotidien/REFONTE_LEDGER.md`).
**Abandonné** : HTML monolithique généré par chaînes, prompt Gemini unique, arrêt total du site quand le quota est épuisé, dépendance à Gmail et au forward manuel des Echos.

## 3. Structure du dépôt

```
plateforme/
  config/
    global.yml               # poids de scoring, seuils, paliers de fiabilité, quotas
    domains/{ia,finance,football,...}.yml
  engine/                    # Python, un module par étape
    collect/  rss.py api.py html.py social.py
    normalize.py cluster.py score.py reliability.py
    summarize.py publish.py
    adapters/                # football_data, yahoo, ...
  schemas/                   # JSON Schema du contrat de données
  data/
    raw/                     # items bruts, purgés après 14 jours
    events/                  # 1 JSONL par mois, source de vérité
    public/                  # ce que lit le site
  site/                      # HTML + CSS + modules JS natifs, sans build
  tests/                     # pytest + fixtures
  .github/workflows/pipeline.yml
```

## 4. Modèle de données

- **Source** : `id, nom, tier` (1 officiel, 2 spécialisé reconnu, 3 généraliste, 4 agrégateur, 5 social), `type` (rss, api, html, social), `domaines`, `poids`, `origine` (pour la détection de syndication).
- **Item** (article brut) : `id` (hash de l'URL), `source`, `titre`, `publié_le`, `extrait`, `langue`, `origine`.
- **Event** (unité centrale) :
  - identité : `id` figé au premier regroupement, `rev` (entier incrémenté à chaque mise à jour du contenu), `first_seen`, `updated_at`.
  - classement : `domaine`, `kind`, `importance` (0-100), `niveau` (1, 2, 3).
  - fiabilité : `officiel | confirmé | rapporté | en_développement | non_confirmé | rumeur`, avec `fiabilité_raison` (règle appliquée, sources décisives).
  - contenu : `titre`, `synthèse {quoi, qui, quand, pourquoi, retenir}`, `synthèse_mode` (`llm` ou `extractif`). Finance : `faits, analyse, interprétation, incertitude, actifs, favorables, risques, à_surveiller`. Géopolitique : `conséquences`, distinction faits / déclarations d'acteurs.
  - liens : `entités[]`, `items[]` (ids des sources), `liés[]`.
- **Structured** : classements, résultats, calendriers, cours, sans LLM.
- **Agenda** : `{date, domaine, titre, importance, entités}`.

Publié pour le site :
- `home.json` : par veille, ~12 événements répartis en niveaux 1/2/3 (nombre configurable), plus « À retenir aujourd'hui ». Objectif inférieur à 100 Ko.
- `domains/<d>.json` : 7 jours d'événements, agenda, données structurées.
- `archive/AAAA-MM.json` : historique mensuel, plus un index de recherche chargé à la demande (MiniSearch côté navigateur).
- `health.json` : état des sources, fraîcheur, consommation du quota IA.

État utilisateur (`localStorage`, exportable en JSON) : `dernière_visite`, `vus{id: rev}`, `suivis[]`, `favoris[]`, `poids_domaines`. Nouveau = `id` absent de `vus` ; Mis à jour = `rev` supérieur à celui vu ; Déjà vu sinon.

## 5. Pipeline

Cadence : toutes les 30 min de 6h à 23h (heure de Paris), avec un déclencheur externe en filet de sécurité (le `schedule` GitHub n'est pas garanti, incident du 29/07/2026 sur l'ancien projet). Groupe `concurrency`, idempotence, commit uniquement s'il y a un diff.

Étapes : `collect → normalize → cluster → score+fiabilité → structured → summarize → publish`.

1. **collect** : chaque source est isolée (timeout, retry, erreur loguée). Une panne ne bloque rien et alimente `health.json`.
2. **normalize** : nettoyage, langue, dédup exacte (URL, hash de titre), détection de syndication (« selon L'Équipe » = 1 origine).
3. **cluster** : chaque item est comparé aux événements ouverts des 48 h du même domaine. Similarité TF-IDF cosinus sur titre et extrait, plus bonus de recouvrement d'entités. Au-dessus du seuil : rattachement (`rev` incrémenté si le contenu change). Sinon : nouvel événement. Embeddings locaux multilingues en second passage, uniquement si les mesures montrent que TF-IDF ne suffit pas.
4. **score + fiabilité** : voir sections 6 et 7.
5. **structured** : adapters API, sans LLM.
6. **summarize** : voir section 8.
7. **publish** : validation de schéma, écriture de `data/public/*`. Jamais de publication d'un JSON invalide : le dernier bon état est conservé et affiché « périmé depuis X ».

## 6. Score d'importance

Somme pondérée (0-100), poids dans `global.yml`, surchargés par domaine :

| Facteur | Principe |
|---|---|
| Autorité | meilleur tier parmi les sources |
| Couverture | nombre d'origines indépendantes (log) et de tiers distincts |
| Nature | poids du `kind` propre au domaine (finale, transfert acté, sortie de modèle, décision Fed > match de poule, etc.) |
| Entités | bonus entités majeures du domaine ; bonus entités suivies appliqué côté site |
| Vélocité | nouvelles sources dans les 2 dernières heures |
| Fraîcheur | décroissance selon l'âge |
| Pénalité | événement porté uniquement par des sources tier 4-5 |

Niveau : déduit du score et de seuils par veille (T1, T2, T3), avec un plafond de niveau 1 par jour, puis quota d'environ 12 événements par veille. Sport-L'essentiel, Tennis et Volley ont des seuils et des filtres d'entrée stricts (l'onglet peut rester vide).

## 7. Fiabilité (déterministe, jamais décidée par le LLM)

- **officiel** : au moins une source tier 1 (site du club, de la ligue, du régulateur, de l'entreprise, communiqué).
- **confirmé** : au moins 2 origines indépendantes de tier ≤ 3, ou 1 tier 2 + 1 autre.
- **rapporté** : 1 seule origine fiable (tier 2 ou journaliste en liste blanche).
- **en_développement** : croissance rapide (nouvelles sources < 1 h) ou marqué en direct.
- **non_confirmé / rumeur** : lexique de conditionnel et d'attribution vague et uniquement des sources tier 4-5.
- La répétition entre agrégateurs ne fait jamais monter la fiabilité. Rumeur et non confirmé sont plafonnés au niveau 2 et toujours étiquetés.

## 8. Stratégie IA et coûts

| Tâche | Solution | LLM |
|---|---|---|
| Collecte, filtrage, dédup | règles, mots-clés, hash | non |
| Regroupement | TF-IDF + entités (embeddings locaux si nécessaire) | non |
| Score, niveau, fiabilité | formule + lexique | non |
| Résultats, classements, calendriers, cours | API structurées | non |
| Détection d'entités | dictionnaires de config | non |
| Synthèses N1-N2 (Quoi/Qui/Quand/Pourquoi/Retenir ; couches Finance et Géopolitique) | Gemini Flash gratuit, 1 appel groupé par veille et par cycle | oui |
| « Ce qui change vraiment » (IA), « À retenir aujourd'hui » | 1 appel par jour sur les synthèses existantes | oui |
| « À connaître » NBA | contenu écrit en config | non |

Garde-fous :
- Le LLM ne reçoit que titres et extraits des sources de l'événement.
- Sortie JSON validée par schéma, avec citation des ids de sources.
- Il ne décide ni de la fiabilité, ni du niveau, ni de l'importance.
- Prompt Finance : analyse factuelle, aucune recommandation, jamais « acheter » ou « vendre ».
- Cache par hash des sources : un événement inchangé n'est jamais résumé deux fois.
- Quota épuisé : repli extractif (`synthèse_mode: extractif`, badge « résumé automatique simple »). Le site ne reste jamais sans contenu.
- Consommation du quota mesurée à chaque cycle (`health.json`), limites gratuites Gemini à vérifier au démarrage, auto-plafonnement du pipeline.

Coût cible : 0 € (Actions sur dépôt public, Vercel Hobby, Gemini gratuit, ntfy.sh, APIs sportives gratuites). Dépôt public : aucun secret dans le code, secrets GitHub uniquement.

## 9. Alertes

Règle stricte, configurable par veille : niveau 1, score ≥ 85, fiabilité officiel ou confirmé, `kind` dans la liste d'alerte du domaine (décision Fed/BCE, sortie majeure OpenAI/Anthropic/Google, blessure d'un joueur clé, transfert acté, etc.), maximum 3 par jour au total, une seule alerte par événement. Canal : ntfy.sh (push) et bandeau sur le site. Les alertes sur entités suivies s'affichent à l'ouverture du site (le serveur ne connaît pas les suivis).

## 10. UX et interface

Trois niveaux : Accueil (2-3 min), page de veille (5-10 min), fiche événement.

**Navigation** : desktop, barre latérale des veilles avec compteur de nouveautés et point pour le niveau 1 non vu. Mobile, barre d'onglets en bas (Accueil, Football, IA, Finance, Plus). Recherche globale `Ctrl+K` (événements, entités, dates, domaines, filtres période et domaine). Page d'archives par mois.

**Accueil** :
- Bandeau « Depuis ta dernière visite » (nombre de nouveautés et de mises à jour, bouton « Tout marquer comme vu »).
- « À retenir aujourd'hui » : 5 à 7 événements de niveau 1 tous domaines, une ligne « Quoi / pourquoi ça compte ».
- Un bloc par veille, dans l'ordre des préférences : niveau 1 en cartes larges, niveau 2 en lignes compactes, niveau 3 replié (« Voir N autres »), bande « À venir », lien « Approfondir ».
- Badges Nouveau / Mis à jour, effacés une fois vus.
- Section « Vos suivis » quand des entités sont suivies.

**Fiche événement** (panneau latéral desktop, page pleine mobile) : synthèse Quoi/Qui/Quand/Pourquoi/Retenir, étiquette de fiabilité avec sa raison, sources triées par tier (sociales repliées), chronologie des mises à jour, événements liés, boutons Suivre, Favori, Ouvrir la source.

**Modules par veille** (même squelette : fil filtrable, agenda, données structurées) :
- Football : Actu, Résultats, Classements, Calendrier, Mercato (rumeurs masquées par défaut, filtre par fiabilité), Blessures et suspensions, Compétitions.
- IA : « Ce qui change vraiment » (3-5 changements concrets) en tête, filtres par acteur et par type (modèle, produit, API, open source, régulation).
- Finance : ruban de cours, couches Faits / Analyse / Interprétation / Incertitude, actifs concernés, favorables, risques, à surveiller.
- Phase 2 : F1 (vue week-end de Grand Prix Vendredi/Samedi/Dimanche + « À retenir » en 5 points), NBA (rubrique « À connaître »), Tennis, Volley, Sport-L'essentiel, Géopolitique (Que s'est-il passé ? Pourquoi c'est important ? Qui est concerné ? Conséquences ?).

**Personnalisation** : bouton Suivre sur les entités, section « Vos suivis », remontée d'un cran de leurs événements, réglage du poids des domaines. Tout en `localStorage`, export/import JSON.

**Design** : sobre, premium, dense sans être surchargé. Tokens « Ledger » repris après relecture. Modes clair et sombre. Une couleur d'accent par veille, avec parcimonie. Hiérarchie par la taille et l'espacement.

**Technique** : ES modules natifs, sans build. PWA installable (manifest + service worker), lecture hors ligne du dernier état. Navigation clavier, contrastes AA, `prefers-reduced-motion`.

## 11. Sources (phase 1)

Hiérarchie : officiel > spécialisé reconnu > généraliste > agrégateur > social. Les URL de flux ci-dessous sont des **candidats** ; un contrôle de santé (HTTP, format, fraîcheur) est fait à l'implémentation de chaque jalon, et toute source non conforme est remplacée. Sources sans flux fiable : `type: html` ou écartées.

**IA**
- Officiel (tier 1) : blogs et pages d'actualités d'OpenAI, Anthropic, Google DeepMind / Google AI, Meta AI, Microsoft AI, xAI, Mistral, NVIDIA, DeepSeek, Alibaba (Qwen), Hugging Face ; dépôts GitHub des grands projets open source (releases, flux Atom).
- Recherche : arXiv (cs.AI, cs.CL, cs.LG, cs.RO), Papers with Code, Hugging Face Daily Papers.
- Spécialisé (tier 2) : The Verge (AI), TechCrunch (AI), Ars Technica, VentureBeat, MIT Technology Review, The Information (titres), Import AI, The Batch.
- Régulation : Commission européenne (AI Act), Journal officiel de l'UE, NIST, Maison-Blanche.
- Détection rapide (tier 4-5) : Hacker News (API Algolia), Reddit r/LocalLLaMA et r/singularity, Bluesky, benchmarks (LMArena, Artificial Analysis).

**Finance et Marchés**
- Officiel (tier 1) : BCE (communiqués, discours), Fed (communiqués, minutes), Banque d'Angleterre, BoJ, SEC EDGAR (8-K), communiqués d'entreprises, Eurostat, BLS, BEA.
- Spécialisé (tier 2) : Bloomberg Markets (RSS existant), The Economist (RSS existant), Financial Times (titres), WSJ Markets, Les Echos, CNBC, MarketWatch, Investing.com.
- Données structurées : Yahoo Finance (indices, actions, devises, matières premières, crypto), FRED (macro, taux), ECB Data Portal, calendrier économique.
- Agrégateurs / sociaux : Google News RSS ciblé par entités suivies, Reddit r/investing.
- Agenda : calendrier macro et résultats d'entreprises (dates de publication).

**Football**
- Officiel (tier 1) : sites de la FFF, UEFA, FIFA, LFP, Premier League, LaLiga, Serie A, Bundesliga, sites des clubs majeurs.
- Données structurées : football-data.org (classements, résultats, calendriers de Ligue 1, Premier League, Liga, Serie A, Bundesliga, Ligue des Champions, Coupe du Monde, Euro), sans LLM. Couverture des autres compétitions (Europa, Conférence, féminines, Ligue des Nations) à vérifier selon le plan gratuit et complétée par d'autres API ou par les sites officiels.
- Presse spécialisée (tier 2) : L'Équipe, RMC Sport, Eurosport, Foot Mercato, Le Figaro Sport, BBC Sport, Sky Sports, The Athletic (titres), ESPN, Marca, AS, Gazzetta dello Sport, Kicker.
- Journalistes de transferts fiables (liste blanche, tier 2 « rapporté ») : à définir en config, avec vérification de leur historique.
- Détection rapide (tier 4-5) : Google News RSS, Reddit r/soccer, Bluesky, chaînes Telegram publiques, YouTube RSS.
- **Actu Foot et BeFootball** vivent surtout sur X, sans API gratuite fiable. Voie proposée : ponts RSS (instance RSSHub) activés « au mieux », désactivés par défaut et sans impact sur le reste. À revoir avec l'utilisateur si ces deux comptes sont indispensables.

## 12. Gestion des erreurs

- Source en panne : isolée, signalée dans `health.json` et sur le site (« source X muette depuis 6 h »).
- Quota IA épuisé : repli extractif.
- Sortie LLM invalide : une nouvelle tentative, puis repli extractif pour l'événement.
- JSON publié invalide : jamais publié, dernier bon état conservé.
- Retour arrière : historique Git.
- Le site affiche toujours l'heure de dernière mise à jour.

## 13. Tests et mesure

- `pytest` avec fixtures réelles sur `cluster`, `score`, `reliability` (15 articles sur un même transfert donnent 1 événement, une rumeur ne devient jamais « confirmée », un événement mis à jour incrémente `rev`).
- Test de contrat : le JSON publié respecte les schémas.
- Vérification visuelle dans le navigateur (desktop et mobile) à chaque jalon.
- Mesures après chaque jalon : articles collectés vs événements affichés, doublons restants, rumeurs correctement étiquetées, quota IA consommé, durée d'un cycle. Toute mesure insatisfaisante est corrigée avant d'avancer.

## 14. Découpage

**Phase 1** (cette spec) :
1. Contrat et coquille : schémas, données d'exemple réalistes, site (navigation, Accueil, fiche événement, « depuis ma dernière visite »), ouvert dans Live Preview (extension `ms-vscode.live-server`).
2. Moteur + veille IA de bout en bout sur de vraies sources.
3. Finance (RSS existants, cours, couches Faits/Analyse/Interprétation/Incertitude), en remplacement de Gmail.
4. Football (sources, compétitions, API structurées, mercato avec fiabilité).
5. Transversal : « À retenir aujourd'hui », recherche et archives, alertes, suivis, PWA, déploiement Vercel en parallèle de l'ancien site.

**Phase 2** : F1, NBA + « À connaître », Tennis, Volley, Sport-L'essentiel, Géopolitique. Chacune = une configuration + un module d'interface éventuel.

## 15. Hypothèses et risques

- Les limites gratuites de Gemini et de football-data.org évoluent ; vérifiées au démarrage.
- TF-IDF peut sous-regrouper les articles multilingues ; mesure au jalon 2, embeddings locaux si besoin.
- Le déclencheur `schedule` de GitHub est non garanti ; cron externe en filet.
- Couverture X/Twitter limitée (voir section 11).
- Le dépôt étant public, tout contenu publié est public.
