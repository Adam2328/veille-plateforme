import { loadState, saveState, resetState, markSeen, pruneSeen, defaultState, toggleFollow, setTheme, setOrder, orderedUniverses } from './state.js';
import { loadHome, loadUniverse, loadEntityIndex, loadEntity, loadBand, loadDomain, loadQuotes, loadFootball, loadF1, loadSearch } from './data.js';
import { viewToday, viewUniverse, viewEvent, viewEntity, viewSearch, viewArchived, resultsHtml, radarHtml, navHtml, viewError } from './views.js';
import { entityMap, bandHtml, panelHtml } from './ui.js';

const storage = (() => {
  try { return window.localStorage; } catch { return { getItem: () => null, setItem: () => {}, removeItem: () => {} }; }
})();
const $ = (id) => document.getElementById(id);
const [$main, $nav, $tabbar, $band, $radar, $panel, $scrim] = ['main', 'nav', 'tabbar', 'band', 'radar', 'panel', 'scrim'].map($);
const UNIVERSE_IDS = ['finance', 'ia', 'geopolitique', 'sport'];
// Anciennes adresses (#/d/<rubrique>) → univers de Vigie 2 ; les liens des alertes déjà envoyées restent valables.
const REDIRECT = { football: 'sport/foot', tennis: 'sport/tennis', f1: 'sport/f1', nba: 'sport/basket', volley: 'sport/volley', 'sport-essentiel': 'sport/autres' };

const ctx = { home: null, index: null, ents: new Map(), state: defaultState(), now: Date.now(), since: null,
  quotes: null, football: null, f1: null, search: null, domainFiles: [] };
const universes = new Map();
const entities = new Map();
const domains = new Map();

const persist = (next) => { ctx.state = next; saveState(storage, next); };
const cached = (map, key, load) => { if (!map.has(key)) map.set(key, load(key).catch((e) => { map.delete(key); throw e; })); return map.get(key); };
const universe = (id) => cached(universes, id, loadUniverse);
const entity = (id) => cached(entities, id, loadEntity);
const domain = (id) => cached(domains, id, loadDomain);

let searchPromise = null;
const ensureSearch = () => (searchPromise ??= loadSearch().then((s) => { ctx.search = s; return s; }).catch(() => null));

async function findEvent(id) {
  if (ctx.home.events[id]) return ctx.home.events[id];
  const files = await Promise.all(UNIVERSE_IDS.map((u) => universe(u).catch(() => null)));
  return files.flatMap((f) => f?.events ?? []).find((e) => e.id === id) ?? null;
}

// ---- Thème ----
const THEMES = ['auto', 'dark', 'light'];
function applyTheme() {
  const t = ctx.state.prefs.theme;
  if (t === 'auto') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
  for (const b of document.querySelectorAll('[data-action="theme"]')) b.setAttribute('aria-pressed', String(b.dataset.theme === t));
}

// ---- Apparition des cartes au défilement (coupée si l'appareil demande moins d'animations) ----
const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const observer = !reduced && 'IntersectionObserver' in window
  ? new IntersectionObserver((entries) => entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); observer.unobserve(en.target); } }), { rootMargin: '0px 0px -8% 0px' })
  : null;
if (observer) document.documentElement.classList.add('anim');
function animateIn() {
  for (const el of $main.querySelectorAll('.card, .data, .uband header')) observer ? observer.observe(el) : el.classList.add('in');
}

// ---- Routeur ----
let routeToken = 0;

