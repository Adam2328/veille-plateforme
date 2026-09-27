// Vues de Vigie 2 : chaînes HTML, toute donnée échappée (esc) et toute URL vérifiée (safeUrl).
import { esc, safeUrl, timeAgo, fmtDate, fmtDateTime, parisDay, parisTime, plural, renderQuotes, renderMatches, renderStandings,
  f1Weekend, f1Strip, f1Tables, layersBlock, linksBlock, matchLine } from './blocks.js';
import { eventStatus, countChanges, orderedUniverses } from './state.js';
import { searchEntities, searchEvents, followedEvents } from './search.js';
import { card, pill, pills, visual, entityVisual, entityHref, title, chains, constellation, followButton } from './ui.js';

const safeId = (s) => (/^[a-z_-]+$/.test(s) ? s : 'x');
const enc = encodeURIComponent;
const REL = { officiel: 'Officiel', 'confirmé': 'Confirmé', 'rapporté': 'Rapporté', 'en_développement': 'En développement', 'non_confirmé': 'Non confirmé', rumeur: 'Rumeur' };
const UNIVERSES = [['sport', 'Sport'], ['geopolitique', 'Géo'], ['finance', 'Finance'], ['ia', 'IA']];

export function navHtml(active) {
  const on = (h) => (h === '#/' ? active === '#/' || active === '' : active === h || active.startsWith(`${h}/`));
  const link = (h, label, cls) => `<a class="nl ${cls}" href="${h}"${on(h) ? ' aria-current="page"' : ''}><span class="ni" aria-hidden="true"></span><span>${label}</span></a>`;
  return `${link('#/', 'Aujourd’hui', 'n-today')}${UNIVERSES.map(([id, label]) => link(`#/u/${id}`, label, `n-${id} u-${id}`)).join('')}`;
}

export const viewError = (message, canRetry = false) =>
  `<div class="err"><p>${esc(message)}</p>${canRetry ? '<button type="button" class="btn" data-action="retry">Réessayer</button>' : ''}</div>`;

// ---- Aujourd'hui ----
const since = (iso) => parisTime(iso).replace(':', ' h ');

function settings(ctx, bands) {
  const order = bands.map((b, i) => `<li><span>${esc(b.name)}</span>
    <button type="button" class="icon-btn" data-action="move" data-universe="${esc(b.id)}" data-dir="-1" aria-label="Monter ${esc(b.name)}"${i === 0 ? ' disabled' : ''}>↑</button>
    <button type="button" class="icon-btn" data-action="move" data-universe="${esc(b.id)}" data-dir="1" aria-label="Descendre ${esc(b.name)}"${i === bands.length - 1 ? ' disabled' : ''}>↓</button></li>`).join('');
  const theme = [['auto', 'Automatique'], ['dark', 'Sombre'], ['light', 'Clair']]
    .map(([t, label]) => `<button type="button" class="chip" data-action="theme" data-theme="${t}" aria-pressed="${ctx.state.prefs.theme === t}">${label}</button>`).join('');
  return `<details class="settings"><summary>Réglages</summary><div class="settings-in">
    <div><h3 class="cmp">Ordre des univers</h3><ol class="order">${order}</ol></div>
    <div><h3 class="cmp">Thème</h3><div class="chips">${theme}</div></div></div></details>`;
}

export function viewToday(ctx) {
  const bands = orderedUniverses(ctx.state, ctx.home.today ?? []);
  const shown = bands.flatMap((b) => b.ids.map((id) => ctx.home.events[id]).filter(Boolean));
  const { fresh, updated } = countChanges(ctx.state, shown);
  const n = fresh + updated;
  const counter = n
    ? `<p class="counter"><span class="dot"></span>${plural(n, 'nouveauté')}${ctx.since ? ` depuis ${esc(since(ctx.since))}` : ''} <button type="button" class="link" data-action="mark-all">Tout marquer comme vu</button></p>`
    : '<p class="counter calm">Rien de nouveau depuis votre dernière visite.</p>';
  const sections = bands.map((b) => {
    const evs = b.ids.map((id) => ctx.home.events[id]).filter(Boolean);
    return `<section class="uband u-${safeId(b.id)}" aria-labelledby="h-${safeId(b.id)}">
      <header class="uhead"><h2 id="h-${safeId(b.id)}"><a href="#/u/${enc(b.id)}">${esc(b.name)}</a></h2><span class="count mono">${evs.length}</span><a class="more" href="#/u/${enc(b.id)}">Tout voir →</a></header>
      ${evs.length ? `<div class="grid">${evs.map((e) => card(e, eventStatus(ctx.state, e), ctx.ents)).join('')}</div>` : '<p class="meta">Rien d’important pour l’instant.</p>'}
    </section>`;
  }).join('');
  const day = parisDay(new Date(ctx.now).toISOString());
  return `${ctx.home.sample ? '<div class="sample-banner">Données d’exemple</div>' : ''}
    <header class="today-head"><p class="kicker-date">${esc(day.charAt(0).toUpperCase() + day.slice(1))}</p>
      <h1>Ce qu’il faut savoir aujourd’hui</h1>${counter}</header>
    ${sections}${settings(ctx, bands)}`;
}

