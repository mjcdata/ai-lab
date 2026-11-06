# NBA Player Similarity — Work Breakdown Structure (WBS)

**Project:** AI Lab / Machine Learning / NBA  
**Status:** Source approved; three-season pilot ingested; historical pilot limitations accepted; data preparation next  
**Execution:** User manually launches Codex for approved implementation tasks; user approves major decisions. GitHub Actions performs tests only.

## Goal and scope

Build a public React + Python application that returns the **top five historical NBA player comparisons** for a selected player. Compare players at approximately the same **cumulative regular-season career minutes**, using the latest available career checkpoint by default. Include NBA history back to 1946–47 **where reliable game-level data permits**.

**Version 1:** ±10% cumulative-minutes matching (initial proposal); six features (points, assists, rebounds, steals, blocks, turnovers) when jointly available, otherwise era-aware comparisons; per-36 rates by default, with per-game option; standardized equal-weight nearest-neighbor baseline; interpretable results. Handle missing historical statistics explicitly, never as zeros. Assess whether incomplete eras can be compared fairly.

## Approved implementation tasks

- [x] **SETUP-1** Create a minimal Python project in `machine-learning/nba/` using `uv`: add `pyproject.toml`, a small importable package, and one lightweight smoke test. Keep dependencies minimal; document commands to install and run tests. Do not fetch data, research sources, train models, or change the planned similarity methodology.
  - Implementation added: `pyproject.toml`, `src/nba_player_similarity/`, a standard-library smoke test, and setup/test commands in `README.md`. Source-tree smoke test passed with `PYTHONPATH=src python -m unittest discover -s tests -v`; TOML metadata and package layout checks passed. Completed validation in GitHub Codespaces (2026-11-05): `uv sync` successfully built and installed `nba-player-similarity==0.1.0`; `uv run python -m unittest discover -s tests -v` passed (1 test, 0 failures).

## Source research decision — approved 2026-11-05

- Primary source: `swar/nba_api` `LeagueGameLog` regular-season player logs; era-aware comparisons approved.
- MacBook retrievals succeeded: 1946-47 (6,508 rows), 1951-52 (6,086), 1965-66 (6,855), 1973-74 (13,380), 1977-78 (17,768), 1985-86 (19,387), 2024-25 (26,306). Codespaces requests timed out; live acquisition runs locally.
- Missing data observed: 1946-47 REB 6508, AST 6377, STL/BLK/TOV 6508; 1951-52 REB 5784, AST 5257, STL/BLK/TOV 6086; 1965-66 AST 945, REB 518, STL/BLK/TOV 6855; 1973-74 REB 1044, AST 1133, STL 9682, BLK 9240, TOV 13379; 1977-78 REB 76, AST 314, STL 5813, BLK 5019, TOV 8848; 1985-86 AST 5, REB/STL/BLK/TOV 6. MIN and PTS had no nulls in these samples, but early minutes still require independent validation.
- Risks: incomplete historical game logs, cloud IP blocking, throttling, uncertain early minutes, upstream changes. Preserve missing values; validate completeness, duplicates, minutes plausibility, and cross-check independent totals before modeling.
- Alternative sources remain fallbacks. Public redistribution/licensing requires separate review before deployment.
- **DATA-1 pilot implemented and locally executed:** CLI, per-season raw JSON cache, structural and missingness reports. Pilot seasons: 1946-47, 1977-78, 2024-25. The user reported successful runs; independent historical completeness and test-suite verification are still pending.

## Local ingestion pilot results — 2026-11-05

- 1946-47: 6,508 rows; missing MIN 0%, PTS 0%, REB 100%, AST 97.99%, STL 100%, BLK 100%, TOV 100%.
- 1977-78: 17,768 rows; missing MIN 0%, PTS 0%, REB 0.43%, AST 1.77%, STL 32.72%, BLK 28.25%, TOV 49.8%.
- 2024-25: 26,306 rows; missing MIN, PTS, REB, AST, STL, BLK, TOV 0%.
- Total: 50,582 player-game rows retrieved and cached locally. This is **not** confirmation of historical completeness or correctness. The 1946-47 raw data includes two conflicting John Murphy team records (PHW and NYK) for game 0024600076; retain raw records and exclude unresolved player-game conflicts from derived aggregates.
- No model training or bulk historical download was performed. The user has not supplied an offline unit-test result for the latest changes.

## Minute precision decision — 2026-11-05

- **Approved by user:** Accept the game-level `MIN` values as supplied in the local NBA API cache, including whole-minute precision; do not delay the project to recover fractional minutes.
- The inspected 2024-25 Shai Gilgeous-Alexander record for 2024-10-24 contains `MIN: 36`. The cached three-player reconciliation matched published games and points, but minute sums differed: Shai 2,596 vs 2,597.6; Nikola Jokić 2,575 vs 2,570.8; Anthony Edwards 2,868 vs 2,871.1. These observations are consistent with limited minute precision, but do not establish whether rounding originated upstream or during normalization.
- **Implementation rule:** Preserve original cached `MIN` values without inventing fractional minutes; sum them for cumulative career-minute checkpoints and use the sums as denominators for per-36 rates. Document that rounding can create small discrepancies versus official totals and derived rates. Never treat the values as second-level precision.
- This decision does **not** establish historical completeness or resolve early-era missingness, duplicate conflicts, or eligibility for era-aware comparisons. WBS 1.6 remains open.

