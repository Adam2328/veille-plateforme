async function get(path) {
  const r = await fetch(path, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${path} : HTTP ${r.status}`);
  return r.json();
}

export const loadHome = () => get('data/home.json');
export const loadDomain = (id) => get(`data/domains/${encodeURIComponent(id)}.json`);
