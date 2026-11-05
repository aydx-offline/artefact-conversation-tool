import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Brand:
    voice: str
    rules: dict
    menus: dict
    catalog: list
    events: dict
    festivals: list


def load_brand(root: Path) -> Brand:
    def read_json(name):
        return json.loads((root / f"{name}.json").read_text(encoding="utf-8"))

    return Brand(
        voice=(root / "voice.md").read_text(encoding="utf-8"),
        rules=read_json("rules"),
        menus=read_json("menus"),
        catalog=read_json("catalog"),
        events=read_json("events"),
        festivals=read_json("festivals"),
    )
