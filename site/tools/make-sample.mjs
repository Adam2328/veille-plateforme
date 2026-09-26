// Génère des données d'exemple conformes à schemas/public.schema.json (usage : design du site).
import { mkdirSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const now = new Date();
const ago = (h) => new Date(now - h * 3600e3).toISOString();
const src = (name, tier, title, h) => ({
  name, tier, url: `https://example.com/${encodeURIComponent(name)}`, title, published_at: ago(h),
});
const S = (quoi, qui, quand, pourquoi, retenir) => ({ quoi, qui, quand, pourquoi, retenir });
let n = 0;
const ev = (domain, level, importance, reliability, reason, kind, title, summary, entities, sources, rev = 1) => ({
  id: `sample_${++n}`, rev, domain, kind, title, first_seen: ago(7), updated_at: ago(1 + n / 4),
  importance, level, reliability, reliability_reason: reason,
  summary, summary_mode: summary ? 'llm' : 'aucun', entities, sources,
});

const DOMAINS = [
  { id: 'ia', name: 'IA', accent: '#5B3FA8' },
  { id: 'finance', name: 'Finance & Marchés', accent: '#1A3A6B' },
  { id: 'football', name: 'Football', accent: '#0B6E4F' },
];

const events = [
  ev('ia', 1, 92, 'officiel', 'Source officielle : blog du laboratoire', 'model_release',
    'Un laboratoire majeur publie un nouveau modèle de raisonnement',
    S('Publication d’un modèle de raisonnement avec une fenêtre de contexte élargie.', 'Exemple Labs', 'Aujourd’hui', 'Le modèle est disponible dans l’API dès aujourd’hui, à prix inchangé.', 'Disponible tout de suite en API, sans surcoût.'),
    ['Exemple Labs'], [src('Exemple Labs (blog officiel)', 1, 'Présentation du nouveau modèle', 3), src('Exemple Tech Media', 2, 'Ce que change le nouveau modèle', 2), src('Exemple Agrégateur', 4, 'Nouveau modèle : tout ce qu’il faut savoir', 1)], 3),
  ev('ia', 1, 84, 'confirmé', '3 origines indépendantes dont 2 médias reconnus', 'funding_acquisition',
    'Un accord de fourniture de puces d’IA de plusieurs milliards annoncé',
    S('Accord pluriannuel de fourniture de puces pour l’entraînement de modèles.', 'Un fabricant de puces et un laboratoire', 'Cette semaine', 'Il sécurise la capacité de calcul du laboratoire pour les prochains modèles.', 'Le calcul reste le facteur limitant de la course aux modèles.'),
    ['Exemple Puces'], [src('Exemple Business', 2, 'Accord de puces à plusieurs milliards', 4), src('Exemple Presse Éco', 2, 'Le laboratoire assure son calcul', 3), src('Exemple Généraliste', 3, 'Un contrat record dans les puces', 2)]),
  ev('ia', 2, 61, 'rapporté', '1 origine fiable (média spécialisé)', 'regulation',
    'Règlement européen sur l’IA : nouvelle étape du calendrier d’application',
    S('Publication du calendrier de la prochaine phase d’application.', 'Commission européenne (selon un média spécialisé)', 'Dans les prochains mois', 'Les fournisseurs de modèles à usage général devront documenter leurs données d’entraînement.', 'Prévoir la mise en conformité documentaire.'),
    ['UE'], [src('Exemple Tech Media', 2, 'Le calendrier d’application se précise', 5)]),
  ev('ia', 2, 55, 'en_développement', 'Croissance rapide du nombre de sources', 'product_launch',
    'Panne de plusieurs heures sur une API d’IA très utilisée',
    S('Interruption de service de l’API, en cours de rétablissement.', 'Un fournisseur d’API', 'Ce matin', 'Des applications tierces sont indisponibles.', 'Situation en évolution, à suivre.'),
    [], [src('Exemple Statut', 1, 'Incident en cours d’investigation', 1), src('Exemple Forum', 5, 'Tout est down chez moi', 0.5), src('Exemple Tech Media', 2, 'Panne sur une API majeure', 0.7)], 2),
  ev('ia', 3, 38, 'rapporté', '1 origine fiable (média spécialisé)', 'research',
    'Un benchmark ouvert classe dix nouveaux modèles', null, [], [src('Exemple Recherche', 2, 'Résultats du benchmark', 9)]),

  ev('finance', 1, 90, 'officiel', 'Source officielle : communiqué de la banque centrale', 'central_bank',
    'La banque centrale maintient ses taux directeurs',
    S('Maintien des taux directeurs, ton attentif sur l’inflation.', 'Banque centrale', 'Hier soir', 'Les marchés obligataires ajustent leurs anticipations de baisse.', 'Pas de changement de taux, le débat se déplace sur le calendrier.'),
    ['Banque centrale'], [src('Banque centrale (communiqué)', 1, 'Décision de politique monétaire', 5), src('Exemple Marchés', 2, 'Taux inchangés, ton prudent', 4)]),
  ev('finance', 2, 66, 'confirmé', '2 origines indépendantes de tier 2', 'earnings',
    'Un géant de la tech relève sa prévision annuelle',
    S('Relèvement de la prévision de chiffre d’affaires annuel après un trimestre supérieur aux attentes.', 'Un groupe technologique', 'Après la clôture', 'Le titre progresse dans les échanges hors séance.', 'Attention à la réaction à l’ouverture.'),
    ['Groupe Tech'], [src('Exemple Marchés', 2, 'Prévision relevée', 6), src('Exemple Business', 2, 'Résultats supérieurs aux attentes', 6)]),
  ev('finance', 2, 52, 'rumeur', 'Formulation au conditionnel, sources tier 4-5 uniquement', 'm_and_a',
    'Un rapprochement dans la banque serait à l’étude',
    S('Des sources non identifiées évoquent une discussion préliminaire.', 'Deux banques (non confirmé)', 'Non précisé', 'Aucune confirmation officielle : à traiter comme une rumeur.', 'Ne pas considérer l’opération comme acquise.'),
    [], [src('Exemple Agrégateur', 4, 'Une fusion serait envisagée', 3), src('Exemple Forum', 5, 'Il paraît que…', 2)]),
  ev('finance', 3, 34, 'rapporté', '1 origine fiable', 'commodities', 'Le pétrole recule après la hausse des stocks', null, [], [src('Exemple Marchés', 2, 'Pétrole en baisse', 8)]),

  ev('football', 1, 91, 'officiel', 'Source officielle : site de la compétition', 'result',
    'Finale de la coupe : victoire 2-1 après prolongation',
    S('Victoire 2-1 après prolongation en finale.', 'Le vainqueur et le finaliste', 'Hier soir', 'Premier titre de la décennie pour le vainqueur.', 'Score 2-1 a.p., but décisif à la 116e minute.'),
    ['Le vainqueur'], [src('Exemple Compétition (officiel)', 1, 'Résultat final', 12), src('Exemple Sport', 2, 'Le récit de la finale', 11), src('Exemple Sport 2', 2, 'Les notes du match', 10)]),
  ev('football', 1, 80, 'confirmé', '2 origines indépendantes de tier 2', 'transfer',
    'Transfert : un attaquant signe pour cinq saisons',
    S('Signature d’un attaquant pour cinq saisons.', 'Un attaquant et son nouveau club', 'Aujourd’hui', 'Le club renforce son secteur offensif avant la reprise.', 'Contrat de cinq ans, visite médicale passée.'),
    ['Le club'], [src('Exemple Sport', 2, 'C’est fait pour l’attaquant', 3), src('Exemple Mercato', 2, 'Signature officialisée', 2.5)]),
  ev('football', 2, 57, 'rumeur', 'Formulation au conditionnel, sources tier 4-5 uniquement', 'transfer',
    'Un milieu de terrain serait proche d’un départ',
    S('Un départ serait envisagé selon des sources non confirmées.', 'Un milieu de terrain', 'Non précisé', 'Aucune confirmation du joueur ni du club.', 'Rumeur : ne rien conclure avant confirmation.'),
    [], [src('Exemple Réseau', 5, 'Il pourrait partir', 4), src('Exemple Agrégateur', 4, 'Départ possible', 3)]),
  ev('football', 2, 54, 'rapporté', '1 origine fiable (média spécialisé)', 'injury',
    'Blessure : un titulaire absent trois semaines',
    S('Absence estimée à trois semaines après un examen.', 'Un joueur titulaire', 'Cette semaine', 'Il manquera les deux prochains matchs de championnat.', 'Retour attendu dans trois semaines.'),
    [], [src('Exemple Sport', 2, 'Trois semaines d’absence', 6)], 2),
  ev('football', 3, 33, 'rapporté', '1 origine fiable', 'fixtures', 'Le calendrier de la prochaine journée est dévoilé', null, [], [src('Exemple Compétition (officiel)', 1, 'Calendrier de la journée', 20)]),
];

const byDomain = (id) => events.filter((e) => e.domain === id);
const upcoming = { ia: [{ date: ago(-72), title: 'Conférence développeurs d’un grand laboratoire' }], finance: [{ date: ago(-48), title: 'Publication de l’inflation mensuelle' }, { date: ago(-120), title: 'Réunion de la banque centrale' }], football: [{ date: ago(-24), title: 'Journée de championnat' }] };

const layers = (o) => ({ faits: [], analyse: [], interpretation: [], incertitude: [], actifs: [], favorables: [], risques: [], a_surveiller: [], ...o });
const byId = (id) => events.find((e) => e.id === id);
byId('sample_6').layers = layers({
  faits: ['Taux directeurs maintenus à l’issue de la réunion.', 'Le communiqué décrit une inflation encore au-dessus de la cible.'],
  analyse: ['Des économistes cités par la presse y voient un signal de prudence.'],
  interpretation: ['Le marché pourrait décaler ses anticipations de baisse de taux.'],
  incertitude: ['Le calendrier des prochaines décisions dépend des chiffres d’inflation.'],
  actifs: ['Obligations souveraines', 'Banques'],
  favorables: ['Visibilité sur la politique monétaire'],
  risques: ['Repli des marchés obligataires si le ton se durcit'],
  a_surveiller: ['Prochaine publication de l’inflation'],
});
byId('sample_7').layers = layers({
  faits: ['Prévision annuelle de chiffre d’affaires relevée.'],
  analyse: ['Un courtier cité par la presse juge le trimestre solide.'],
  incertitude: ['La durabilité de la demande au trimestre suivant reste à confirmer.'],
  actifs: ['Groupe Tech'],
  a_surveiller: ['Réaction du titre à l’ouverture'],
});
const quote = (symbol, name, group, price, change, change_pct, extra = {}) => ({
  symbol, name, group, price, change, change_pct, currency: '', as_of: ago(2), stale: false, ...extra,
});
const quotes = {
  checked_at: now.toISOString(),
  quotes: [
    quote('^FCHI', 'CAC 40', 'Indices', 8077.8, -3.63, -0.04),
    quote('^GSPC', 'S&P 500', 'Indices', 7743.41, 92.91, 1.21),
    quote('^GDAXI', 'DAX', 'Indices', 25408.64, 104.5, 0.41),
    quote('EURUSD=X', 'EUR/USD', 'Devises', 1.14, -0.0079, -0.69),
    quote('^TNX', 'Taux US 10 ans', 'Taux', 5.18, 0.22, 4.45),
    quote('GC=F', 'Or', 'Matières premières', 4321.2, -62.7, -1.43, { stale: true }),
    quote('BTC-USD', 'Bitcoin', 'Crypto', 83973.18, -2199.1, -2.55),
    quote('^VIX', 'VIX', 'Volatilité', 14.87, 0, 0),
  ],
};
const row = (position, team, played, won, draw, lost, gf, ga, points, form) => ({ position, team, played, won, draw, lost, gf, ga, gd: gf - ga, points, form });
const mtch = (id, competition, home, away, hs, as, h, status = 'FINISHED') => ({
  id, competition, date: ago(h), home, away, home_score: hs, away_score: as, status, matchday: 7,
});
const football = {
  checked_at: now.toISOString(),
  competitions: [
    { code: 'FL1', name: 'Ligue 1', stale: false, flashscore: 'https://www.flashscore.fr/football/france/ligue-1/',
      standings: [row(1, 'Monaco', 5, 4, 1, 0, 8, 3, 13, 'WDWWW'), row(2, 'PSG', 5, 4, 0, 1, 11, 4, 12, 'WWLWW'), row(3, 'Lens', 5, 3, 2, 0, 7, 2, 11, 'DWWDW'), row(4, 'Marseille', 5, 3, 1, 1, 9, 6, 10, 'WLDWW')] },
    { code: 'PL', name: 'Premier League', stale: true, flashscore: 'https://www.flashscore.fr/football/angleterre/premier-league/',
      standings: [row(1, 'Arsenal', 6, 5, 1, 0, 14, 3, 16, 'WWDWW'), row(2, 'Liverpool', 6, 5, 0, 1, 12, 5, 15, 'WWWLW')] },
  ],
  results: [mtch(1, 'FL1', 'Marseille', 'PSG', 1, 2, 20), mtch(2, 'FL1', 'Lens', 'Lille', 0, 0, 44), mtch(3, 'PL', 'Arsenal', 'Chelsea', 2, 1, 30)],
  fixtures: [mtch(4, 'FL1', 'Nice', 'Brest', null, null, -30, 'TIMED'), mtch(5, 'FL1', 'Lyon', 'Metz', null, null, -54, 'SCHEDULED'), mtch(6, 'PL', 'Liverpool', 'Spurs', null, null, -60, 'TIMED')],
};

const home = {
  generated_at: now.toISOString(),
  sample: true,
  domains: DOMAINS.map((d) => ({
    ...d,
    levels: Object.fromEntries([1, 2, 3].map((l) => [String(l), byDomain(d.id).filter((e) => e.level === l).map((e) => e.id)])),
    upcoming: upcoming[d.id],
  })),
  retain: events.filter((e) => e.level === 1).sort((a, b) => b.importance - a.importance).slice(0, 7).map((e) => e.id),
  events: Object.fromEntries(events.map((e) => [e.id, e])),
};

// Dossier de sortie : argument optionnel, sinon site/data/ (attention : écrase les données publiées par le pipeline).
const OUT = process.argv[2] ? pathToFileURL(resolve(process.argv[2]) + '/') : new URL('../data/', import.meta.url);
mkdirSync(new URL('domains/', OUT), { recursive: true });
const write = (rel, obj) => writeFileSync(new URL(rel, OUT), JSON.stringify(obj, null, 1) + '\n');
write('home.json', home);
write('quotes.json', quotes);
write('football.json', football);
for (const d of DOMAINS) {
  write(`domains/${d.id}.json`, { generated_at: home.generated_at, domain: d, events: byDomain(d.id), upcoming: upcoming[d.id] });
}
console.log(`${events.length} événements d’exemple écrits dans ${OUT.pathname}`);
