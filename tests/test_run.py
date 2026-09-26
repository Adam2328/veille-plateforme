import json
import shutil

import yaml

from engine.config import ROOT
from engine.contract import validate
from engine.run import run
from tests.helpers import NOW

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>OpenAI lance GPT-6 avec un contexte de deux millions de tokens</title><link>https://ex.com/1</link>
<pubDate>Sat, 26 Sep 2026 10:30:00 GMT</pubDate><description>Details.</description></item>
<item><title>OpenAI d\xc3\xa9voile GPT-6 : contexte de deux millions de tokens</title><link>https://ex.com/2</link>
<pubDate>Sat, 26 Sep 2026 10:45:00 GMT</pubDate><description>Details.</description></item>
<item><title>GPT-6 d'OpenAI : deux millions de tokens de contexte</title><link>https://ex.com/3</link>
<pubDate>Sat, 26 Sep 2026 11:00:00 GMT</pubDate><description>Details.</description></item>
<item><title>Vieil article</title><link>https://ex.com/old</link>
<pubDate>Mon, 21 Sep 2026 11:00:00 GMT</pubDate></item>
</channel></rss>"""
DOM = {
    "id": "ia", "name": "IA", "accent": "#5B3FA8", "order": 1, "quota": 12, "max_l1": 4,
    "thresholds": {"l1": 70, "l2": 50, "l3": 30},
    "entities": {"OpenAI": ["openai", "gpt-6"]},
    "kinds": {"model_release": {"weight": 25, "keywords": ["lance", "dévoile"]}},
    "sources": [
        {"id": "s1", "name": "Src 1", "tier": 2, "origin": "src1", "type": "rss", "url": "mem://1"},
        {"id": "s2", "name": "Src 2", "tier": 2, "origin": "src2", "type": "rss", "url": "mem://2"},
    ],
}


def fake_fetch(url):
    if url.endswith("2"):
        raise TimeoutError("boom")
    return RSS


def setup(tmp_path):
    (tmp_path / "config" / "domains").mkdir(parents=True)
    shutil.copy(ROOT / "config" / "global.yml", tmp_path / "config" / "global.yml")
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(DOM, allow_unicode=True), "utf-8")


def snapshot(tmp_path):
    data = tmp_path / "site" / "data"
    events = next((tmp_path / "data" / "events").glob("*.jsonl")).read_text("utf-8")
    return events, (data / "home.json").read_bytes(), (data / "health.json").read_bytes()


def test_run_publishes_valid_json_one_event_and_isolates_the_failing_source(tmp_path):
    setup(tmp_path)
    report = run(tmp_path, now=NOW, fetch=fake_fetch)
    assert report["new_items"] == 3 and report["sources_failed"] == ["s2"]      # l'article de 5 jours est ignoré
    home = json.loads((tmp_path / "site" / "data" / "home.json").read_text("utf-8"))
    validate("home", home)
    assert len(home["events"]) == 1
    ev = next(iter(home["events"].values()))
    assert ev["summary_mode"] == "extractif" and ev["summary"]["retenir"]        # pas de clé Gemini : repli extractif
    health = json.loads((tmp_path / "site" / "data" / "health.json").read_text("utf-8"))
    assert [s["ok"] for s in health["sources"]] == [True, False]


def test_second_run_without_new_articles_changes_nothing(tmp_path):
    setup(tmp_path)
    run(tmp_path, now=NOW, fetch=fake_fetch)
    before = snapshot(tmp_path)
    report = run(tmp_path, now=NOW, fetch=fake_fetch)
    assert report["new_items"] == 0
    assert snapshot(tmp_path) == before


def test_llm_summary_is_used_and_not_requested_twice(tmp_path):
    setup(tmp_path)
    calls = []

    def call(prompt):
        calls.append(1)
        ev_id = prompt.split("## ")[1].split("\n")[0]
        return json.dumps({ev_id: {k: f"llm {k}" for k in ("quoi", "qui", "quand", "pourquoi", "retenir")}})

    run(tmp_path, now=NOW, fetch=fake_fetch, call=call)
    run(tmp_path, now=NOW, fetch=fake_fetch, call=call)
    home = json.loads((tmp_path / "site" / "data" / "home.json").read_text("utf-8"))
    assert next(iter(home["events"].values()))["summary_mode"] == "llm"
    assert len(calls) == 1


FIN_LAYERS = {k: [f"{k} un"] for k in ("faits", "analyse", "interpretation", "incertitude", "actifs", "favorables", "risques", "a_surveiller")}


def test_finance_profile_publishes_layers_and_stays_idempotent(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "domains" / "ia.yml").write_text(
        yaml.safe_dump({**DOM, "summary_profile": "finance"}, allow_unicode=True), "utf-8")

    def call(prompt):
        ev_id = prompt.split("## ")[1].split("\n")[0]
        return json.dumps({ev_id: {**{k: f"llm {k}" for k in ("quoi", "qui", "quand", "pourquoi", "retenir")}, "layers": FIN_LAYERS}})

    run(tmp_path, now=NOW, fetch=fake_fetch, call=call)
    before = snapshot(tmp_path)
    run(tmp_path, now=NOW, fetch=fake_fetch, call=call)
    home = json.loads((tmp_path / "site" / "data" / "home.json").read_text("utf-8"))
    validate("home", home)
    ev = next(iter(home["events"].values()))
    assert ev["layers"]["faits"] == ["faits un"] and "layers" not in ev["summary"]
    assert snapshot(tmp_path) == before


QSPECS = [{"symbol": "^GSPC", "name": "S&P 500", "group": "Indices"}, {"symbol": "^TNX", "name": "Taux US 10 ans", "group": "Taux"}]


def relay_payload(*rows):
    return {"derniere_maj": "x", "indices": [{"nom": s, "valeur": v, "variation": p} for s, v, p in rows]}


def test_run_publishes_quotes_and_reports_a_symbol_without_value(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "quotes.yml").write_text(yaml.safe_dump({"symbols": QSPECS}), "utf-8")
    report = run(tmp_path, now=NOW, fetch=fake_fetch,
                 quote_fetch=lambda url: relay_payload(("^GSPC", 5000.0, 0.5), ("^TNX", None, None)))
    quotes = json.loads((tmp_path / "site" / "data" / "quotes.json").read_text("utf-8"))
    validate("quotes", quotes)
    assert [q["symbol"] for q in quotes["quotes"]] == ["^GSPC"]
    assert report["quotes"] == {"ok": 1, "failed": 1} and "quote:^TNX" in report["sources_failed"]
    health = json.loads((tmp_path / "site" / "data" / "health.json").read_text("utf-8"))
    assert "quote-relay" in [s["source"] for s in health["sources"]]


def test_quotes_are_skipped_when_only_names_other_domains(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "quotes.yml").write_text(yaml.safe_dump({"symbols": QSPECS}), "utf-8")
    run(tmp_path, now=NOW, fetch=fake_fetch, only=["ia"], quote_fetch=lambda url: relay_payload(("^GSPC", 1.0, 0.0)))
    assert not (tmp_path / "site" / "data" / "quotes.json").exists()


def test_second_run_rewrites_quotes_only_when_values_change(tmp_path):
    setup(tmp_path)
    (tmp_path / "config" / "quotes.yml").write_text(yaml.safe_dump({"symbols": QSPECS[:1]}), "utf-8")
    path = tmp_path / "site" / "data" / "quotes.json"
    run(tmp_path, now=NOW, fetch=fake_fetch, quote_fetch=lambda url: relay_payload(("^GSPC", 5000.0, 0.5)))
    first = path.read_bytes()
    later = NOW.replace(hour=13)
    run(tmp_path, now=later, fetch=fake_fetch, quote_fetch=lambda url: relay_payload(("^GSPC", 5000.0, 0.5)))
    assert path.read_bytes() == first
    run(tmp_path, now=later, fetch=fake_fetch, quote_fetch=lambda url: relay_payload(("^GSPC", 5001.0, 0.6)))
    assert path.read_bytes() != first


def test_run_imports_the_agenda_and_survives_a_failing_import(tmp_path):
    setup(tmp_path)
    dom = {**DOM, "agenda_url": "mem://agenda", "agenda_keywords": ["inflation"]}
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(dom, allow_unicode=True), "utf-8")
    home_path = tmp_path / "site" / "data" / "home.json"
    run(tmp_path, now=NOW, fetch=fake_fetch, agenda_fetch=lambda url: ["30/09 :: usa :: macro :: Inflation PCE US"])
    assert json.loads(home_path.read_text("utf-8"))["domains"][0]["upcoming"] == [
        {"date": "2026-09-30", "title": "États-Unis · Inflation PCE US"}]

    def boom(url):
        raise TimeoutError("boom")

    report = run(tmp_path, now=NOW, fetch=fake_fetch, agenda_fetch=boom)
    assert "agenda:ia" in report["sources_failed"]
    assert json.loads(home_path.read_text("utf-8"))["domains"][0]["upcoming"] == []
