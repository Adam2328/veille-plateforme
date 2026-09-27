// Recherche côté navigateur : actualités (data/search.json, 30 jours) et entités (data/entities/index.json).

export const normalize = (s) =>
  String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const haystack = (e) => normalize(`${e.title} ${e.title_fr ?? ''} ${e.retenir} ${e.entities.join(' ')}`);

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
  const wanted = new Set(state.follows);
  return index.events
    .filter((e) => (e.entity_ids ?? []).some((x) => wanted.has(x)))
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))
    .slice(0, limit);
}

// Entités dont le nom ou un alias commence par la requête (mots entiers ou préfixe), groupées par type.
export function searchEntities(entityIndex, query, perType = 8) {
  const q = normalize(query);
  if (!entityIndex || !q) return [];
  const hit = (e) => [e.name, ...e.aliases].some((a) => { const n = normalize(a); return n.startsWith(q) || ` ${n}`.includes(` ${q}`); });
  const byType = new Map();
  for (const e of entityIndex.entities.filter(hit).sort((a, b) => b.n30 - a.n30 || a.name.localeCompare(b.name, 'fr'))) {
    if (!byType.has(e.type)) byType.set(e.type, []);
    if (byType.get(e.type).length < perType) byType.get(e.type).push(e);
  }
  return [...byType].map(([type, items]) => ({ type, label: entityIndex.types?.[type] ?? type, items }));
}
