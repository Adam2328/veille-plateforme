from engine.wikidata_ids import insert_qid, pick


def test_pick_takes_the_first_result_whose_description_fits_the_type():
    results = [{"id": "Q1", "description": "fruit"}, {"id": "Q312", "description": "entreprise américaine"}]
    assert pick(results, "company") == "Q312" and pick(results, "country") is None and pick([], "company") is None


def test_insert_qid_adds_the_id_once_after_the_entity_id():
    text = "- {id: company:apple, name: Apple, aliases: [x]}\n- {id: company:applex, name: X, aliases: [y]}\n"
    once = insert_qid(text, "company:apple", "Q312")
    assert once.splitlines()[0] == "- {id: company:apple, wikidata: Q312, name: Apple, aliases: [x]}"
    assert once.splitlines()[1] == "- {id: company:applex, name: X, aliases: [y]}"
    assert insert_qid(once, "company:apple", "Q999") == once
