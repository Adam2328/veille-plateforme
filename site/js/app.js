import { loadState, saveState, resetState, markSeen, pruneSeen, defaultState, toggleFollow } from './state.js';
import { loadHome, loadDomain, loadQuotes, loadFootball, loadF1, loadSearch } from './data.js';
import { renderHome, renderDomain, renderEvent, renderNav, renderError, renderSearch, renderResults, renderArchived } from './render.js';
import { searchEvents } from './search.js';

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
let index = null;

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

// L'index de recherche (30 jours) n'est chargé que s'il sert : recherche, archive ou « Vos suivis ».
let indexPromise = null;
const ensureIndex = () => (indexPromise ??= loadSearch().then((i) => { index = i; return i; }).catch(() => null));

function refreshResults() {
  const $r = document.getElementById('results');
  if (!$r || !index) return;
  const q = document.getElementById('q').value;
  const filters = { domain: document.getElementById('qd').value, days: Number(document.getElementById('qp').value) };
  $r.innerHTML = renderResults(searchEvents(index, q, filters, Date.now()), index, Date.now());
  history.replaceState(null, '', `#/s/${encodeURIComponent(q)}`);
}

let routeToken = 0;

async function route() {
  const hash = location.hash || '#/';
  const now = Date.now();
  const token = ++routeToken;
  // Une navigation plus récente a eu lieu pendant un chargement : on n'écrase pas son affichage.
  const stale = () => token !== routeToken;
  const $out = { set innerHTML(html) { if (!stale()) $main.innerHTML = html; } };
  try {
    if (hash.startsWith('#/d/')) {
      const [id, tab = 'actu', arg = null] = hash.slice(4).split('/').map(decodeURIComponent);
      $out.innerHTML = renderDomain(await domainFile(id), state, now, quotes, football, tab, arg, f1);
    } else if (hash.startsWith('#/s/')) {
      await ensureIndex();
      $out.innerHTML = renderSearch(index, decodeURIComponent(hash.slice(4)), {}, now);
      if (!stale()) {
        refreshResults();
        document.getElementById('q').focus();
      }
    } else if (hash.startsWith('#/e/')) {
      const id = decodeURIComponent(hash.slice(4));
      const ev = await findEvent(id);
      const archived = !ev && (await ensureIndex()) ? index.events.find((e) => e.id === id) : null;
      if (ev) {
        $out.innerHTML = renderEvent(ev, state, now);
        persist(markSeen(state, [ev]));
      } else if (archived) {
        $out.innerHTML = renderArchived(archived, index);
      } else {
        $out.innerHTML = renderError('Événement introuvable ou archivé.');
      }
    } else {
      if (state.follows.length) await ensureIndex();
      $out.innerHTML = renderHome(home, state, now, previousVisit, quotes, football, f1, index);
    }
  } catch (err) {
    $out.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
  }
  if (stale()) return;
  $nav.innerHTML = renderNav(home, state, hash);
  if (!hash.startsWith('#/s/')) window.scrollTo(0, 0);
}

async function init() {
  try {
    home = await loadHome();
  } catch (err) {
    $main.innerHTML = renderError(`Impossible de charger les données (${err.message}).`, true);
    return;
  }
  // Données complémentaires chargées en parallèle ; un échec n'empêche jamais l'affichage.
  [quotes, football, f1] = await Promise.all([loadQuotes, loadFootball, loadF1].map((f) => f().catch(() => null)));
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
  if (btn.dataset.action === 'follow') {
    persist(toggleFollow(state, btn.dataset.entity));
    const on = state.follows.includes(btn.dataset.entity);
    btn.setAttribute('aria-pressed', String(on));
    btn.textContent = `${on ? '✓ Suivi' : '+ Suivre'} : ${btn.dataset.entity}`;
  }
});
document.addEventListener('input', (e) => { if (['q', 'qd', 'qp'].includes(e.target.id)) refreshResults(); });
document.addEventListener('keydown', (e) => {
  const typing = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName);
  if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
    e.preventDefault();
    location.hash = '#/s/';
  }
});
window.addEventListener('hashchange', route);
// Application installable et lecture hors ligne ; sans support ou en cas d'échec, le site fonctionne normalement.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
init();