export function radarHtml(ctx) {
  const follows = ctx.state.follows.filter((id) => ctx.ents.has(id));
  const followed = followedEvents(ctx.search, ctx.state, 5);
  const rising = [...(ctx.index?.entities ?? [])].sort((a, b) => b.n30 - a.n30).slice(0, 8);
  const quotes = ctx.quotes ? renderQuotes({ quotes: ctx.quotes.quotes.slice(0, 6) }, ctx.now) : '';
  const next = (ctx.football?.fixtures ?? []).slice(0, 4);
  return `<section><h2 class="cmp">Vos suivis</h2>${follows.length
    ? `<div class="pills">${follows.map((id) => pill(id, ctx.ents)).join('')}</div>${followed.length ? `<ul class="plist">${followed.map((e) => `<li><a href="#/e/${enc(e.id)}">${esc(e.title_fr || e.title)}</a><span class="meta">${esc(timeAgo(e.date, ctx.now))}</span></li>`).join('')}</ul>` : ''}`
    : '<p class="meta">Touchez une entité puis « Suivre » : ses actualités apparaîtront ici.</p>'}</section>
    <section><h2 class="cmp">Entités en hausse</h2><div class="pills">${rising.map((e) => pill(e.id, ctx.ents)).join('')}</div></section>
    ${quotes ? `<section><h2 class="cmp">Marchés</h2>${quotes}</section>` : ''}
    ${next.length ? `<section><h2 class="cmp">Prochains matchs</h2><ul class="matches">${next.map(matchLine).join('')}</ul></section>` : ''}`;
}

// ---- Univers ----
export function matchSub(s, e) {
  const ids = e.entity_ids ?? [];
  return Boolean(s.domains?.includes(e.domain) || s.kinds?.includes(e.kind)
    || ids.some((id) => s.entity_types?.includes(id.split(':')[0]) || s.entities?.includes(id)));
}

function footballBlock(fb) {
  if (!fb) return '';
  const standings = (fb.competitions ?? []).map((c) => `<details class="fold"><summary>${esc(c.name)}</summary>${renderStandings(c)}</details>`).join('');
  return `<section class="data"><h2>Matchs</h2><div class="cols"><div><h3 class="cmp">Derniers résultats</h3>${renderMatches((fb.results ?? []).slice(0, 12), fb, 'resultats/')}</div>
    <div><h3 class="cmp">Prochains matchs</h3>${renderMatches((fb.fixtures ?? []).slice(0, 12), fb, 'calendrier/')}</div></div>
    ${standings ? `<h2>Classements</h2>${standings}` : ''}</section>`;
}

function f1Block(f1, full) {
  if (!f1) return '';
  return `<section class="data"><h2>Formule 1</h2>${f1Strip(f1)}${f1.next ? `<h3 class="cmp">Week-end : ${esc(f1.next.name)}</h3>${f1Weekend(f1.next)}` : ''}${full ? f1Tables(f1) : ''}</section>`;
}

function dataBlocks(ctx, uid, sub) {
  if (uid === 'finance' && ctx.quotes) return `<section class="data"><h2>Marchés</h2>${renderQuotes(ctx.quotes, ctx.now)}</section>`;
  if (uid !== 'sport') return '';
  return `${!sub || sub === 'foot' ? footballBlock(ctx.football) : ''}${!sub || sub === 'f1' ? f1Block(ctx.f1, sub === 'f1') : ''}`;
}

