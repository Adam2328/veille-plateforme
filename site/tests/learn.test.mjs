import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState } from '../js/state.js';
import { domainBlock, renderDomain } from '../js/render.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const CARD = { category: 'Règle', title: 'Le shot clock', text: '24 secondes pour tirer.' };

test('la fiche « À connaître » apparaît sur l’Accueil et sur la page de la veille', () => {
  const dom = { id: 'nba', name: 'NBA', accent: '#1D428A', levels: { 1: [], 2: [], 3: [] }, upcoming: [], learn: CARD };
  const block = domainBlock(dom, {}, defaultState(), NOW);
  assert.match(block, /À connaître/);
  assert.match(block, /Le shot clock/);
  const page = renderDomain({ domain: { id: 'nba', name: 'NBA', accent: '#1D428A' }, events: [], upcoming: [], learn: CARD }, defaultState(), NOW);
  assert.match(page, /À connaître[\s\S]*Règle[\s\S]*24 secondes/);
});

test('sans fiche, rien ; le contenu est échappé', () => {
  const dom = { id: 'nba', name: 'NBA', accent: '#1D428A', levels: { 1: [], 2: [], 3: [] }, upcoming: [] };
  assert.ok(!domainBlock(dom, {}, defaultState(), NOW).includes('À connaître'));
  const hostile = domainBlock({ ...dom, learn: { ...CARD, text: '<img src=x onerror=1>' } }, {}, defaultState(), NOW);
  assert.ok(!hostile.includes('<img'));
});
