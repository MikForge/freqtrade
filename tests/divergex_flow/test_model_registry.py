import hashlib
import json
from pathlib import Path

import pytest

from divergex_flow.model_registry import ModelManifestError, resolve_model_bundle


def _write_manifest(tmp_path: Path, model_path: Path, sha256: str) -> Path:
    manifest = tmp_path / "model-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "model_id": "MODEL-test",
                "models": {
                    "REGULARPOSTIVE": {
                        "path": str(model_path),
                        "sha256": sha256,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_model_bundle_requires_explicit_manifest(tmp_path: Path) -> None:
    with pytest.raises(ModelManifestError, match="model manifest"):
        resolve_model_bundle(None, "REGULARPOSTIVE", base_dir=tmp_path)


def test_model_bundle_resolves_and_verifies_hash(tmp_path: Path) -> None:
    model = tmp_path / "model.pkl"
    model.write_bytes(b"stable-model")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    manifest = _write_manifest(tmp_path, model, digest)

    resolved = resolve_model_bundle(manifest, "REGULARPOSTIVE", base_dir=tmp_path)

    assert resolved.model_id == "MODEL-test"
    assert resolved.path == model.resolve()
    assert resolved.sha256 == digest


def test_model_bundle_rejects_hash_mismatch(tmp_path: Path) -> None:
    model = tmp_path / "model.pkl"
    model.write_bytes(b"changed-model")
    manifest = _write_manifest(tmp_path, model, "0" * 64)

    with pytest.raises(ModelManifestError, match="checksum mismatch"):
        resolve_model_bundle(manifest, "REGULARPOSTIVE", base_dir=tmp_path)
