import pytest

from engine.contract import validate
from engine.football_data import collect_football, parse_matches, parse_standings
from tests.helpers import NOW

CFG = {"competitions": [{"code": "FL1", "name": "Ligue 1"}, {"code": "PL", "name": "Premier League"}]}


def row(pos, name, played=5, w=4, d=1, l=0, gf=8, ga=3, pts=13, form="W,D,W,W,W"):
    return {"position": pos, "team": {"name": f"{name} FC", "shortName": name}, "playedGames": played, "won": w, "draw": d,
            "lost": l, "goalsFor": gf, "goalsAgainst": ga, "goalDifference": gf - ga, "points": pts, "form": form}


def standings(*rows):
    return {"standings": [{"stage": "REGULAR_SEASON", "type": "HOME", "table": [row(1, "Domicile")]},
                          {"stage": "REGULAR_SEASON", "type": "TOTAL", "table": list(rows)}]}


def match(id, status, home, away, hs=None, aws=None, date="2026-09-20T18:45:00Z", comp="FL1", md=5):
    return {"id": id, "utcDate": date, "status": status, "matchday": md, "competition": {"code": comp},
            "homeTeam": {"shortName": home}, "awayTeam": {"shortName": away},
            "score": {"fullTime": {"home": hs, "away": aws}}}


MATCHES = {"matches": [
    match(1, "FINISHED", "Marseille", "PSG", 1, 2, "2026-09-20T18:45:00Z"),
    match(2, "FINISHED", "Lens", "Lille", 0, 0, "2026-09-25T18:45:00Z"),
    match(3, "TIMED", "Nice", "Brest", None, None, "2026-09-28T18:45:00Z", md=6),
    match(4, "SCHEDULED", "Lyon", "Metz", None, None, "2026-09-27T15:00:00Z", md=6),
    match(5, "CANCELLED", "Nantes", "Reims", None, None, "2026-09-29T15:00:00Z"),
]}


def fake(url, token):
    assert token == "secret"
    return standings(row(1, "Monaco"), row(2, "PSG", pts=12)) if "/standings" in url else MATCHES


def test_parse_standings_reads_the_total_table_only():
    rows = parse_standings(standings(row(1, "Monaco"), row(2, "PSG", pts=12)))
    assert [(r["position"], r["team"], r["points"]) for r in rows] == [(1, "Monaco", 13), (2, "PSG", 12)]
    assert rows[0] == {"position": 1, "team": "Monaco", "played": 5, "won": 4, "draw": 1, "lost": 0, "gf": 8, "ga": 3,
                       "gd": 5, "points": 13, "form": "WDWWW"}


@pytest.mark.parametrize("bad", [{}, {"standings": []}, {"standings": [{"type": "HOME", "table": [row(1, "X")]}]},
                                 {"standings": [{"type": "TOTAL", "table": []}]}])
def test_parse_standings_rejects_missing_or_empty_tables(bad):
    with pytest.raises(ValueError):
        parse_standings(bad)


def test_parse_matches_filters_by_status_and_maps_scores_and_dates():
    played = parse_matches(MATCHES, {"FINISHED"})
    assert [m["id"] for m in played] == [1, 2]
    assert played[0] == {"id": 1, "competition": "FL1", "date": "2026-09-20T18:45:00+00:00", "home": "Marseille",
                         "away": "PSG", "home_score": 1, "away_score": 2, "status": "FINISHED", "matchday": 5}
    upcoming = parse_matches(MATCHES, {"SCHEDULED", "TIMED"})
    assert [m["id"] for m in upcoming] == [3, 4] and upcoming[0]["home_score"] is None
    assert parse_matches({}, {"FINISHED"}) == []


