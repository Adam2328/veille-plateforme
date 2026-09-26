import datetime as dt

import pytest

from engine.agenda import imported_events, parse_point

TODAY = dt.date(2026, 9, 26)
KW = ["fomc", "bce", "pce", "inflation"]


def test_parse_point_reads_date_region_and_title():
    p = parse_point("30/09 :: usa :: macro :: Publication Indice Prix PCE US", TODAY)
    assert p == {"start": dt.date(2026, 9, 30), "end": dt.date(2026, 9, 30), "region": "usa", "title": "Publication Indice Prix PCE US"}


def test_parse_point_reads_ranges_and_keeps_the_detail_out_of_the_title():
    p = parse_point("15-16/09 :: usa :: mkt-n :: Réunion FOMC Fed :: détail ignoré", TODAY)
    assert (p["start"], p["end"], p["title"]) == (dt.date(2026, 9, 15), dt.date(2026, 9, 16), "Réunion FOMC Fed")


def test_parse_point_rolls_over_to_next_year_after_60_days():
    assert parse_point("05/01 :: europe :: macro :: X", dt.date(2026, 12, 20))["start"] == dt.date(2027, 1, 5)
    assert parse_point("05/09 :: europe :: macro :: X", TODAY)["start"] == dt.date(2026, 9, 5)


@pytest.mark.parametrize("bad", [
    "Semaine du 09/09 :: global :: corp :: Résultats", "Fin juillet :: usa :: macro :: X", "31/02 :: usa :: macro :: X",
    "30/09 :: usa", "30/09", "", "99/99 :: usa :: macro :: X", "20-10/09 :: usa :: macro :: X",
])
def test_parse_point_rejects_approximate_or_invalid_dates(bad):
    assert parse_point(bad, TODAY) is None


def test_imported_events_keep_the_horizon_and_the_keywords_only():
    points = [
        "30/09 :: usa :: macro :: Inflation PCE US Août",          # dans l'horizon, mot-clé
        "30/09 :: usa :: geo :: G20 Trade Ministerial",              # pas de mot-clé
        "25/09 :: usa :: macro :: Inflation ancienne",               # passé
        "20/10 :: usa :: macro :: Inflation lointaine",              # au-delà de l'horizon (24 jours)
        "24-28/09 :: usa :: mkt-n :: Réunion FOMC Fed",              # plage en cours
    ]
    got = imported_events(points, KW, TODAY)
    assert {(e["date"], e["title"]) for e in got} == {("2026-09-30", "États-Unis · Inflation PCE US Août"),
                                                    ("2026-09-26", "États-Unis · Réunion FOMC Fed")}


def test_keywords_match_whole_words_only_and_case_insensitively():
    assert imported_events(["30/09 :: usa :: macro :: Discours BCE"], KW, TODAY)
    assert not imported_events(["30/09 :: usa :: macro :: Bcetera"], KW, TODAY)
    assert imported_events(["30/09 :: usa :: macro :: Discours bce"], KW, TODAY)


def test_regions_are_labelled_and_unknown_ones_kept():
    got = imported_events(["30/09 :: asie :: macro :: Décision BCE", "30/09 :: mars :: macro :: Inflation"], KW, TODAY)
    assert {e["title"] for e in got} == {"Asie · Décision BCE", "Mars · Inflation"}


def test_garbage_input_is_ignored():
    assert imported_events(["", "n'importe quoi", "30/09 :: usa"], KW, TODAY) == []
    assert imported_events([], KW, TODAY) == []
    assert imported_events(["30/09 :: usa :: macro :: Inflation"], [], TODAY) == []
