import { eventStatus, countChanges } from './state.js';

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function safeUrl(u) {
  try {
    const x = new URL(u);
    return x.protocol === 'http:' || x.protocol === 'https:' ? x.href : null;
  } catch {
    return null;
  }
}

const color = (c) => (/^#[0-9a-f]{3,8}$/i.test(c) ? c : '#1A3A6B');
const plural = (n, word) => `${n} ${word}${n > 1 ? 's' : ''}`;
const enc = encodeURIComponent;

const REL = { officiel: 'Officiel', 'confirmé': 'Confirmé', 'rapporté': 'Rapporté', 'en_développement': 'En développement', 'non_confirmé': 'Non confirmé', rumeur: 'Rumeur' };
const REL_CLASS = { officiel: 'officiel', 'confirmé': 'confirme', 'rapporté': 'rapporte', 'en_développement': 'dev', 'non_confirmé': 'nc', rumeur: 'rumeur' };
const STATUS = { new: 'Nouveau', updated: 'Mis à jour' };
const relLabel = (r) => REL[r] ?? REL['non_confirmé'];
const relClass = (r) => REL_CLASS[r] ?? 'nc';

export function timeAgo(iso, now = Date.now()) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const m = Math.max(0, Math.round((now - t) / 60000));
  if (m < 60) return `il y a ${m} min`;
  const h = Math.round(m / 60);
  return h < 24 ? `il y a ${h} h` : `il y a ${Math.round(h / 24)} j`;
}

const fmtDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
};
const fmtDateTime = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

export function badges(ev, status) {
  const st = STATUS[status] ? `<span class="badge st-${status}">${STATUS[status]}</span>` : '';
  return `${st}<span class="badge rel-${relClass(ev.reliability)}" title="${esc(ev.reliability_reason)}">${esc(relLabel(ev.reliability))}</span>`;
}

const href = (ev) => `#/e/${enc(ev.id)}`;

export function card(ev, status, now) {
  return `<a class="card" href="${href(ev)}">
    <div>${badges(ev, status)}</div>
    <h3>${esc(ev.title)}</h3>
    ${ev.summary ? `<p>${esc(ev.summary.retenir === ev.title ? ev.summary.quoi : ev.summary.retenir)}</p>` : ''}
    <div class="meta">${esc(plural(ev.sources.length, 'source'))} · ${esc(timeAgo(ev.updated_at, now))}</div>
  </a>`;
}

export function row(ev, status, now) {
  return `<a class="row" href="${href(ev)}">${badges(ev, status)}<span class="t">${esc(ev.title)}</span><span class="meta">${esc(timeAgo(ev.updated_at, now))}</span></a>`;
}

const upcomingList = (items) =>
  items && items.length
    ? `<ul class="upcoming">${items.map((u) => `<li><b>${esc(fmtDate(u.date))}</b> ${esc(u.title)}</li>`).join('')}</ul>`
    : '';

const nf = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 });
const signed = (n, suffix) => `${n > 0 ? '+' : ''}${nf.format(n)}${suffix}`;

export function renderQuotes(quotes, now = Date.now()) {
  if (!quotes || !quotes.quotes || !quotes.quotes.length) return '';
  const item = (x) => {
    const rate = x.group === 'Taux';
    const delta = rate ? x.change : x.change_pct;
    const dir = delta == null ? 'flat' : delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
    const txt = delta == null ? '—' : signed(delta, rate ? ' pt' : ' %');
    const tip = `${x.symbol} · ${timeAgo(x.as_of, now)}${x.stale ? ' · valeur non actualisée' : ''}`;
    return `<li class="q ${dir}" title="${esc(tip)}"><span class="qn">${esc(x.name)}</span><span class="qp">${esc(nf.format(x.price))}</span><span class="qc">${esc(txt)}</span>${x.stale ? '<span class="qs">≈</span>' : ''}</li>`;
  };
  return `<ul class="quotes" aria-label="Cours de marché">${quotes.quotes.map(item).join('')}</ul>`;
}

const LAYER_SECTIONS = [['faits', 'Faits'], ['analyse', 'Analyse'], ['interpretation', 'Interprétation'], ['incertitude', 'Incertitude'],
  ['actifs', 'Actifs concernés'], ['favorables', 'Éléments favorables'], ['risques', 'Risques'], ['a_surveiller', 'À surveiller']];
// Mêmes couches, rôles propres à la Géopolitique (voir le profil « geopolitique » du moteur).
const LAYER_TITLES = {
  geopolitique: { analyse: 'Déclarations des acteurs', interpretation: 'Conséquences possibles', incertitude: 'Incertitudes', actifs: 'Pays et acteurs concernés' },
};
const LAYER_NOTES = {
  finance: 'Synthèse générée automatiquement à partir des sources. Elle ne constitue pas un conseil en investissement.',
  geopolitique: 'Synthèse générée automatiquement à partir des sources ; les déclarations sont attribuées à leurs auteurs et ne sont pas des faits établis.',
};

