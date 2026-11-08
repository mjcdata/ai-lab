# NBA player similarity

Minimal Python project for the [project work plan](WORKPLAN.md).
Requires Python 3.12 or newer and `uv`.

From this directory, install the project into its isolated environment:

```sh
uv sync
```

Run the lightweight import smoke test with Python's standard-library test runner:

```sh
uv run python -m unittest discover -s code/tests -v
```

The package uses a `code/src/` layout. The season-scoped baseline is implemented; full career-history modeling remains future work.


## Project layout and complete local application

```text
nba/
├── code/
│   ├── src/nba_player_similarity/   # Python preparation, model and API
│   ├── tests/                      # Python offline tests
│   └── frontend/                   # Next.js React app and browser tests
├── data/                           # Local raw/derived caches and lineage reports (ignored)
├── artifacts/                      # Tracked evaluation reports; ignored generated experiment/model outputs
├── README.md
├── WORKPLAN.md
├── pyproject.toml
└── uv.lock
```

Python package names/imports and the API contract are unchanged. `uv` now builds
from `code/src`; test discovery uses `code/tests`. Existing raw/prepared caches
and lineage reports remain in `data/`. The generated scaler sensitivity JSON
moved to `artifacts/scaler_experiment.json` without changing its contents.
Baseline/evaluation Markdown reports moved into `artifacts/` and remain tracked;
future generated model/scaler binaries, screenshots and evaluation outputs there
are ignored. There are no persisted trained model files to migrate.

### Build and view the static application

One-time dependency setup (package downloads only, no NBA acquisition):

```sh
# From machine-learning/nba/:
uv sync --locked
# From code/frontend/:
pnpm install --frozen-lockfile
```

Generate and validate a local immutable snapshot, then export Next.js:

```sh
# From machine-learning/nba/:
uv run --offline python -m nba_player_similarity.snapshot
cd code/frontend
pnpm build
pnpm start
```

Open **http://127.0.0.1:3000**. `pnpm start` serves `out/` using Python's static
HTTP server; there is no Next.js runtime server or Python model API dependency.
FastAPI remains available independently from the NBA root:

```sh
uv run --offline uvicorn nba_player_similarity.api:app --host 127.0.0.1 --port 8000
```

Optional API docs: **http://127.0.0.1:8000/docs**. `pnpm dev` stages the same
validated snapshot before starting Next.js for UI iteration. The static UI does
not proxy to FastAPI. Local generated datasets and snapshot assets stay ignored.
No accounts, public upload, paid service or recurring automation are configured.

On this Mac, if commands are absent from PATH, use the installed tools:

```sh
export PATH="$HOME/.local/bin:$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback:$PATH"
```

### Snapshot layout, refresh and failure safety

`artifacts/snapshots/current.json` is a small atomic pointer to an immutable
`releases/<snapshot_id>/` directory. Each release has `manifest.json`,
`players.json`, and **one `results/<mode>/<player_id>.json` file per player/mode**.
The actual local release contains 569 players / 1,138 comparison records. No
single bulk-results payload is loaded by the browser. The player index is
searched/paginated locally, with one coherent release pinned per page session.
The UI continues to show both modes, reference stats, scores, six-feature
explanations, dates/exposure, warnings and all loading/error/empty states.
`page.jsx` manages state; `components/` retains the existing logical boundaries.

The manifest records schema version, UTC generation timestamp, season, model
version/code digest, source hashes, modes/counts and each file's size/SHA-256.
The model version combines the approved baseline identifier with a digest of
scoring/preparation/response code. Generation uses the unchanged scoring model
and a shared response formatter also used by FastAPI, avoiding divergent data
contracts. No frontend calculations approximate or rerank model results.

For a refresh, first obtain/prepare any approved source updates through the
existing local workflow. Snapshot generation itself **never downloads or
prepares NBA data**. Then run the same generator/build commands above; no
scheduler is enabled. The CLI also accepts `--data-dir` and `--output-dir` for
future automated invocations. Only the approved 2024–25 season is accepted;
adding a new season still requires a scope decision and UI/data updates.
Set `NBA_SNAPSHOT_DIR` to an absolute artifact snapshot root when building from
another approved artifact location.

Generation writes into a staging directory under the snapshot root while
holding `.generation-lock`. It validates every player/mode against the complete
API-shaped payload, checks counts/eligibility/explanations, serializes finite
JSON, re-reads checksums, and confirms sources stayed unchanged. Only then is
the release made immutable and `current.json` atomically replaced. Partial
computation, bad data, parity failures or activation failure leave the previous
pointer and release intact. Old releases are retained for rollback; no automatic
pruning occurs. Concurrent runs fail rather than race. After a killed process,
inspect for a live generator before manually removing a stale lock/staging dir.
An orphan fully generated release after a failed activation is safe to retain.
This protects against process failure; it is not a substitute for disk backups.

`pnpm build` first verifies the active manifest and every indexed file, stages
only that complete release into ignored `public/snapshots/`, then creates a
fully static `out/`. A fresh checkout without a local snapshot fails clearly
instead of attempting NBA downloads or building an empty site. Cloud builds
would need an explicitly supplied snapshot artifact. No GitHub automation or
workflow is configured to generate/deploy data. No public build should be
uploaded before separate deployment permission and redistribution review.

Keep the immutable artifacts for rollback; restore a verified prior manifest
and pointer with an atomic replacement, then rebuild. Serve a completed `out/`
directory, never a build-in-progress directory. Publication/version rollout is
not configured. An already open tab pins its release; if a later deployment no
longer contains that release, reload the page to select the new snapshot. The
loader reports a retry/refresh error rather than silently mixing versions.

### Tests

```sh
# NBA root:
uv run --offline python -m unittest discover -s code/tests -v
# Frontend directory:
pnpm run test:unit
# With the static export serving on port 3000:
pnpm exec playwright install chromium
pnpm test
```

The browser install is test tooling, not NBA data. This Mac's existing temporary
browser can be reused with `PLAYWRIGHT_BROWSERS_PATH=/private/tmp/nba-playwright`.
Validation: **40 Python tests**, **4 Node loader/build-staging tests**, and **8
desktop/mobile Playwright cases** pass. Failure injection covers partial
snapshot generation, parity corruption and atomic-pointer activation failures.
All 1,138 real result files were checked for exact complete JSON parity against
FastAPI via in-process TestClient. Source cache hashes remain unchanged. The
static browser suite ran with FastAPI stopped and rejects runtime `/api/`
requests; both modes, reference stats, explanations/warnings, search, retries,
loading and empty states pass. Next.js build produces no dynamic routes.

## Historical ingestion pilot (MacBook only)

The NBA Stats endpoint timed out in GitHub Codespaces. Run live ingestion from the MacBook, not CI:

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.ingestion 1946-47 1977-78 2024-25
```

This writes `data/raw/YYYY-YY.json` and `data/reports/YYYY-YY.json`. Raw JSON preserves missing historical statistics as `null`; no imputation is performed. The cache is reused on subsequent runs; use `--refresh` only to explicitly re-fetch a season. Each season is saved independently so interrupted runs can resume.

Reports include record counts, per-stat missingness, duplicate player/game pairs, missing IDs, invalid points and implausible minutes. Structural errors stop caching. A successful report is **not** proof of historical completeness: cross-check season totals and early minutes independently before building comparisons. The pilot does not automatically retrieve NBA history or authorize redistribution of NBA data.

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
