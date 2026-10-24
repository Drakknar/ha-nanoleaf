"""Build translations/en.json from strings.json.

Custom integrations only load translations/<lang>.json, and Home Assistant
resolves [%key:...%] references only for core integrations. This resolves them
the same way, against Home Assistant's common strings.

Usage: python scripts/build_translations.py [HA version, default: dev]
"""

import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen

COMPONENT = Path(__file__).parent.parent / "custom_components" / "nanoleaf"
COMMON_URL = (
    "https://raw.githubusercontent.com/home-assistant/core/{ref}/homeassistant/strings.json"
)
KEY = re.compile(r"\[%key:([a-z0-9_:]+)%\]")


def lookup(tree: dict, path: list[str]) -> str:
    """Return the string at a :: separated path."""
    node = tree
    for part in path:
        node = node[part]
    if not isinstance(node, str):
        raise TypeError(f"{'::'.join(path)} is not a string")
    return node


def resolve(value: str, common: dict, own: dict) -> str:
    """Replace every reference in a string, recursively."""

    def replace(match: re.Match[str]) -> str:
        path = match.group(1).split("::")
        if path[0] == "common":
            target = lookup(common["common"], path[1:])
        elif path[:2] == ["component", "nanoleaf"]:
            target = lookup(own, path[2:])
        else:
            raise ValueError(f"Unsupported reference {match.group(0)}")
        return resolve(target, common, own)

    return KEY.sub(replace, value)


def walk(node, common: dict, own: dict):
    """Resolve all strings in a tree."""
    if isinstance(node, dict):
        return {key: walk(value, common, own) for key, value in node.items()}
    return resolve(node, common, own)


def main() -> None:
    """Write translations/en.json."""
    ref = sys.argv[1] if len(sys.argv) > 1 else "dev"
    with urlopen(COMMON_URL.format(ref=ref)) as response:
        common = json.load(response)
    own = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    out = COMPONENT / "translations" / "en.json"
    out.write_text(
        json.dumps(walk(own, common, own), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