function layersBlock(layers, domain) {
  if (!layers) return '';
  const titles = LAYER_TITLES[domain] ?? {};
  const sections = LAYER_SECTIONS
    .filter(([key]) => Array.isArray(layers[key]) && layers[key].length)
    .map(([key, title]) => `<section class="layer layer-${key}"><h3>${titles[key] ?? title}</h3><ul>${layers[key].map((b) => `<li>${esc(b)}</li>`).join('')}</ul></section>`);
  if (!sections.length) return '';
  const note = LAYER_NOTES[domain] ?? 'Synthèse générée automatiquement à partir des sources.';
  return `<div class="layers">${sections.join('')}<p class="meta">${note}</p></div>`;
}

const FB_TABS = [['actu', 'Actu'], ['resultats', 'Résultats'], ['classements', 'Classements'], ['calendrier', 'Calendrier'], ['mercato', 'Mercato']];
const HIDDEN_IN_MERCATO = ['rumeur', 'non_confirmé'];
const compName = (football, code) => football?.competitions?.find((c) => c.code === code)?.name ?? code;
const fmtKickoff = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

// Lien « approfondir » vers Flashscore (s'ouvre dans l'application sur mobile) ; page = '' | 'resultats/' | 'calendrier/' | 'classement/'.
function flashscoreLink(comp, page = '') {
  const url = comp?.flashscore ? safeUrl(`${comp.flashscore}${page}`) : null;
  return url && url.startsWith('https://www.flashscore.fr/')
    ? `<a class="fs" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Voir sur Flashscore ↗</a>`
    : '';
}

export function matchLine(m) {
  const played = Number.isInteger(m.home_score) && Number.isInteger(m.away_score);
  const middle = played ? `${m.home_score} – ${m.away_score}` : fmtKickoff(m.date);
  return `<li class="match${played ? '' : ' next'}"><span class="mh">${esc(m.home)}</span><span class="ms">${esc(middle)}</span><span class="ma">${esc(m.away)}</span></li>`;
}

export function renderMatches(list, football, page = '') {
  if (!list || !list.length) return '<p class="meta">Aucun match à afficher.</p>';
  const codes = [...new Set(list.map((m) => m.competition))];
  const comp = (code) => football?.competitions?.find((c) => c.code === code);
  return codes
    .map((code) => `<h3 class="cmp">${esc(compName(football, code))} ${flashscoreLink(comp(code), page)}</h3><ul class="matches">${list.filter((m) => m.competition === code).map(matchLine).join('')}</ul>`)
    .join('');
}

export function renderStandings(comp) {
  const rows = comp.standings
    .map((r) => `<tr><td>${esc(r.position)}</td><td class="tn">${esc(r.team)}</td><td>${esc(r.played)}</td><td>${esc(r.won)}</td><td>${esc(r.draw)}</td><td>${esc(r.lost)}</td><td>${esc(r.gd)}</td><td><b>${esc(r.points)}</b></td><td class="form">${esc(r.form)}</td></tr>`)
    .join('');
  const link = flashscoreLink(comp, 'classement/');
  return `<table class="standings"><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>Diff</th><th>Pts</th><th>Forme</th></tr></thead><tbody>${rows}</tbody></table>${comp.stale ? '<p class="meta">Classement non actualisé.</p>' : ''}${link ? `<p class="meta">${link}</p>` : ''}`;
}

export function footballStrip(football) {
  if (!football) return '';
  const last = (football.results ?? []).slice(0, 6);
  const next = (football.fixtures ?? []).slice(0, 6);
  if (!last.length && !next.length) return '';
  const col = (title, list) => (list.length ? `<div><h3 class="cmp">${title}</h3><ul class="matches">${list.map(matchLine).join('')}</ul></div>` : '');
  return `<div class="fb-strip">${col('Derniers résultats', last)}${col('Prochains matchs', next)}</div>`;
}

function eventSections(events, state, now) {
  const by = (n) => events.filter((e) => e.level === n);
  const st = (e) => eventStatus(state, e);
  const section = (title, list, fn) => (list.length ? `<h2>${title}</h2>${list.map((e) => fn(e, st(e), now)).join('')}` : '');
  return `${section('Incontournable', by(1), card)}${section('Important', by(2), row)}${section('À savoir', by(3), row)}`;
}

