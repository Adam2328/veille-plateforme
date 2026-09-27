import test from 'node:test';
import assert from 'node:assert/strict';
import { artFor } from '../js/art.js';
import { entityMap, relBadge, pill, pills, card } from '../js/ui.js';

const INDEX = {
  types: { company: 'Entreprise', country: 'Pays', player: 'Joueur' },
  entities: [
    { id: 'company:nvidia', name: 'Nvidia', type: 'company', universes: ['finance'], aliases: ['nvidia'], n30: 5, image: 'https://commons.wikimedia.org/x.png' },
    { id: 'country:france', name: 'France', type: 'country', universes: ['geopolitique'], aliases: ['france'], n30: 9 },
    { id: 'player:kylian-mbappe', name: 'Kylian <b>Mbappé</b>', type: 'player', universes: ['sport'], aliases: ['mbappe'], n30: 3 },
    { id: 'company:a', name: 'A', type: 'company', universes: [], aliases: [], n30: 0 },
    { id: 'company:b', name: 'B', type: 'company', universes: [], aliases: [], n30: 0 },
  ],
};
const ENTS = entityMap(INDEX);
const ev = (o = {}) => ({
  id: 'e1', rev: 1, domain: 'finance', kind: 'earnings', title: 'Nvidia beats', title_fr: 'Nvidia dépasse les attentes', universe: 'finance',
  first_seen: '2026-09-26T10:00:00Z', updated_at: '2026-09-26T11:00:00Z', importance: 80, level: 1, reliability: 'confirmé',
  reliability_reason: 'r', summary: { quoi: 'q', qui: 'w', quand: 'n', pourquoi: 'Pourquoi ça compte', retenir: 'ret' },
  summary_mode: 'llm', entities: [], entity_ids: ['company:nvidia'], sources: [], ...o,
});

test('une illustration est déterministe et dépend de sa graine', () => {
  assert.equal(artFor('ev_1', 'finance', 'Nvidia', 'earnings'), artFor('ev_1', 'finance', 'Nvidia', 'earnings'));
  assert.notEqual(artFor('ev_1', 'finance', 'Nvidia', 'earnings'), artFor('ev_2', 'finance', 'Nvidia', 'earnings'));
  assert.match(artFor('ev_1', 'finance', 'Nvidia', 'earnings'), /^<svg/);
});

test('une illustration échappe son étiquette et n’injecte pas de classe arbitraire', () => {
  const svg = artFor('x', 'fin"ance><script>', '<img src=x onerror=1>', 'kind"><b>');
  assert.ok(!svg.includes('<img') && !svg.includes('<script>') && !svg.includes('<b>'));
});

test('le badge de fiabilité n’apparaît que pour rumeur, non confirmé et en développement', () => {
  for (const r of ['officiel', 'confirmé', 'rapporté']) assert.equal(relBadge(ev({ reliability: r })), '');
  assert.match(relBadge(ev({ reliability: 'rumeur' })), /Rumeur/);
  assert.match(relBadge(ev({ reliability: 'non_confirmé' })), /Non confirmé/);
  assert.match(relBadge(ev({ reliability: 'en_développement' })), /En développement/);
});

test('une pastille ouvre l’aperçu de l’entité, échappe son nom et ignore une entité inconnue', () => {
  assert.match(pill('company:nvidia', ENTS), /<button type="button" class="pill t-company" data-entity="company:nvidia"/);
  assert.ok(!pill('player:kylian-mbappe', ENTS).includes('<b>'));
  assert.equal(pill('company:inconnue', ENTS), '');
});

test('les pastilles sont limitées et peuvent exclure des types', () => {
  const ids = ['country:france', 'company:nvidia', 'company:a', 'company:b'];
  assert.equal((pills(ids, ENTS).match(/class="pill/g) || []).length, 3);
  assert.ok(!pills(ids, ENTS, 3, ['country']).includes('France'));
});

test('la carte montre titre français, ligne « pourquoi », pastilles et lien vers l’événement', () => {
  const html = card(ev(), 'seen', ENTS);
  assert.match(html, /href="#\/e\/e1"/);
  assert.match(html, /Nvidia dépasse les attentes/);
  assert.ok(!html.includes('Nvidia beats'));
  assert.match(html, /Pourquoi ça compte/);
  assert.match(html, /data-entity="company:nvidia"/);
  assert.ok(!html.includes('is-new'));
  assert.match(card(ev(), 'new', ENTS), /is-new/);
});

test('sans photo https la carte affiche l’illustration ; avec photo, image sans référent et repli prévu', () => {
  assert.ok(!card(ev(), 'seen', ENTS).includes('<img'));
  assert.ok(!card(ev({ image: 'http://ex.com/a.jpg' }), 'seen', ENTS).includes('<img'));
  const html = card(ev({ image: 'https://ex.com/a.jpg' }), 'seen', ENTS);
  assert.match(html, /<img[^>]*src="https:\/\/ex\.com\/a\.jpg"[^>]*referrerpolicy="no-referrer"/);
  assert.match(html, /<svg/);                                      // l'illustration reste dessous, visible si l'image échoue
});

test('un titre malveillant est inerte et les pays sont masqués sur une carte Sport', () => {
  const html = card(ev({ title_fr: '<img src=x onerror=alert(1)>' }), 'seen', ENTS);
  assert.ok(!html.includes('<img src=x'));
  const sport = card(ev({ universe: 'sport', entity_ids: ['country:france', 'player:kylian-mbappe'] }), 'seen', ENTS);
  assert.ok(!sport.includes('data-entity="country:france"') && sport.includes('data-entity="player:kylian-mbappe"'));
});

test('sans résumé la carte n’affiche pas de ligne vide et la rumeur porte son badge', () => {
  const html = card(ev({ summary: null, reliability: 'rumeur' }), 'seen', ENTS);
  assert.ok(!html.includes('class="why"'));
  assert.match(html, /Rumeur/);
});