## Historical pilot review — accepted limitations (2026-11-05)

**User decision:** End game-by-game historical reconciliation after the pilot; document findings and proceed to data preparation. Do not investigate individual early-era discrepancies further unless they materially affect the model.

- **1946-47:** 6,508 cached player-game rows. MIN and PTS have no nulls, but inspected leading players have total MIN = 0, making per-36 and cumulative-minute matching unreliable. REB/STL/BLK/TOV are 100% missing; AST is 97.99% missing. George Nostrand has 62 distinct cached games / 488 points versus a previously consulted reference of 61 / 482; discrepancy remains unresolved. One duplicate player-game pair has conflicting team records. Preserve the raw data; exclude zero-minute/ineligible checkpoints and unresolved duplicate groups from modeling.
- **1977-78:** 17,768 rows. Missing REB 0.43%, AST 1.77%, STL 32.72%, BLK 28.25%, TOV 49.8%. Two duplicate player-game pairs have conflicting team records. James Edwards' 83 games / 2,405 minutes / 1,262 points reconciled to the previously consulted reference; Jim Price's 83 games / 723 points matched while cached minutes (1,909) differed from the reference (1,929). Do not impute missing values as zero.
- **2024-25:** 26,306 rows, no missing values in the seven reported metrics, no duplicate player-game pairs. Games and points reconciled for Shai Gilgeous-Alexander (76 / 2,484), Nikola Jokić (70 / 2,071), and Anthony Edwards (79 / 2,177) when matched by PLAYER_ID. Minute sums differ slightly from published totals; whole-minute precision is accepted.
- **Policy:** Retain original raw data; keep unresolved duplicate groups out of derived aggregates; use era-aware feature availability, require positive usable cumulative minutes for per-36 comparisons, and surface coverage limitations in model documentation. A small pilot and spot checks do **not** establish full historical completeness.
- **Next work:** Move to WBS 2.1–2.6 on the available pilot dataset, then expand ingestion only as needed for historical coverage. Full-history ingestion under WBS 1.6 remains open; do not mark it complete based on the pilot.

## Work breakdown structure

### 1.0 Historical data acquisition
- [x] **1.1** Evaluate `nba_api` (preferred candidate) and alternative sources for historical game logs.
- [x] **1.2** Test sample seasons from early, middle, and modern NBA history; verify minutes, games, all six stats, and player identifiers.
- [x] **1.3** Assess coverage gaps, API reliability, throttling, permitted usage, costs, and reproducibility.
- [x] **1.4** Write a concise source comparison and recommendation, with evidence from sample retrievals.
- [x] **1.5 DECISION GATE:** Present source recommendation and coverage limitations; obtain user approval **before bulk download**.
- [ ] **1.6** Implement reproducible, resumable ingestion with caching and raw-data validation. Three-season pilot ran locally; full-history acquisition and independent coverage validation remain pending.
- [x] **1.7** [CODEX-READY] Document the local pilot's data lineage, cache/re-run procedure, duplicate-conflict handling and historical quality review checklist. Add offline tests for report consistency and unresolved duplicate exclusion from future derived datasets. Do not fetch more data, change the similarity methodology, or mark full historical acquisition complete.
  - Completed 2026-11-06: README documents reported lineage and its limits, network-free cache review, refresh/resume behavior, conflict policy and the user-led historical review checklist. Added `exclude_unresolved_duplicates` for future derived data and offline tests covering persisted/re-run report consistency, whole-group exclusion (including identical duplicates), preserved raw records and empty input. Validation: `UV_CACHE_DIR=/tmp/nba-uv-cache uv run --offline python -m unittest discover -s tests -v` passed all 10 tests. No live data was accessed; WBS 1.6 and independent historical validation remain incomplete.

**Deliverable:** Approved data source, reproducible local historical game-level dataset.

### 2.0 Data preparation

**Approved next implementation task — [CODEX-READY] DATA-2 (pilot-only preparation):** Implement WBS 2.1–2.6 using the existing locally cached pilot seasons; no bulk historical download, live API requests, model training, frontend, or deployment. Codex should implement importable, reusable Python functions for chronological player-game ordering; exclusion of all unresolved duplicate player/game groups; player career cumulative games, minutes, and available counting totals; approximately matched cumulative-minute checkpoints; per-36 and per-game feature calculations; explicit missing-statistic/era eligibility; and a concise data-quality summary. Keep raw JSON untouched and outputs derived/reproducible. Never convert missing stats to zero, never divide by zero, and exclude records/checkpoints with zero or invalid cumulative minutes from per-36 matching. Preserve whole-minute MIN precision as approved. For features with missing game values, track coverage and do not label partial sums as complete; define and document eligibility conservatively. Treat the three pilot seasons as **nonconsecutive samples**, not complete player careers: do not describe their combined cumulative totals as career totals or use cross-season pilot totals as career checkpoints. Support a season-scoped pilot demonstration and design the cumulative-career functions to operate on full chronological history once acquired. Add offline unit tests for sorting, duplicates, missingness, zero minutes, rates, checkpoints, and partial-history handling; use no live network calls. Codex may make routine implementation choices and document them, but must stop for consequential changes to approved matching methodology. Run the local test suite and report results. Mark 2.1–2.6 complete only to the extent implemented and tested, explicitly noting pilot-only scope.

