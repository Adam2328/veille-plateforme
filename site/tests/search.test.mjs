import test from 'node:test';
import assert from 'node:assert/strict';
import { normalize, searchEvents, followedEvents } from '../js/search.js';
import { defaultState, toggleFollow, isFollowed } from '../js/state.js';
import { renderSearch, renderResults, renderArchived, renderEvent, renderHome, renderNav } from '../js/render.js';

const NOW = Date.parse('2026-09-27T12:00:00Z');
const E = (id, o = {}) => ({ id, domain: 'football', title: `Titre ${id}`, retenir: '', entities: [], date: '2026-09-27T10:00:00Z',
  level: 1, reliability: 'confirmé', source: 'L’Équipe', url: 'https://ex.com/a', ...o });
const INDEX = {
  generated_at: 'x', domains: [{ id: 'football', name: 'Football' }, { id: 'ia', name: 'IA' }],
  events: [E('a', { title: 'Mbappé blessé au genou', entities: ['Mbappé', 'Équipe de France'] }),
           E('b', { title: 'OpenAI lance un modèle', domain: 'ia', entities: ['OpenAI'], date: '2026-09-26T09:00:00Z' }),
           E('c', { title: 'Le PSG s’impose', retenir: 'Victoire nette à Marseille', entities: ['PSG'], date: '2026-09-10T09:00:00Z' })],
};

test('normalize retire accents, casse et ponctuation', () => {
  assert.equal(normalize('  Mbappé, BLESSÉ ! '), 'mbappe blesse');
});

test('la recherche trouve tous les mots, sans accents, dans le titre, le résumé ou les entités', () => {
  assert.deepEqual(searchEvents(INDEX, 'mbappe genou', {}, NOW).map((e) => e.id), ['a']);
  assert.deepEqual(searchEvents(INDEX, 'marseille', {}, NOW).map((e) => e.id), ['c']);
  assert.deepEqual(searchEvents(INDEX, 'equipe de france', {}, NOW).map((e) => e.id), ['a']);
  assert.deepEqual(searchEvents(INDEX, 'mbappe openai', {}, NOW), []);
});

test('sans mot-clé la recherche sert d’archives, du plus récent au plus ancien, filtrable par veille et période', () => {
  assert.deepEqual(searchEvents(INDEX, '', {}, NOW).map((e) => e.id), ['a', 'b', 'c']);
  assert.deepEqual(searchEvents(INDEX, '', { domain: 'ia' }, NOW).map((e) => e.id), ['b']);
  assert.deepEqual(searchEvents(INDEX, '', { days: 7 }, NOW).map((e) => e.id), ['a', 'b']);
  assert.deepEqual(searchEvents(null, 'x', {}, NOW), []);
});

test('suivre une entité est immuable et réversible', () => {
  const s0 = defaultState();
  const s1 = toggleFollow(s0, 'PSG');
  assert.ok(isFollowed(s1, 'PSG') && !isFollowed(s0, 'PSG'));
  assert.ok(!isFollowed(toggleFollow(s1, 'PSG'), 'PSG'));
});

test('les événements suivis sont ceux qui citent une entité suivie, au plus 8, les plus récents d’abord', () => {
  const s = toggleFollow(toggleFollow(defaultState(), 'PSG'), 'OpenAI');
  assert.deepEqual(followedEvents(INDEX, s).map((e) => e.id), ['b', 'c']);
  assert.deepEqual(followedEvents(INDEX, defaultState()), []);
});

test('la page de recherche échappe la requête et groupe les résultats par jour', () => {
  const html = renderSearch(INDEX, '"><script>x</script>', {}, NOW);
  assert.ok(!html.includes('<script>x'));
  assert.match(html, /id="q"/);
  const res = renderResults(searchEvents(INDEX, '', {}, NOW), INDEX, NOW);
  assert.equal((res.match(/<h3 class="cmp">/g) || []).length, 3);
  assert.match(res, /href="#\/e\/a"/);
  assert.match(renderResults([], INDEX, NOW), /Aucun résultat/);
});

test('un événement archivé s’affiche en fiche courte avec un lien sûr vers la source', () => {
  const html = renderArchived(E('z', { url: 'javascript:alert(1)', title: '<img src=x>' }), INDEX);
  assert.ok(!html.includes('javascript:') && !html.includes('<img'));
  assert.match(renderArchived(E('z'), INDEX), /href="https:\/\/ex\.com\/a"[^>]*noopener/);
});

test('la fiche propose de suivre chaque entité, avec l’état courant', () => {
  const ev = { id: 'e', rev: 1, domain: 'football', kind: 'other', title: 'T', first_seen: 'x', updated_at: '2026-09-27T10:00:00Z',
    importance: 70, level: 1, reliability: 'confirmé', reliability_reason: 'r', summary: null, summary_mode: 'aucun',
    entities: ['PSG', 'O"M'], sources: [{ name: 'S', tier: 2, url: 'https://ex.com', title: 't', published_at: '2026-09-27T09:00:00Z' }] };
  const html = renderEvent(ev, toggleFollow(defaultState(), 'PSG'), NOW);
  assert.match(html, /data-action="follow" data-entity="PSG"[^>]*aria-pressed="true"/);
  assert.match(html, /data-entity="O&quot;M"[^>]*aria-pressed="false"/);
});

test('l’Accueil affiche « Vos suivis » seulement si des entités sont suivies ; la navigation propose la recherche', () => {
  const home = { generated_at: 'x', sample: false, domains: [], retain: [], events: {} };
  assert.ok(!renderHome(home, defaultState(), NOW, null, null, null, null, INDEX).includes('Vos suivis'));
  const html = renderHome(home, toggleFollow(defaultState(), 'PSG'), NOW, null, null, null, null, INDEX);
  assert.match(html, /Vos suivis[\s\S]*Le PSG s’impose/);
  assert.match(renderNav({ domains: [], events: {} }, defaultState(), '#/s/'), /href="#\/s\/" aria-current="page"/);
});
