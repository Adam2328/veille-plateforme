import yaml

from engine.config import load_config


def test_load_config_reads_global_and_every_domain(tmp_path):
    (tmp_path / "config" / "domains").mkdir(parents=True)
    (tmp_path / "config" / "global.yml").write_text("cluster: {threshold: 0.5}\n", "utf-8")
    (tmp_path / "config" / "domains" / "x.yml").write_text(yaml.safe_dump({"id": "x", "name": "É"}, allow_unicode=True), "utf-8")
    cfg = load_config(tmp_path)
    assert cfg["global"]["cluster"]["threshold"] == 0.5
    assert cfg["domains"]["x"]["name"] == "É"


def test_real_global_config_has_every_scoring_key():
    g = load_config()["global"]
    assert {"authority", "coverage_per_log2", "coverage_cap", "default_kind_weight", "entity_bonus",
            "velocity_bonus", "freshness_max", "freshness_half_life_h", "freshness_bucket_h",
            "social_only_penalty"} <= set(g["score"])
    assert set(g["score"]["authority"]) == {1, 2, 3, 4, 5}


def test_quotes_config_is_optional_and_the_real_one_is_well_formed(tmp_path):
    (tmp_path / "config" / "domains").mkdir(parents=True)
    (tmp_path / "config" / "global.yml").write_text("cluster: {threshold: 0.5}\n", "utf-8")
    assert load_config(tmp_path)["quotes"] == []
    real = load_config()["quotes"]
    symbols = [q["symbol"] for q in real]
    assert real and len(symbols) == len(set(symbols)) <= 20          # le relais accepte 20 symboles au plus
    assert all(q["name"].strip() and q["group"].strip() for q in real)


def test_football_config_is_optional_and_the_real_one_is_well_formed(tmp_path):
    (tmp_path / "config" / "domains").mkdir(parents=True)
    (tmp_path / "config" / "global.yml").write_text("cluster: {threshold: 0.5}\n", "utf-8")
    assert load_config(tmp_path)["football"] is None
    real = load_config()["football"]
    codes = [c["code"] for c in real["competitions"]]
    assert len(codes) == len(set(codes)) and 1 <= len(codes) <= 6      # budget : 6 classements + 2 fenêtres = 8 requêtes par minute
    assert all(c["name"].strip() for c in real["competitions"])
    assert all(c["flashscore"].startswith("https://www.flashscore.fr/football/") and c["flashscore"].endswith("/")
               for c in real["competitions"])
    assert 1 <= real["results_days"] <= 9 and 1 <= real["fixtures_days"] <= 9      # limite de 10 jours du plan gratuit
