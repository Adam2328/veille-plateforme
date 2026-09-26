import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { esc, safeUrl, timeAgo, badges, card, domainBlock, renderHome, renderEvent, renderNav } from '../js/render.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const SRC = { name: 'S', tier: 2, url: 'https://ex.com/a', title: 'x', published_at: '2026-09-26T10:30:00Z' };
const ev = (o = {}) => ({
  id: 'e1', rev: 1, domain: 'ia', kind: 'other', title: 'T', first_seen: '2026-09-26T10:00:00Z',
  updated_at: '2026-09-26T11:00:00Z', importance: 80, level: 1, reliability: 'confirmé', reliability_reason: 'r',
  summary: { quoi: 'q', qui: 'w', quand: 'n', pourquoi: 'p', retenir: 'ret' }, summary_mode: 'llm',
  entities: [], sources: [SRC], ...o,
});
const dom = (o = {}) => ({ id: 'ia', name: 'IA', accent: '#5B3FA8', levels: { 1: [], 2: [], 3: [] }, upcoming: [], ...o });

test('esc neutralise HTML, guillemets et apostrophes', () => {
  assert.equal(esc(`<a href="x" onclick='y'>&`), '&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;');
  assert.equal(esc(null), '');
});

test('un titre malveillant est rendu inerte dans une carte', () => {
  const html = card(ev({ title: '<img src=x onerror=alert(1)>' }), 'seen', NOW);
  assert.ok(!html.includes('<img'));
  assert.match(html, /&lt;img/);
});

test('un nom de source malveillant est rendu inerte dans la fiche', () => {
  const html = renderEvent(ev({ sources: [{ ...SRC, name: '"><script>x</script>' }] }), defaultState(), NOW);
  assert.ok(!html.includes('<script>'));
});

test('safeUrl refuse javascript:, data: et les URL invalides', () => {
  assert.equal(safeUrl('javascript:alert(1)'), null);
  assert.equal(safeUrl('data:text/html,x'), null);
  assert.equal(safeUrl('pas une url'), null);
  assert.equal(safeUrl('https://ex.com/a'), 'https://ex.com/a');
});

test('la fiche ne crée aucun lien pour une source en javascript:', () => {
  const html = renderEvent(ev({ sources: [{ ...SRC, url: 'javascript:alert(1)' }] }), defaultState(), NOW);
  assert.ok(!html.includes('javascript:'));
  assert.ok(html.includes('S'));
});

test('la fiche affiche les 5 champs de la synthèse et sépare les sources sociales', () => {
  const html = renderEvent(ev({ sources: [SRC, { ...SRC, name: 'Forum', tier: 5 }] }), defaultState(), NOW);
  for (const label of ['Quoi', 'Qui', 'Quand', 'Pourquoi', 'À retenir']) assert.ok(html.includes(label));
  assert.match(html, /<details[^>]*>[\s\S]*Forum/);
});

test('un résumé extractif est signalé', () => {
  assert.match(renderEvent(ev({ summary_mode: 'extractif' }), defaultState(), NOW), /Résumé automatique simple/);
});

test('badge Nouveau présent pour un événement nouveau, absent pour un événement vu', () => {
  assert.match(badges(ev(), 'new'), /Nouveau/);
  assert.match(badges(ev(), 'updated'), /Mis à jour/);
  assert.ok(!/Nouveau|Mis à jour/.test(badges(ev(), 'seen')));
});

test('une fiabilité inconnue retombe sur « Non confirmé » sans injecter de classe', () => {
  const html = badges(ev({ reliability: 'x" onmouseover="y' }), 'seen');
  assert.match(html, /Non confirmé/);
  assert.ok(!html.includes('onmouseover'));
});

test('timeAgo tolère une date invalide', () => {
  assert.equal(timeAgo('nope', NOW), '');
  assert.equal(timeAgo('2026-09-26T11:30:00Z', NOW), 'il y a 30 min');
  assert.equal(timeAgo('2026-09-26T08:00:00Z', NOW), 'il y a 4 h');
});

test('une veille sans événement affiche un message explicite', () => {
  assert.match(domainBlock(dom(), {}, defaultState(), NOW), /Rien d’important/);
});

test('un accent invalide ne peut pas injecter de CSS', () => {
  const html = domainBlock(dom({ accent: 'red;}body{display:none' }), {}, defaultState(), NOW);
  assert.ok(!html.includes('display:none'));
});

test('renderHome compte les nouveautés et propose « Tout marquer comme vu »', () => {
  const e = ev();
  const home = { generated_at: '2026-09-26T11:00:00Z', sample: true, domains: [dom({ levels: { 1: ['e1'], 2: [], 3: [] } })], retain: ['e1'], events: { e1: e } };
  const html = renderHome(home, defaultState(), NOW);
  assert.match(html, /<b>1<\/b> nouveauté/);
  assert.match(html, /data-action="mark-all"/);
  assert.match(html, /Données d’exemple/);
  assert.match(html, /À retenir aujourd’hui/);
  const seen = renderHome(home, { ...defaultState(), seen: { e1: 1 } }, NOW);
  assert.ok(!seen.includes('mark-all'));
});

test('renderNav affiche un compteur par veille et marque la page active', () => {
  const home = { domains: [dom({ levels: { 1: ['e1'], 2: [], 3: [] } })], events: { e1: ev() } };
  const html = renderNav(home, defaultState(), '#/d/ia');
  assert.match(html, /class="count">1</);
  assert.match(html, /href="#\/d\/ia" aria-current="page"/);
});

test('la carte n’affiche pas deux fois le titre quand « à retenir » le répète', () => {
  const e = ev({ title: 'Même texte', summary: { quoi: 'Première phrase utile.', qui: 'w', quand: 'n', pourquoi: 'p', retenir: 'Même texte' } });
  const html = card(e, 'seen', NOW);
  assert.equal(html.split('Même texte').length - 1, 1);
  assert.match(html, /Première phrase utile\./);
});
