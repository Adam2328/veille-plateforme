import re


def _has(low: str, alias: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", low) is not None


def extract_entities(text: str, entity_cfg: dict) -> list[str]:
    low = text.lower()
    return sorted(name for name, aliases in entity_cfg.items() if any(_has(low, a) for a in aliases))


def detect_kind(text: str, kinds_cfg: dict) -> str:
    low = text.lower()
    hits = [(cfg.get("weight", 0), name) for name, cfg in kinds_cfg.items()
            if any(_has(low, k) for k in cfg["keywords"])]
    return max(hits)[1] if hits else "other"


def event_image(ev: dict) -> str | None:
    """Photo de l'événement : celle de la meilleure source (tier le plus bas), la plus récente à tier égal."""
    with_image = sorted((i for i in ev["items"] if i.get("image")), key=lambda i: i["published_at"], reverse=True)
    return min(with_image, key=lambda i: i["tier"])["image"] if with_image else None


def is_relevant(text: str, dom: dict) -> bool:
    """Vrai si le texte cite une entité de la veille ou contient un mot-clé d'un de ses types d'événements."""
    return bool(extract_entities(text, dom["entities"])) or detect_kind(text, dom["kinds"]) != "other"
