"""Load YAML configuration once and expose typed accessors."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent / "config"


@functools.lru_cache(maxsize=None)
def _load(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def checklists() -> dict[str, Any]:
    """Return the parsed checklists.yaml."""
    return _load("checklists.yaml")


def rules() -> dict[str, Any]:
    """Return the parsed rules.yaml."""
    return _load("rules.yaml")