export function viewUniverse(ctx, file, sub) {
  const u = file.universe;
  const cur = u.subthemes.find((s) => s.id === sub) ?? null;
  const evs = file.events.filter((e) => !cur || matchSub(cur, e));
  const main = evs.filter((e) => e.level <= 2);
  const minor = evs.filter((e) => e.level === 3);
  const tab = (href, label, active) => `<a href="${href}"${active ? ' aria-current="page"' : ''}>${esc(label)}</a>`;
  const tabs = `<nav class="tabs" aria-label="Sous-thèmes">${tab(`#/u/${enc(u.id)}`, 'Tout', !cur)}${u.subthemes
    .map((s) => tab(`#/u/${enc(u.id)}/${enc(s.id)}`, s.name, cur?.id === s.id)).join('')}</nav>`;
  const agenda = (file.upcoming ?? []).length
    ? `<section class="data"><h2>Agenda</h2><ul class="agenda">${file.upcoming.map((a) => `<li><time class="mono">${esc(fmtDate(a.date))}</time><span>${esc(a.title)}</span></li>`).join('')}</ul></section>` : '';
  const links = (ctx.domainFiles ?? []).filter((d) => !cur || !cur.domains || cur.domains.includes(d.domain.id)).flatMap((d) => d.links ?? []);
  const deeper = links.length ? `<section class="data"><h2>Approfondir</h2>${linksBlock(links)}</section>` : '';
  return `<div class="universe u-${safeId(u.id)}">
    <header class="uhero"><p class="kicker-date">Univers</p><h1>${esc(u.name)}</h1></header>
    ${tabs}
    ${main.length ? `<div class="grid">${main.map((e) => card(e, eventStatus(ctx.state, e), ctx.ents)).join('')}</div>` : '<p class="meta">Rien d’important pour l’instant dans ce thème.</p>'}
    ${minor.length ? `<section class="data"><h2>À savoir</h2><ul class="rows">${minor.map((e) => `<li><a href="#/e/${enc(e.id)}">${esc(title(e))}</a><span class="meta">${esc(timeAgo(e.updated_at, ctx.now))}</span></li>`).join('')}</ul></section>` : ''}
    ${dataBlocks(ctx, u.id, cur?.id)}${agenda}${deeper}</div>`;
}

// ---- Événement ----
function sourcesBlock(ev, now) {
  const sorted = [...ev.sources].sort((a, b) => Date.parse(a.published_at) - Date.parse(b.published_at));
  const li = (x) => {
    const url = safeUrl(x.url);
    const label = `${esc(x.name)} — ${esc(x.title)}`;
    return `<li><time class="mono">${esc(fmtDateTime(x.published_at))}</time>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label}${x.tier >= 5 ? ' <span class="badge">réseau social</span>' : ''}</li>`;
  };
  return `<h3>Chronologie des sources (${sorted.length})</h3><ol class="timeline">${sorted.map(li).join('')}</ol>`;
}

export function viewEvent(ctx, ev) {
  const s = ev.summary;
  const ids = ev.entity_ids ?? [];
  const names = Object.fromEntries(ids.concat((ev.layers?.actifs ?? []).filter((x) => ctx.ents.has(x)))
    .filter((id) => ctx.ents.has(id)).map((id) => [id, ctx.ents.get(id).name]));
  const faces = ids.filter((id) => ctx.ents.has(id)).slice(0, 8)
    .map((id) => `<button type="button" class="face" data-entity="${esc(id)}">${entityVisual(ctx.ents.get(id), 'fvisual')}<span>${esc(ctx.ents.get(id).name)}</span></button>`).join('');
  const rel = `<p class="rel rel-${safeId(ev.reliability)}"><b>${esc(REL[ev.reliability] ?? REL['non_confirmé'])}</b> · ${esc(ev.reliability_reason)}</p>`;
  const lede = s
    ? `<section class="lede"><h2>Ce qui s’est passé</h2><p>${esc(s.quoi)}</p><h2>Pourquoi c’est important</h2><p>${esc(s.pourquoi)}</p></section>`
    : '<p class="meta">Événement secondaire : pas de synthèse, voir les sources.</p>';
  const facts = s ? `<dl class="facts">${[['Qui', s.qui], ['Quand', s.quand], ['À retenir', s.retenir]].map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>` : '';
  const concerned = ev.concerned?.length ? `<h3>Concernés</h3><p class="meta">Liens d’exposition du catalogue Vigie : du contexte, pas une recommandation.</p>${chains(ev.concerned, ctx.ents)}` : '';
  const follows = ids.filter((id) => ctx.ents.has(id)).map((id) => `${followButton(id, ctx.state.follows.includes(id))}<span class="fname">${esc(ctx.ents.get(id).name)}</span>`).join('');
  return `<article class="event u-${safeId(ev.universe ?? 'x')}">
    ${visual(ev, ctx.ents, 'hero')}
    <div class="event-in">
      <p class="crumbs"><a href="#/u/${enc(ev.universe ?? '')}">${esc(ev.universe ?? '')}</a> · mis à jour ${esc(timeAgo(ev.updated_at, ctx.now))}${ev.summary_mode === 'extractif' ? ' · résumé automatique simple' : ''}</p>
      <h1>${esc(title(ev))}</h1>
      ${ev.title_fr && ev.title_fr !== ev.title ? `<p class="orig">Titre original : ${esc(ev.title)}</p>` : ''}
      ${faces ? `<div class="faces">${faces}</div>` : ''}
      ${rel}${lede}
      <details class="deeper"><summary>Aller plus loin</summary>
        ${facts}${layersBlock(ev.layers, ev.domain, names)}${concerned}${sourcesBlock(ev, ctx.now)}
        ${follows ? `<h3>Suivre</h3><div class="follows">${follows}</div>` : ''}
      </details>
    </div></article>`;
}

// ---- Fiche entité ----
export function viewEntity(ctx, page) {
  const e = page.entity;
  const idx = ctx.ents.get(e.id);
  const key = [...(page.facts ?? []).slice(0, 3).map((f) => f.value)].join(' · ');
  const groups = new Map();
  for (const r of page.relations ?? []) {
    if (!ctx.ents.has(r.id)) continue;
    if (!groups.has(r.label)) groups.set(r.label, []);
    groups.get(r.label).push(r.id);
  }
  const rels = [...groups].map(([label, ids]) => `<div class="relgroup"><h3 class="cmp">${esc(label)}</h3><div class="pills">${[...new Set(ids)].map((id) => pill(id, ctx.ents)).join('')}</div></div>`).join('');
  const timeline = (page.events ?? []).map((x) => `<li><time class="mono">${esc(fmtDate(x.date))}</time><a href="#/e/${enc(x.id)}">${esc(x.title_fr || x.title)}</a></li>`).join('');
  const quote = page.quote ? `<p class="keyline mono">${esc(String(page.quote.price))} ${esc(page.quote.currency)} · ${page.quote.change_pct > 0 ? '+' : ''}${esc(String(page.quote.change_pct))} %</p>` : '';
  const svg = constellation(page, ctx.ents);
  return `<article class="entity u-${safeId(e.universes?.[0] ?? 'x')}">
    <header class="ehero">${entityVisual({ ...e, image: page.image ?? idx?.image }, 'ebig')}
      <div class="ehead"><p class="ptype">${esc(e.type_label)}</p><h1>${esc(e.name)}</h1>
        ${key ? `<p class="keyline">${esc(key)}</p>` : ''}${quote}
        ${page.description ? `<p class="desc">${esc(page.description)}</p>` : ''}
        <div class="pactions">${followButton(e.id, ctx.state.follows.includes(e.id))}${(e.universes ?? []).map((u) => `<a class="chip" href="#/u/${enc(u)}">${esc(u)}</a>`).join('')}</div>
      </div></header>
    ${svg ? `<section class="data"><h2>Constellation</h2>${svg}</section>` : ''}
    ${(page.facts ?? []).length > 3 ? `<section class="data"><h2>Repères</h2><dl class="facts">${page.facts.map((f) => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value)}</dd></div>`).join('')}</dl></section>` : ''}
    ${rels ? `<section class="data"><h2>Relations</h2>${rels}</section>` : ''}
    <section class="data"><h2>Chronologie</h2>${timeline ? `<ol class="etimeline">${timeline}</ol>` : '<p class="meta">Aucune actualité ces 30 derniers jours.</p>'}</section>
  </article>`;
}

