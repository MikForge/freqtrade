# DivergeX Freqtrade workflow

This is the first migration stage for the local DivergeX strategy workflow. It does not
change Redis, data_center, tradeX, ft-weblogic-server, or Telethon.

## Pinned model

The strategy requires `divergex.model_manifest` in the selected Freqtrade config. The
manifest pins every enabled divergence model by file path and SHA-256. Startup fails if
the setting, file, model key, or checksum is invalid. Runtime selection of
`latest_version` is intentionally unsupported.

Verify the currently pinned model:

```bash
python -m divergex_flow.cli model verify \
  --manifest user_data/divergex/models/MODEL-fc358577a097/model-manifest.json \
  --model-key REGULARPOSTIVE
```

## Experiment commands

The baseline experiment is
`user_data/divergex/configs/experiments/EXP-000-baseline.yaml`.

```bash
python -m divergex_flow.cli backtest run \
  --experiment user_data/divergex/configs/experiments/EXP-000-baseline.yaml

python -m divergex_flow.cli validate lookahead \
  --experiment user_data/divergex/configs/experiments/EXP-000-baseline.yaml

python -m divergex_flow.cli validate recursive \
  --experiment user_data/divergex/configs/experiments/EXP-000-baseline.yaml
```

Each command creates a new directory below `user_data/divergex/artifacts/runs/`, records
the exact argv and inputs, captures stdout/stderr, and writes a final status. Existing run
directories and final statuses are never overwritten. A failed command remains a failed
run and is not silently replaced by an older result.

Inspect a run:

```bash
python -m divergex_flow.cli artifacts inspect --run RUN-ID
```

`dry-run start` is available but intentionally requires an explicit experiment. It is a
foreground process and should only be invoked after backtest, lookahead, and recursive
checks pass.

## Current migration boundary

This stage pins the legacy `version_26` model as `MODEL-fc358577a097` and standardizes
Freqtrade execution artifacts. The legacy trainer still creates `version_N` directories;
training and model registration will be migrated next. Do not point a manifest at a newly
created model until it has been evaluated and registered with its checksum.
