from engine.score import assign_levels, importance
from tests.helpers import DOM, G, NOW, mk_event, mk_item


def test_official_multi_origin_recent_event_scores_high():
    ev = mk_event([mk_item("a", "x", tier=1), mk_item("b", "x", tier=2), mk_item("c", "x", tier=2)])
    assert importance(ev, DOM, G, NOW) >= 85


def test_lone_social_post_scores_low():
    ev = mk_event([mk_item("a", "x", tier=5)], kind="other", entities=[])
    assert importance(ev, DOM, G, NOW) < 30


def test_score_stays_within_bounds():
    ev = mk_event([mk_item(str(i), "x", tier=1) for i in range(40)])
    assert 0 <= importance(ev, DOM, G, NOW) <= 100


def test_freshness_decays_by_buckets_not_continuously():
    fresh = mk_event([mk_item("a", "x", minutes_ago=10)])
    still_fresh = mk_event([mk_item("a", "x", minutes_ago=100)])      # même palier de 3 h
    old = mk_event([mk_item("a", "x", minutes_ago=24 * 60)])
    assert importance(fresh, DOM, G, NOW) == importance(still_fresh, DOM, G, NOW)
    assert importance(old, DOM, G, NOW) < importance(fresh, DOM, G, NOW)


def _ev(id, imp, rel):
    return {"id": id, "importance": imp, "reliability": rel}


def test_levels_follow_thresholds_and_hide_the_irrelevant():
    out = {e["id"]: e["level"] for e in assign_levels(
        [_ev("a", 75, "officiel"), _ev("b", 55, "confirmé"), _ev("c", 35, "confirmé"), _ev("d", 20, "confirmé")], DOM)}
    assert out == {"a": 1, "b": 2, "c": 3, "d": 0}


def test_rumor_is_capped_at_level_two_and_does_not_use_a_level_one_slot():
    out = {e["id"]: e["level"] for e in assign_levels(
        [_ev("r", 95, "rumeur"), _ev("n", 90, "non_confirmé"), _ev("a", 90, "officiel"), _ev("b", 88, "confirmé")], DOM)}
    assert out["r"] == 2 and out["n"] == 2
    assert out["a"] == 1 and out["b"] == 1


def test_level_one_is_capped_per_domain():
    out = {e["id"]: e["level"] for e in assign_levels(
        [_ev("a", 90, "officiel"), _ev("b", 88, "confirmé"), _ev("c", 85, "confirmé")], DOM)}     # max_l1 = 2
    assert sorted(out.values()) == [1, 1, 2]
    assert out["c"] == 2


def test_assign_levels_does_not_mutate_input():
    src = [_ev("a", 90, "officiel")]
    assign_levels(src, DOM)
    assert "level" not in src[0]
