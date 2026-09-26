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
