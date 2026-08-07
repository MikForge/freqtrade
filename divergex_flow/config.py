from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ExperimentConfigError(ValueError):
    """Raised when an experiment configuration is incomplete."""


def load_experiment(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise ExperimentConfigError(f"experiment does not exist: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ExperimentConfigError("experiment must be a YAML mapping")
    required = ("experiment_id", "model_manifest", "freqtrade")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ExperimentConfigError(f"experiment is missing: {', '.join(missing)}")
    freqtrade = payload["freqtrade"]
    if not isinstance(freqtrade, dict):
        raise ExperimentConfigError("freqtrade must be a mapping")
    for key in ("config", "strategy", "timerange"):
        if not freqtrade.get(key):
            raise ExperimentConfigError(f"freqtrade.{key} is required")
    payload["_config_path"] = str(config_path)
    return payload
