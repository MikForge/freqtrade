from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from divergex_flow.artifacts import RunArtifact, RunStore


class WorkflowCommandError(ValueError):
    """Raised when a stage cannot be rendered as an explicit command."""


def build_freqtrade_command(stage: str, config: dict[str, Any]) -> list[str]:
    commands = {
        "backtest": "backtesting",
        "lookahead": "lookahead-analysis",
        "recursive": "recursive-analysis",
        "dry-run": "trade",
    }
    if stage not in commands:
        raise WorkflowCommandError(f"unsupported Freqtrade stage: {stage}")
    required = ("config", "strategy") if stage == "dry-run" else ("config", "strategy", "timerange")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise WorkflowCommandError(f"stage {stage} is missing: {', '.join(missing)}")
    command = [
        "freqtrade",
        commands[stage],
        "--config",
        str(config["config"]),
        "--strategy",
        str(config["strategy"]),
    ]
    if stage != "dry-run":
        command.extend(["--timerange", str(config["timerange"])])
    if stage == "backtest":
        command.extend(["--cache", "none", "--export", "trades"])
    for pair in config.get("pairs", []):
        command.extend(["--pairs", str(pair)])
    return command


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def execute_stage(
    stage: str,
    command: list[str],
    *,
    artifact_root: str | Path,
    cwd: str | Path,
    inputs: dict[str, Any],
) -> RunArtifact:
    run = RunStore(artifact_root).create_run(stage, inputs)
    _write_json(run.path / "command.json", {"argv": command, "cwd": str(Path(cwd).resolve())})
    logs = run.path / "logs"
    logs.mkdir()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    (logs / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (logs / "stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode == 0:
        run.complete({"stdout": "logs/stdout.log", "stderr": "logs/stderr.log"})
    else:
        run.fail("stage command failed", result.returncode)
    return run
