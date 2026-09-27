import pathlib

import yaml

from .catalog import check_universes, load_catalog, load_relations, load_universes

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config(root: pathlib.Path | str = ROOT) -> dict:
    root = pathlib.Path(root)
    g = yaml.safe_load((root / "config" / "global.yml").read_text("utf-8"))
    domains = {}
    for path in sorted((root / "config" / "domains").glob("*.yml")):
        d = yaml.safe_load(path.read_text("utf-8"))
        domains[d["id"]] = d
    quotes_path = root / "config" / "quotes.yml"
    quotes = yaml.safe_load(quotes_path.read_text("utf-8"))["symbols"] if quotes_path.exists() else []
    football_path = root / "config" / "football.yml"
    football = yaml.safe_load(football_path.read_text("utf-8")) if football_path.exists() else None
    universes = load_universes(root)
    errors = check_universes(universes, domains)
    if errors:
        raise ValueError("univers invalides :\n" + "\n".join(errors))
    catalog = load_catalog(root, universes)
    return {"global": g, "domains": domains, "quotes": quotes, "football": football,
            "universes": universes, "catalog": catalog, "relations": load_relations(root, catalog)}
