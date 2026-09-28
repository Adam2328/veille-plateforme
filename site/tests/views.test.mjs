import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, setOrder, markSeen } from '../js/state.js';
import { entityMap } from '../js/ui.js';
import { viewToday, viewUniverse, viewEvent, viewEntity, resultsHtml, navHtml, matchSub, radarHtml } from '../js/views.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const INDEX = { types: { company: 'Entreprise', rate: 'Taux', country: 'Pays' }, entities: [
  { id: 'company:nvidia', name: 'Nvidia', type: 'company', universes: ['finance'], aliases: ['nvidia', 'NVDA'], n30: 12 },
  { id: 'rate:us-10y', name: 'Taux US 10 ans', type: 'rate', universes: ['finance'], aliases: [], n30: 4 },
  { id: 'country:iran', name: 'Iran', type: 'country', universes: ['geopolitique'], aliases: ['iran'], n30: 20 },
] };
const ev = (id, o = {}) => ({
  id, rev: 1, domain: 'finance', kind: 'earnings', title: `Title ${id}`, title_fr: `Titre ${id}`, universe: 'finance',
  first_seen: '2026-09-27T10:00:00Z', updated_at: '2026-09-27T11:00:00Z', importance: 80, level: 1, reliability: 'confirmé',
  reliability_reason: '2 origines', summary: { quoi: 'Quoi.', qui: 'Qui.', quand: 'Quand.', pourquoi: 'Pourquoi.', retenir: 'Retenir.' },
  summary_mode: 'llm', entities: [], entity_ids: ['company:nvidia'],
  sources: [{ name: 'Reuters', tier: 2, url: 'https://ex.com/a', title: 'a', published_at: '2026-09-27T09:00:00Z' }], ...o,
});
const HOME = {
  generated_at: 'x', sample: false, domains: [], retain: [],
  events: { f1: ev('f1'), f2: ev('f2'), g1: ev('g1', { universe: 'geopolitique', domain: 'geopolitique' }) },
  today: [{ id: 'finance', name: 'Finance & Marchés', short: 'Finance', color: 'finance', ids: ['f1', 'f2'] },
          { id: 'ia', name: 'Intelligence artificielle', short: 'IA', color: 'ia', ids: [] },
          { id: 'geopolitique', name: 'Géopolitique', short: 'Géo', color: 'geo', ids: ['g1'] },
          { id: 'sport', name: 'Sport', short: 'Sport', color: 'sport', ids: [] }],
};
const ctx = (o = {}) => ({ home: HOME, index: INDEX, ents: entityMap(INDEX), state: defaultState(), now: NOW, since: '2026-09-27T06:12:00Z',
  quotes: null, football: null, f1: null, search: null, domainFiles: [], ...o });

