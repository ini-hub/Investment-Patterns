"""Settings loading. Defaults live in default.yaml next to this file."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_PATH = Path(__file__).with_name("default.yaml")


def _deep_update(base: dict, overrides: dict) -> dict:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict:
    """Return the default settings, optionally merged with a YAML file and a dict of overrides."""
    with open(_DEFAULT_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if path is not None:
        with open(path, encoding="utf-8") as fh:
            _deep_update(cfg, yaml.safe_load(fh) or {})
    if overrides:
        _deep_update(cfg, copy.deepcopy(overrides))
    return cfg


def settings_hash(cfg: dict) -> str:
    """Short, stable fingerprint of a settings dict, so two reports can be checked for identical settings."""
    payload = json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
