# NBA Player Similarity — Work Breakdown Structure (WBS)

**Project:** AI Lab / Machine Learning / NBA  
**Status:** Source approved; three-season pilot ingested; historical quality validation pending  
**Execution:** Codex implements routine work autonomously; user approves major decisions.

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
- [ ] **2.1** Clean and order regular-season game logs chronologically by player.
- [ ] **2.2** Calculate cumulative career games, minutes, and counting stats.
- [ ] **2.3** Build approximate career-minute checkpoints from game-level records; document tolerance and edge cases.
- [ ] **2.4** Derive per-36 and per-game rates using cumulative totals.
- [ ] **2.5** Identify incomplete historical features and define fair comparison eligibility.
- [ ] **2.6** Add data-quality tests and summary report.

**Deliverable:** Analysis-ready player checkpoint dataset.

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
- Proceed independently on routine coding, tests, cleaning, and documentation.
- Pause **only for consequential decisions** (data source, methodology, architecture, scope, paid services, public deployment); present options and a recommendation.
- Do not treat a milestone boundary as an automatic approval checkpoint unless it includes a decision gate.
- **Research WBS 1.1–1.5 is performed by the user with ChatGPT, not automated Codex. Only run implementation tasks tagged `[CODEX-READY]`; SETUP-1 is independently approved and does not require research or data access. Do not bulk-download historical data until 1.5 is approved.**
