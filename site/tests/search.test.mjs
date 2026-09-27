import test from 'node:test';
import assert from 'node:assert/strict';
import { normalize, searchEvents, followedEvents, searchEntities } from '../js/search.js';
import { defaultState, toggleFollow, isFollowed } from '../js/state.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const E = (id, o = {}) => ({ id, domain: 'football', title: `Titre ${id}`, retenir: '', entities: [], date: '2026-09-27T10:00:00Z',
  level: 1, reliability: 'confirmé', source: 'L’Équipe', url: 'https://ex.com/a', ...o });
const INDEX = {
  generated_at: 'x', domains: [{ id: 'football', name: 'Football' }, { id: 'ia', name: 'IA' }],
  events: [E('a', { title: 'Mbappé blessé au genou', entities: ['Mbappé', 'Équipe de France'], entity_ids: ['player:kylian-mbappe'] }),
           E('b', { title: 'OpenAI launches a model', title_fr: 'OpenAI lance un modèle', domain: 'ia', entities: ['OpenAI'], entity_ids: ['company:openai'], date: '2026-09-26T09:00:00Z' }),
           E('c', { title: 'Le PSG s’impose', retenir: 'Victoire nette à Marseille', entities: ['PSG'], entity_ids: ['team:psg'], date: '2026-09-10T09:00:00Z' })],
};
const ENT = (id, name, aliases, n30 = 0) => ({ id, name, type: id.split(':')[0], universes: [], aliases, n30 });
const ENTITIES = {
  types: { company: 'Entreprise', country: 'Pays' },
  entities: [ENT('company:nvidia', 'Nvidia', ['nvidia', 'NVDA'], 12), ENT('company:nvidea-fake', 'Nvidea', ['nvidea'], 1),
             ENT('country:etats-unis', 'États-Unis', ['états-unis', 'washington'], 40), ENT('company:apple', 'Apple', ['Apple'], 9)],
};

test('normalize retire accents, casse et ponctuation', () => {
  assert.equal(normalize('  Mbappé, BLESSÉ ! '), 'mbappe blesse');
});

test('la recherche trouve tous les mots, sans accents, dans le titre (y compris traduit), le résumé ou les entités', () => {
  assert.deepEqual(searchEvents(INDEX, 'mbappe genou', {}, NOW).map((e) => e.id), ['a']);
  assert.deepEqual(searchEvents(INDEX, 'marseille', {}, NOW).map((e) => e.id), ['c']);
  assert.deepEqual(searchEvents(INDEX, 'lance un modele', {}, NOW).map((e) => e.id), ['b']);
  assert.deepEqual(searchEvents(INDEX, 'mbappe openai', {}, NOW), []);
});

test('sans mot-clé la recherche sert d’archives, du plus récent au plus ancien, filtrable par rubrique et période', () => {
  assert.deepEqual(searchEvents(INDEX, '', {}, NOW).map((e) => e.id), ['a', 'b', 'c']);
  assert.deepEqual(searchEvents(INDEX, '', { domain: 'ia' }, NOW).map((e) => e.id), ['b']);
  assert.deepEqual(searchEvents(INDEX, '', { days: 7 }, NOW).map((e) => e.id), ['a', 'b']);
  assert.deepEqual(searchEvents(null, 'x', {}, NOW), []);
});

test('suivre une entité est immuable et réversible', () => {
  const s0 = defaultState();
  const s1 = toggleFollow(s0, 'team:psg');
  assert.ok(isFollowed(s1, 'team:psg') && !isFollowed(s0, 'team:psg'));
  assert.ok(!isFollowed(toggleFollow(s1, 'team:psg'), 'team:psg'));
});

test('les événements suivis sont ceux qui citent une entité suivie, au plus 8, les plus récents d’abord', () => {
  const s = toggleFollow(toggleFollow(defaultState(), 'team:psg'), 'company:openai');
  assert.deepEqual(followedEvents(INDEX, s).map((e) => e.id), ['b', 'c']);
  assert.deepEqual(followedEvents(INDEX, defaultState()), []);
});

test('la recherche d’entités passe par les alias, ignore les accents et groupe par type', () => {
  assert.deepEqual(searchEntities(ENTITIES, 'nvda')[0].items.map((e) => e.id), ['company:nvidia']);
  const groups = searchEntities(ENTITIES, 'etats unis');
  assert.equal(groups[0].label, 'Pays');
  assert.deepEqual(groups[0].items.map((e) => e.id), ['country:etats-unis']);
  assert.deepEqual(searchEntities(ENTITIES, 'nvid')[0].items.map((e) => e.id), ['company:nvidia', 'company:nvidea-fake']);
  assert.deepEqual(searchEntities(ENTITIES, ''), []);
  assert.deepEqual(searchEntities(null, 'x'), []);
});
