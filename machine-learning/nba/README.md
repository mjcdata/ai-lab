# NBA player similarity

Minimal Python project for the [project work plan](WORKPLAN.md).
Requires Python 3.12 or newer and `uv`.

From this directory, install the project into its isolated environment:

```sh
uv sync
```

Run the lightweight import smoke test with Python's standard-library test runner:

```sh
uv run python -m unittest discover -s tests -v
```

The package uses a `src/` layout. The similarity methodology is not implemented yet.

## Historical ingestion pilot (MacBook only)

The NBA Stats endpoint timed out in GitHub Codespaces. Run live ingestion from the MacBook, not CI:

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.ingestion 1946-47 1977-78 2024-25
```

This writes `data/raw/YYYY-YY.json` and `data/reports/YYYY-YY.json`. Raw JSON preserves missing historical statistics as `null`; no imputation is performed. The cache is reused on subsequent runs; use `--refresh` only to explicitly re-fetch a season. Each season is saved independently so interrupted runs can resume.

Reports include record counts, per-stat missingness, duplicate player/game pairs, missing IDs, invalid points and implausible minutes. Structural errors stop caching. A successful report is **not** proof of historical completeness: cross-check season totals and early minutes independently before building comparisons. The pilot does not automatically retrieve NBA history or authorize redistribution of NBA data.

Run offline tests:

```sh
uv run python -m unittest discover -s tests -v
```

Local `data/` is ignored by Git.
