import pytest

from engine.reliability import LOW, classify
from tests.helpers import NOW, mk_item


def label(items):
    return classify(items, NOW)[0]


def test_tier_one_source_makes_it_official():
    assert label([mk_item("a", "Communiqué", tier=1)]) == "officiel"


def test_two_independent_reliable_origins_confirm():
    assert label([mk_item("a", "X", tier=2), mk_item("b", "X", tier=3)]) == "confirmé"


def test_one_reliable_origin_plus_any_other_origin_confirms():
    assert label([mk_item("a", "X", tier=2), mk_item("b", "X", tier=5)]) == "confirmé"


def test_same_origin_repeated_is_only_reported():
    items = [mk_item("a", "X", tier=2, origin="l'équipe"), mk_item("b", "X", tier=2, origin="l'équipe", minutes_ago=40)]
    assert label(items) == "rapporté"


def test_fast_growth_from_one_reliable_origin_is_developing():
    items = [mk_item(i, "Direct", tier=3, origin="media", minutes_ago=m) for i, m in (("a", 5), ("b", 20), ("c", 40))]
    assert label(items) == "en_développement"


def test_rumor_repeated_by_many_low_tier_origins_stays_a_rumor():
    items = [mk_item(i, "Le joueur X serait proche de Y", tier=5, minutes_ago=m) for i, m in (("a", 5), ("b", 10), ("c", 15))]
    lab, why = classify(items, NOW)
    assert lab == "rumeur" and lab in LOW
    assert lab not in ("confirmé", "en_développement", "officiel")
    assert "tier 4-5" in why


def test_single_generalist_without_hedging_is_unconfirmed():
    assert label([mk_item("a", "Annonce", tier=3)]) == "non_confirmé"


def test_low_tier_without_hedging_is_unconfirmed_not_rumor():
    assert label([mk_item("a", "Annonce", tier=4)]) == "non_confirmé"


@pytest.mark.parametrize("hedge", ["would join", "reportedly close", "il pourrait signer", "selon nos informations"])
def test_hedging_lexicon_detected(hedge):
    assert label([mk_item("a", f"Player {hedge}", tier=5)]) == "rumeur"


def test_three_distinct_media_without_hedging_are_reported_not_unconfirmed():
    items = [mk_item(i, "Un tribunal donne raison au Pentagone", tier=4) for i in "abc"]
    lab, why = classify(items, NOW)
    assert lab == "rapporté" and "3" in why


def test_two_low_tier_media_stay_unconfirmed():
    assert label([mk_item(i, "Un tribunal donne raison", tier=4) for i in "ab"]) == "non_confirmé"


def test_three_distinct_media_with_hedging_stay_a_rumor():
    assert label([mk_item(i, "Le joueur serait proche de Y", tier=4) for i in "abc"]) == "rumeur"


def test_social_posts_do_not_count_as_media():
    assert label([mk_item(i, "Un tribunal donne raison", tier=5) for i in "abc"]) == "non_confirmé"


DOM_FB = {"rumor_markers": ["serait", "intéress", "dans le viseur"], "confirm_markers": ["officiel", "here we go"]}


def test_hedged_single_source_transfer_is_a_rumor_even_from_a_reliable_outlet():
    items = [mk_item("a", "Mbappé serait dans le viseur du Real", tier=2)]
    assert classify(items, NOW, DOM_FB)[0] == "rumeur"
    assert classify(items, NOW)[0] == "rapporté"                       # sans config, comportement inchangé
    assert classify([mk_item("a", "Un joueur intéressé par un départ", tier=3)], NOW, DOM_FB)[0] == "rumeur"


def test_confirmation_markers_win_over_rumor_markers():
    items = [mk_item("a", "Officiel : le Real annonce l'arrivée, le PSG était intéressé", tier=2)]
    assert classify(items, NOW, DOM_FB)[0] == "rapporté"
    assert classify([mk_item("a", "Here we go, il serait proche de signer", tier=2)], NOW, DOM_FB)[0] == "rapporté"


def test_strong_labels_are_never_downgraded_by_rumor_markers():
    two = [mk_item("a", "Il serait intéressé", tier=2), mk_item("b", "Il serait intéressé", tier=2)]
    assert classify(two, NOW, DOM_FB)[0] == "confirmé"
    assert classify([mk_item("a", "Il serait intéressé", tier=1)], NOW, DOM_FB)[0] == "officiel"


def test_markers_match_word_starts_only():
    assert classify([mk_item("a", "Le désintéressement du club est total", tier=2)], NOW, DOM_FB)[0] == "rapporté"
    assert classify([mk_item("a", "SERAIT-il prêt ?", tier=2)], NOW, DOM_FB)[0] == "rumeur"


def test_missing_marker_lists_change_nothing():
    items = [mk_item("a", "Il serait intéressé", tier=2)]
    assert classify(items, NOW, {})[0] == "rapporté"
    assert classify(items, NOW, {"rumor_markers": ["serait"]})[0] == "rumeur"


def test_rescore_passes_the_domain_markers_to_the_classifier():
    from engine.run import rescore
    from tests.helpers import DOM, G, mk_event
    ev = mk_event([mk_item("a", "Le club serait intéressé par le joueur", tier=2)], id="ev_r", entities=[])
    assert rescore([ev], {**DOM, "rumor_markers": ["serait"]}, G, NOW)[0]["reliability"] == "rumeur"
    assert rescore([ev], DOM, G, NOW)[0]["reliability"] == "rapporté"