def test_collect_builds_a_valid_sorted_file_with_one_request_per_call():
    calls = []
    data, health = collect_football(CFG, "secret", None, NOW, lambda url, t: calls.append(url) or fake(url, t))
    validate("football", data)
    assert len(calls) == 4                                      # 2 classements + 2 fenêtres de matchs
    assert [c["code"] for c in data["competitions"]] == ["FL1", "PL"] and not any(c["stale"] for c in data["competitions"])
    assert [m["id"] for m in data["results"]] == [2, 1]         # du plus récent au plus ancien
    assert [m["id"] for m in data["fixtures"]] == [4, 3]        # du plus proche au plus lointain
    assert all(h["ok"] for h in health)
    assert {h["source"] for h in health} == {"football:standings:FL1", "football:standings:PL",
                                             "football:matches:results", "football:matches:fixtures"}


def test_flashscore_link_is_copied_from_the_config_when_present():
    cfg = {"competitions": [{"code": "FL1", "name": "Ligue 1", "flashscore": "https://www.flashscore.fr/football/france/ligue-1/"},
                            {"code": "PL", "name": "Premier League"}]}
    data, _ = collect_football(cfg, "secret", None, NOW, fake)
    validate("football", data)
    by = {c["code"]: c for c in data["competitions"]}
    assert by["FL1"]["flashscore"] == "https://www.flashscore.fr/football/france/ligue-1/" and "flashscore" not in by["PL"]


def test_match_windows_respect_the_ten_day_limit_of_the_free_plan():
    urls = []
    collect_football(CFG, "secret", None, NOW, lambda url, t: urls.append(url) or fake(url, t))
    windows = [u for u in urls if "/matches" in u]
    assert len(windows) == 2 and all("competitions=FL1,PL" in u for u in windows)
    assert "dateFrom=2026-09-17" in windows[0] and "dateTo=2026-09-26" in windows[0]
    assert "dateFrom=2026-09-26" in windows[1] and "dateTo=2026-10-05" in windows[1]


def test_without_a_token_nothing_is_requested_and_nothing_is_published():
    def never(url, t):
        raise AssertionError("aucun appel attendu")
    data, health = collect_football(CFG, None, None, NOW, never)
    assert data is None and len(health) == 1 and health[0]["ok"] is False and "FOOTBALL_DATA_TOKEN" in health[0]["error"]
    assert collect_football(CFG, "", None, NOW, never)[0] is None


def test_failures_keep_the_previous_values_marked_stale():
    first, _ = collect_football(CFG, "secret", None, NOW, fake)

    def flaky(url, t):
        if "/standings" in url and "/FL1/" in url:
            raise TimeoutError("boom")
        if "/matches" in url:
            raise RuntimeError("429 Too Many Requests")
        return fake(url, t)

    second, health = collect_football(CFG, "secret", first, NOW, flaky)
    by = {c["code"]: c for c in second["competitions"]}
    assert by["FL1"]["stale"] is True and by["FL1"]["standings"] == first["competitions"][0]["standings"]
    assert by["PL"]["stale"] is False
    assert second["results"] == first["results"] and second["fixtures"] == first["fixtures"]
    assert [h["ok"] for h in health] == [False, True, False, False]
    validate("football", second)


def test_failure_without_history_omits_the_competition_and_keeps_going():
    def only_pl(url, t):
        if "/FL1/" in url:
            raise ValueError("boom")
        return fake(url, t)
    data, _ = collect_football(CFG, "secret", None, NOW, only_pl)
    assert [c["code"] for c in data["competitions"]] == ["PL"]
    validate("football", data)


def test_malformed_answers_are_handled_like_failures():
    data, health = collect_football(CFG, "secret", None, NOW, lambda url, t: {"unexpected": True})
    assert data["competitions"] == [] and data["results"] == [] and data["fixtures"] == []
    assert not any(h["ok"] for h in health[:2])


def test_lists_are_capped_at_forty_entries():
    many = {"matches": [match(i, "FINISHED", "A", "B", 1, 0, f"2026-09-{(i % 9) + 17:02d}T18:00:00Z") for i in range(60)]}
    data, _ = collect_football(CFG, "secret", None, NOW, lambda url, t: standings(row(1, "X")) if "/standings" in url else many)
    assert len(data["results"]) == 40
