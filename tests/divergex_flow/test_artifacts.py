import json
from pathlib import Path

import pytest

from divergex_flow.artifacts import ArtifactError, RunStore


def test_run_store_creates_immutable_manifest(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    run = store.create_run("backtest", {"experiment_id": "EXP-001"})

    manifest = json.loads((run.path / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == run.run_id
    assert manifest["stage"] == "backtest"
    assert manifest["status"] == "running"

    with pytest.raises(ArtifactError, match="already exists"):
        store.create_run("backtest", {}, run_id=run.run_id)


def test_run_completion_is_append_only_state_transition(tmp_path: Path) -> None:
    run = RunStore(tmp_path).create_run("lookahead", {})
    run.complete({"report": "lookahead.json"})

    status = json.loads((run.path / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "completed"

    with pytest.raises(ArtifactError, match="already finalized"):
        run.fail("cannot overwrite completion")