// ---- Recherche ----
export function resultsHtml(ctx, query) {
  if (!String(query ?? '').trim()) return '<p class="meta">Tapez un nom : entreprise, pays, personne, joueur, équipe, modèle d’IA, sujet…</p>';
  const groups = searchEntities(ctx.index, query);
  const events = searchEvents(ctx.search, query, {}, ctx.now).slice(0, 60);
  if (!groups.length && !events.length) return '<p class="meta">Aucun résultat.</p>';
  const ents = groups.map((g) => `<div class="relgroup"><h3 class="cmp">${esc(g.label)}</h3><div class="pills">${g.items.map((x) => pill(x.id, ctx.ents)).join('')}</div></div>`).join('');
  const rows = events.map((e) => `<li><a href="#/e/${enc(e.id)}">${esc(e.title_fr || e.title)}</a><span class="meta">${esc(fmtDate(e.date))}</span></li>`).join('');
  return `${ents ? `<section class="data"><h2>Entités</h2>${ents}</section>` : ''}${rows ? `<section class="data"><h2>Actualités (30 jours)</h2><ul class="rows">${rows}</ul></section>` : ''}`;
}

export function viewSearch(ctx, query) {
  return `<div class="search-page"><h1>Rechercher</h1>
    <form class="search" role="search" onsubmit="return false"><input id="q" type="search" autocomplete="off" value="${esc(query)}"
      placeholder="Nvidia, Iran, Mbappé, taux, Claude…" aria-label="Rechercher"></form>
    <div id="results">${resultsHtml(ctx, query)}</div></div>`;
}

// Événement sorti des fichiers publiés (ancien lien d'alerte) : fiche courte tirée de l'index de recherche.
export function viewArchived(e) {
  const url = safeUrl(e.url);
  return `<article class="event archived"><div class="event-in"><p class="crumbs">Archive · ${esc(fmtDateTime(e.date))}</p>
    <h1>${esc(e.title_fr || e.title)}</h1>${e.retenir ? `<p>${esc(e.retenir)}</p>` : ''}
    <p>${url ? `<a class="btn" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Lire la source : ${esc(e.source)} ↗</a>` : esc(e.source)}</p></div></article>`;
}
