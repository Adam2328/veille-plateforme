const KEY = 'veille.state.v1';

export const defaultState = () => ({ lastVisit: null, seen: {}, follows: [], favorites: [], weights: {} });

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function sanitize(raw) {
  const s = { ...defaultState(), ...(isPlainObject(raw) ? raw : {}) };
  if (!isPlainObject(s.seen)) s.seen = {};
  if (!isPlainObject(s.weights)) s.weights = {};
  for (const k of ['follows', 'favorites']) if (!Array.isArray(s[k])) s[k] = [];
  return s;
}

export function loadState(storage) {
  try { return sanitize(JSON.parse(storage.getItem(KEY))); } catch { return defaultState(); }
}

export function saveState(storage, state) {
  try { storage.setItem(KEY, JSON.stringify(state)); return true; } catch { return false; }
}

export function resetState(storage) {
  try { storage.removeItem(KEY); } catch { /* stockage indisponible : rien à effacer */ }
}

export function eventStatus(state, ev) {
  const seenRev = state.seen[ev.id];
  if (seenRev === undefined) return 'new';
  return ev.rev > seenRev ? 'updated' : 'seen';
}

export function markSeen(state, events) {
  const seen = { ...state.seen };
  for (const ev of events) seen[ev.id] = Math.max(seen[ev.id] ?? 0, ev.rev);
  return { ...state, seen };
}

export function countChanges(state, events) {
  let fresh = 0;
  let updated = 0;
  for (const ev of events) {
    const status = eventStatus(state, ev);
    if (status === 'new') fresh++;
    else if (status === 'updated') updated++;
  }
  return { fresh, updated };
}

export function pruneSeen(state, max = 3000) {
  const keys = Object.keys(state.seen);
  if (keys.length <= max) return state;
  return { ...state, seen: Object.fromEntries(keys.slice(keys.length - max).map((k) => [k, state.seen[k]])) };
}
