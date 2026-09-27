import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from .agenda import fetch_points
from .alerts import prune_sent, select_alerts, send_ntfy
from .band import build_band
from .candidates import top_candidates, update_candidates
from .catalog import football_teams
from .cluster import cluster, merge_events
from .collect import collect_source, fetch_bytes
from .config import ROOT, load_config
from .enrich import event_image, is_relevant
from .entity_pages import build_entity_pages
from .f1_data import collect_f1
from .f1_data import fetch_json as fetch_f1
from .facts import fetch_json as fetch_facts
from .facts import load_facts, refresh_facts
from .football_data import collect_football, fetch_fd
from .graph import adjacency, build_edges, concerned
from .linker import build_matcher, event_text, final_ids, link
from .normalize import dedupe, excluded, normalize, recent
from .publish import (build_domain, build_home, build_universe, publish, publish_entities, publish_football,
                      publish_json, publish_quotes, write_if_changed)
from .quotes import collect_quotes, fetch_relay
from .reliability import classify
from .score import assign_levels, importance
from .search import FULL_DAYS, build_index
from .store import append, load_recent
from .summarize import fingerprint, gemini_call, summarize
from .timeutil import iso, now_utc


def collect_domain(dom: dict, g: dict, now: datetime, fetch: Callable[[str], bytes]) -> tuple[list, list]:
    items, health = [], []
    for src in dom["sources"]:
        source = {**src, "domain": dom["id"]}
        raws, h = collect_source(source, fetch)
        health.append(h)
        items += [i for i in (normalize(r, source, g.get("publishers")) for r in raws)
                  if not excluded(i, dom.get("exclude", []))
                  and (not dom.get("relevance") or is_relevant(f"{i['title']} {i['snippet']}", dom))]
    return recent(items, now, g["collect"]["max_age_hours"]), health


def rescore(events: list, dom: dict, g: dict, now: datetime) -> list:
    out = []
    for ev in events:
        label, reason = classify(ev["items"], now, dom)
        scored = {**ev, "reliability": label, "reliability_reason": reason}
        out.append({**scored, "importance": importance(scored, dom, g, now)})
    return assign_levels(out, dom)


def annotate(ev: dict, universe: str | None, matcher: dict | None) -> dict:
    """Univers, entités candidates et photo : recalculés à chaque cycle à partir des articles de l'événement."""
    if universe is None or matcher is None:
        return ev
    image = event_image(ev)
    return {**ev, "universe": universe, "candidates": link(event_text(ev), matcher), **({"image": image} if image else {})}


def add_summaries(events: list, dom: dict, g: dict, call: Callable[[str], str] | None) -> tuple[list, set, list]:
    need = sorted((e for e in events if e["level"] in (1, 2) and e.get("summary_fp") != fingerprint(e)),
                  key=lambda e: -e["importance"])[: g["ai"]["max_events_per_run"]]
    results, errors = summarize(need, call, profile=dom.get("summary_profile", "default"))
    done, touched = {}, set()
    for e in need:
        summary, mode = results[e["id"]]
        if mode == "extractif" and e.get("summary_mode") == "llm":
            continue                        # échec ou quota : on garde le résumé LLM, nouvel essai au cycle suivant
        summary = dict(summary)
        layers = summary.pop("layers", None)
        title_fr = summary.pop("title_fr", None)
        chosen = summary.pop("entities_llm", None)
        unknown = summary.pop("unknown", [])
        upd = {**e, "summary": summary, "summary_mode": mode, "layers": layers,
               "summary_fp": fingerprint(e) if mode == "llm" else None}
        if mode == "llm":
            offered = e.get("candidates", [])
            upd = {**upd, "title_fr": title_fr, "llm_offered": offered,
                   "llm_entities": offered if chosen is None else chosen, "unknown": unknown}
        done[e["id"]] = upd
        if (summary, mode, layers, upd.get("title_fr")) != (e.get("summary"), e.get("summary_mode"), e.get("layers"), e.get("title_fr")):
            touched.add(e["id"])
    return [done.get(e["id"], e) for e in events], touched, errors


def _tally(report: dict, events: list, errors: list) -> None:
    for e in events:
        if e["level"] >= 1:
            report["events"][str(e["level"])] += 1
            report["reliability"][e["reliability"]] = report["reliability"].get(e["reliability"], 0) + 1
        if e.get("summary_mode") in ("llm", "extractif"):
            report["ai"][e["summary_mode"]] += 1
    report["ai"]["errors"] += errors


def _previous(root: Path, name: str) -> dict | None:
    path = root / "site" / "data" / name
    try:
        return json.loads(path.read_text("utf-8")) if path.exists() else None
    except ValueError:
        return None


