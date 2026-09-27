"""Rattachement des événements aux entités du catalogue par alias (mot entier)."""
import re

_Pattern = tuple[re.Pattern | None, dict[str, list[str]]]


def _pattern(keys: dict, flags: int) -> re.Pattern | None:
    if not keys:
        return None
    alternatives = "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))   # le plus long d'abord
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", flags)


def build_matcher(catalog: dict, universe: str | None = None, domain: str | None = None) -> dict[str, _Pattern]:
    """Deux expressions : alias en minuscules (insensibles à la casse) et alias « = » (casse exacte).

    `link_in` restreint une entité à des univers, `link_domains` à des rubriques (ex. clubs : Football seulement).
    """
    loose, strict = {}, {}
    for eid, e in catalog.items():
        if universe and e.get("link_in") and universe not in e["link_in"]:
            continue
        if domain and e.get("link_domains") and domain not in e["link_domains"]:
            continue
        for alias in map(str, e["aliases"]):
            if alias.startswith("="):
                strict.setdefault(alias[1:], []).append(eid)
            else:
                loose.setdefault(alias.lower(), []).append(eid)
    return {"loose": (_pattern(loose, re.IGNORECASE), loose), "strict": (_pattern(strict, 0), strict)}


def link(text: str, matcher: dict[str, _Pattern]) -> list[str]:
    first = {}
    for mode, (pattern, table) in matcher.items():
        if pattern is None:
            continue
        for m in pattern.finditer(text):
            key = m.group(0).lower() if mode == "loose" else m.group(0)
            for eid in table.get(key, []):
                first[eid] = min(first.get(eid, m.start()), m.start())
    return sorted(first, key=lambda eid: (first[eid], eid))


def event_text(ev: dict) -> str:
    return " ".join([ev["title"], *(f"{i['title']} {i['snippet'][:300]}" for i in ev["items"])])


def final_ids(ev: dict) -> list[str]:
    """Candidats confirmés par le LLM, plus ceux qui ne lui ont jamais été proposés (catalogue enrichi depuis)."""
    offered, kept = set(ev.get("llm_offered", [])), set(ev.get("llm_entities", []))
    return [c for c in ev.get("candidates", []) if c in kept or c not in offered]
