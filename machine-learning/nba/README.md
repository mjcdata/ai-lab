# NBA Player Similarity — local season-based MVP

**Deployment readiness (2026-11-09):** CEO accepted the MVP and approved public deployment; no deployment has been performed. See [Vercel readiness and exact manual instructions](DEPLOYMENT.md). The app uses static snapshots; a fresh Git checkout lacks ignored build inputs. Rights clearance and Vercel plan/account eligibility remain unresolved.

**Current methodology (approved 2026-11-08):** Compare 2026–27 season-to-date players against historical **player-season** records from 1946–47 through 2025–26. Per-36 statistics only; PTS, REB, AST, STL, BLK and TOV have equal weight. No career-stage alignment, minute window, per-game mode, minimum games/minutes cutoff, predictive model, public deployment or scheduler.

## Calculation and eligibility

`seasonal.py` aggregates each player's regular-season game logs into one player-season, including all teams for traded players. Six-feature per-36 rates use total statistics × 36 / total minutes. Each eligible player-season contributes once to its season's **population** mean and standard deviation (ddof=0). Distances compare the current player's current-season Z-scores against each historical record's own-season Z-scores. A constant feature receives Z=0 and is recorded in the season coverage report.

The five smallest equal-weight Euclidean distances are returned, ordered deterministically by distance, season and player ID. Distinct **player-season records**, including multiple years of the same historical player, are allowed. The selected player's own prior seasons are excluded. No candidate minutes matching is performed. Explanations show all six raw per-36 values, each season's Z-scores and squared-distance contributions, which sum to distance squared.

A profile requires finite, nonnegative observations for every feature and minutes across all its source games, positive total minutes, valid dates and no unresolved duplicate player/game records. Missing historical statistics are **never zero-filled or extrapolated from a subset of games**. A zero-minute row with any positive six-stat count makes season rates unreliable under source whole-minute precision; the entire player-season is excluded. Zero-minute rows with all six counts zero may remain if total season minutes are positive. A positive but tiny sample remains eligible and carries exposure warnings. Duplicate conflicts exclude the entire affected player-season rather than silently shortening it. These are reliability checks, not exposure cutoffs.

Local `data/reports/season-profiles.json` records exclusions by player, season and reason, with counts, missingness and season scalers. `/coverage` exposes the same report locally. Reasons overlap; do not sum reason counts as unique exclusions. Fitting uses the eligible complete-case population, so missingness can bias the season normalization. Z-scores do not fully account for pace, roles, rules or data quality.

## Current local results

All **80 historical season caches** are present (1,389,756 raw rows); no historical fetch was needed for this change. Current-season availability was verified and 3,171 rows through **2026-11-08** were cached using the existing nba_api fetcher. There are 460 current player-seasons: **457 eligible**, 3 excluded. The historical pool has **19,134 eligible player-seasons**. Across history and current data, 6,605 player-seasons are excluded. The earliest usable complete six-stat profiles are from **1977–78**; having raw seasons back to 1946 does not imply comparisons can cover them.

Examples from the current frozen snapshot (lower distance is closer): Stephen Curry → Tracy McGrady 2003–04 (0.610); Nikola Jokić → Grant Hill 1996–97 (0.687); Anthony Edwards → Paul Pierce 2000–01 (0.450). Bronny James has only 12 observed minutes and illustrates unstable tiny-sample rates. These are descriptive statistical matches, not claims of equivalent ability or style. Complete historical game coverage has not been independently verified.

## Layout and local commands

- `code/src/nba_player_similarity/`: ingestion, season profiles, scoring, API and snapshot generation.
- `code/frontend/`: static Next.js application and desktop/mobile tests.
- `data/`: ignored local raw/derived data and quality reports.
- `artifacts/`: ignored generated immutable snapshots; tracked Markdown evaluation records.
- README, WORKPLAN and Python configuration remain at the project root. Use `uv` for the isolated Python environment.

From `machine-learning/nba/`, install dependencies with `uv sync --locked`; install frontend dependencies in `code/frontend/` using `pnpm install --frozen-lockfile`.

Verify/inventory historical caches without network:

```sh
uv run --offline python -m nba_player_similarity.ingestion
```

