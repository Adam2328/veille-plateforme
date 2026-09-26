import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { domainBlock, renderNav, renderDomain, matchLine, renderMatches, renderStandings, footballStrip, renderFootball } from '../js/render.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const SRC = { name: 'S', tier: 2, url: 'https://ex.com/a', title: 'x', published_at: '2026-09-26T10:30:00Z' };
const ev = (o = {}) => ({
  id: 'e1', rev: 1, domain: 'ia', kind: 'other', title: 'T', first_seen: '2026-09-26T10:00:00Z',
  updated_at: '2026-09-26T11:00:00Z', importance: 80, level: 1, reliability: 'confirmé', reliability_reason: 'r',
  summary: { quoi: 'q', qui: 'w', quand: 'n', pourquoi: 'p', retenir: 'ret' }, summary_mode: 'llm',
  entities: [], sources: [SRC], ...o,
});
const dom = (o = {}) => ({ id: 'ia', name: 'IA', accent: '#5B3FA8', levels: { 1: [], 2: [], 3: [] }, upcoming: [], ...o });

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
const fbFile = (events = []) => ({ domain: { id: 'football', name: 'Football', accent: '#0B6E4F' }, events, upcoming: [] });
const fbEv = (id, o = {}) => ev({ id, domain: 'football', kind: 'other', ...o });

test('un match joué affiche son score, un match à venir sa date', () => {
  assert.match(matchLine(M()), /1 – 2/);
  assert.match(matchLine(M({ home_score: 0, away_score: 0 })), /0 – 0/);
  const next = matchLine(M({ home_score: null, away_score: null, date: '2026-09-28T18:45:00Z' }));
  assert.ok(!next.includes('–'));
  assert.match(next, /class="match next"/);
});

test('les noms d’équipes et de compétitions sont échappés', () => {
  const html = renderMatches([M({ home: '<img src=x onerror=alert(1)>', competition: 'X"><script>' })], FB());
  assert.ok(!html.includes('<img') && !html.includes('<script>'));
  const table = renderStandings({ code: 'A', name: 'A', stale: false, standings: [ROW({ team: '<b onmouseover=x>' })] });
  assert.ok(!table.includes('<b onmouseover'));
});

test('les matchs sont groupés par compétition avec le nom lu dans les données', () => {
  const html = renderMatches(FB().results, FB());
  assert.match(html, /Ligue 1/);
  assert.equal((html.match(/<h3/g) || []).length, 1);
  assert.match(renderMatches([], FB()), /Aucun match/);
});

test('le classement affiche les colonnes et signale un classement périmé', () => {
  const html = renderStandings(FB().competitions[1]);
  for (const col of ['Équipe', 'Pts', 'Diff', 'Forme']) assert.ok(html.includes(col), col);
  assert.match(html, /Arsenal/);
  assert.match(html, /non actualisé/);
  assert.ok(!renderStandings(FB().competitions[0]).includes('non actualisé'));
});