const fbTabs = (tab) =>
  `<div class="tabs">${FB_TABS.map(([k, t]) => `<a href="#/d/football${k === 'actu' ? '' : `/${k}`}"${k === tab ? ' aria-current="page"' : ''}>${t}</a>`).join('')}</div>`;

export function renderFootball(file, football, tab, arg, state, now) {
  const unavailable = '<p class="meta">Données indisponibles pour le moment.</p>';
  let body;
  if (tab === 'resultats') {
    body = football ? `<h2>Résultats récents</h2>${renderMatches(football.results, football, 'resultats/')}` : unavailable;
  } else if (tab === 'calendrier') {
    body = football ? `<h2>Prochains matchs</h2>${renderMatches(football.fixtures, football, 'calendrier/')}` : unavailable;
  } else if (tab === 'classements') {
    const comps = football?.competitions ?? [];
    if (!comps.length) {
      body = unavailable;
    } else {
      const cur = comps.find((c) => c.code === arg) ?? comps[0];
      const subtabs = comps.map((c) => `<a href="#/d/football/classements/${enc(c.code)}"${c.code === cur.code ? ' aria-current="page"' : ''}>${esc(c.name)}</a>`).join('');
      body = `<div class="tabs sub">${subtabs}</div><h2>${esc(cur.name)}</h2>${renderStandings(cur)}`;
    }
  } else if (tab === 'mercato') {
    const all = file.events.filter((e) => e.kind === 'transfer');
    const showAll = arg === 'rumeurs';
    const shown = showAll ? all : all.filter((e) => !HIDDEN_IN_MERCATO.includes(e.reliability));
    const hidden = all.length - shown.length;
    const toggle = hidden
      ? `<p class="meta"><a href="#/d/football/mercato/rumeurs">Afficher les rumeurs (${plural(hidden, 'masquée')})</a></p>`
      : showAll ? '<p class="meta"><a href="#/d/football/mercato">Masquer les rumeurs</a></p>' : '';
    body = `${toggle}${shown.length ? eventSections(shown, state, now) : '<p class="meta">Aucune information de mercato pour l’instant.</p>'}`;
  } else {
    const news = file.events.filter((e) => e.kind !== 'transfer');
    body = `${news.length ? eventSections(news, state, now) : '<p class="meta">Rien d’important pour l’instant.</p>'}${upcomingList(file.upcoming)}`;
  }
  const tabName = FB_TABS.some(([k]) => k === tab) ? tab : 'actu';
  return `<div style="--dom:${color(file.domain.accent)}"><a class="back" href="#/">← Accueil</a><h1>${esc(file.domain.name)}</h1>${fbTabs(tabName)}${body}</div>`;
}

export function domainBlock(dom, events, state, now, quotes = null, football = null) {
  const pick = (n) => (dom.levels[n] ?? []).map((id) => events[id]).filter(Boolean);
  const [l1, l2, l3] = [pick(1), pick(2), pick(3)];
  const st = (e) => eventStatus(state, e);
  const empty = !l1.length && !l2.length && !l3.length;
  const more = l3.length
    ? `<details class="more"><summary>Voir ${plural(l3.length, 'autre')}</summary>${l3.map((e) => `<a href="${href(e)}">${esc(e.title)}</a>`).join('')}</details>`
    : '';
  return `<section class="block" style="--dom:${color(dom.accent)}">
    <h2><a href="#/d/${enc(dom.id)}">${esc(dom.name)}</a></h2>
    ${dom.id === 'finance' ? renderQuotes(quotes, now) : ''}
    ${empty ? '<p class="meta">Rien d’important pour l’instant.</p>' : ''}
    ${l1.map((e) => card(e, st(e), now)).join('')}
    ${l2.map((e) => row(e, st(e), now)).join('')}
    ${more}
    ${dom.id === 'football' ? footballStrip(football) : ''}
    ${upcomingList(dom.upcoming)}
  </section>`;
}

export function renderHome(home, state, now, since = null, quotes = null, football = null) {
  const { fresh, updated } = countChanges(state, Object.values(home.events));
  const retain = home.retain.map((id) => home.events[id]).filter(Boolean);
  const sinceTxt = since && fmtDateTime(since) ? ` (dernière visite : ${esc(fmtDateTime(since))})` : '';
  return `${home.sample ? '<div class="sample-banner">Données d’exemple</div>' : ''}
    <h1>Aujourd’hui</h1>
    <p class="meta">Dernier changement de contenu : ${esc(timeAgo(home.generated_at, now))}</p>
    <div class="since"><span>Depuis ta dernière visite${sinceTxt} : <b>${fresh}</b> nouveauté${fresh > 1 ? 's' : ''} · <b>${updated}</b> mise${updated > 1 ? 's' : ''} à jour</span>${fresh + updated ? '<button class="link" data-action="mark-all">Tout marquer comme vu</button>' : ''}</div>
    ${retain.length ? `<section class="retain"><h2>À retenir aujourd’hui</h2><ol>${retain.map((e) => `<li>${badges(e, eventStatus(state, e))}<a href="${href(e)}">${esc(e.title)}</a><div class="meta">${esc(e.summary?.retenir ?? '')}</div></li>`).join('')}</ol></section>` : ''}
    ${home.domains.map((d) => domainBlock(d, home.events, state, now, quotes, football)).join('')}`;
}