// keepScroll : réaffichage sur place (réglages, données arrivées après coup) sans remonter ni fermer le panneau.
async function route({ keepScroll = false } = {}) {
  const hash = location.hash || '#/';
  const moved = hash.startsWith('#/d/') ? `#/u/${REDIRECT[decodeURIComponent(hash.slice(4).split('/')[0])] ?? hash.slice(4).split('/')[0]}` : null;
  if (moved) { history.replaceState(null, '', moved); return route(); }
  const token = ++routeToken;
  const stale = () => token !== routeToken;   // une navigation plus récente a eu lieu pendant un chargement
  const show = (html) => { if (!stale()) $main.innerHTML = html; };
  ctx.now = Date.now();
  if (!keepScroll) closePanel();
  try {
    if (hash.startsWith('#/u/')) {
      const [id, sub = null] = hash.slice(4).split('/').map(decodeURIComponent);
      const file = await universe(id);
      ctx.domainFiles = (await Promise.all(file.domains.map((d) => domain(d.id).catch(() => null)))).filter(Boolean);
      show(viewUniverse(ctx, file, sub));
    } else if (hash.startsWith('#/e/')) {
      const id = decodeURIComponent(hash.slice(4));
      const ev = await findEvent(id);
      if (ev) {
        show(viewEvent(ctx, ev));
        persist(markSeen(ctx.state, [ev]));
      } else {
        const archived = (await ensureSearch())?.events.find((e) => e.id === id);
        show(archived ? viewArchived(archived) : viewError('Information introuvable ou archivée depuis plus de 30 jours.'));
      }
    } else if (hash.startsWith('#/x/')) {
      const [type, slug] = hash.slice(4).split('/').map(decodeURIComponent);
      show(viewEntity(ctx, await entity(`${type}:${slug}`)));
    } else if (hash.startsWith('#/s/')) {
      await ensureSearch();
      show(viewSearch(ctx, decodeURIComponent(hash.slice(4))));
      if (!stale()) $('q')?.focus();
    } else {
      show(viewToday(ctx));
    }
  } catch (err) {
    show(viewError(`Impossible de charger cette page (${err.message}).`, true));
  }
  if (stale()) return;
  $nav.innerHTML = navHtml(hash);
  $tabbar.innerHTML = navHtml(hash);
  if (!keepScroll && !hash.startsWith('#/s/')) window.scrollTo(0, 0);
  animateIn();
}

function renderRadar() {
  $radar.innerHTML = radarHtml(ctx);
}

// ---- Panneau d'aperçu d'une entité ----
// Le reste de la page devient inerte pendant l'aperçu : le focus clavier reste dans le panneau (dialogue modal).
const BACKGROUND = ['band', 'main', 'radar', 'tabbar'].map($).concat([document.querySelector('.top')]);
const setBackgroundInert = (on) => BACKGROUND.forEach((el) => el?.toggleAttribute('inert', on));
let lastFocus = null;
async function openPanel(id) {
  if ($panel.hidden) lastFocus = document.activeElement;
  setBackgroundInert(true);
  $panel.hidden = false;
  $scrim.hidden = false;
  document.body.classList.add('panel-open');
  $panel.innerHTML = '<div class="panel-in"><p class="meta">Chargement…</p></div>';
  try {
    $panel.innerHTML = panelHtml(await entity(id), ctx.ents, ctx.state, Date.now());
  } catch {
    $panel.innerHTML = `<div class="panel-in"><button type="button" class="panel-close" data-action="close-panel" aria-label="Fermer">×</button>${viewError('Fiche indisponible pour le moment.')}</div>`;
  }
  $panel.querySelector('.panel-close')?.focus();
}

function closePanel() {
  if ($panel.hidden) return;
  $panel.hidden = true;
  $scrim.hidden = true;
  setBackgroundInert(false);
  document.body.classList.remove('panel-open');
  lastFocus?.focus?.();
}

// ---- Interactions ----
function toggleFollowButtons(id) {
  persist(toggleFollow(ctx.state, id));
  const on = ctx.state.follows.includes(id);
  for (const b of document.querySelectorAll('[data-action="follow"]')) {
    if (b.dataset.entity !== id) continue;
    b.setAttribute('aria-pressed', String(on));
    b.textContent = on ? '✓ Suivi' : '+ Suivre';
  }
  renderRadar();
  ensureSearch().then(renderRadar);      // premier suivi : l'index des actualités n'était pas encore chargé
}

