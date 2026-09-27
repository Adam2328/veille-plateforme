// Recherche et archives côté navigateur, sur l'index data/search.json (30 jours).

export const normalize = (s) =>
  String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const haystack = (e) => normalize(`${e.title} ${e.retenir} ${e.entities.join(' ')}`);

export function searchEvents(index, query, { domain = '', days = 0 } = {}, now = Date.now()) {
  if (!index) return [];
  const words = normalize(query).split(' ').filter(Boolean);
  const since = days ? now - days * 86400e3 : -Infinity;
  return index.events
    .filter((e) => (!domain || e.domain === domain) && Date.parse(e.date) >= since)
    .filter((e) => { const h = ` ${haystack(e)} `; return words.every((w) => h.includes(w)); })
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
}

export function followedEvents(index, state, limit = 8) {
  if (!index || !state.follows.length) return [];
  const wanted = new Set(state.follows.map(normalize));
  return index.events
    .filter((e) => e.entities.some((x) => wanted.has(normalize(x))))
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))
    .slice(0, limit);
}