- [x] **2.1** Clean and order regular-season game logs chronologically by player.
- [x] **2.2** Calculate cumulative career games, minutes, and counting stats.
- [x] **2.3** Build approximate career-minute checkpoints from game-level records; document tolerance and edge cases.
- [x] **2.4** Derive per-36 and per-game rates using cumulative totals.
- [x] **2.5** Identify incomplete historical features and define fair comparison eligibility.
- [x] **2.6** Add data-quality tests and summary report.

**DATA-2 implementation:** Pilot-scoped functions, offline file runner and tests implemented for 2.1–2.6. Season totals/checkpoints are not career totals. Full-history functions require explicit complete-history confirmation; full historical acquisition remains open. Complete observed feature coverage is required for rates/eligibility; unresolved duplicate groups are excluded wholesale. All 20 offline tests passed with `UV_CACHE_DIR=/workspace/.cache/uv uv run --offline python -m unittest discover -s tests -v`. Actual MacBook pilot caches were unavailable here, so actual-season processing and quality counts remain pending local execution using the README command. No new data, training or similarity-methodology changes.

**Deliverable:** Reusable preparation implementation tested on offline fixtures; actual pilot-derived dataset pending local cache execution.

### 3.0 Similarity baseline and model
- [ ] **3.1** Implement transparent baseline comparison for reference.
- [ ] **3.2** Standardize six features using a documented fitting strategy.
- [ ] **3.3** Implement equal-weight nearest-neighbor similarity with initial ±10% cumulative-minute eligibility.
- [ ] **3.4** Exclude self-matches; select one relevant checkpoint per historical player; return five distinct players.
- [ ] **3.5** Produce interpretable scores and feature-level comparison explanations; avoid misleading percentage-like scores.
- [ ] **3.6** Test per-36 default and per-game alternative.
- [ ] **3.7 DECISION GATE:** Seek approval before changing core matching logic or feature set.

**Deliverable:** Reproducible local similarity engine and baseline evaluation.

### 4.0 Validation and review
- [ ] **4.1** Evaluate rookies, veterans, limited-minute players, and different eras.
- [ ] **4.2** Check sample-size sensitivity, missing features, duplicates, and unexpected rankings.
- [ ] **4.3** Document limitations and proposed refinements.
- [ ] **4.4 DECISION GATE:** Present representative top-five results for user review before application build.

**Deliverable:** Validated local model and evaluation report.

### 5.0 Application development
- [ ] **5.1** Design Python API (FastAPI candidate) for player search and similarity results.
- [ ] **5.2** Build/test API with local model and stored data.
- [ ] **5.3** Build independent React frontend with searchable player selection.
- [ ] **5.4** Show top five, scores, per-stat explanations, and per-36/per-game toggle.
- [ ] **5.5** Add responsive UI, errors/loading states, and end-to-end tests.

**Deliverable:** Working local web app within `machine-learning/nba/`.

### 6.0 Public deployment
- [ ] **6.1** Compare hosting and data-serving architectures, costs, and operational requirements.
- [ ] **6.2 DECISION GATE:** Obtain approval for hosting approach and any recurring costs.
- [ ] **6.3** Deploy React frontend and Python API; validate production behavior.
- [ ] **6.4** Link independent NBA app from existing portfolio.
- [ ] **6.5** Document deployment, operations, and reproducibility.

**Deliverable:** Publicly accessible NBA similarity app linked from portfolio.

## Future enhancements (not version 1)
- Playoff comparisons.
- Shooting percentages and efficiency metrics.
- User-selected historical career-minute checkpoints.
- User-adjustable statistical weights.
- Automated incremental game-data refreshes.

## Codex operating rules
- Follow repository `AGENTS.md` and keep project code inside `machine-learning/nba/`; use `uv` for the Python environment.
- Explain significant steps concisely; assume user knows ML fundamentals.
- Once manually launched for an approved `[CODEX-READY]` task, proceed independently on routine coding, tests, cleaning, and documentation. Do not assume unattended or scheduled Codex runs.
- Pause **only for consequential decisions** (data source, methodology, architecture, scope, paid services, public deployment); present options and a recommendation.
- Do not treat a milestone boundary as an automatic approval checkpoint unless it includes a decision gate.
- **Research WBS 1.1–1.5 is performed by the user with ChatGPT, not Codex. Manually initiate Codex only for approved implementation tasks tagged `[CODEX-READY]`; SETUP-1 is independently approved and does not require research or data access. Do not bulk-download historical data until 1.5 is approved.**
