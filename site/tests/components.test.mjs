import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, toggleFollow } from '../js/state.js';
import { entityMap, bandHtml, panelHtml, chains, constellation } from '../js/ui.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const INDEX = { types: {}, entities: [
  { id: 'country:iran', name: 'Iran', type: 'country', universes: ['geopolitique'], aliases: [], n30: 3 },
  { id: 'commodity:petrole', name: 'Pétrole', type: 'commodity', universes: ['finance'], aliases: [], n30: 8 },
  { id: 'sector:energie', name: 'Énergie', type: 'sector', universes: ['finance'], aliases: [], n30: 1 },
  ...Array.from({ length: 15 }, (_, i) => ({ id: `company:c${i}`, name: `Société ${i}`, type: 'company', universes: ['finance'], aliases: [], n30: 0 })),
] };
const ENTS = entityMap(INDEX);
const item = (o = {}) => ({ universe: 'finance', kind: 'quote', label: 'CAC 40', value: 8077.8, delta: -0.4, unit: '%', at: '2026-09-27T11:00:00Z', href: '#/u/finance', ...o });
const PAGE = {
  generated_at: 'x', entity: { id: 'country:iran', name: 'Iran', type: 'country', type_label: 'Pays', universes: ['geopolitique'] },
  description: 'pays d’Asie de l’Ouest', image: null,
  facts: [{ label: 'Capitale', value: 'Téhéran' }, { label: 'Population', value: '90 millions' }, { label: 'Monnaie', value: 'rial' },
          { label: 'Régime', value: 'république islamique' }, { label: 'PIB', value: '400 Md$ (2024)' }],
  relations: [{ id: 'commodity:petrole', name: 'Pétrole', type: 'commodity', label: 'produit', origin: 'config', weight: 1 },
              ...Array.from({ length: 15 }, (_, i) => ({ id: `company:c${i}`, name: `Société ${i}`, type: 'company', label: 'souvent cité avec', origin: 'cooccurrence', weight: 3 }))],
  events: [1, 2, 3, 4].map((i) => ({ id: `e${i}`, domain: 'geopolitique', title: `Titre ${i}`, title_fr: `Titre FR ${i}`, retenir: '', entities: [], date: '2026-09-27T10:00:00Z', level: 1, reliability: 'confirmé', source: 'S', url: 'https://ex.com' })),
};

test('le bandeau répète ses segments pour défiler, colore les variations et ignore les liens externes', () => {
  const html = bandHtml({ items: [item(), item({ kind: 'match', label: 'PSG – OM', value: null, delta: null, unit: null, href: 'https://evil.example/' })] }, NOW);
  assert.equal((html.match(/CAC 40/g) || []).length, 2);
  assert.match(html, /class="bd down"/);
  assert.ok(!html.includes('evil.example'));
  assert.equal(bandHtml({ items: [] }, NOW), '');
  assert.equal(bandHtml(null, NOW), '');
  assert.ok(!bandHtml({ items: [item({ label: '<img src=x onerror=1>' })] }, NOW).includes('<img'));
});

test('le panneau d’aperçu montre faits, 3 actualités, relations, suivi et lien vers la fiche', () => {
  const html = panelHtml(PAGE, ENTS, toggleFollow(defaultState(), 'country:iran'), NOW);
  assert.match(html, /Téhéran/);
  assert.ok(!html.includes('400 Md$'));                            // 4 faits au plus
  assert.equal((html.match(/href="#\/e\//g) || []).length, 3);
  assert.match(html, /Titre FR 1/);
  assert.match(html, /data-action="follow" data-entity="country:iran"[^>]*aria-pressed="true"/);
  assert.match(html, /href="#\/x\/country\/iran"/);
  assert.match(html, /<svg/);                                     // sans image : illustration
  assert.equal((html.match(/class="pill t-/g) || []).length, 6);
});

test('les chaînes Concernés sont lisibles et un maillon inconnu reste du texte', () => {
  const html = chains([[{ from: 'country:iran', to: 'commodity:petrole', label: 'produit' }, { from: 'commodity:petrole', to: 'sector:inconnu', label: 'influence' }]], ENTS);
  assert.match(html, /Iran[\s\S]*produit[\s\S]*Pétrole[\s\S]*influence/);
  assert.match(html, /href="#\/x\/commodity\/petrole"/);
  assert.ok(!html.includes('href="#/x/sector/inconnu"'));
  assert.equal(chains([], ENTS), '');
});

test('la constellation place au plus 12 voisins, reliés à leur fiche, relations écrites d’abord', () => {
  const svg = constellation(PAGE, ENTS);
  assert.equal((svg.match(/<a /g) || []).length, 12);
  assert.match(svg, /href="#\/x\/commodity\/petrole"/);
  assert.match(svg, /<title>produit<\/title>/);
  assert.equal(constellation({ ...PAGE, relations: [] }, ENTS), '');
});
