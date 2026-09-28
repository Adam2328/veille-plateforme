// Composants de l'interface : pastilles d'entités, badges, cartes, visuels.
import { esc, safeUrl, nf, signed, timeAgo, parisTime, fmtDate } from './blocks.js';
import { artFor, artEntity } from './art.js';

const safeType = (t) => (/^[a-z_]+$/.test(t) ? t : 'x');
const LOW = { rumeur: 'Rumeur', 'non_confirmé': 'Non confirmé', 'en_développement': 'En développement' };
const LOW_CLASS = { rumeur: 'rumeur', 'non_confirmé': 'nc', 'en_développement': 'dev' };

export const entityMap = (index) => new Map((index?.entities ?? []).map((e) => [e.id, e]));
export const entityHref = (id) => {
  const [type, slug] = String(id).split(':');
  return `#/x/${encodeURIComponent(type)}/${encodeURIComponent(slug ?? '')}`;
};
export const title = (ev) => ev.title_fr || ev.title;

// Badge sur les cartes : seulement quand il faut se méfier (une rumeur ne doit jamais passer pour un fait).
export function relBadge(ev) {
  const label = LOW[ev.reliability];
  return label ? `<span class="badge rel-${LOW_CLASS[ev.reliability]}" title="${esc(ev.reliability_reason)}">${label}</span>` : '';
}

export function pill(id, ents) {
  const e = ents.get(id);
  if (!e) return '';
  return `<button type="button" class="pill t-${safeType(e.type)}" data-entity="${esc(id)}"><span class="pi" aria-hidden="true"></span>${esc(e.name)}</button>`;
}

export const pills = (ids, ents, max = 3, skipTypes = []) =>
  (ids ?? []).filter((id) => ents.has(id) && !skipTypes.includes(ents.get(id).type)).slice(0, max).map((id) => pill(id, ents)).join('');

// Photo de l'article au-dessus de l'illustration : si la photo échoue, app.js la retire et l'illustration apparaît.
export function visual(ev, ents, cls = 'visual') {
  const lead = ents.get((ev.entity_ids ?? [])[0]);
  const art = artFor(ev.id, ev.universe ?? 'x', lead?.name ?? '', ev.kind);
  const url = safeUrl(ev.image);
  const img = url && url.startsWith('https://')
    ? `<img src="${esc(url)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : '';
  return `<div class="${cls}">${art}${img}</div>`;
}

export function entityVisual(entity, cls = 'evisual') {
  const url = safeUrl(entity?.image);
  const img = url && url.startsWith('https://')
    ? `<img src="${esc(url)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : '';
  return `<div class="${cls}">${artEntity(entity ?? { id: 'x', name: '?' })}${img}</div>`;
}

export function card(ev, status, ents) {
  const fresh = status === 'new' || status === 'updated';
  const why = ev.summary?.pourquoi || ev.summary?.retenir || '';
  const skip = ev.universe === 'sport' ? ['country'] : [];
  return `<article class="card u-${safeType(ev.universe ?? 'x')}${fresh ? ' is-new' : ''}">
    ${visual(ev, ents)}
    <div class="body">
      ${fresh || relBadge(ev) ? `<div class="kicker">${fresh ? '<span class="dot" title="Nouveau depuis votre dernière visite"></span>' : ''}${relBadge(ev)}</div>` : ''}
      <h3><a class="stretch" href="#/e/${encodeURIComponent(ev.id)}">${esc(title(ev))}</a></h3>
      ${why ? `<p class="why">${esc(why)}</p>` : ''}
      <div class="pills">${pills(ev.entity_ids, ents, 3, skip)}</div>
    </div>
  </article>`;
}

// ---- Bandeau Vigie : segments répétés deux fois pour un défilement continu (le second exemplaire est masqué aux lecteurs d'écran) ----
function bandItem(it) {
  const value = typeof it.value === 'number' ? nf.format(it.value) : it.value ?? '';
  const dir = it.delta == null ? '' : it.delta > 0 ? 'up' : it.delta < 0 ? 'down' : 'flat';
  const delta = it.delta == null ? '' : `<span class="bd ${dir}">${esc(signed(it.delta, it.unit === 'pt' ? ' pt' : ' %'))}</span>`;
  const when = it.kind === 'agenda' ? fmtDate(it.at) : ['match', 'race'].includes(it.kind) && !it.value ? `${fmtDate(it.at)} ${parisTime(it.at)}` : '';
  const inner = `<span class="bdot"></span><span class="bl">${esc(it.label)}</span>${value !== '' ? `<span class="bv">${esc(value)}</span>` : ''}${delta}${when ? `<span class="bt">${esc(when)}</span>` : ''}`;
  const href = typeof it.href === 'string' && it.href.startsWith('#/') ? it.href : null;
  const cls = `bi u-${safeType(it.universe)} k-${safeType(it.kind)}`;
  return href ? `<a class="${cls}" href="${esc(href)}">${inner}</a>` : `<span class="${cls}">${inner}</span>`;
}

