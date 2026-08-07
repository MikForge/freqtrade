from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ArtifactError(RuntimeError):
    """Raised when an immutable artifact contract would be violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_run_id(stage: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{stage}-{secrets.token_hex(4)}"


def _write_new_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise ArtifactError(f"artifact already exists: {path}") from exc


@dataclass
class RunArtifact:
    run_id: str
    path: Path

    @property
    def _status_path(self) -> Path:
        return self.path / "status.json"

    def _finalize(self, status: str, details: dict[str, Any]) -> None:
        if self._status_path.exists():
            raise ArtifactError(f"run {self.run_id} is already finalized")
        _write_new_json(
            self._status_path,
            {"run_id": self.run_id, "status": status, "finished_at": utc_now(), **details},
        )

    def complete(self, outputs: dict[str, Any] | None = None) -> None:
        self._finalize("completed", {"outputs": outputs or {}})

    def fail(self, error: str, exit_code: int | None = None) -> None:
        self._finalize("failed", {"error": error, "exit_code": exit_code})


class RunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def create_run(
        self,
        stage: str,
        inputs: dict[str, Any],
        *,
        run_id: str | None = None,
    ) -> RunArtifact:
        selected_id = run_id or make_run_id(stage)
        path = self.root / "runs" / selected_id
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ArtifactError(f"run already exists: {selected_id}") from exc
        _write_new_json(
            path / "run_manifest.json",
            {
                "schema_version": 1,
                "run_id": selected_id,
                "stage": stage,
                "status": "running",
                "started_at": utc_now(),
                "inputs": inputs,
            },
        )
        return RunArtifact(selected_id, path)

    def inspect(self, run_id: str) -> dict[str, Any]:
        path = self.root / "runs" / run_id
        manifest_path = path / "run_manifest.json"
        if not manifest_path.is_file():
            raise ArtifactError(f"run does not exist: {run_id}")
        result = json.loads(manifest_path.read_text(encoding="utf-8"))
        status_path = path / "status.json"
        if status_path.is_file():
            result["final"] = json.loads(status_path.read_text(encoding="utf-8"))
        return result
