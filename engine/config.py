import pathlib

import yaml

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
    return {"global": g, "domains": domains, "quotes": quotes}