test('chaque compétition renvoie vers sa page Flashscore, jamais vers un autre domaine', () => {
  const fb = FB({ competitions: [{ ...FB().competitions[0], flashscore: 'https://www.flashscore.fr/football/france/ligue-1/' },
                                 { ...FB().competitions[1], flashscore: 'javascript:alert(1)//' }] });
  const results = renderMatches(fb.results, fb, 'resultats/');
  assert.match(results, /href="https:\/\/www\.flashscore\.fr\/football\/france\/ligue-1\/resultats\/"/);
  assert.match(results, /rel="noopener noreferrer"/);
  assert.match(renderStandings(fb.competitions[0]), /ligue-1\/classement\//);
  assert.ok(!renderStandings(fb.competitions[1]).includes('javascript:'));
  assert.ok(!renderStandings(fb.competitions[1]).includes('Flashscore'));
  const evil = { ...fb.competitions[0], flashscore: 'https://evil.example/' };
  assert.ok(!renderStandings(evil).includes('evil.example'));
  assert.ok(!renderStandings(FB().competitions[0]).includes('Flashscore'));
});

test('la page Football propose les cinq onglets et marque l’onglet actif', () => {
  const html = renderFootball(fbFile(), FB(), 'resultats', null, defaultState(), NOW);
  for (const t of ['Actu', 'Résultats', 'Classements', 'Calendrier', 'Mercato']) assert.ok(html.includes(t), t);
  assert.match(html, /href="#\/d\/football\/resultats" aria-current="page"/);
  assert.match(html, /Marseille/);
});

test('onglets résultats, calendrier et classements sans données affichent un message', () => {
  for (const tab of ['resultats', 'calendrier', 'classements']) {
    assert.match(renderFootball(fbFile(), null, tab, null, defaultState(), NOW), /Données indisponibles/);
  }
  assert.match(renderFootball(fbFile(), FB({ competitions: [] }), 'classements', null, defaultState(), NOW), /Données indisponibles/);
});

test('l’onglet classements choisit la compétition demandée, sinon la première, sans planter sur un code inconnu', () => {
  const pl = renderFootball(fbFile(), FB(), 'classements', 'PL', defaultState(), NOW);
  assert.match(pl, /Arsenal/);
  assert.ok(!pl.includes('>Monaco<'));
  assert.match(renderFootball(fbFile(), FB(), 'classements', 'ZZZ', defaultState(), NOW), /Monaco/);
  assert.match(renderFootball(fbFile(), FB(), 'inconnu', null, defaultState(), NOW), /Rien d’important/);
});

test('le mercato masque les rumeurs par défaut avec un décompte et un lien, et les affiche à la demande', () => {
  const events = [fbEv('t1', { kind: 'transfer', title: 'Transfert acté', reliability: 'officiel' }),
                  fbEv('t2', { kind: 'transfer', title: 'Piste évoquée', reliability: 'rumeur' }),
                  fbEv('t3', { kind: 'transfer', title: 'Autre piste', reliability: 'non_confirmé' }),
                  fbEv('n1', { title: 'Résultat du week-end' })];
  const hidden = renderFootball(fbFile(events), FB(), 'mercato', null, defaultState(), NOW);
  assert.match(hidden, /Transfert acté/);
  assert.ok(!hidden.includes('Piste évoquée') && !hidden.includes('Résultat du week-end'));
  assert.match(hidden, /Afficher les rumeurs \(2 masquées\)/);
  const all = renderFootball(fbFile(events), FB(), 'mercato', 'rumeurs', defaultState(), NOW);
  assert.match(all, /Piste évoquée/);
  assert.match(all, /Masquer les rumeurs/);
  assert.match(renderFootball(fbFile([]), FB(), 'mercato', null, defaultState(), NOW), /Aucune information de mercato/);
});

test('l’onglet Actu exclut les transferts', () => {
  const events = [fbEv('t1', { kind: 'transfer', title: 'Transfert acté' }), fbEv('n1', { title: 'Résultat du week-end' })];
  const html = renderFootball(fbFile(events), FB(), 'actu', null, defaultState(), NOW);
  assert.match(html, /Résultat du week-end/);
  assert.ok(!html.includes('Transfert acté'));
});

test('renderDomain délègue à la page Football uniquement pour la veille football', () => {
  assert.match(renderDomain(fbFile(), defaultState(), NOW, null, FB(), 'calendrier'), /Nice/);
  const other = renderDomain({ domain: { id: 'ia', name: 'IA', accent: '#5B3FA8' }, events: [], upcoming: [] }, defaultState(), NOW, null, FB());
  assert.ok(!other.includes('Calendrier'));
});

test('la bande de l’Accueil n’apparaît que dans le bloc football, avec 6 lignes au plus par colonne', () => {
  const many = FB({ results: Array.from({ length: 9 }, (_, i) => M({ id: i, home: `H${i}` })) });
  const strip = footballStrip(many);
  assert.match(strip, /Derniers résultats/);
  assert.match(strip, /Prochains matchs/);
  assert.equal((strip.match(/class="match"/g) || []).length, 6);
  assert.equal(footballStrip(null), '');
  assert.equal(footballStrip(FB({ results: [], fixtures: [] })), '');
  assert.match(domainBlock(dom({ id: 'football', name: 'Football' }), {}, defaultState(), NOW, null, FB()), /fb-strip/);
  assert.ok(!domainBlock(dom(), {}, defaultState(), NOW, null, FB()).includes('fb-strip'));
});

test('la veille active reste marquée dans la navigation sur une sous-route', () => {
  const home = { domains: [dom({ id: 'football', name: 'Football' })], events: {} };
  assert.match(renderNav(home, defaultState(), '#/d/football/classements/PL'), /href="#\/d\/football" aria-current="page"/);
  assert.ok(!renderNav(home, defaultState(), '#/d/footballeur').includes('aria-current="page"><span>Football'));
});
