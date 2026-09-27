import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { domainBlock, renderDomain, f1Weekend, f1Strip } from '../js/render.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const R = (position, driver, team, result, points = 0) => ({ position, driver, team, result, points });
const F1 = (o = {}) => ({
  checked_at: 'x', season: '2026', stale: false,
  last: { round: 15, name: 'Azerbaijan Grand Prix', country: 'Azerbaijan', date: '2026-09-26',
          race: [R(1, 'George Russell', 'Mercedes', '1:38:02.143', 25), R(2, 'Max Verstappen', 'Red Bull', '+0.196', 18), R(3, 'Isack Hadjar', 'Red Bull', '+10.704', 15), R(4, 'Lando Norris', 'McLaren', '+12.000', 12)],
          qualifying: [R(1, 'George Russell', 'Mercedes', '1:42.526')], sprint: [] },
  next: { round: 16, name: 'Bahrain Grand Prix in Malaysia', country: 'Malaysia', sessions: [
    { name: 'Essais libres 1', start: '2026-10-02T03:30:00+00:00' }, { name: 'Essais libres 2', start: '2026-10-02T07:00:00+00:00' },
    { name: 'Essais libres 3', start: '2026-10-03T03:30:00+00:00' }, { name: 'Qualifications', start: '2026-10-03T07:00:00+00:00' },
    { name: 'Course', start: '2026-10-04T07:00:00+00:00' }] },
  drivers: [{ position: 1, driver: 'Andrea Kimi Antonelli', team: 'Mercedes', points: 302, wins: 8 }],
  constructors: [{ position: 1, team: 'Mercedes', points: 538, wins: 11 }],
  ...o,
});
const file = (events = []) => ({ domain: { id: 'f1', name: 'F1', accent: '#C1121F' }, events, upcoming: [] });
const ev = (id, importance, level) => ({ id, rev: 1, domain: 'f1', kind: 'other', title: `Titre ${id}`, first_seen: 'x', updated_at: '2026-09-27T10:00:00Z',
  importance, level, reliability: 'confirmé', reliability_reason: 'r', summary: null, summary_mode: 'aucun', entities: [],
  sources: [{ name: 'S', tier: 2, url: 'https://ex.com', title: 't', published_at: '2026-09-27T09:00:00Z' }] });

test('le week-end de Grand Prix est groupé par jour en heure de Paris', () => {
  const html = f1Weekend(F1().next);
  const days = [...html.matchAll(/<h3[^>]*>([^<]+)<\/h3>/g)].map((m) => m[1].toLowerCase());
  assert.deepEqual(days.map((d) => d.split(' ')[0]), ['vendredi', 'samedi', 'dimanche']);
  assert.match(html, /Essais libres 1[\s\S]*05:30/);          // 03:30 UTC = 05:30 à Paris (heure d'été)
  assert.match(html, /Course[\s\S]*09:00/);
  assert.equal(f1Weekend(null), '');
});

test('la page F1 montre à retenir, prochain et dernier Grand Prix, classements et podium', () => {
  const events = [1, 2, 3, 4, 5, 6, 7].map((i) => ev(`e${i}`, 90 - i, i <= 2 ? 1 : 2));
  const html = renderDomain(file(events), defaultState(), NOW, null, null, 'actu', null, F1());
  for (const t of ['À retenir', 'Prochain Grand Prix', 'Dernier Grand Prix', 'Championnat pilotes', 'Championnat constructeurs']) assert.ok(html.includes(t), t);
  assert.equal((html.match(/retain-f1"[\s\S]*?<\/ol>/)[0].match(/<li/g) || []).length, 5);
  assert.match(html, /George Russell[\s\S]*1:38:02\.143/);
  assert.match(html, /Pole[\s\S]*George Russell/);
  assert.ok(!html.includes('Sprint'));                         // pas de sprint ce week-end
});

test('sans données F1 la page affiche l’actualité et un message, les noms sont échappés', () => {
  assert.match(renderDomain(file([]), defaultState(), NOW, null, null, 'actu', null, null), /Données indisponibles/);
  const hostile = F1({ last: { ...F1().last, race: [R(1, '<img src=x onerror=1>', 'X', 'y')] } });
  assert.ok(!renderDomain(file([]), defaultState(), NOW, null, null, 'actu', null, hostile).includes('<img'));
  assert.match(renderDomain(file([]), defaultState(), NOW, null, null, 'actu', null, F1({ stale: true })), /non actualisées/);
});

test('la bande de l’Accueil résume prochain Grand Prix et dernier vainqueur, dans le bloc F1 seulement', () => {
  const strip = f1Strip(F1());
  assert.match(strip, /Bahrain Grand Prix in Malaysia/);
  assert.match(strip, /George Russell/);
  assert.equal(f1Strip(null), '');
  const dom = { id: 'f1', name: 'F1', accent: '#C1121F', levels: { 1: [], 2: [], 3: [] }, upcoming: [] };
  assert.match(domainBlock(dom, {}, defaultState(), NOW, null, null, F1()), /f1-strip/);
  assert.ok(!domainBlock({ ...dom, id: 'ia' }, {}, defaultState(), NOW, null, null, F1()).includes('f1-strip'));
});
