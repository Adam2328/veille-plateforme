import re


def _has(low, alias):
    return re.search(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", low) is not None


def extract_entities(text, entity_cfg):
    low = text.lower()
    return sorted(name for name, aliases in entity_cfg.items() if any(_has(low, a) for a in aliases))


def detect_kind(text, kinds_cfg):
    low = text.lower()
    hits = [(cfg.get("weight", 0), name) for name, cfg in kinds_cfg.items()
            if any(_has(low, k) for k in cfg["keywords"])]
    return max(hits)[1] if hits else "other"
