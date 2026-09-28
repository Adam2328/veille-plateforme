// Illustrations générées (SVG, sans coût) pour les informations sans photo et les entités sans image.
// Déterministes : même graine, même dessin. Couleurs lues dans les variables CSS de l'univers (--u-<univers>).
import { esc } from './blocks.js';

const hash = (s) => {
  let h = 2166136261;
  for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
};
const safeId = (s) => (/^[a-z_-]+$/.test(s) ? s : 'x');

// Pictogrammes 24 × 24, tracés au trait.
const ICONS = {
  spark: 'M12 2v6M12 16v6M2 12h6M16 12h6M5 5l4 4M15 15l4 4M19 5l-4 4M9 15l-4 4',
  chart: 'M3 20h18M5 16l4-5 4 3 6-8M15 6h4v4',
  bank: 'M3 9l9-5 9 5M5 9v9M9 9v9M15 9v9M19 9v9M3 20h18',
  coins: 'M12 3a7 3 0 1 0 0.01 0M5 6v5c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  gavel: 'M14 4l6 6M11 7l6 6M8 10l6-6M4 20l7-7M3 21h8',
  target: 'M12 3a9 9 0 1 0 0.01 0M12 7a5 5 0 1 0 0.01 0M12 11a1 1 0 1 0 0.01 0',
  globe: 'M12 3a9 9 0 1 0 0.01 0M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18',
  ballot: 'M4 10h16v10H4zM8 10V4h8v6M10 15h4',
  drop: 'M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z',
  atom: 'M12 12a1 1 0 1 0 0.01 0M4 12c0-3 3.6-5 8-5s8 2 8 5-3.6 5-8 5-8-2-8-5zM8 5c2.6-1.5 6.4 2.1 8.4 5.6s2.2 7.4-.4 8.9-6.4-2.1-8.4-5.6S5.4 6.5 8 5z',
  trophy: 'M7 4h10v5a5 5 0 0 1-10 0zM7 6H3c0 3 2 4 4 4M17 6h4c0 3-2 4-4 4M12 14v4M8 21h8',
  flag: 'M5 21V4M5 4h12l-2 4 2 4H5',
  arrows: 'M4 8h14l-3-3M20 16H6l3 3',
  pulse: 'M3 12h4l2-5 4 10 2-5h6',
  person: 'M12 12a4 4 0 1 0 0.01 0M4 21c1-4 4-6 8-6s7 2 8 6',
  node: 'M12 12a3 3 0 1 0 0.01 0M5 5l4.5 4.5M19 5l-4.5 4.5M5 19l4.5-4.5M19 19l-4.5-4.5',
};
const KIND_ICON = {
  model_release: 'spark', product_launch: 'spark', research: 'atom', funding_acquisition: 'coins', m_and_a: 'coins',
  earnings: 'chart', markets: 'chart', macro_data: 'chart', central_bank: 'bank', regulation: 'gavel', sanctions: 'gavel',
  conflict: 'target', humanitarian: 'target', diplomacy: 'globe', alliance: 'globe', election: 'ballot', institutions: 'ballot',
  commodities: 'drop', crypto: 'coins', result: 'trophy', final: 'trophy', grand_slam: 'trophy', major_final: 'trophy',
  world_title: 'trophy', championship: 'trophy', race_result: 'flag', qualifying: 'flag', transfer: 'arrows', trade: 'arrows',
  injury: 'pulse', record: 'pulse',
  company: 'chart', country: 'globe', org: 'globe', person: 'person', player: 'person', driver: 'flag', team: 'trophy',
  competition: 'trophy', etf: 'chart', index: 'chart', crypto_asset: 'coins', rate: 'chart', commodity: 'drop',
  sector: 'node', tech: 'atom', ai_model: 'spark', central_bank_type: 'bank', topic: 'node',
};

function pattern(h) {
  switch (h % 4) {
    case 0: // lignes d'horizon et astre
      return `<circle cx="${220 + (h % 60)}" cy="${60 + (h % 30)}" r="${26 + (h % 18)}" class="art-sun"/>${
        [0, 1, 2, 3, 4, 5].map((i) => `<path d="M0 ${118 + i * 11}H320" class="art-line" style="opacity:${(0.5 - i * 0.07).toFixed(2)}"/>`).join('')}`;
    case 1: // anneaux concentriques
      return [1, 2, 3, 4, 5].map((i) => `<circle cx="${240 - (h % 80)}" cy="${90 + (h % 40) - 20}" r="${i * 24}" class="art-line"/>`).join('');
    case 2: // grille de points
      return Array.from({ length: 10 }, (_, x) => Array.from({ length: 6 }, (__, y) =>
        `<circle cx="${20 + x * 32}" cy="${18 + y * 30}" r="${1 + ((h >> (x + y)) & 1) * 1.6}" class="art-dot"/>`).join('')).join('');
    default: // relèvements (rose des vents)
      return Array.from({ length: 9 }, (_, i) => {
        const a = (Math.PI / 8) * i + (h % 10) / 20;
        return `<path d="M${260} ${170}L${(260 - Math.cos(a) * 260).toFixed(1)} ${(170 - Math.sin(a) * 260).toFixed(1)}" class="art-line"/>`;
      }).join('');
  }
}

export function artFor(seed, universe, label = '', kind = '') {
  const h = hash(seed);
  const u = safeId(universe);
  const icon = ICONS[KIND_ICON[kind] ?? 'node'];
  const text = String(label ?? '').slice(0, 28);
  const gid = `g${h.toString(36)}`;
  return `<svg class="art" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${esc(text)}" style="--u:var(--u-${u})">`
    + `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" class="art-a"/><stop offset="1" class="art-b"/></linearGradient></defs>`
    + `<rect width="320" height="180" fill="url(#${gid})"/>${pattern(h)}`
    + `<g transform="translate(24 ${text ? 104 : 128}) scale(1.5)"><path d="${icon}" class="art-icon"/></g>`
    + (text ? `<text x="24" y="160" class="art-label">${esc(text)}</text>` : '')
    + '</svg>';
}

// Illustration d'une entité sans image : même principe, initiale en grand.
export function artEntity(entity) {
  const u = entity.universes?.[0] ?? 'x';
  const initial = String(entity.name ?? '?').trim().charAt(0).toUpperCase();
  const kind = entity.type === 'crypto' ? 'crypto_asset' : entity.type === 'central_bank' ? 'central_bank_type' : entity.type;
  return artFor(entity.id, u, '', kind).replace('</svg>', `<text x="160" y="118" text-anchor="middle" class="art-initial">${esc(initial)}</text></svg>`);
}
