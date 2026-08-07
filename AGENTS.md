# Freqtrade — Crypto Trading Bot

Open-source Python crypto trading bot. Supports backtesting, hyperopt, FreqAI (ML), dry-run/live trading, Telegram + WebUI control. Built on ccxt for exchange access.

## Project

- **Stack**: Python ≥3.9, SQLAlchemy + sqlite, ccxt, pandas, numpy, FastAPI
- **Entry point**: `freqtrade.main:main` → CLI `freqtrade` (or `python -m freqtrade`)
- **Package manager**: pip + setuptools (`setup.py` / `pyproject.toml`)
- **Config**: JSON config file (default `config.json`), env-var overrides

## Commands

```bash
# Install (editable dev)
pip install -e .

# Run the bot
freqtrade trade -c config.json
freqtrade trade -c config.json --dry-run

# Backtesting
freqtrade backtesting -c config.json --strategy SampleStrategy

# Hyperopt
freqtrade hyperopt -c config.json --strategy SampleStrategy

# Tests (with coverage)
pytest --random-order --cov=freqtrade --cov-config=.coveragerc tests/

# Single test file
pytest tests/test_main.py

# Lint / format / type-check
ruff check freqtrade/ tests/
mypy freqtrade/
isort --check freqtrade/ tests/
black --check freqtrade/ tests/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Architecture

| Module | Role |
|---|---|
| `freqtrade/main.py` | CLI entry point, arg parsing dispatch |
| `freqtrade/commands/` | Subcommand implementations (trade, backtesting, hyperopt, etc.) |
| `freqtrade/freqtradebot.py` | Main bot loop — order management, position tracking, signal processing |
| `freqtrade/exchange/` | Exchange abstraction (ccxt wrapper). `exchange.py` ≈154k. Per-exchange overrides in sibling files |
| `freqtrade/strategy/` | Strategy interface (`IStrategy`), hyper helpers, parameter definitions |
| `freqtrade/optimize/` | Backtesting engine + hyperopt optimization |
| `freqtrade/persistence/` | DB models (Trade, Order) via SQLAlchemy, migrations |
| `freqtrade/data/` | OHLCV data download, conversion, history |
| `freqtrade/rpc/` | Telegram bot + FastAPI WebUI server |
| `freqtrade/freqai/` | ML pipeline for adaptive strategy prediction |
| `freqtrade/plugins/` | Pairlist filters, trade protections |
| `freqtrade/resolvers/` | Dynamic class loading (strategies, pairlists, etc.) |
| `freqtrade/configuration/` | Config loading, validation, env-var resolution |
| `freqtrade/enums/` | Shared enums (RunMode, TradingMode, CandleType, etc.) |
| `divergex_flow/` | Separate divergence-detection helper (own CLI: `divergex`) |
| `ft_client/` | External freqtrade REST client |

## Conventions

- **Formatting**: Black + isort, **line-length 100**. Ruff for linting. Config in `pyproject.toml`.
- **Typing**: Type annotations required; mypy strict on `freqtrade/`, relaxed on `tests/`.
- **Exceptions**: All custom exceptions inherit from `FreqtradeException`. `OperationalException` stops the bot; `DependencyException` for transient issues.
- **Logging**: `logger = logging.getLogger(__name__)` or `logging.getLogger("freqtrade")` at module level.
- **Tests**: pytest with `asyncio_mode = "auto"`. Test files mirror `freqtrade/` tree under `tests/`. Shared fixtures in `tests/conftest.py`. Use `# pragma pylint: disable=missing-docstring` at the top of test files.
- **Docstrings**: Triple-double-quote docstrings on public modules/classes/functions. Test functions: descriptive names, docstrings optional.
- **No `os.path`** — use `pathlib.Path`.
- **Imports**: stdlib → third-party → first-party (`freqtrade`) with 2 blank lines after imports.

## Notes

<!-- Add project-specific notes, gotchas, or temporary context here. -->
