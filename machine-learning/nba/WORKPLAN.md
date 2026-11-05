# NBA Player Similarity — Work Breakdown Structure (WBS)

**Project:** AI Lab / Machine Learning / NBA  
**Status:** Planning — Phase 1 research pending  
**Execution:** Codex implements routine work autonomously; user approves major decisions.

## Goal and scope

Build a public React + Python application that returns the **top five historical NBA player comparisons** for a selected player. Compare players at approximately the same **cumulative regular-season career minutes**, using the latest available career checkpoint by default. Include NBA history back to 1946–47 **where reliable game-level data permits**.

**Version 1:** ±10% cumulative-minutes matching (initial proposal); six features (points, assists, rebounds, steals, blocks, turnovers); per-36 rates by default, with per-game option; standardized equal-weight nearest-neighbor baseline; interpretable results. Handle missing historical statistics explicitly, never as zeros. Assess whether incomplete eras can be compared fairly.

## Work breakdown structure

### 1.0 Historical data acquisition
- [ ] **1.1** Evaluate `nba_api` (preferred candidate) and alternative sources for historical game logs.
- [ ] **1.2** Test sample seasons from early, middle, and modern NBA history; verify minutes, games, all six stats, and player identifiers.
- [ ] **1.3** Assess coverage gaps, API reliability, throttling, permitted usage, costs, and reproducibility.
- [ ] **1.4** Write a concise source comparison and recommendation, with evidence from sample retrievals.
- [ ] **1.5 DECISION GATE:** Present source recommendation and coverage limitations; obtain user approval **before bulk download**.
- [ ] **1.6** Implement reproducible, resumable ingestion with caching and raw-data validation.
- [ ] **1.7** Store historical game logs locally; document data lineage and update procedure.

**Deliverable:** Approved data source, reproducible local historical game-level dataset.

#### WBS 1.1 progress — 2026-11-05

Attempted to access the `nba_api` documentation and candidate source sites using Python's `urllib.request`:

- https://raw.githubusercontent.com/swar/nba_api/master/README.md
- https://www.nba.com/stats/
- https://www.basketball-reference.com/

All three requests failed with `URLError: <urlopen error [Errno -3] Temporary failure in name resolution>`. External access is blocked in this environment; no source documentation or game logs were retrieved. WBS 1.1 remains incomplete, with no verified coverage, usage, cost, or reliability findings and no source recommendation. Resume source evaluation when network access is available; the bulk-download approval gate at 1.5 remains pending.

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
- **Start at WBS 1.1–1.4. Do not bulk-download historical data until 1.5 is approved.**
