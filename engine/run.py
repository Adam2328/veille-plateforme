import argparse
import json
import os
import sys

from .cluster import cluster
from .collect import collect_source, fetch_bytes
from .config import ROOT, load_config
from .normalize import dedupe, excluded, normalize, recent
from .publish import build_domain, build_home, publish, write_if_changed
from .reliability import classify
from .score import assign_levels, importance
from .store import append, load_recent
from .summarize import fingerprint, gemini_call, summarize
from .timeutil import iso, now_utc


def collect_domain(dom, g, now, fetch):
    items, health = [], []
    for src in dom["sources"]:
        source = {**src, "domain": dom["id"]}
        raws, h = collect_source(source, fetch)
        health.append(h)
        items += [i for i in (normalize(r, source, g.get("publishers")) for r in raws)
                  if not excluded(i, dom.get("exclude", []))]
    return recent(items, now, g["collect"]["max_age_hours"]), health


def rescore(events, dom, g, now):
    out = []
    for ev in events:
        label, reason = classify(ev["items"], now)
        scored = {**ev, "reliability": label, "reliability_reason": reason}
        out.append({**scored, "importance": importance(scored, dom, g, now)})
    return assign_levels(out, dom)


def add_summaries(events, g, call):
    need = sorted((e for e in events if e["level"] in (1, 2) and e.get("summary_fp") != fingerprint(e)),
                  key=lambda e: -e["importance"])[: g["ai"]["max_events_per_run"]]
    results, errors = summarize(need, call)
    done, touched = {}, set()
    for e in need:
        summary, mode = results[e["id"]]
        done[e["id"]] = {**e, "summary": summary, "summary_mode": mode,
                         "summary_fp": fingerprint(e) if mode == "llm" else None}
        if (summary, mode) != (e.get("summary"), e.get("summary_mode")):
            touched.add(e["id"])
    return [done.get(e["id"], e) for e in events], touched, errors


def _tally(report, events, errors):
    for e in events:
        if e["level"] >= 1:
            report["events"][str(e["level"])] += 1
            report["reliability"][e["reliability"]] = report["reliability"].get(e["reliability"], 0) + 1
        if e.get("summary_mode") in ("llm", "extractif"):
            report["ai"][e["summary_mode"]] += 1
    report["ai"]["errors"] += errors


def run(root=ROOT, now=None, only=None, call=None, fetch=fetch_bytes):
    now = now or now_utc()
    cfg = load_config(root)
    g = cfg["global"]
    stored = load_recent(root, now)
    report = {"collected": 0, "new_items": 0, "events": {"1": 0, "2": 0, "3": 0}, "reliability": {},
              "ai": {"llm": 0, "extractif": 0, "errors": []}, "sources_failed": []}
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
        mine, touched, errors = add_summaries(mine, g, call)
        append(root, [e for e in mine if e["id"] in changed | touched], now)
        by_domain[dom["id"]] = mine
        _tally(report, mine, errors)
    publish(root, build_home(cfg, by_domain, now),
            [build_domain(cfg["domains"][d], evs, now) for d, evs in by_domain.items()])
    report["sources_failed"] = [h["source"] for h in health if not h["ok"]]
    write_if_changed(root / "site" / "data" / "health.json",
                     {"checked_at": iso(now), "sources": health, "ai": report["ai"]}, now, max_age_min=55)
    return report


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="ids des veilles à collecter (défaut : toutes)")
    ap.add_argument("--no-ai", action="store_true", help="résumés extractifs uniquement")
    args = ap.parse_args()
    call = gemini_call() if os.environ.get("GEMINI_API_KEY") and not args.no_ai else None
    print(json.dumps(run(only=args.only, call=call), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
