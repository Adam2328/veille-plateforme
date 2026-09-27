import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { renderDomain } from '../js/render.js';

const NOW = Date.parse('2026-09-26T12:00:00Z');
const file = (links) => ({ domain: { id: 'tennis', name: 'Tennis', accent: '#B5651D' }, events: [], upcoming: [], links });

test('la page d’une veille affiche ses liens « Approfondir » en nouvel onglet', () => {
  const html = renderDomain(file([{ title: 'Classement ATP', url: 'https://www.flashscore.fr/tennis/classements/atp/' }]), defaultState(), NOW);
  assert.match(html, /Approfondir/);
  assert.match(html, /href="https:\/\/www\.flashscore\.fr\/tennis\/classements\/atp\/" target="_blank" rel="noopener noreferrer">Classement ATP/);
});

test('sans liens, pas de bloc ; un lien dangereux ou un titre hostile sont neutralisés', () => {
  assert.ok(!renderDomain(file(undefined), defaultState(), NOW).includes('Approfondir'));
  const html = renderDomain(file([{ title: '<img src=x onerror=1>', url: 'javascript:alert(1)' }, { title: 'Ok', url: 'https://www.flashscore.fr/' }]), defaultState(), NOW);
  assert.ok(!html.includes('javascript:') && !html.includes('<img'));
  assert.match(html, />Ok</);
});