def _import_agendas(cfg: dict, only: list[str] | None, fetch_agenda: Callable[[str], list[str]],
                    health: list) -> dict:
    agendas = {}
    for dom in cfg["domains"].values():
        if not dom.get("agenda_url") or (only is not None and dom["id"] not in only):
            continue
        try:
            agendas[dom["id"]] = fetch_agenda(dom["agenda_url"])
            health.append({"source": f"agenda:{dom['id']}", "ok": True, "count": len(agendas[dom["id"]]), "error": None})
        except Exception as exc:  # ponytail: en cas d'échec l'agenda importé disparaît jusqu'au cycle suivant
            health.append({"source": f"agenda:{dom['id']}", "ok": False, "count": 0, "error": f"{type(exc).__name__}: {exc}"})
    return agendas


def _send_alerts(root: Path, cfg: dict, by_domain: dict, now: datetime, topic: str,
                 post: Callable[..., object], health: list) -> int:
    path = root / "data" / "alerts.json"
    sent = prune_sent(_read_json(path) or {}, now)
    events = [e for evs in by_domain.values() for e in evs]
    count, error = 0, None
    for e in select_alerts(events, cfg["domains"], cfg["global"], sent, now):
        try:
            send_ntfy(topic, e, cfg["domains"][e["domain"]], cfg["global"], post)
            sent[e["id"]] = iso(now)       # enregistré seulement si l'envoi a réussi : sinon, nouvel essai au cycle suivant
            count += 1
        except Exception as exc:  # ntfy injoignable : ne doit jamais arrêter le cycle
            error = f"{type(exc).__name__}: {exc}"
    health.append({"source": "alerts:ntfy", "ok": error is None, "count": count, "error": error})
    write_if_changed(path, sent)
    return count


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text("utf-8")) if path.exists() else None
    except ValueError:
        return None


def _with_concerned(ev: dict, adj: dict, catalog: dict, g: dict) -> dict:
    # Un pays n'ouvre une chaîne que pour un événement économique ou un conflit : sinon « Chine → terres rares »
    # s'accroche à n'importe quelle actualité (constaté sur les données réelles du 27/09/2026).
    economic = ev.get("kind") in g.get("links", {}).get("country_start_kinds", [])
    starts = [i for i in ev.get("entity_ids", []) if economic or not i.startswith("country:")]
    if ev.get("level") in (1, 2) and starts:
        chains = concerned(starts, adj, catalog)
        if chains:
            return {**ev, "concerned": chains}
    return ev


def _facts(root: Path, catalog: dict, now: datetime, only: list[str] | None, fetch: Callable, health: list) -> dict:
    if only is not None:
        return load_facts(root)
    facts, entry = refresh_facts(root, catalog, now, fetch)
    if entry:
        health.append(entry)
    return facts


def _update_candidates(root: Path, unknown: list, catalog: dict, now: datetime) -> dict:
    path = root / "data" / "candidates.json"
    everything = build_matcher(catalog)
    data = update_candidates((_read_json(path) or {}).get("candidates", {}), unknown,
                             lambda name: bool(link(name, everything)), now)
    write_if_changed(path, {"candidates": data})
    return data


def _linked_pct(by_domain: dict) -> int:
    shown = [e for evs in by_domain.values() for e in evs if e.get("level", 0) >= 1 and "candidates" in e]
    return round(100 * sum(1 for e in shown if e.get("entity_ids")) / len(shown)) if shown else 0


