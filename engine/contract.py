import json
import pathlib

from jsonschema import Draft202012Validator

_SCHEMA = json.loads(
    (pathlib.Path(__file__).resolve().parent.parent / "schemas" / "public.schema.json").read_text("utf-8")
)


def validate(kind: str, instance: dict) -> None:
    """Lève jsonschema.ValidationError si `instance` ne respecte pas le contrat `kind`."""
    Draft202012Validator({"$ref": f"#/$defs/{kind}", "$defs": _SCHEMA["$defs"]}).validate(instance)
