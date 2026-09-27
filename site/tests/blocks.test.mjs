import test from 'node:test';
import assert from 'node:assert/strict';
import { esc, safeUrl, timeAgo, renderQuotes, matchLine, renderMatches, renderStandings, f1Weekend, f1Strip, f1Tables, layersBlock, linksBlock } from '../js/blocks.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const Q = (o = {}) => ({ symbol: '^FCHI', name: 'CAC 40', group: 'Indices', price: 8077.8, change: -3.6, change_pct: -0.04, currency: 'EUR', as_of: '2026-09-26T11:00:00Z', stale: false, ...o });
const M = (o = {}) => ({ id: 1, competition: 'FL1', date: '2026-09-20T18:45:00Z', home: 'Marseille', away: 'PSG', home_score: 1, away_score: 2, status: 'FINISHED', matchday: 5, ...o });
const ROW = (o = {}) => ({ position: 1, team: 'Monaco', played: 5, won: 4, draw: 1, lost: 0, gf: 8, ga: 3, gd: 5, points: 13, form: 'WDWWW', ...o });
const FB = (o = {}) => ({
  checked_at: 'x',
  competitions: [{ code: 'FL1', name: 'Ligue 1', stale: false, standings: [ROW(), ROW({ position: 2, team: 'PSG', points: 12 })] },
                 { code: 'PL', name: 'Premier League', stale: true, standings: [ROW({ team: 'Arsenal' })] }],
  results: [M(), M({ id: 2, home: 'Lens', away: 'Lille', home_score: 0, away_score: 0 })],
  fixtures: [M({ id: 3, home: 'Nice', away: 'Brest', home_score: null, away_score: null, status: 'TIMED', date: '2026-09-28T18:45:00Z' })],
  ...o,
});
const R = (position, driver, team, result, points = 0) => ({ position, driver, team, result, points });
const F1 = {
  last: { round: 15, name: 'Azerbaijan Grand Prix', country: 'Azerbaijan', date: '2026-09-26', race: [R(1, 'George Russell', 'Mercedes', '1:38:02.143', 25)], qualifying: [], sprint: [] },
  next: { round: 16, name: 'GP Malaisie', country: 'Malaysia', sessions: [
    { name: 'Essais libres 1', start: '2026-10-02T03:30:00+00:00' }, { name: 'Qualifications', start: '2026-10-03T07:00:00+00:00' },
    { name: 'Course', start: '2026-10-04T07:00:00+00:00' }] },
  drivers: [{ position: 1, driver: '<b>Antonelli</b>', team: 'Mercedes', points: 302, wins: 8 }],
  constructors: [{ position: 1, team: 'Mercedes', points: 538, wins: 11 }],
};
const LAYERS = { faits: ['Un fait.'], analyse: ['Selon X.'], interpretation: [], incertitude: [], actifs: ['rate:us-10y', 'Pays A', '<img src=x onerror=1>'], favorables: [], risques: [], a_surveiller: ['Un vote.'] };

test('esc neutralise HTML, guillemets et apostrophes', () => {
  assert.equal(esc(`<a href="x" onclick='y'>&`), '&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;');
  assert.equal(esc(null), '');
});

test('safeUrl refuse javascript:, data: et les URL invalides', () => {
  assert.equal(safeUrl('javascript:alert(1)'), null);
  assert.equal(safeUrl('data:text/html,x'), null);
  assert.equal(safeUrl('pas une url'), null);
  assert.equal(safeUrl('https://ex.com/a'), 'https://ex.com/a');
});

test('timeAgo tolère une date invalide', () => {
  assert.equal(timeAgo('n’importe quoi', NOW), '');
  assert.equal(timeAgo('2026-09-26T11:30:00Z', NOW), 'il y a 30 min');
});

test('les cours affichent nom, prix et variation, le groupe Taux en points, une valeur périmée signalée', () => {
  const html = renderQuotes({ quotes: [Q(), Q({ symbol: '^TNX', name: 'Taux US 10 ans', group: 'Taux', change: 0.22 }), Q({ symbol: 'GC=F', name: 'Or', stale: true, change_pct: 1.2 })] }, NOW);
  assert.match(html, /CAC 40/);
  assert.match(html, /class="q down"/);
  assert.match(html, /\+0,22 pt/);
  assert.match(html, /≈/);
  assert.equal(renderQuotes(null), '');
  assert.ok(!renderQuotes({ quotes: [Q({ name: '<img src=x>' })] }).includes('<img'));
});

test('un match joué affiche son score, un match à venir sa date ; noms échappés', () => {
  assert.match(matchLine(M()), /1 – 2/);
  assert.match(matchLine(M({ home_score: null, away_score: null })), /class="match next"/);
  const html = renderMatches([M({ home: '<img src=x onerror=alert(1)>' })], FB());
  assert.ok(!html.includes('<img'));
  assert.match(renderMatches([], FB()), /Aucun match/);
});

test('le classement signale un classement périmé et ne renvoie qu’à Flashscore', () => {
  assert.match(renderStandings(FB().competitions[1]), /non actualisé/);
  const ok = { ...FB().competitions[0], flashscore: 'https://www.flashscore.fr/football/france/ligue-1/' };
  assert.match(renderStandings(ok), /ligue-1\/classement\//);
  assert.ok(!renderStandings({ ...ok, flashscore: 'https://evil.example/' }).includes('evil.example'));
  assert.ok(!renderStandings({ ...ok, flashscore: 'javascript:alert(1)//' }).includes('javascript:'));
});

test('le week-end de Grand Prix est groupé par jour en heure de Paris', () => {
  const html = f1Weekend(F1.next);
  assert.match(html, /Essais libres 1[\s\S]*05:30/);
  assert.match(html, /Course[\s\S]*09:00/);
  assert.equal(f1Weekend(null), '');
  assert.match(f1Strip(F1), /GP Malaisie/);
  assert.match(f1Strip(F1), /George Russell/);
});

test('les championnats F1 sont affichés et échappés', () => {
  const html = f1Tables(F1);
  assert.match(html, /Championnat pilotes/);
  assert.match(html, /Championnat constructeurs/);
  assert.ok(!html.includes('<b>'));
  assert.equal(f1Tables(null), '');
});

test('les couches remplacent un identifiant d’entité connu par son nom et échappent le reste', () => {
  const html = layersBlock(LAYERS, 'finance', { 'rate:us-10y': 'Taux US 10 ans' });
  assert.match(html, /Taux US 10 ans/);
  assert.ok(!html.includes('rate:us-10y'));
  assert.match(html, /Pays A/);
  assert.ok(!html.includes('<img'));
  assert.match(html, /ne constitue pas un conseil en investissement/);
  assert.match(layersBlock(LAYERS, 'geopolitique'), /Pays et acteurs concernés/);
  assert.equal(layersBlock(null, 'finance'), '');
});

test('les liens « Approfondir » s’ouvrent en nouvel onglet et un lien dangereux est neutralisé', () => {
  const html = linksBlock([{ title: 'Classement ATP', url: 'https://www.flashscore.fr/tennis/' }, { title: '<img src=x>', url: 'javascript:alert(1)' }]);
  assert.match(html, /target="_blank" rel="noopener noreferrer">Classement ATP/);
  assert.ok(!html.includes('javascript:') && !html.includes('<img'));
  assert.equal(linksBlock(undefined), '');
});
