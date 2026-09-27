const KEY = 'veille.state.v1';
const THEMES = ['auto', 'dark', 'light'];
const ENTITY_ID = /^[a-z_]+:[a-z0-9-]+$/;

export const defaultState = () => ({ lastVisit: null, seen: {}, follows: [], favorites: [], weights: {}, prefs: { theme: 'auto', order: null } });

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function sanitize(raw) {
  const s = { ...defaultState(), ...(isPlainObject(raw) ? raw : {}) };
  if (!isPlainObject(s.seen)) s.seen = {};
  if (!isPlainObject(s.weights)) s.weights = {};
  for (const k of ['follows', 'favorites']) if (!Array.isArray(s[k])) s[k] = [];
  // Vigie 2 : on suit des entités du catalogue (« company:nvidia ») ; les anciens suivis par nom sont ignorés.
  s.follows = s.follows.filter((x) => typeof x === 'string' && ENTITY_ID.test(x));
  const p = isPlainObject(s.prefs) ? s.prefs : {};
  s.prefs = {
    theme: THEMES.includes(p.theme) ? p.theme : 'auto',
    order: Array.isArray(p.order) && p.order.every((x) => typeof x === 'string') ? p.order : null,
  };
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

export const isFollowed = (state, entity) => state.follows.includes(entity);

export function toggleFollow(state, entity) {
  const follows = isFollowed(state, entity) ? state.follows.filter((x) => x !== entity) : [...state.follows, entity];
  return { ...state, follows };
}

export const setTheme = (state, theme) => ({ ...state, prefs: { ...state.prefs, theme: THEMES.includes(theme) ? theme : 'auto' } });

export const setOrder = (state, ids) => ({ ...state, prefs: { ...state.prefs, order: [...ids] } });

// Ordre des bandes de l'accueil : celui choisi par l'utilisateur, les univers non listés gardent leur ordre par défaut.
export function orderedUniverses(state, bands) {
  const order = state.prefs?.order ?? [];
  const rank = (b) => (order.includes(b.id) ? order.indexOf(b.id) : order.length + bands.indexOf(b));
  return [...bands].sort((a, b) => rank(a) - rank(b));
}