// Liens « Approfondir » déclarés dans la config de la veille (ex. pages Flashscore des tournois).
function linksBlock(links) {
  const safe = (links ?? []).map((l) => ({ title: l.title, url: safeUrl(l.url) })).filter((l) => l.url && l.url.startsWith('https://'));
  if (!safe.length) return '';
  return `<h2>Approfondir</h2><ul class="links">${safe.map((l) => `<li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.title)}</a></li>`).join('')}</ul>`;
}

export function renderDomain(file, state, now, quotes = null, football = null, tab = 'actu', arg = null) {
  if (file.domain.id === 'football') return renderFootball(file, football, tab, arg, state, now);
  const empty = !file.events.length;
  return `<div style="--dom:${color(file.domain.accent)}"><a class="back" href="#/">← Accueil</a>
    <h1>${esc(file.domain.name)}</h1>
    ${file.domain.id === 'finance' ? renderQuotes(quotes, now) : ''}
    ${empty ? '<p class="meta">Rien d’important pour l’instant.</p>' : ''}
    ${eventSections(file.events, state, now)}
    ${upcomingList(file.upcoming)}
    ${linksBlock(file.links)}</div>`;
}

export function renderEvent(ev, state, now) {
  const s = ev.summary;
  const fields = s ? [['Quoi', s.quoi], ['Qui', s.qui], ['Quand', s.quand], ['Pourquoi c’est important', s.pourquoi], ['À retenir', s.retenir]] : [];
  const sorted = [...ev.sources].sort((a, b) => a.tier - b.tier || Date.parse(b.published_at) - Date.parse(a.published_at));
  const li = (x) => {
    const url = safeUrl(x.url);
    const label = `${esc(x.name)} — ${esc(x.title)}`;
    return `<li><span class="badge">tier ${esc(x.tier)}</span>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label}<span class="meta"> ${esc(timeAgo(x.published_at, now))}</span></li>`;
  };
  const main = sorted.filter((x) => x.tier < 5);
  const social = sorted.filter((x) => x.tier >= 5);
  return `<article class="detail"><a class="back" href="#/">← Accueil</a>
    <div>${badges(ev, eventStatus(state, ev))}${ev.summary_mode === 'extractif' ? '<span class="badge">Résumé automatique simple</span>' : ''}</div>
    <h1>${esc(ev.title)}</h1>
    <p class="meta">Fiabilité : ${esc(ev.reliability_reason)} · première détection ${esc(timeAgo(ev.first_seen, now))} · mis à jour ${esc(timeAgo(ev.updated_at, now))}</p>
    ${fields.length ? `<dl>${fields.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` : '<p class="meta">Événement secondaire : pas de synthèse, voir les sources.</p>'}
    ${layersBlock(ev.layers, ev.domain)}
    <h2>Sources (${sorted.length})</h2>
    <ul class="sources">${main.map(li).join('')}</ul>
    ${social.length ? `<details class="more"><summary>Réseaux sociaux (${social.length})</summary><ul class="sources">${social.map(li).join('')}</ul></details>` : ''}
  </article>`;
}

export function renderNav(home, state, activeHash) {
  const changed = (d) =>
    [1, 2, 3].flatMap((n) => d.levels[n] ?? []).map((id) => home.events[id]).filter((e) => e && eventStatus(state, e) !== 'seen').length;
  const isActive = (h) => (h === '#/' ? activeHash === h : activeHash === h || activeHash.startsWith(`${h}/`));
  const link = (h, label, n) =>
    `<a href="${h}"${isActive(h) ? ' aria-current="page"' : ''}><span>${esc(label)}</span>${n ? `<span class="count">${n}</span>` : ''}</a>`;
  return `<div class="brand">Veille</div>${link('#/', 'Accueil', 0)}${home.domains.map((d) => link(`#/d/${enc(d.id)}`, d.name, changed(d))).join('')}`;
}

export function renderError(message, canRetry = false) {
  return `<div class="err"><p>${esc(message)}</p>${canRetry ? '<button class="link" data-action="retry">Réessayer</button>' : ''}</div>`;
}