Explicit manual current-season acquisition/refresh (network; never run by build/API):

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.ingestion 2026-27 --download
# Only for an intentional update: add --refresh; old raw bytes are backed up.
```

Generate the season-based snapshot offline, then build/view locally:

```sh
uv run --offline python -m nba_player_similarity.season_snapshot
cd code/frontend
pnpm build
pnpm start
```

Open [the local app](http://127.0.0.1:3000). It loads individual `results/per36/<player_id>.json` files from one immutable release; there is no continuously running Python API dependency or client-side scoring. Search, six-stat reference/candidate grids, Z-score explanations, dates, games/minutes, exposure warnings and loading/error/empty states remain available. Reload an existing tab after refresh. `pnpm dev` stages the same snapshot for UI iteration.

Optional local API, from the NBA root:

```sh
uv run --offline uvicorn nba_player_similarity.api:app --host 127.0.0.1 --port 8000
```

[API docs](http://127.0.0.1:8000/docs): `/health`, `/players?q=...`, `/players/{id}`, `/players/{id}/comparisons`, `/coverage`. Only `mode=per36` is accepted; `per_game` is rejected. Missing historical/current caches fail explicitly without downloading or falling back to old data. The API reads the same raw sources and uses the same season model as snapshot generation.

Snapshots retain the existing versioned-release/atomic-pointer architecture. Schema v2 metadata includes generation time, current season, model/code version, all 81 raw source hashes, per-season eligibility counts, per-file checksums and per-36-only counts. Failed generation preserves the last valid release; a generation lock prevents concurrent activation. Missing source files, nonfinite JSON, parity errors, source changes or checksum failures prevent publication. Old schema-v1 prototype releases are retained for research rollback but rejected by the active frontend. Builds stage only one validated release, then export static HTML/JS/JSON; all generated data stay Git-ignored. No automation is configured.

The old `similarity.py`, `preparation.py`, `snapshot.py` and experimental reports are retained as **archived 2024–25 research/reproducibility tools**. Their checkpoint, scoring and export workflows are not used by the current app; shared numeric/date validation utilities are reused. Use `season_snapshot`, not the old `snapshot` command, for current application refreshes. Never serve a build-in-progress export or publish data without separate approval.

## Validation

```sh
# NBA root
uv run --offline python -m unittest discover -s code/tests -v
# Frontend directory
pnpm run test:unit
pnpm build
# With static server on port 3000; use the existing local browser cache on this Mac
PLAYWRIGHT_BROWSERS_PATH=/private/tmp/nba-playwright pnpm test
```

**Current validation:** 51 Python tests, 4 Node loader/staging tests and all 8 desktop/mobile browser cases passed; production static build passed. Initial browser attempts exposed test synchronization timing failures; after waiting explicitly for the roster/results to render, the full suite passed. The existing httpx/Starlette test transport deprecation warning remains.

Python tests cover aggregation, independent per-season normalization, unit scaling invariance, missing/zero-minute/duplicate exclusions, small exposures, own-player exclusion, repeated historical players across seasons, deterministic ties, sparse results, explanation identities, API parity and snapshot failure safety. Loader tests cover schema/identity validation, per-game rejection, aborts/retries and corrupt snapshot staging. Browser tests cover search, reference stats/explanations, historical season labels, removed mode controls, limited-exposure warnings, desktop/mobile layout and loading/error/empty states. Real-source API/snapshot parity was checked for Curry, Jokić, Bronny James, Edwards and LeBron James; all 81 source hashes stayed unchanged during generation and validation.

The following ingestion and DATA-2 notes retain historical context; any old checkpoint, per-game or fixed-scaler methodology below is superseded by the season-based method above.

## Historical ingestion (HIST-1, MacBook only)

The existing `nba_api` LeagueGameLog implementation supports all **80 regular seasons, 1946–47 through 2025–26**. No playoffs, current-season inputs, model changes or historical comparability assumptions are added. Run from `machine-learning/nba/`.

Read-only inventory (no optional NBA packages or network required):

```sh
uv run --offline python -m nba_player_similarity.ingestion
```

Download the first five missing seasons locally, only when you choose to start acquisition:

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.ingestion --download --start-season 1946-47 --end-season 2025-26 --batch-size 5
```

Repeat the same command for the next batch. Existing caches are structurally revalidated before being skipped; report existence alone is never trusted. Current inventory selects 1947–48 through 1951–52 first. `--batch-size` limits attempted season fetches (default 5), not cached seasons. You can also list explicit seasons instead of a range. Without `--download`, every invocation is read-only.

Each successful season is atomically saved to ignored `data/raw/YYYY-YY.json`; the next invocation resumes from those complete caches. An interrupted season is fetched again as a whole: the endpoint does not provide row-level resume. Three fetch attempts use bounded exponential backoff by default (`--attempts`, `--backoff`); `--delay` defaults to two seconds between seasons. Exhausted requests are recorded and the remaining selected seasons are attempted. Failed seasons remain missing and are retried on the next invocation. Missing optional packages fail immediately rather than retrying. Run one acquisition process at a time.

