from engine.enrich import detect_kind, extract_entities

ENT = {"OpenAI": ["openai", "gpt-6"], "NVIDIA": ["nvidia"]}
KINDS = {
    "model_release": {"weight": 25, "keywords": ["lance", "releases"]},
    "research": {"weight": 12, "keywords": ["étude"]},
}


def test_entities_match_whole_words_case_insensitively():
    assert extract_entities("OpenAI lance GPT-6", ENT) == ["OpenAI"]
    assert extract_entities("NVIDIA et openai", ENT) == ["NVIDIA", "OpenAI"]


def test_entities_do_not_match_inside_other_words():
    assert extract_entities("Nvidiafoo et unopenai", ENT) == []


def test_detect_kind_prefers_highest_weight_and_defaults_to_other():
    assert detect_kind("Une étude : OpenAI lance un modèle", KINDS) == "model_release"
    assert detect_kind("Une étude sur les modèles", KINDS) == "research"
    assert detect_kind("Rien à signaler", KINDS) == "other"
