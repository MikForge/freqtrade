from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from divergex_flow.artifacts import ArtifactError, RunStore
from divergex_flow.config import ExperimentConfigError, load_experiment
from divergex_flow.model_registry import ModelManifestError, load_model_manifest, resolve_model_bundle
from divergex_flow.runner import WorkflowCommandError, build_freqtrade_command, execute_stage


DEFAULT_ARTIFACT_ROOT = Path("user_data/divergex/artifacts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="divergex")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    groups = parser.add_subparsers(dest="group", required=True)

    artifacts = groups.add_parser("artifacts")
    artifacts_commands = artifacts.add_subparsers(dest="command", required=True)
    inspect = artifacts_commands.add_parser("inspect")
    inspect.add_argument("--run", required=True)

    model = groups.add_parser("model")
    model_commands = model.add_subparsers(dest="command", required=True)
    verify = model_commands.add_parser("verify")
    verify.add_argument("--manifest", required=True, type=Path)
    verify.add_argument("--model-key")

    backtest = groups.add_parser("backtest")
    backtest_commands = backtest.add_subparsers(dest="command", required=True)
    backtest_run = backtest_commands.add_parser("run")
    backtest_run.add_argument("--experiment", required=True, type=Path)

    validate = groups.add_parser("validate")
    validate_commands = validate.add_subparsers(dest="command", required=True)
    for validation in ("lookahead", "recursive"):
        validation_parser = validate_commands.add_parser(validation)
        validation_parser.add_argument("--experiment", required=True, type=Path)

    dry_run = groups.add_parser("dry-run")
    dry_run_commands = dry_run.add_subparsers(dest="command", required=True)
    dry_run_start = dry_run_commands.add_parser("start")
    dry_run_start.add_argument("--experiment", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.group == "artifacts" and args.command == "inspect":
            print(json.dumps(RunStore(args.artifact_root).inspect(args.run), indent=2, ensure_ascii=False))
            return 0
        if args.group == "model" and args.command == "verify":
            if args.model_key:
                resolved = resolve_model_bundle(args.manifest, args.model_key)
                result = {
                    "model_id": resolved.model_id,
                    "model_key": args.model_key,
                    "path": str(resolved.path),
                    "sha256": resolved.sha256,
                }
            else:
                manifest_path, payload = load_model_manifest(args.manifest)
                result = {
                    "model_id": payload["model_id"],
                    "manifest": str(manifest_path),
                    "model_keys": sorted(payload["models"]),
                }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        stage = None
        if args.group == "backtest" and args.command == "run":
            stage = "backtest"
        elif args.group == "validate" and args.command in {"lookahead", "recursive"}:
            stage = args.command
        elif args.group == "dry-run" and args.command == "start":
            stage = "dry-run"
        if stage:
            experiment = load_experiment(args.experiment)
            resolve_model_bundle(experiment["model_manifest"], "REGULARPOSTIVE", base_dir=Path.cwd())
            command = build_freqtrade_command(stage, experiment["freqtrade"])
            run = execute_stage(
                stage,
                command,
                artifact_root=args.artifact_root,
                cwd=Path.cwd(),
                inputs={
                    "experiment_id": experiment["experiment_id"],
                    "experiment_config": experiment["_config_path"],
                    "model_manifest": experiment["model_manifest"],
                },
            )
            print(run.run_id)
            status = json.loads((run.path / "status.json").read_text(encoding="utf-8"))
            return 0 if status["status"] == "completed" else 1
    except (ArtifactError, ExperimentConfigError, ModelManifestError, WorkflowCommandError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
