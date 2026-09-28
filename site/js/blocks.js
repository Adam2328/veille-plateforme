// Utilitaires d'affichage et blocs de données réutilisés par les vues (cours, matchs, classements, F1, couches, liens).

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

export const plural = (n, word) => `${n} ${word}${n > 1 ? 's' : ''}`;
export const enc = encodeURIComponent;

export function timeAgo(iso, now = Date.now()) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '';
  const m = Math.max(0, Math.round((now - t) / 60000));
  if (m < 60) return `il y a ${m} min`;
  const h = Math.round(m / 60);
  return h < 24 ? `il y a ${h} h` : `il y a ${Math.round(h / 24)} j`;
}

const PARIS = 'Europe/Paris';
const valid = (iso) => !Number.isNaN(new Date(iso).getTime());
export const fmtDate = (iso) => (valid(iso) ? new Date(iso).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', timeZone: PARIS }) : '');
export const fmtDateTime = (iso) => (valid(iso) ? new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: PARIS }) : '');
export const parisDay = (iso) => (valid(iso) ? new Date(iso).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', timeZone: PARIS }) : '');
export const parisTime = (iso) => (valid(iso) ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: PARIS }) : '');
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export const nf = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 });
export const signed = (n, suffix) => `${n > 0 ? '+' : ''}${nf.format(n)}${suffix}`;

// ---- Marchés ----
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

// ---- Football ----
const compName = (football, code) => football?.competitions?.find((c) => c.code === code)?.name ?? code;
const fmtKickoff = (iso) => (valid(iso) ? new Date(iso).toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: PARIS }) : '');

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
  return `<div class="table-wrap"><table class="standings"><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>Diff</th><th>Pts</th><th>Forme</th></tr></thead><tbody>${rows}</tbody></table></div>${comp.stale ? '<p class="meta">Classement non actualisé.</p>' : ''}${link ? `<p class="meta">${link}</p>` : ''}`;
}

// ---- F1 : week-end de Grand Prix (heure de Paris), dernier Grand Prix, championnats ----
export function f1Weekend(next) {
  if (!next || !next.sessions?.length) return '';
  const days = [];
  for (const s of next.sessions) {
    const day = parisDay(s.start);
    if (!days.length || days[days.length - 1].day !== day) days.push({ day, sessions: [] });
    days[days.length - 1].sessions.push(s);
  }
  return `<div class="f1-weekend">${days.map((d) => `<div><h3 class="cmp">${esc(capital(d.day))}</h3><ul class="matches">${d.sessions
    .map((s) => `<li class="match next"><span class="mh">${esc(s.name)}</span><span class="ms">${esc(parisTime(s.start))}</span><span class="ma"></span></li>`).join('')}</ul></div>`).join('')}</div>`;
}

const table = (rows, cols) =>
  `<div class="table-wrap"><table class="standings"><thead><tr>${cols.map(([, t]) => `<th>${t}</th>`).join('')}</tr></thead><tbody>${rows
    .map((r) => `<tr>${cols.map(([k]) => `<td${k === 'driver' || k === 'team' ? ' class="tn"' : ''}>${esc(r[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;

export function f1Strip(f1) {
  if (!f1) return '';
  const race = f1.next?.sessions?.find((s) => s.name === 'Course');
  const next = f1.next ? `<div><h3 class="cmp">Prochain Grand Prix</h3><p>${esc(f1.next.name)}${race ? ` · course ${esc(parisDay(race.start))} à ${esc(parisTime(race.start))}` : ''}</p></div>` : '';
  const winner = f1.last?.race?.[0];
  const last = winner ? `<div><h3 class="cmp">Dernier vainqueur</h3><p>${esc(winner.driver)} (${esc(winner.team)}) · ${esc(f1.last.name)}</p></div>` : '';
  return next || last ? `<div class="strip">${next}${last}</div>` : '';
}

export function f1Tables(f1) {
  if (!f1) return '';
  const last = f1.last?.race?.length
    ? `<h3 class="cmp">Dernier Grand Prix : ${esc(f1.last.name)}</h3>${table(f1.last.race.slice(0, 10), [['position', '#'], ['driver', 'Pilote'], ['team', 'Écurie'], ['result', 'Temps'], ['points', 'Pts']])}`
    : '';
  const drivers = f1.drivers?.length ? `<h3 class="cmp">Championnat pilotes</h3>${table(f1.drivers.slice(0, 10), [['position', '#'], ['driver', 'Pilote'], ['team', 'Écurie'], ['wins', 'V'], ['points', 'Pts']])}` : '';
  const teams = f1.constructors?.length ? `<h3 class="cmp">Championnat constructeurs</h3>${table(f1.constructors, [['position', '#'], ['team', 'Écurie'], ['wins', 'V'], ['points', 'Pts']])}` : '';
  return `${last}${drivers}${teams}`;
}

// ---- Couches Faits / Analyse / Interprétation / Incertitude ----
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

// `names` : identifiant d'entité → nom (Gemini recopie parfois les identifiants candidats dans « actifs »).
export function layersBlock(layers, domain, names = {}) {
  if (!layers) return '';
  const titles = LAYER_TITLES[domain] ?? {};
  const label = (b) => names[b] ?? b;
  const sections = LAYER_SECTIONS
    .filter(([key]) => Array.isArray(layers[key]) && layers[key].length)
    .map(([key, title]) => `<section class="layer layer-${key}"><h3>${titles[key] ?? title}</h3><ul>${layers[key].map((b) => `<li>${esc(label(b))}</li>`).join('')}</ul></section>`);
  if (!sections.length) return '';
  const note = LAYER_NOTES[domain] ?? 'Synthèse générée automatiquement à partir des sources.';
  return `<div class="layers">${sections.join('')}<p class="meta">${note}</p></div>`;
}

// Liens « Approfondir » déclarés dans la config des rubriques (ex. pages Flashscore des tournois).
export function linksBlock(links) {
  const safe = (links ?? []).map((l) => ({ title: l.title, url: safeUrl(l.url) })).filter((l) => l.url && l.url.startsWith('https://'));
  if (!safe.length) return '';
  return `<ul class="links">${safe.map((l) => `<li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.title)}</a></li>`).join('')}</ul>`;
}
