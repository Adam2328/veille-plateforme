async function get(path) {
  const r = await fetch(path, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${path} : HTTP ${r.status}`);
  return r.json();
}

export const loadHome = () => get('data/home.json');
export const loadDomain = (id) => get(`data/domains/${encodeURIComponent(id)}.json`);
export const loadQuotes = () => get('data/quotes.json');
export const loadFootball = () => get('data/football.json');
export const loadF1 = () => get('data/f1.json');
export const loadSearch = () => get('data/search.json');
