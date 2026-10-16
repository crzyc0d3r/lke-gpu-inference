"""Render the NodeBalancer firewall annotation before applying any Service."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def render(firewall_id: int) -> str:
    if firewall_id <= 0:
        raise ValueError("firewall_id must be a positive integer")
    template = Path(__file__).parent / "manifests" / "stack.yaml.template"
    content = template.read_text(encoding="utf-8").replace("__FIREWALL_ID__", str(firewall_id))
    documents = list(yaml.safe_load_all(content))
    if len(documents) != 5:
        raise ValueError("Expected namespace, volume, deployment, service, and network policy")
    return content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firewall-id", type=int, required=True)
    parser.add_argument("--output", type=Path, default=Path("rendered/stack.yaml"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(args.firewall_id), encoding="utf-8")
    print(args.output)

