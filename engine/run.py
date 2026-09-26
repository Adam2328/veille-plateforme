import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .agenda import fetch_points
from .cluster import cluster
from .collect import collect_source, fetch_bytes
from .config import ROOT, load_config
from .enrich import is_relevant
from .normalize import dedupe, excluded, normalize, recent
from .publish import build_domain, build_home, publish, publish_quotes, write_if_changed
from .quotes import collect_quotes, fetch_relay
from .reliability import classify
from .score import assign_levels, importance
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
        label, reason = classify(ev["items"], now)
        scored = {**ev, "reliability": label, "reliability_reason": reason}
        out.append({**scored, "importance": importance(scored, dom, g, now)})
    return assign_levels(out, dom)


def add_summaries(events: list, dom: dict, g: dict, call: Callable[[str], str] | None) -> tuple[list, set, list]:
    need = sorted((e for e in events if e["level"] in (1, 2) and e.get("summary_fp") != fingerprint(e)),
                  key=lambda e: -e["importance"])[: g["ai"]["max_events_per_run"]]
    results, errors = summarize(need, call, profile=dom.get("summary_profile", "default"))
    done, touched = {}, set()
    for e in need:
        summary, mode = results[e["id"]]
        summary = dict(summary)
        layers = summary.pop("layers", None)
        done[e["id"]] = {**e, "summary": summary, "summary_mode": mode, "layers": layers,
                         "summary_fp": fingerprint(e) if mode == "llm" else None}
        if (summary, mode, layers) != (e.get("summary"), e.get("summary_mode"), e.get("layers")):
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


def _previous_quotes(root: Path) -> dict | None:
    path = root / "site" / "data" / "quotes.json"
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


def run(root: Path = ROOT, now: datetime | None = None, only: list[str] | None = None,
        call: Callable[[str], str] | None = None, fetch: Callable[[str], bytes] = fetch_bytes,
        quote_fetch: Callable[[str], dict] = fetch_relay,
        agenda_fetch: Callable[[str], list[str]] = fetch_points) -> dict:
    now = now or now_utc()
    cfg = load_config(root)
    g = cfg["global"]
    stored = load_recent(root, now)
    report = {"collected": 0, "new_items": 0, "events": {"1": 0, "2": 0, "3": 0}, "reliability": {},
              "ai": {"llm": 0, "extractif": 0, "errors": []}, "quotes": {"ok": 0, "failed": 0}, "sources_failed": []}
    health, by_domain = [], {}
    for dom in sorted(cfg["domains"].values(), key=lambda d: d["order"]):
        mine = [e for e in stored if e["domain"] == dom["id"]]
        changed = set()
        if only is None or dom["id"] in only:
            items, h = collect_domain(dom, g, now, fetch)
            health += h
            fresh = dedupe(items, {i["id"] for e in mine for i in e["items"]})
            report["collected"] += len(items)
            report["new_items"] += len(fresh)
            mine, changed = cluster(fresh, mine, dom, g, now)
        mine = rescore(mine, dom, g, now)
        mine, touched, errors = add_summaries(mine, dom, g, call)
        append(root, [e for e in mine if e["id"] in changed | touched], now)
        by_domain[dom["id"]] = mine
        _tally(report, mine, errors)
    agendas = _import_agendas(cfg, only, agenda_fetch, health)
    publish(root, build_home(cfg, by_domain, now, agendas),
            [build_domain(cfg["domains"][d], evs, now, agendas.get(d)) for d, evs in by_domain.items()])
    if cfg["quotes"] and (only is None or "quotes" in only):
        quotes, qhealth = collect_quotes(cfg["quotes"], _previous_quotes(root), now, quote_fetch)
        publish_quotes(root, quotes)
        health += qhealth
        symbols = [h for h in qhealth if h["source"] != "quote-relay"]
        report["quotes"] = {"ok": sum(h["ok"] for h in symbols), "failed": sum(not h["ok"] for h in qhealth)}
    report["sources_failed"] = [h["source"] for h in health if not h["ok"]]
    write_if_changed(root / "site" / "data" / "health.json",
                     {"checked_at": iso(now), "sources": health, "ai": report["ai"]}, now, max_age_min=55)
    return report


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="ids des veilles à collecter, ou « quotes » (défaut : tout)")
    ap.add_argument("--no-ai", action="store_true", help="résumés extractifs uniquement")
    args = ap.parse_args()
    call = gemini_call() if os.environ.get("GEMINI_API_KEY") and not args.no_ai else None
    print(json.dumps(run(only=args.only, call=call), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