export function bandHtml(band) {
  const items = band?.items ?? [];
  if (!items.length) return '';
  const run = items.map(bandItem).join('');
  return `<div class="band-track"><div class="band-run">${run}</div><div class="band-run" aria-hidden="true" inert>${run}</div></div>`;
}

// ---- Panneau d'aperçu d'une entité ----
export function followButton(id, followed) {
  return `<button type="button" class="btn follow" data-action="follow" data-entity="${esc(id)}" aria-pressed="${followed}">${followed ? '✓ Suivi' : '+ Suivre'}</button>`;
}

export function panelHtml(page, ents, state, now = Date.now()) {
  const e = page.entity;
  const facts = (page.facts ?? []).slice(0, 4).map((f) => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value)}</dd></div>`).join('');
  const news = (page.events ?? []).slice(0, 3)
    .map((x) => `<li><a href="#/e/${encodeURIComponent(x.id)}">${esc(x.title_fr || x.title)}</a><span class="meta">${esc(timeAgo(x.date, now))}</span></li>`).join('');
  const rels = [...new Set((page.relations ?? []).map((r) => r.id))].filter((id) => ents.has(id)).slice(0, 6).map((id) => pill(id, ents)).join('');
  const quote = page.quote ? `<p class="pquote mono">${esc(nf.format(page.quote.price))} ${esc(page.quote.currency)} <span class="bd ${page.quote.change_pct > 0 ? 'up' : page.quote.change_pct < 0 ? 'down' : 'flat'}">${esc(signed(page.quote.change_pct ?? 0, ' %'))}</span></p>` : '';
  return `<div class="panel-in">
    <button type="button" class="panel-close" data-action="close-panel" aria-label="Fermer">×</button>
    ${entityVisual({ ...e, image: page.image }, 'pvisual')}
    <p class="ptype">${esc(e.type_label)}</p>
    <h2 id="panel-title">${esc(e.name)}</h2>
    ${page.description ? `<p class="desc">${esc(page.description)}</p>` : ''}
    ${quote}
    ${facts ? `<dl class="facts">${facts}</dl>` : ''}
    ${news ? `<h3 class="cmp">Dernières actualités</h3><ul class="plist">${news}</ul>` : '<p class="meta">Aucune actualité ces 30 derniers jours.</p>'}
    ${rels ? `<h3 class="cmp">Liens</h3><div class="pills">${rels}</div>` : ''}
    <div class="pactions">${followButton(e.id, state.follows.includes(e.id))}<a class="btn primary" href="${entityHref(e.id)}">Ouvrir la fiche →</a></div>
  </div>`;
}

// ---- Chaînes « Concernés » ----
const node = (id, ents) => (ents.has(id)
  ? `<a class="cn t-${safeType(ents.get(id).type)}" href="${entityHref(id)}">${esc(ents.get(id).name)}</a>`
  : `<span class="cn">${esc(id)}</span>`);

export function chains(concerned, ents) {
  if (!concerned?.length) return '';
  return `<ol class="chains">${concerned.map((steps) => `<li>${node(steps[0].from, ents)}${steps
    .map((s) => `<span class="via">${esc(s.label)}</span>${node(s.to, ents)}`).join('')}</li>`).join('')}</ol>`;
}

// ---- Constellation : l'entité au centre, ses voisins autour (relations écrites d'abord) ----
export function constellation(page, ents, max = 12) {
  const seen = new Set();
  const around = (page.relations ?? []).filter((r) => ents.has(r.id) && !seen.has(r.id) && seen.add(r.id)).slice(0, max);
  if (!around.length) return '';
  const c = 200;
  const nodes = around.map((r, i) => {
    const a = (2 * Math.PI * i) / around.length - Math.PI / 2;
    const rad = i % 2 ? 150 : 128;
    const x = (c + Math.cos(a) * rad).toFixed(1);
    const y = (c + Math.sin(a) * rad).toFixed(1);
    const name = ents.get(r.id).name;
    return `<a href="${entityHref(r.id)}" class="cnode t-${safeType(r.type)}${r.origin === 'cooccurrence' ? ' co' : ''}" style="--i:${i}"><title>${esc(r.label)}</title>`
      + `<line x1="${c}" y1="${c}" x2="${x}" y2="${y}"/><circle cx="${x}" cy="${y}" r="7"/>`
      + `<text x="${x}" y="${(Number(y) + 22).toFixed(1)}" text-anchor="middle">${esc(name.length > 18 ? `${name.slice(0, 17)}…` : name)}</text></a>`;
  }).join('');
  return `<svg class="constellation" viewBox="0 0 400 400" role="img" aria-label="Entités liées à ${esc(page.entity.name)}">${nodes}`
    + `<circle cx="${c}" cy="${c}" r="16" class="ccenter"/><text x="${c}" y="${c + 38}" text-anchor="middle" class="ccname">${esc(page.entity.name)}</text></svg>`;
}
