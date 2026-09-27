"""Graphe des entités : relations rédigées, faits Wikidata, co-occurrences ; chaînes « Concernés » (spec §5.5)."""
from collections import Counter, defaultdict
from itertools import combinations

from .catalog import EXPOSURE, VERBS

_TRADABLE = {"etf", "index", "commodity", "crypto", "rate"}


def cooccurrence(events: list, min_events: int = 3) -> list[dict]:
    pairs = Counter()
    for e in events:
        pairs.update(combinations(sorted(set(e.get("entity_ids", []))), 2))
    return [{"src": a, "verb": "lie_a", "dst": b, "weight": n, "origin": "cooccurrence"}
            for (a, b), n in sorted(pairs.items()) if n >= min_events]


def build_edges(relations: list, fact_edges: list, events: list, min_events: int = 3) -> list[dict]:
    curated = [{"src": s, "verb": v, "dst": d, "weight": 1, "origin": "config"} for s, v, d in relations]
    out, seen = [], set()
    for edge in [*curated, *fact_edges, *cooccurrence(events, min_events)]:
        key = (edge["src"], edge["verb"], edge["dst"])
        if key not in seen:
            seen.add(key)
            out.append(edge)
    return out


def adjacency(edges: list) -> dict[str, list[dict]]:
    adj = defaultdict(list)
    for e in edges:
        forward, backward = VERBS[e["verb"]]
        adj[e["src"]].append({"id": e["dst"], "verb": e["verb"], "label": forward, "weight": e["weight"], "origin": e["origin"]})
        adj[e["dst"]].append({"id": e["src"], "verb": e["verb"], "label": backward, "weight": e["weight"], "origin": e["origin"]})
    return dict(adj)


def _tradable(entity: dict) -> bool:
    return bool(entity.get("ticker")) or entity.get("type") in _TRADABLE


def concerned(start_ids: list[str], adj: dict, catalog: dict, limit: int = 6) -> list[list[dict]]:
    """Parcours en largeur, 2 sauts au plus, par les seuls liens d'exposition ; actifs cotés d'abord."""
    seen, chains = set(start_ids), []
    queue = [(s, []) for s in start_ids]
    while queue:
        node, steps = queue.pop(0)
        if len(steps) == 2:
            continue
        for nb in adj.get(node, []):
            if nb["verb"] not in EXPOSURE or nb["id"] in seen or nb["id"] not in catalog:
                continue
            seen.add(nb["id"])
            chain = [*steps, {"from": node, "to": nb["id"], "label": nb["label"]}]
            chains.append(chain)
            queue.append((nb["id"], chain))
    end = lambda c: catalog[c[-1]["to"]]  # noqa: E731
    return sorted(chains, key=lambda c: (not _tradable(end(c)), len(c), end(c)["name"]))[:limit]
