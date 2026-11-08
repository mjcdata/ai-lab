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

The package uses a `src/` layout. The season-scoped baseline is implemented; full career-history modeling remains future work.

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

## Pilot lineage and cache review

The user reported successful MacBook retrievals on 2026-11-05 using
`nba_api.stats.endpoints.leaguegamelog.LeagueGameLog`, with player logs
(`player_or_team_abbreviation="P"`) and `season_type_all_star="Regular Season"`.
The pilot contains 6,508 rows for 1946-47, 17,768 for 1977-78, and 26,306 for
2024-25 (50,582 total). These are user-reported acquisition results, not an
independent audit of the local files. Detailed missingness is recorded in
[the work plan](WORKPLAN.md).

The lineage is endpoint response → pandas scalar/null normalization → raw
JSON records → validation report. Missing values become JSON `null`; no
statistics are filled and duplicate records remain in raw storage. Reports
are regenerated from those records. Their `source` field describes the current
run (`nba_api` or `cache`), not the original acquisition time. The current
format does not capture retrieval timestamps, dependency versions, hashes,
or the unnormalized HTTP response. Preserve the original cache and record
these details separately during a local quality review; they cannot be
reconstructed from a report alone.

### Re-run from existing files without network access

From this project directory, the following validates all three caches and
regenerates reports. It fails if any cache is absent; the injected fetcher
prevents accidental acquisition:

```sh
uv run python - <<'PY'
from pathlib import Path
from nba_player_similarity.ingestion import PILOT, ingest

def offline_only(season):
    raise RuntimeError(f"Missing cache for {season}; offline review only")

for season in PILOT:
    print(ingest(season, Path("data"), fetcher=offline_only))
PY
```

The ingestion CLI reuses existing season files but fetches missing ones.
Interrupted acquisition resumes by retaining completed season files; there is
no partial-season resume. `--data-dir` selects another cache root. `--refresh`
fetches again and replaces an existing raw file after validation, so preserve
the original files before a user-authorized refresh. Reports are overwritten
on a successful run; validation failures raise an error and may leave an older
report in place. Inspect the error and raw records rather than treating that
older report as evidence of a successful run.

### Unresolved duplicate policy

Player/game identity uses `PLAYER_ID` and `GAME_ID`, compared as strings.
`duplicate_player_game_rows` counts excess rows (group size minus one), while
`duplicate_conflict_rows` lists selected fields for every row in each repeated
group. Consult raw records for fields omitted from the report.
The known 1946-47 John Murphy conflict for game `0024600076` has PHW and NYK
records; no team assignment has been resolved.

Future derived datasets must call `exclude_unresolved_duplicates(rows)` before
aggregation. It excludes **all** rows in repeated player/game groups, including
identical duplicates, and preserves order and values for the remaining records.
It leaves the raw input unchanged. This helper does not resolve conflicts or
certify other data quality; the preparation module applies this policy before computing totals.
Any resolution needs independently reviewed evidence before those records can
be reintroduced.

### Historical quality review checklist

The user performs independent source evaluation and totals comparisons with
ChatGPT. Before feature preparation, record the evidence and unresolved gaps:

- Confirm cached row counts and report missing counts/percentages agree;
  distinguish nulls from observed zeros for every statistic and era.
- Review missing player/game IDs, dates and season assignments, negative or
  nonnumeric statistics, and minutes plausibility, including early-era minutes.
  Current automated checks cover only required columns on the first record,
  missing player/game IDs, minutes in 0–70, and nonnegative numeric points;
  they do not establish complete schema or historical correctness.
- Inspect every repeated player/game group in raw data; retain unresolved
  conflicts in the cache and exclude them from future aggregates.
- Independently reconcile player/team season games, minutes and available
  counting totals against user-reviewed sources; record the source, access date,
  expected totals, discrepancies and conclusions. Assess missing games and
  players as well as missing fields; a zero-null report does not prove coverage.
- Record cache provenance, local environment versions and any changes between
  retrievals. Document unresolved early-era coverage and minutes limitations
  before deciding comparison eligibility under the approved methodology.

Full historical acquisition and independent completeness validation remain open
under WBS 1.6. These offline checks do not complete either activity.

