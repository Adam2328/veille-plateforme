import hashlib
from datetime import datetime, timedelta

from scipy.sparse import vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .enrich import detect_kind, extract_entities
from .timeutil import iso, parse

_STOP = ["le", "la", "les", "un", "une", "des", "du", "de", "et", "en", "au", "aux", "pour", "par", "sur", "dans",
         "avec", "qui", "que", "ce", "ces", "the", "an", "of", "to", "and", "in", "for", "on", "with", "is", "are",
         "as", "at", "by", "its", "it"]


def _text(it: dict) -> str:
    return f"{it['title']} {it['snippet'][:300]}"


def _event_text(ev: dict) -> str:
    return " ".join(_text(i) for i in ev["items"])


def _new_event(it: dict, dom: dict, now: datetime) -> dict:
    text = _text(it)
    return {
        "id": "ev_" + hashlib.sha1(it["id"].encode("utf-8")).hexdigest()[:12], "rev": 1, "domain": dom["id"],
        "kind": detect_kind(text, dom["kinds"]), "title": it["title"], "first_seen": iso(now), "updated_at": iso(now),
        "entities": extract_entities(text, dom["entities"]), "items": [it],
    }


def _attach(ev: dict, it: dict, dom: dict, now: datetime) -> dict:
    best = min(i["tier"] for i in ev["items"])
    grew = it["origin"] not in {i["origin"] for i in ev["items"]} or it["tier"] < best
    text = _text(it)
    return {
        **ev, "items": [*ev["items"], it],
        "entities": sorted(set(ev["entities"]) | set(extract_entities(text, dom["entities"]))),
        "title": it["title"] if it["tier"] < best else ev["title"],
        "kind": ev["kind"] if ev["kind"] != "other" else detect_kind(text, dom["kinds"]),
        "rev": ev["rev"] + (1 if grew else 0),
        "updated_at": iso(now) if grew else ev["updated_at"],
    }


def cluster(items: list, events: list, dom: dict, g: dict, now: datetime) -> tuple[list, set]:
    known = {i["id"] for e in events for i in e["items"]}
    new = sorted((i for i in items if i["id"] not in known), key=lambda i: i["published_at"])
    if not new:
        return list(events), set()

    by_id = {e["id"]: e for e in events}
    window = timedelta(hours=g["cluster"]["window_hours"])
    open_ids = [e["id"] for e in events if e["domain"] == dom["id"] and now - parse(e["updated_at"]) <= window]
    vectorizer = TfidfVectorizer(strip_accents="unicode", stop_words=_STOP, sublinear_tf=True)
    vectorizer.fit([_event_text(by_id[i]) for i in open_ids] + [_text(i) for i in new])
    vecs = {i: vectorizer.transform([_event_text(by_id[i])]) for i in open_ids}
    changed = set()

    for it in new:
        v = vectorizer.transform([_text(it)])
        best_id, best_score = None, 0.0
        if open_ids:
            sims = cosine_similarity(v, vstack([vecs[i] for i in open_ids]))[0]
            # les noms d'entités sont déjà des tokens du TF-IDF : un bonus supplémentaire faisait fusionner
            # tout ce qui cite les mêmes grands noms (constaté sur les données réelles du 26/09/2026)
            for eid, sim in zip(open_ids, sims):
                if sim > best_score:
                    best_id, best_score = eid, sim
        if best_id is not None and best_score >= g["cluster"]["threshold"]:
            by_id[best_id] = _attach(by_id[best_id], it, dom, now)
            target = best_id
        else:
            ev = _new_event(it, dom, now)
            by_id[ev["id"]] = ev
            open_ids.append(ev["id"])
            target = ev["id"]
        vecs[target] = vectorizer.transform([_event_text(by_id[target])])
        changed.add(target)
    return list(by_id.values()), changed


def _absorb(keep: dict, drop: dict, now: datetime) -> dict:
    known_ids = {i["id"] for i in keep["items"]}
    extra = [i for i in drop["items"] if i["id"] not in known_ids]
    items = [*keep["items"], *extra]
    keep_best = min(i["tier"] for i in keep["items"])
    new_origin = bool({i["origin"] for i in extra} - {i["origin"] for i in keep["items"]})
    better_tier = bool(extra) and min(i["tier"] for i in extra) < keep_best
    title = min(items, key=lambda i: (i["tier"], i["published_at"]))["title"] if better_tier else keep["title"]
    grew = new_origin or better_tier
    return {
        **keep, "items": items, "title": title,
        "entities": sorted(set(keep["entities"]) | set(drop["entities"])),
        "kind": keep["kind"] if keep["kind"] != "other" else drop["kind"],
        "first_seen": min(keep["first_seen"], drop["first_seen"]),
        "rev": keep["rev"] + (1 if grew else 0),
        "updated_at": iso(now) if grew else keep["updated_at"],
    }


def merge_events(events: list, dom: dict, g: dict, now: datetime) -> tuple[list, list]:
    """Second passage : fusionne les événements ouverts d'une veille qui racontent la même histoire.

    Au plus une fusion par événement et par cycle (limite le chaînage) ; l'événement le plus fourni survit.
    Désactivé si `cluster.merge_threshold` est absent de la config.
    """
    threshold = g["cluster"].get("merge_threshold")
    window = timedelta(hours=g["cluster"]["window_hours"])
    open_ = [e for e in events if e["domain"] == dom["id"] and now - parse(e["updated_at"]) <= window]
    if threshold is None or len(open_) < 2:
        return list(events), []
    vectorizer = TfidfVectorizer(strip_accents="unicode", stop_words=_STOP, sublinear_tf=True)
    sims = cosine_similarity(vectorizer.fit_transform([_event_text(e) for e in open_]))
    pairs = sorted(((sims[i][j], i, j) for i in range(len(open_)) for j in range(i + 1, len(open_))
                    if sims[i][j] >= threshold), reverse=True)
    by_id = {e["id"]: e for e in events}
    used, merges = set(), []
    for _, i, j in pairs:
        if i in used or j in used:
            continue
        a, b = open_[i], open_[j]
        keep, drop = (a, b) if len(a["items"]) >= len(b["items"]) else (b, a)
        by_id[keep["id"]] = _absorb(keep, drop, now)
        del by_id[drop["id"]]
        merges.append((drop, keep["id"]))
        used |= {i, j}
    return list(by_id.values()), merges