test('l’accueil suit l’ordre choisi, compte les nouveautés et signale un univers vide', () => {
  const html = viewToday(ctx({ state: markSeen(setOrder(defaultState(), ['geopolitique', 'finance']), [HOME.events.f1]) }));
  const order = [...html.matchAll(/<section class="uband u-(\w+)/g)].map((m) => m[1]);
  assert.deepEqual(order, ['geopolitique', 'finance', 'ia', 'sport']);
  assert.match(html, /2 nouveautés depuis 08 h 12/);
  assert.match(html, /Rien d’important pour l’instant/);
  assert.match(html, /Titre f2/);
});

test('les réglages proposent l’ordre des univers et le thème', () => {
  const html = viewToday(ctx());
  assert.match(html, /data-action="move" data-universe="ia" data-dir="-1"/);
  assert.match(html, /data-action="theme" data-theme="dark"/);
});

test('le radar montre les entités en hausse et les suivis', () => {
  const html = radarHtml(ctx({ state: { ...defaultState(), follows: ['country:iran'] } }));
  assert.match(html, /Entités en hausse[\s\S]*Iran[\s\S]*Nvidia/);
  assert.match(html, /Vos suivis/);
});

test('un sous-thème filtre par rubrique, type d’événement, type d’entité ou entité', () => {
  assert.ok(matchSub({ id: 'foot', domains: ['football'] }, ev('x', { domain: 'football' })));
  assert.ok(matchSub({ id: 'a', kinds: ['earnings'] }, ev('x')));
  assert.ok(matchSub({ id: 't', entity_types: ['rate'] }, ev('x', { kind: 'other', entity_ids: ['rate:us-10y'] })));
  assert.ok(matchSub({ id: 'i', entities: ['company:nvidia'] }, ev('x', { kind: 'other' })));
  assert.ok(!matchSub({ id: 'c', kinds: ['crypto'] }, ev('x')));
});

test('la page univers affiche onglets, cartes filtrées, niveau 3 compact et agenda', () => {
  const file = { universe: { id: 'finance', name: 'Finance & Marchés', short: 'Finance', color: 'finance', order: 1,
    subthemes: [{ id: 'crypto', name: 'Crypto', kinds: ['crypto'] }, { id: 'actions', name: 'Actions', kinds: ['earnings'] }] },
    domains: [{ id: 'finance', name: 'Finance' }], events: [ev('a'), ev('b', { kind: 'crypto', level: 3 })],
    upcoming: [{ date: '2026-09-29', title: 'Réunion BCE', domain: 'finance' }] };
  const all = viewUniverse(ctx(), file, null);
  assert.match(all, /href="#\/u\/finance\/crypto"/);
  assert.match(all, /Titre a/);
  assert.match(all, /À savoir[\s\S]*Titre b/);
  assert.match(all, /Réunion BCE/);
  const crypto = viewUniverse(ctx(), file, 'crypto');
  assert.ok(!crypto.includes('Titre a') && crypto.includes('Titre b'));
  assert.match(crypto, /href="#\/u\/finance\/crypto" aria-current="page"/);
});

test('la page événement : court d’abord, puis Concernés, actifs nommés, sources et fiabilité', () => {
  const html = viewEvent(ctx(), ev('e', {
    layers: { faits: ['F'], analyse: [], interpretation: [], incertitude: [], actifs: ['rate:us-10y'], favorables: [], risques: [], a_surveiller: [] },
    concerned: [[{ from: 'company:nvidia', to: 'rate:us-10y', label: 'exposé à' }]],
  }));
  assert.ok(html.indexOf('Pourquoi c’est important') < html.indexOf('Aller plus loin'));
  assert.match(html, /Concernés[\s\S]*exposé à/);
  assert.ok(!html.includes('<li>rate:us-10y</li>'));
  assert.match(html, /Confirmé[\s\S]*2 origines/);
  assert.match(html, /href="https:\/\/ex\.com\/a"[^>]*noopener/);
  assert.match(html, /Titre original : Title e/);
  assert.match(html, /href="#\/u\/finance">Finance</);
});

test('un événement sans résumé montre ses sources, et rien n’est injecté', () => {
  const html = viewEvent(ctx(), ev('e', { summary: null, summary_mode: 'aucun', title_fr: '<img src=x onerror=1>',
    sources: [{ name: '<b>x</b>', tier: 2, url: 'javascript:alert(1)', title: 't', published_at: 'x' }] }));
  assert.match(html, /pas de synthèse/);
  assert.ok(!html.includes('<img src=x') && !html.includes('javascript:') && !html.includes('<b>x'));
});

test('la fiche entité : visuel, chiffres clés, suivi, chronologie ; sans relations pas de constellation', () => {
  const page = { generated_at: 'x', entity: { id: 'company:nvidia', name: 'Nvidia', type: 'company', type_label: 'Entreprise', universes: ['finance'] },
    description: 'fabricant de puces', image: null, facts: [{ label: 'Siège', value: 'Santa Clara' }], relations: [],
    events: [{ id: 'e1', domain: 'finance', title: 'T', title_fr: 'Nvidia publie', retenir: '', entities: [], date: '2026-09-27T10:00:00Z', level: 1, reliability: 'confirmé', source: 'S', url: 'https://ex.com' }] };
  const html = viewEntity(ctx(), page);
  assert.match(html, /<h1>Nvidia<\/h1>/);
  assert.match(html, /Santa Clara/);
  assert.match(html, /data-action="follow" data-entity="company:nvidia"/);
  assert.match(html, /href="#\/e\/e1"[^>]*>Nvidia publie/);
  assert.ok(!html.includes('class="constellation"'));
  assert.match(html, /href="#\/u\/finance">Finance<\/a>/);                 // nom de l'univers, pas son identifiant
});

test('la recherche propose entités par catégorie puis actualités ; vide, une invite', () => {
  const search = { domains: [], events: [{ id: 's1', domain: 'finance', title: 'Nvidia earnings', title_fr: 'Résultats de Nvidia', retenir: '', entities: [], date: '2026-09-27T10:00:00Z', level: 1, reliability: 'confirmé', source: 'S', url: 'https://ex.com' }] };
  const html = resultsHtml(ctx({ search }), 'nvidia');
  assert.match(html, /Entreprise[\s\S]*data-entity="company:nvidia"[\s\S]*Résultats de Nvidia/);
  assert.match(resultsHtml(ctx({ search }), ''), /Tapez/);
  assert.match(resultsHtml(ctx({ search }), 'zzzz'), /Aucun résultat/);
});

test('la navigation marque la page active', () => {
  assert.match(navHtml('#/u/finance/crypto'), /href="#\/u\/finance" aria-current="page"/);
  assert.match(navHtml('#/'), /href="#\/" aria-current="page"/);
});

test('un événement archivé (ancien lien d’alerte) s’affiche en fiche courte avec un lien sûr', async () => {
  const { viewArchived } = await import('../js/views.js');
  const e = { id: 'z', domain: 'finance', title: '<img src=x>', title_fr: 'Titre archivé', retenir: 'R', entities: [], date: '2026-09-20T10:00:00Z', level: 2, reliability: 'confirmé', source: 'S', url: 'javascript:alert(1)' };
  const html = viewArchived(e);
  assert.match(html, /Titre archivé/);
  assert.ok(!html.includes('javascript:') && !html.includes('<img'));
  assert.match(viewArchived({ ...e, url: 'https://ex.com/a' }), /href="https:\/\/ex\.com\/a"[^>]*noopener/);
});

test('une dernière visite d’un autre jour est datée, pas seulement l’heure', () => {
  const html = viewToday(ctx({ since: '2026-09-24T06:12:00Z' }));
  assert.match(html, /depuis le jeu\. 24 sept\. à 08 h 12/);
});