def run(root: Path = ROOT, now: datetime | None = None, only: list[str] | None = None,
        call: Callable[[str], str] | None = None, fetch: Callable[[str], bytes] = fetch_bytes,
        quote_fetch: Callable[[str], dict] = fetch_relay,
        agenda_fetch: Callable[[str], list[str]] = fetch_points,
        football_token: str | None = None,
        football_fetch: Callable[[str, str], dict] = fetch_fd,
        f1_fetch: Callable[[str], dict] = fetch_f1,
        ntfy_topic: str | None = None,
        ntfy_post: Callable[..., object] = requests.post,
        facts_fetch: Callable[..., object] = fetch_facts) -> dict:
    now = now or now_utc()
    cfg = load_config(root)
    g, universes = cfg["global"], cfg["universes"]
    catalog = {**cfg["catalog"], **football_teams(_previous(root, "football.json"), cfg["catalog"], universes)}
    uni_of = {d: u for u, uni in universes.items() for d in uni["domains"]}
    matchers = {d: build_matcher(catalog, u, d) for d, u in uni_of.items()}
    stored = load_recent(root, now)
    report = {"collected": 0, "new_items": 0, "events": {"1": 0, "2": 0, "3": 0}, "reliability": {},
              "ai": {"llm": 0, "extractif": 0, "errors": []}, "quotes": {"ok": 0, "failed": 0},
              "football": {"ok": 0, "failed": 0}, "f1": {"ok": 0, "failed": 0}, "alerts": 0,
              "entities": {"linked_pct": 0, "candidates": 0}, "sources_failed": []}
    health, by_domain, unknown = [], {}, []
    for dom in sorted(cfg["domains"].values(), key=lambda d: d["order"]):
        mine = [e for e in stored if e["domain"] == dom["id"]]
        changed, merges = set(), []
        if only is None or dom["id"] in only:
            items, h = collect_domain(dom, g, now, fetch)
            health += h
            fresh = dedupe(items, {i["id"] for e in mine for i in e["items"]})
            report["collected"] += len(items)
            report["new_items"] += len(fresh)
            mine, changed = cluster(fresh, mine, dom, g, now)
            mine, merges = merge_events(mine, dom, g, now)
            changed = (changed - {d["id"] for d, _ in merges}) | {sid for _, sid in merges}
        universe = uni_of.get(dom["id"])
        mine = [annotate(e, universe, matchers.get(dom["id"])) for e in mine]
        mine = rescore(mine, dom, g, now)
        mine, touched, errors = add_summaries(mine, dom, g, call)
        mine = [{**e, "entity_ids": final_ids(e)} if "candidates" in e else e for e in mine]
        unknown += [(name, dom["id"]) for e in mine if e["id"] in touched for name in e.get("unknown", [])]
        append(root, [{**d, "merged_into": sid} for d, sid in merges]          # marqueur : l'absorbé ne revient pas
               + [e for e in mine if e["id"] in changed | touched], now)
        by_domain[dom["id"]] = mine
        _tally(report, mine, errors)
    history = {e["id"]: e for e in load_recent(root, now, days=FULL_DAYS)}
    history.update({e["id"]: e for evs in by_domain.values() for e in evs})       # niveaux du cycle en cours
    facts = _facts(root, catalog, now, only, facts_fetch, health)
    adj = adjacency(build_edges(cfg["relations"], [e for f in facts.values() for e in f.get("edges", [])],
                                list(history.values()), g.get("links", {}).get("cooccurrence_min", 3)))
    by_domain = {d: [_with_concerned(e, adj, catalog, g) for e in evs] for d, evs in by_domain.items()}
    agendas = _import_agendas(cfg, only, agenda_fetch, health)
    home = build_home(cfg, by_domain, now, agendas)
    publish(root, home, [build_domain(cfg["domains"][d], evs, now, agendas.get(d)) for d, evs in by_domain.items()],
            [build_universe(u, cfg["domains"], by_domain, now, agendas) for u in universes.values()])
    if cfg["quotes"] and (only is None or "quotes" in only):
        quotes, qhealth = collect_quotes(cfg["quotes"], _previous(root, "quotes.json"), now, quote_fetch)
        publish_quotes(root, quotes)
        health += qhealth
        symbols = [h for h in qhealth if h["source"] != "quote-relay"]
        report["quotes"] = {"ok": sum(h["ok"] for h in symbols), "failed": sum(not h["ok"] for h in qhealth)}
    publish_json(root, "search", "search.json", build_index(list(history.values()), cfg["domains"], now))
    if "f1" in cfg["domains"] and (only is None or "f1-data" in only or "f1" in only):
        f1, f1health = collect_f1(_previous(root, "f1.json"), now, f1_fetch)
        if f1 is not None:
            publish_json(root, "f1", "f1.json", f1)
        health += f1health
        report["f1"] = {"ok": sum(h["ok"] for h in f1health), "failed": sum(not h["ok"] for h in f1health)}
    if cfg["football"] and (only is None or "football-data" in only):
        data, fhealth = collect_football(cfg["football"], football_token, _previous(root, "football.json"), now, football_fetch)
        if data is not None:
            publish_football(root, data)
        health += fhealth
        report["football"] = {"ok": sum(h["ok"] for h in fhealth), "failed": sum(not h["ok"] for h in fhealth)}
    if universes:
        index, pages = build_entity_pages(catalog, facts, adj, list(history.values()), _previous(root, "quotes.json"), now)
        publish_entities(root, index, pages)
        publish_json(root, "band", "band.json", build_band(_previous(root, "quotes.json"), _previous(root, "football.json"),
                                                           _previous(root, "f1.json"), home, uni_of, g, now))
    candidates = _update_candidates(root, unknown, catalog, now)
    report["entities"] = {"linked_pct": _linked_pct(by_domain), "candidates": len(candidates)}
    if ntfy_topic and g.get("alerts"):
        report["alerts"] = _send_alerts(root, cfg, by_domain, now, ntfy_topic, ntfy_post, health)
    report["sources_failed"] = [h["source"] for h in health if not h["ok"]]
    write_if_changed(root / "site" / "data" / "health.json",
                     {"checked_at": iso(now), "sources": health, "ai": report["ai"], "candidates": top_candidates(candidates)},
                     now, max_age_min=55)
    return report


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="ids des veilles à collecter, « quotes » ou « football-data » (défaut : tout)")
    ap.add_argument("--no-ai", action="store_true", help="résumés extractifs uniquement")
    args = ap.parse_args()
    call = gemini_call() if os.environ.get("GEMINI_API_KEY") and not args.no_ai else None
    report = run(only=args.only, call=call, football_token=os.environ.get("FOOTBALL_DATA_TOKEN"),
                 ntfy_topic=os.environ.get("NTFY_TOPIC"))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
