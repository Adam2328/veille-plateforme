import { loadState, saveState, resetState, markSeen, pruneSeen, defaultState } from './state.js';
import { loadHome, loadDomain, loadQuotes, loadFootball, loadF1 } from './data.js';
import { renderHome, renderDomain, renderEvent, renderNav, renderError } from './render.js';

const storage = (() => {
  try { return window.localStorage; } catch { return { getItem: () => null, setItem: () => {}, removeItem: () => {} }; }
})();

const $main = document.getElementById('main');
const $nav = document.getElementById('nav');
const domains = new Map();
let home = null;
let state = defaultState();
let previousVisit = null;
let quotes = null;
let football = null;
let f1 = null;

const persist = (next) => { state = next; saveState(storage, state); };

async function domainFile(id) {
  if (!domains.has(id)) domains.set(id, await loadDomain(id));
  return domains.get(id);
}

async function findEvent(id) {
  if (home.events[id]) return home.events[id];
  for (const d of home.domains) {
    const hit = (await domainFile(d.id)).events.find((e) => e.id === id);
    if (hit) return hit;
  }
  return null;
}

async function route() {
  const hash = location.hash || '#/';
  const now = Date.now();
  try {
    if (hash.startsWith('#/d/')) {
      const [id, tab = 'actu', arg = null] = hash.slice(4).split('/').map(decodeURIComponent);
      $main.innerHTML = renderDomain(await domainFile(id), state, now, quotes, football, tab, arg, f1);
    } else if (hash.startsWith('#/e/')) {
      const ev = await findEvent(decodeURIComponent(hash.slice(4)));
      if (!ev) {
        $main.innerHTML = renderError('Événement introuvable ou archivé.');
      } else {
        $main.innerHTML = renderEvent(ev, state, now);
        persist(markSeen(state, [ev]));
      }
    } else {
      $main.innerHTML = renderHome(home, state, now, previousVisit, quotes, football, f1);
    }
  } catch (err) {
    $main.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
  }
  $nav.innerHTML = renderNav(home, state, hash);
  window.scrollTo(0, 0);
}

async function init() {
  try {
    home = await loadHome();
  } catch (err) {
    $main.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
    return;
  }
  quotes = await loadQuotes().catch(() => null);
  football = await loadFootball().catch(() => null);
  f1 = await loadF1().catch(() => null);
  if (new URLSearchParams(location.search).has('reset')) resetState(storage);
  state = loadState(storage);
  previousVisit = state.lastVisit;
  // Première visite sur de vraies données : tout est marqué vu, seules les nouveautés à venir seront signalées.
  if (!state.lastVisit && !home.sample) state = markSeen(state, Object.values(home.events));
  persist(pruneSeen({ ...state, lastVisit: new Date().toISOString() }));
  route();
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  if (btn.dataset.action === 'mark-all') { persist(markSeen(state, Object.values(home.events))); route(); }
  if (btn.dataset.action === 'retry') location.reload();
});
window.addEventListener('hashchange', route);
init();
