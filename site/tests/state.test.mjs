import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, loadState, saveState, resetState, eventStatus, markSeen, countChanges, pruneSeen } from '../js/state.js';

const memory = (initial = null) => {
  let v = initial;
  return { getItem: () => v, setItem: (_k, x) => { v = x; }, removeItem: () => { v = null; } };
};
const ev = (id, rev = 1) => ({ id, rev });

test('un événement absent de seen est nouveau', () => {
  assert.equal(eventStatus(defaultState(), ev('a')), 'new');
});

test('un événement vu à la même révision est vu', () => {
  assert.equal(eventStatus({ ...defaultState(), seen: { a: 2 } }, ev('a', 2)), 'seen');
});

test('un événement dont la révision a augmenté est mis à jour', () => {
  assert.equal(eventStatus({ ...defaultState(), seen: { a: 1 } }, ev('a', 2)), 'updated');
});

test('markSeen est immuable et garde la plus grande révision', () => {
  const s0 = { ...defaultState(), seen: { a: 5 } };
  const s1 = markSeen(s0, [ev('a', 2), ev('b', 1)]);
  assert.deepEqual(s1.seen, { a: 5, b: 1 });
  assert.deepEqual(s0.seen, { a: 5 });
});

test('countChanges distingue nouveautés et mises à jour', () => {
  const s = { ...defaultState(), seen: { a: 1, c: 1 } };
  assert.deepEqual(countChanges(s, [ev('a', 2), ev('b'), ev('c')]), { fresh: 1, updated: 1 });
});

test('loadState : stockage vide, JSON corrompu ou null donnent un état vide', () => {
  for (const raw of [null, '{corrompu', 'null', '42', '[]']) {
    assert.deepEqual(loadState(memory(raw)), defaultState());
  }
});

test('loadState : stockage qui lève une exception donne un état vide', () => {
  const throwing = { getItem() { throw new Error('SecurityError'); } };
  assert.deepEqual(loadState(throwing), defaultState());
});

test('loadState : mauvais types corrigés sans exception', () => {
  const s = loadState(memory(JSON.stringify({ seen: 5, follows: 'x', weights: [], lastVisit: 'd' })));
  assert.deepEqual(s.seen, {});
  assert.deepEqual(s.follows, []);
  assert.deepEqual(s.weights, {});
  assert.equal(s.lastVisit, 'd');
});

test('saveState renvoie false si l’écriture échoue et true sinon', () => {
  assert.equal(saveState({ setItem() { throw new Error('Quota'); } }, defaultState()), false);
  const m = memory();
  assert.equal(saveState(m, { ...defaultState(), seen: { a: 1 } }), true);
  assert.deepEqual(loadState(m).seen, { a: 1 });
});

test('resetState vide le stockage et ne lève jamais', () => {
  const m = memory('{"seen":{"a":1}}');
  resetState(m);
  assert.deepEqual(loadState(m), defaultState());
  resetState({ removeItem() { throw new Error('x'); } });
});

test('pruneSeen garde les entrées les plus récentes', () => {
  const s = { ...defaultState(), seen: { a: 1, b: 1, c: 1, d: 1, e: 1 } };
  assert.deepEqual(Object.keys(pruneSeen(s, 3).seen), ['c', 'd', 'e']);
  assert.equal(pruneSeen(s, 10), s);
});

test('préférences corrompues : thème et ordre reviennent aux valeurs par défaut ; anciens suivis par nom ignorés', async () => {
  const { loadState: load } = await import('../js/state.js');
  const bad = memory(JSON.stringify({ prefs: { theme: 'fluo', order: 'finance' }, follows: ['Nvidia', 'company:nvidia', 3] }));
  const s = load(bad);
  assert.deepEqual(s.prefs, { theme: 'auto', order: null });
  assert.deepEqual(s.follows, ['company:nvidia']);
  const ok = load(memory(JSON.stringify({ prefs: { theme: 'dark', order: ['ia', 'sport'] } })));
  assert.deepEqual(ok.prefs, { theme: 'dark', order: ['ia', 'sport'] });
});

test('setTheme, setOrder et orderedUniverses', async () => {
  const { setTheme, setOrder, orderedUniverses } = await import('../js/state.js');
  const s0 = defaultState();
  assert.equal(setTheme(s0, 'light').prefs.theme, 'light');
  assert.equal(setTheme(s0, 'fluo').prefs.theme, 'auto');
  assert.equal(s0.prefs.theme, 'auto');                                   // immuable
  const bands = [{ id: 'finance' }, { id: 'ia' }, { id: 'geopolitique' }, { id: 'sport' }];
  assert.deepEqual(orderedUniverses(s0, bands).map((b) => b.id), ['finance', 'ia', 'geopolitique', 'sport']);
  const s1 = setOrder(s0, ['sport', 'ia', 'inconnu']);
  assert.deepEqual(orderedUniverses(s1, bands).map((b) => b.id), ['sport', 'ia', 'finance', 'geopolitique']);
});
