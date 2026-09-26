import pytest
from jsonschema import ValidationError

from engine.contract import validate

EVENT = {
    "id": "ev_1", "rev": 1, "domain": "ia", "kind": "model_release", "title": "Titre",
    "first_seen": "2026-09-26T10:00:00+00:00", "updated_at": "2026-09-26T11:00:00+00:00",
    "importance": 80.5, "level": 1, "reliability": "confirmé", "reliability_reason": "2 origines",
    "summary": {"quoi": "q", "qui": "w", "quand": "n", "pourquoi": "p", "retenir": "r"},
    "summary_mode": "llm", "entities": ["OpenAI"],
    "sources": [{"name": "S", "tier": 2, "url": "https://ex.com/a", "title": "t",
                 "published_at": "2026-09-26T10:30:00+00:00"}],
}
HOME = {
    "generated_at": "2026-09-26T12:00:00+00:00", "sample": False,
    "domains": [{"id": "ia", "name": "IA", "accent": "#5B3FA8",
                 "levels": {"1": ["ev_1"], "2": [], "3": []}, "upcoming": []}],
    "retain": ["ev_1"], "events": {"ev_1": EVENT},
}
DOMAIN_FILE = {
    "generated_at": "2026-09-26T12:00:00+00:00",
    "domain": {"id": "ia", "name": "IA", "accent": "#5B3FA8"},
    "events": [EVENT], "upcoming": [{"date": "2026-10-01", "title": "Conférence"}],
}


def test_valid_event_home_and_domain_file_pass():
    validate("event", EVENT)
    validate("home", HOME)
    validate("domainFile", DOMAIN_FILE)


def test_level_three_event_may_have_no_summary():
    validate("event", {**EVENT, "level": 3, "summary": None, "summary_mode": "aucun"})


@pytest.mark.parametrize("field", ["id", "rev", "level", "reliability", "sources", "summary_mode"])
def test_event_missing_required_field_fails(field):
    bad = {k: v for k, v in EVENT.items() if k != field}
    with pytest.raises(ValidationError):
        validate("event", bad)


@pytest.mark.parametrize("patch", [
    {"reliability": "certain"},
    {"level": 4},
    {"level": 0},
    {"importance": 101},
    {"sources": []},
    {"summary_mode": "magie"},
])
def test_event_invalid_value_fails(patch):
    with pytest.raises(ValidationError):
        validate("event", {**EVENT, **patch})


def test_home_without_levels_key_fails():
    bad = {**HOME, "domains": [{**HOME["domains"][0], "levels": {"1": [], "2": []}}]}
    with pytest.raises(ValidationError):
        validate("home", bad)


LAYER_KEYS = ("faits", "analyse", "interpretation", "incertitude", "actifs", "favorables", "risques", "a_surveiller")
LAYERS = {k: ["puce"] for k in LAYER_KEYS}
QUOTE = {"symbol": "^FCHI", "name": "CAC 40", "group": "Indices", "price": 8077.8, "change": -3.63,
         "change_pct": -0.04, "currency": "EUR", "as_of": "2026-09-25T16:05:02+00:00", "stale": False}


def test_layers_are_optional_nullable_and_may_have_empty_lists():
    validate("event", {**EVENT, "layers": LAYERS})
    validate("event", {**EVENT, "layers": None})
    validate("event", {**EVENT, "layers": {k: [] for k in LAYER_KEYS}})


def test_layers_must_be_complete_and_made_of_short_string_lists():
    incomplete = {k: v for k, v in LAYERS.items() if k != "risques"}
    for bad in (incomplete, {**LAYERS, "faits": [1]}, {**LAYERS, "faits": ["x"] * 9}, {**LAYERS, "extra": []}):
        with pytest.raises(ValidationError):
            validate("event", {**EVENT, "layers": bad})


def test_quotes_file_is_valid_and_change_may_be_null():
    validate("quotes", {"checked_at": "2026-09-26T12:00:00+00:00", "quotes": [QUOTE, {**QUOTE, "change": None, "change_pct": None}]})
    validate("quotes", {"checked_at": "2026-09-26T12:00:00+00:00", "quotes": []})


def test_quote_missing_field_or_wrong_type_fails():
    for bad in ({k: v for k, v in QUOTE.items() if k != "as_of"}, {**QUOTE, "price": "8077"}, {**QUOTE, "stale": "non"}):
        with pytest.raises(ValidationError):
            validate("quotes", {"checked_at": "t", "quotes": [bad]})
    with pytest.raises(ValidationError):
        validate("quotes", {"quotes": [QUOTE]})


MATCH = {"id": 501, "competition": "FL1", "date": "2026-09-20T18:45:00+00:00", "home": "Marseille", "away": "PSG",
         "home_score": 1, "away_score": 2, "status": "FINISHED", "matchday": 5}
ROW = {"position": 1, "team": "Monaco", "played": 5, "won": 4, "draw": 1, "lost": 0, "gf": 8, "ga": 3, "gd": 5, "points": 13, "form": "WDWWW"}
FOOTBALL = {"checked_at": "2026-09-26T12:00:00+00:00",
            "competitions": [{"code": "FL1", "name": "Ligue 1", "stale": False, "standings": [ROW]}],
            "results": [MATCH], "fixtures": [{**MATCH, "id": 502, "home_score": None, "away_score": None, "status": "SCHEDULED", "matchday": None}]}


def test_football_file_is_valid_with_unplayed_matches_and_empty_lists():
    validate("football", FOOTBALL)
    validate("football", {"checked_at": "t", "competitions": [], "results": [], "fixtures": []})


def test_football_rejects_missing_fields_and_wrong_types():
    bad_row = {**ROW, "points": "13"}
    bad_match = {k: v for k, v in MATCH.items() if k != "home"}
    for bad in ({"competitions": [], "results": [], "fixtures": []},
                {**FOOTBALL, "competitions": [{"code": "FL1", "name": "L1", "stale": False, "standings": [bad_row]}]},
                {**FOOTBALL, "results": [bad_match]},
                {**FOOTBALL, "results": [{**MATCH, "home_score": "1"}]},
                {**FOOTBALL, "competitions": [{"code": "FL1", "name": "L1", "standings": []}]}):
        with pytest.raises(ValidationError):
            validate("football", bad)
