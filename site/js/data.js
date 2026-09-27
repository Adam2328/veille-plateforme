async function get(path) {
  const r = await fetch(path, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${path} : HTTP ${r.status}`);
  return r.json();
}

const enc = encodeURIComponent;

export const loadHome = () => get('data/home.json');
export const loadDomain = (id) => get(`data/domains/${enc(id)}.json`);
export const loadUniverse = (id) => get(`data/universes/${enc(id)}.json`);
export const loadEntityIndex = () => get('data/entities/index.json');
// Identifiant « type:slug » → data/entities/<type>/<slug>.json
export const loadEntity = (id) => {
  const [type, slug] = String(id).split(':');
  return get(`data/entities/${enc(type)}/${enc(slug)}.json`);
};
export const loadBand = () => get('data/band.json');
export const loadQuotes = () => get('data/quotes.json');
export const loadFootball = () => get('data/football.json');
export const loadF1 = () => get('data/f1.json');
export const loadSearch = () => get('data/search.json');