Invalid existing caches are flagged and preserved, never silently downloaded over. Inspect the error before explicitly using `--refresh` with selected seasons. A refresh retains the original raw bytes under `data/raw/backups/` before replacing them, and rejected new data never replaces an old cache. `--data-dir` selects another local root.

Per-season `data/reports/YYYY-YY.json` reports row counts, per-stat missing counts/percentages, duplicates/conflict rows, missing IDs, implausible minutes, invalid points and wrong-season records. Required columns are checked on every row. Null historical statistics and unresolved duplicates remain unchanged in raw records; duplicate exclusion remains a downstream preparation step. Structural warnings reject new caches; reports for those warnings are still written. Empty/malformed responses and fetch failures appear in unique `data/reports/batch-*.json` summaries, updated after every attempted season. On interruption, the last summary may be incomplete; raw caches are the resume authority. A per-season report describes the most recent validated/rejected payload, so inspect its source and warnings as well as the batch outcome.

Passing structural validation **does not prove complete historical coverage**, reliable early minutes or cross-era comparability. Cross-check coverage before career preparation. HIST-1 implementation does not complete full-history acquisition, impute missing values, or authorize public redistribution. All raw/prepared data, backups and generated reports remain local and Git-ignored.

Run offline tests:

```sh
uv run python -m unittest discover -s code/tests -v
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

The HIST-1 CLI defaults to read-only inventory; add `--download` to fetch missing seasons. See the batch/resume and explicit refresh procedures above. The direct Python `ingest()` call used in the offline cache audit also reuses existing files; the assertion above prevents missing pilot files from initiating network access.

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
  Current automated checks cover only required columns on every record,
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
uv run --offline python -m unittest discover -s code/tests -v
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
judgments. See [local representative results](artifacts/BASELINE_RESULTS.md).

## Local FastAPI service (WBS 5.1–5.2)

From `machine-learning/nba/`, install the locked project and test dependencies,
then start a loopback-only server using existing caches:

```sh
uv sync --locked
uv run --offline uvicorn nba_player_similarity.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive endpoint documentation.
The service loads local `data/raw/2024-25.json` for names and
`data/derived/2024-25.json` for checkpoints once at startup. Set `NBA_DATA_DIR`
to an absolute cache directory if launching elsewhere. Missing or invalid
caches stop startup with an actionable error; there is no download fallback.
Restart after intentionally updating local data. Import alone does not read data.
Dependency installation may access the package registry; serving and tests use
no live NBA API calls. On a fresh machine, sync dependencies before offline tests.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Ready status, season and eligible player count |
| `GET /players?q=Curry&limit=25&offset=0` | Case-insensitive name/ID substring search; paginated, alphabetically sorted |
| `GET /players/201939` | Select a player; latest eligible date, games and season minutes |
| `GET /players/201939/comparisons?mode=per36` | Up to five distinct comparisons with full explanations |

Selection/search also accept `mode=per36` or `mode=per_game`; per-36 is default.
Search/select include eligible players only. Unknown/ineligible IDs return 404;
invalid modes or pagination return 422. Pagination limit is 1–100. Comparison
responses retain existing model fields: `distance` (lower is closer), diagnostic
raw distance, checkpoint date/games/minutes, minute differences, six-stat values,
z-scores and squared-distance contributions, plus readable player names.
Reference exposure is in `reference`; candidate exposure is in each `checkpoint`.
Both modes reuse the original fixed-scaler policy and candidate eligibility.

Every response from the comparison endpoint warns about limited-exposure
instability, including possible zero-distance matches from tiny samples. No
new exposure threshold or confidence score is invented. Distances are not
probabilities; this is exploratory 2024–25 season similarity, not career matching.
All state is read-only after startup; model results are copied before decoration.
The frontend now reads static snapshots; this API remains available for local development. No database, data download, authentication, or deployment is included.
Use loopback only for this local development service.

```sh
uv run --offline python -m unittest discover -s code/tests -v
```

Offline API tests use temporary fixtures and FastAPI's in-process TestClient:
search/pagination, selection, both modes, direct model parity, error handling,
sparse/low-exposure cases and file preservation. Local real-cache checks also
verified exact model parity for Bronny James, Curry and Jokić in both modes.
The pinned Starlette TestClient currently emits an httpx deprecation warning;
all tests pass. The warning affects the test transport, not scoring or serving.