## DATA-2: offline pilot preparation

From this directory, with the three existing MacBook caches present:

```sh
uv run --offline python -m nba_player_similarity.preparation --data-dir data
uv run --offline python -m unittest discover -s tests -v
```

Preparation has no fetch fallback. It requires all three nonempty raw caches,
checks regular-season SEASON_ID against each filename, and writes only
`data/derived/{season}.json` and `data/derived/quality.json`. The summary records
raw SHA-256 hashes, input/output/excluded counts, unusable metric counts and
usable-minute checkpoint counts. Reruns deterministically replace derived files;
raw bytes are untouched. A failed run is not validation of older output files.

`cumulative(rows)` excludes every repeated player/game group, rejects missing
identifiers and invalid dates, and sorts by player, date, then game ID. Dates
accept ISO dates and NBA-style `OCT 01, 2024`. Totals reset for each player/season.
Games count retained observations, not verified scheduled appearances. No missing
games are inferred. `observed_totals` are partial sums with explicit `coverage`
counts; entirely unavailable totals are null. Missing, negative, nonnumeric,
boolean and nonfinite metric values are unusable, never filled with zero.
Cumulative minutes are null after any unusable minute observation. Per-36 rates
require positive complete observed minutes and full observed-game coverage for
each feature; per-game rates likewise require complete feature coverage.
Original minute values are summed without rounding or inventing fractions.
Whole-minute source precision can cause discrepancies with published totals.

`match_checkpoints` selects the nearest eligible minute checkpoint per player
inside the approved inclusive ±10% target window. Equal-distance ties use earliest
date then game ID. Default eligibility requires all six features; callers may
explicitly supply an era-appropriate nonempty subset of the approved six, with
complete coverage for every selected feature. It rejects mixed season scopes.
This is minute-checkpoint selection only, not nearest-neighbor similarity scoring.

Pilot seasons are nonconsecutive samples, **not complete careers**. The module
never combines them into pilot career checkpoints. Full-history use requires
`cumulative(..., scope="career", complete_history=True)`; that assertion must
come from independently acquired complete history, not this pilot. Excluded
records conservatively invalidate career matching for the entire supplied set.
Even fully observed retained data does not establish historical completeness.
Zero-minute early-era checkpoints remain in derived audit output but cannot match.

Validation here used synthetic offline fixtures (20 total suite tests), including
three-season file processing, reproducibility and byte-for-byte raw preservation.
The actual MacBook pilot caches were not present in the cloud checkout; no actual
pilot quality counts or processed dataset are claimed. Run the command above
locally to obtain them. No data acquisition or model training is part of DATA-2.

## Season-scoped similarity baseline

From this project directory, run against existing derived data:

```sh
uv run --offline python -m nba_player_similarity.similarity 1630162
uv run --offline python -m nba_player_similarity.similarity 1630162 --mode per_game
```

Default: six per-36 features (PTS/AST/REB/STL/BLK/TOV), fixed population z-score
scaler using one latest eligible checkpoint per player, equal-weight Euclidean
distance. Zero-variance scales are 1. Each query uses the selected player's
latest eligible checkpoint; each other player contributes its nearest eligible
checkpoint within inclusive ±10% cumulative season minutes, before scoring.
Minute ties use earliest date/game; distance ties use PLAYER_ID. Return five
unique other players, or fewer with a shortage explanation; never widen the
window. Per-game mode is separately standardized and remains optional.

Output includes dates, games/minutes, minute differences, feature values,
z-scores, differences and squared-distance contributions. These contributions
sum to squared distance. Smaller distance means closer, not a probability.
Raw distance is diagnostic only. Complete feature coverage and positive usable
minutes are required; missing or invalid values are never filled with zero.
All queries warn about low-exposure instability; no extra exposure cutoff applies.

This is retrospective season-to-date similarity, not career matching or
predictive evaluation. The end-of-season scaler is not a leakage-free predictive
benchmark. No early-era samples are included. Shooting efficiency and position
are outside the six-feature model: results are not complete style/quality
judgments. See [local representative results](BASELINE_RESULTS.md).
