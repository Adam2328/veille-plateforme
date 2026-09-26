import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config(root=ROOT):
    root = pathlib.Path(root)
    g = yaml.safe_load((root / "config" / "global.yml").read_text("utf-8"))
    domains = {}
    for path in sorted((root / "config" / "domains").glob("*.yml")):
        d = yaml.safe_load(path.read_text("utf-8"))
        domains[d["id"]] = d
    return {"global": g, "domains": domains}
