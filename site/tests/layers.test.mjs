import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { renderEvent } from '../js/render.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const SRC = { name: 'S', tier: 2, url: 'https://ex.com/a', title: 'x', published_at: '2026-09-26T10:30:00Z' };
const LAYERS = { faits: ['Un fait.'], analyse: ['Selon X, une déclaration.'], interpretation: ['Une conséquence possible.'],
  incertitude: [], actifs: ['Pays A'], favorables: [], risques: [], a_surveiller: ['Un vote.'] };
const ev = (domain) => ({
  id: 'e1', rev: 1, domain, kind: 'other', title: 'T', first_seen: '2026-09-26T10:00:00Z', updated_at: '2026-09-26T11:00:00Z',
  importance: 80, level: 1, reliability: 'confirmé', reliability_reason: 'r',
  summary: { quoi: 'q', qui: 'w', quand: 'n', pourquoi: 'p', retenir: 'ret' }, summary_mode: 'llm', entities: [], sources: [SRC], layers: LAYERS,
});

test('la Géopolitique a ses propres intitulés et pas de mention d’investissement', () => {
  const html = renderEvent(ev('geopolitique'), defaultState(), NOW);
  for (const t of ['Faits', 'Déclarations des acteurs', 'Conséquences possibles', 'Pays et acteurs concernés', 'À surveiller']) assert.ok(html.includes(t), t);
  assert.ok(!html.includes('Actifs concernés') && !html.includes('conseil en investissement'));
  assert.match(html, /attribuées à leurs auteurs/);
});

test('la Finance garde ses intitulés et sa mention', () => {
  const html = renderEvent(ev('finance'), defaultState(), NOW);
  assert.ok(html.includes('Actifs concernés') && html.includes('Analyse'));
  assert.match(html, /ne constitue pas un conseil en investissement/);
});