async function moveUniverse(id, dir) {
  const order = orderedUniverses(ctx.state, ctx.home.today ?? []).map((b) => b.id);
  const i = order.indexOf(id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= order.length) return;
  [order[i], order[j]] = [order[j], order[i]];
  persist(setOrder(ctx.state, order));
  await route({ keepScroll: true });
  const details = $main.querySelector('details.settings');
  if (details) details.open = true;
  const buttons = [dir, -dir].map((d) => $main.querySelector(`[data-action="move"][data-universe="${CSS.escape(id)}"][data-dir="${d}"]`));
  buttons.find((b) => b && !b.disabled)?.focus();
}

document.addEventListener('click', (e) => {
  const actor = e.target.closest('[data-action]');
  const action = actor?.dataset.action;
  if (action === 'follow') return toggleFollowButtons(actor.dataset.entity);
  if (action === 'close-panel') return closePanel();
  if (action === 'retry') return location.reload();
  if (action === 'mark-all') {
    persist(markSeen(ctx.state, (ctx.home.today ?? []).flatMap((b) => b.ids.map((id) => ctx.home.events[id]).filter(Boolean))));
    return route();
  }
  if (action === 'move') return moveUniverse(actor.dataset.universe, Number(actor.dataset.dir));
  if (action === 'theme' || action === 'theme-cycle') {
    const next = action === 'theme' ? actor.dataset.theme : THEMES[(THEMES.indexOf(ctx.state.prefs.theme) + 1) % THEMES.length];
    persist(setTheme(ctx.state, next));
    return applyTheme();
  }
  const pillEl = e.target.closest('[data-entity]');
  if (pillEl) { e.preventDefault(); openPanel(pillEl.dataset.entity); }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') return closePanel();
  const typing = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName);
  if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
    e.preventDefault();
    location.hash = '#/s/';
  }
});

document.addEventListener('input', (e) => {
  if (e.target.id !== 'q') return;
  $('results').innerHTML = resultsHtml(ctx, e.target.value);
  for (const el of $('results').querySelectorAll('.data')) el.classList.add('in');   // sinon masqués par l'animation d'apparition
  history.replaceState(null, '', `#/s/${encodeURIComponent(e.target.value)}`);
});

// Photo d'article indisponible : on la retire, l'illustration générée placée dessous apparaît.
document.addEventListener('error', (e) => { if (e.target.tagName === 'IMG') e.target.remove(); }, true);

// Bandeau : défilement continu, pause au survol (CSS) et au toucher ; glissable au doigt (défilement natif).
let resume = null;
$band.addEventListener('pointerdown', () => { $band.classList.add('paused'); clearTimeout(resume); });
$band.addEventListener('pointerup', () => { resume = setTimeout(() => $band.classList.remove('paused'), 4000); });

window.addEventListener('hashchange', route);

async function init() {
  try {
    [ctx.home, ctx.index] = await Promise.all([loadHome(), loadEntityIndex()]);
  } catch (err) {
    $main.innerHTML = viewError(`Impossible de charger les données (${err.message}).`, true);
    return;
  }
  ctx.ents = entityMap(ctx.index);
  if (new URLSearchParams(location.search).has('reset')) resetState(storage);
  let state = loadState(storage);
  ctx.since = state.lastVisit;
  // Première visite : tout est marqué vu, seules les nouveautés suivantes seront signalées.
  if (!state.lastVisit && !ctx.home.sample) state = markSeen(state, Object.values(ctx.home.events));
  persist(pruneSeen({ ...state, lastVisit: new Date().toISOString() }));
  applyTheme();
  route();
  // Données complémentaires : un échec n'empêche jamais l'affichage.
  const [band, quotes, football, f1] = await Promise.all([loadBand, loadQuotes, loadFootball, loadF1].map((f) => f().catch(() => null)));
  Object.assign(ctx, { quotes, football, f1 });
  $band.innerHTML = bandHtml(band);
  if (ctx.state.follows.length) await ensureSearch();
  renderRadar();
  if (/^#\/u\/(finance|sport)/.test(location.hash)) route({ keepScroll: true });   // blocs de données arrivés après le premier affichage
}

// Application installable et lecture hors ligne ; sans support ou en cas d'échec, le site fonctionne normalement.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
init();
