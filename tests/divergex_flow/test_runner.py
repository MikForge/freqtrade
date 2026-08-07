import json
from pathlib import Path

from divergex_flow.runner import build_freqtrade_command, execute_stage


def test_build_backtest_command_is_fully_explicit() -> None:
    command = build_freqtrade_command(
        "backtest",
        {
            "config": "user_data/config_dev.json",
            "strategy": "LiveDivSignalStrategy",
            "timerange": "20240101-20240201",
            "pairs": ["BTC/USDT:USDT"],
        },
    )

    assert command == [
        "freqtrade",
        "backtesting",
        "--config",
        "user_data/config_dev.json",
        "--strategy",
        "LiveDivSignalStrategy",
        "--timerange",
        "20240101-20240201",
        "--cache",
        "none",
        "--export",
        "trades",
        "--pairs",
        "BTC/USDT:USDT",
    ]


def test_execute_stage_records_command_and_result(tmp_path: Path) -> None:
    run = execute_stage(
        "test",
        ["python", "-c", "print('ok')"],
        artifact_root=tmp_path,
        cwd=tmp_path,
        inputs={"experiment_id": "EXP-TEST"},
    )

    assert json.loads((run.path / "status.json").read_text())["status"] == "completed"
    assert (run.path / "logs" / "stdout.log").read_text().strip() == "ok"
    assert json.loads((run.path / "command.json").read_text())["argv"][0] == "python"
