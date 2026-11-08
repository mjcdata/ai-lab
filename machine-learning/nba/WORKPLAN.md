# NBA Player Similarity — Work Breakdown Structure (WBS)

## Current MVP direction — supersedes earlier deployment-first sequencing (2026-11-08)

**Product goal:** A locally accessible Next.js NBA Player Similarity application where a fan selects a player from the **2026–27 NBA regular season** and discovers up to five statistically closest historical NBA players, with understandable explanations of the similarities. This is **comparison, not prediction**.

**MVP acceptance criteria**
- Historical reference pool covers NBA regular-season history **1946–47 through 2025–26**, to the extent usable records exist. Report historical coverage and exclude or transparently flag ineligible early-era records; do not imply every season is fully comparable.
- The **2026–27 season** supplies current player queries. Historical candidates must be drawn from prior seasons, without current-season leakage. Players who appeared historically and are active in 2026–27 require a clear self-exclusion policy.
- Compare equivalent **career-stage checkpoints**, supporting games-played and cumulative-minutes modes. Do not compare a rookie's partial career against an entire veteran career by default. Document how incomplete careers, overlapping seasons, and checkpoint tolerances are handled.
- Keep **standardized, equal-weight Euclidean distance** as the baseline; use per-36 statistics by default, preserve existing per-game support where appropriate. Era adjustments and feature-availability rules require explicit design and validation before modifying approved scoring logic (WBS 3.7).
- Return up to five distinct historical comparisons, distances (not percentages), reference/candidate statistics, and human-readable reasons for each match. Handle missing features without filling them with zero, including early eras with zero/unreliable minutes.
- The existing Next.js UI must run **locally**, with usable search and comparison results for real 2026–27 players. Precomputed, versioned static results are preferred where they can support the expanded scope; retain Python/FastAPI for development and parity checks. No public portfolio integration is needed for MVP completion.
- Reproducible local data preparation, provenance/coverage reporting, tests for checkpoint and era eligibility, exact result parity, and a successful local browser walkthrough are required. **Do not mark the MVP complete until the end-to-end 2026–27 → historical comparison works locally.**

**Development sequence (current priority)**
1. **HIST-1 — Full-history ingestion (implementation complete; acquisition open):** Extend existing resumable local ingestion to 1946–47 through 2025–26; inventory existing caches first, retrieve only missing approved seasons in controlled batches on the Mac, preserve raw data and missingness, and report per-season coverage/quality. Do not assume pilot samples constitute complete careers. Historical source approval already exists; do not repeat source selection. No cloud bulk ingestion or committing raw data.
2. **HIST-2 — Career checkpoints:** Build chronological complete-career datasets from verified contiguous history; implement games and minutes checkpoint alignment with conservative exclusions for invalid minutes, duplicates, and partial features. Record historical eligibility by era.
3. **HIST-3 — Era-aware similarity:** Define and review era normalization and shared-feature comparisons, then implement with tests and representative player comparisons. Preserve the existing 2024–25 baseline and avoid unapproved methodology changes.
4. **CURR-1 — 2026–27 inputs:** Ingest and validate current-season regular-season logs locally; connect current-player selection to the historical reference pool, keeping current-season data out of historical candidates. Specify refresh process manually; **no scheduler**.
5. **APP-1 — Complete local MVP:** Extend existing snapshot generator, Next.js UI and/or local API as needed; preserve search, both exposure modes, explanations, warnings, and regression tests. Run locally and review real current-to-history results.

**Explicitly deferred:** portfolio integration, Cloudflare/other public deployment, publication/licensing decision, automated/scheduled refresh, headshots, similarity percentages, predictive modeling, and unrelated fan features. The 2024–25 569-player / 1,138-result static implementation is a **validated prototype**, not the completed full-history MVP. Prior WBS 6.1–6.2 architecture work remains useful, but any earlier text implying that deployment or portfolio integration is the next step is superseded by this section. WBS 1.6 remains open until full-history acquisition and coverage review are done.

**Next execution boundary:** HIST-1 ingestion code is implemented and tested offline; no historical downloads have been run for this task. The user initiates controlled local acquisition next. Existing approval of nba_api as source does not authorize altering the approved matching methodology without the 3.7 decision gate.


**Project:** AI Lab / Machine Learning / NBA  
**Status:** Source approved; three-season pilot ingested; local DATA-2 preparation validated; season-scoped baseline implemented and locally exercised; 2024–25 baseline review complete; WBS 4.4 approved; local Next.js + FastAPI MVP implemented and tested
**Execution:** User manually launches Codex for approved implementation tasks; user approves major decisions. GitHub Actions performs tests only.

## Goal and scope

Build a public React + Python application that returns the **top five historical NBA player comparisons** for a selected player. Compare players at approximately the same **cumulative regular-season career minutes**, using the latest available career checkpoint by default. Include NBA history back to 1946–47 **where reliable game-level data permits**.

**Version 1:** ±10% cumulative-minutes matching (initial proposal); six features (points, assists, rebounds, steals, blocks, turnovers) when jointly available, otherwise era-aware comparisons; per-36 rates by default, with per-game option; standardized equal-weight nearest-neighbor baseline; interpretable results. Handle missing historical statistics explicitly, never as zeros. Assess whether incomplete eras can be compared fairly.

## Approved implementation tasks

- [x] **SETUP-1** Create a minimal Python project in `machine-learning/nba/` using `uv`: add `pyproject.toml`, a small importable package, and one lightweight smoke test. Keep dependencies minimal; document commands to install and run tests. Do not fetch data, research sources, train models, or change the planned similarity methodology.
  - Implementation added: `pyproject.toml`, `code/src/nba_player_similarity/`, a standard-library smoke test, and setup/test commands in `README.md`. Source-tree smoke test passed with `PYTHONPATH=code/src python -m unittest discover -s code/tests -v`; TOML metadata and package layout checks passed. Completed validation in GitHub Codespaces (2026-11-05): `uv sync` successfully built and installed `nba-player-similarity==0.1.0`; `uv run python -m unittest discover -s code/tests -v` passed (1 test, 0 failures).

## Source research decision — approved 2026-11-05

- Primary source: `swar/nba_api` `LeagueGameLog` regular-season player logs; era-aware comparisons approved.
- MacBook retrievals succeeded: 1946-47 (6,508 rows), 1951-52 (6,086), 1965-66 (6,855), 1973-74 (13,380), 1977-78 (17,768), 1985-86 (19,387), 2024-25 (26,306). Codespaces requests timed out; live acquisition runs locally.
- Missing data observed: 1946-47 REB 6508, AST 6377, STL/BLK/TOV 6508; 1951-52 REB 5784, AST 5257, STL/BLK/TOV 6086; 1965-66 AST 945, REB 518, STL/BLK/TOV 6855; 1973-74 REB 1044, AST 1133, STL 9682, BLK 9240, TOV 13379; 1977-78 REB 76, AST 314, STL 5813, BLK 5019, TOV 8848; 1985-86 AST 5, REB/STL/BLK/TOV 6. MIN and PTS had no nulls in these samples, but early minutes still require independent validation.
- Risks: incomplete historical game logs, cloud IP blocking, throttling, uncertain early minutes, upstream changes. Preserve missing values; validate completeness, duplicates, minutes plausibility, and cross-check independent totals before modeling.
- Alternative sources remain fallbacks. Public redistribution/licensing requires separate review before deployment.
- **DATA-1 pilot implemented and locally executed:** CLI, per-season raw JSON cache, structural and missingness reports. Pilot seasons: 1946-47, 1977-78, 2024-25. Local retrieval and DATA-2 offline tests are verified below; full historical completeness remains unverified.

## Local ingestion pilot results — 2026-11-05

- 1946-47: 6,508 rows; missing MIN 0%, PTS 0%, REB 100%, AST 97.99%, STL 100%, BLK 100%, TOV 100%.
- 1977-78: 17,768 rows; missing MIN 0%, PTS 0%, REB 0.43%, AST 1.77%, STL 32.72%, BLK 28.25%, TOV 49.8%.
- 2024-25: 26,306 rows; missing MIN, PTS, REB, AST, STL, BLK, TOV 0%.
- Total: 50,582 player-game rows retrieved and cached locally. This is **not** confirmation of historical completeness or correctness. The 1946-47 raw data includes two conflicting John Murphy team records (PHW and NYK) for game 0024600076; retain raw records and exclude unresolved player-game conflicts from derived aggregates.
- No model training or bulk historical download was performed. Local DATA-2 validation subsequently passed all 20 offline tests (see below).

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
  - Completed 2026-11-06: README documents reported lineage and its limits, network-free cache review, refresh/resume behavior, conflict policy and the user-led historical review checklist. Added `exclude_unresolved_duplicates` for future derived data and offline tests covering persisted/re-run report consistency, whole-group exclusion (including identical duplicates), preserved raw records and empty input. Validation: `UV_CACHE_DIR=/tmp/nba-uv-cache uv run --offline python -m unittest discover -s code/tests -v` passed all 10 tests. No live data was accessed; WBS 1.6 and independent historical validation remain incomplete.

**Deliverable:** Approved data source, reproducible local historical game-level dataset.

### 2.0 Data preparation

**Completed approved task — DATA-2 (pilot-only preparation):** Implement WBS 2.1–2.6 using the existing locally cached pilot seasons; no bulk historical download, live API requests, model training, frontend, or deployment. Codex should implement importable, reusable Python functions for chronological player-game ordering; exclusion of all unresolved duplicate player/game groups; player career cumulative games, minutes, and available counting totals; approximately matched cumulative-minute checkpoints; per-36 and per-game feature calculations; explicit missing-statistic/era eligibility; and a concise data-quality summary. Keep raw JSON untouched and outputs derived/reproducible. Never convert missing stats to zero, never divide by zero, and exclude records/checkpoints with zero or invalid cumulative minutes from per-36 matching. Preserve whole-minute MIN precision as approved. For features with missing game values, track coverage and do not label partial sums as complete; define and document eligibility conservatively. Treat the three pilot seasons as **nonconsecutive samples**, not complete player careers: do not describe their combined cumulative totals as career totals or use cross-season pilot totals as career checkpoints. Support a season-scoped pilot demonstration and design the cumulative-career functions to operate on full chronological history once acquired. Add offline unit tests for sorting, duplicates, missingness, zero minutes, rates, checkpoints, and partial-history handling; use no live network calls. Codex may make routine implementation choices and document them, but must stop for consequential changes to approved matching methodology. Run the local test suite and report results. Mark 2.1–2.6 complete only to the extent implemented and tested, explicitly noting pilot-only scope.

- [x] **2.1** Clean and order regular-season game logs chronologically by player.
- [x] **2.2** Calculate cumulative career games, minutes, and counting stats.
- [x] **2.3** Build approximate career-minute checkpoints from game-level records; document tolerance and edge cases.
- [x] **2.4** Derive per-36 and per-game rates using cumulative totals.
- [x] **2.5** Identify incomplete historical features and define fair comparison eligibility.
- [x] **2.6** Add data-quality tests and summary report.

**DATA-2 implementation and actual local validation: COMPLETE (2026-11-08).** WBS 2.1–2.6 is complete for the season-scoped pilot, including execution against the actual MacBook caches. This does not complete full-history acquisition or validate complete player careers.

| Season | Raw rows | Duplicate rows excluded | Invalid rows excluded | Derived rows | Positive usable-minute checkpoints | All-six-feature eligible checkpoints |
|---|---:|---:|---:|---:|---:|---:|
| 1946–47 | 6,508 | 2 | 0 | 6,506 | 0 | 0 |
| 1977–78 | 17,768 | 4 | 0 | 17,764 | 17,733 | 2,043 |
| 2024–25 | 26,306 | 0 | 0 | 26,306 | 26,305 | 26,305 |

- Actual preparation command: `UV_CACHE_DIR=/private/tmp/ai-lab-uv-cache /Users/mj/.local/bin/uv run --offline python -m nba_player_similarity.preparation --data-dir data` (from the NBA project directory).
- Validation: `UV_CACHE_DIR=/private/tmp/ai-lab-uv-cache /Users/mj/.local/bin/uv run --offline python -m unittest discover -s code/tests -v` — **20 tests passed, 0 failures**. Generated row counts were checked against the report; raw SHA-256 hashes matched before and after processing.
- Outputs: local `data/derived/{season}.json` and `data/derived/quality.json`; all remain Git-ignored. No generated datasets are committed. No downloads, training, or methodology changes occurred.
- 1946–47: all 6,506 retained checkpoints have zero cumulative minutes and cannot participate in per-36/minute matching. REB/STL/BLK/TOV are entirely unavailable; AST has 6,376 unusable observations after duplicate exclusion. Numeric zero minutes are not counted as missing by the report, so zero missing MIN does not establish usability.
- 1977–78: retained unusable observations are AST 312, REB 74, STL 5,810, BLK 5,016, TOV 8,845; 31 checkpoints have zero cumulative minutes. Positive minutes alone do not imply complete feature eligibility.
- 2024–25: no unusable observations in the seven metrics; one zero-minute checkpoint is ineligible. Accepted whole-minute source precision still applies.
- These are three nonconsecutive season samples. Do not combine them into career histories or infer historical completeness from passing tests. Preserve missing values and exclude all unresolved duplicate groups; WBS **1.6 remains open**.

**Deliverable:** Actual pilot-derived season datasets and quality report generated and inspected locally; preparation implementation verified with 20 offline tests.

### 3.0 Similarity baseline and model
- [x] **3.1** Implement transparent baseline comparison for reference.
- [x] **3.2** Standardize six features using a documented fitting strategy.
- [x] **3.3** Implement equal-weight nearest-neighbor similarity with initial ±10% cumulative-minute eligibility.
- [x] **3.4** Exclude self-matches; select one relevant checkpoint per historical player; return five distinct players.
- [x] **3.5** Produce interpretable scores and feature-level comparison explanations; avoid misleading percentage-like scores.
- [x] **3.6** Test per-36 default and per-game alternative.
- [ ] **3.7 DECISION GATE:** Seek approval before changing core matching logic or feature set.

**Deliverable:** Reproducible local similarity engine and baseline evaluation.

#### Approved 2024–25 baseline implementation plan — implemented

User explicitly approved the fixed latest-checkpoint scaler, equal-weight standardized Euclidean metric, no additional exposure threshold, and fewer-than-five behavior on 2026-11-08. Implementation and local execution are complete. Per-36 is default; per-game diagnostic mode is also tested.

1. Read only the existing 2024–25 derived checkpoints. Require positive valid cumulative **season** minutes and complete coverage of PTS, AST, REB, STL, BLK and TOV. Default target: the selected player's latest eligible season checkpoint. Clearly label results as season-to-date comparisons, not historical career comparisons.
2. For each other PLAYER_ID, use the existing checkpoint selector to select its nearest eligible season-minute checkpoint within the inclusive ±10% target window, breaking minute-distance ties by earliest date then game ID. Exclude the target player entirely. No cross-season matching or automatic window expansion.
3. Standardize the six cumulative per-36 features with a fixed, documented reference scaler. Proposed reference: one latest eligible checkpoint per player in 2024–25, with population mean/standard deviation; each player contributes once. For zero-variance features use scale 1 so they contribute zero distance. Reuse the reference for every query and disclose that this is retrospective similarity, not predictive evaluation.
4. Rank candidate checkpoints by Euclidean distance over the six z-scores, with equal feature weights. Return five distinct players when available; otherwise return fewer with a candidate-shortage explanation. Break equal-distance ties deterministically by PLAYER_ID. Retain an unstandardized per-36 distance as a diagnostic reference only; standardized distance controls ranking.
5. Explain each result with both checkpoints' dates, games and minutes, minute difference/percentage, per-36 values, raw differences, standardized differences and each feature's squared-distance contribution. Show distance as distance, not a probability or similarity percentage; smaller means closer. Warn about low exposure and season-only scope.
6. Add offline synthetic tests for scaling/reference consistency, equal weighting, zero variance, self-exclusion, distinct-player selection, ±10% boundaries, ties, missing/zero-minute exclusion, shortages and explanation reconciliation. Later run representative queries locally on existing derived data and document results/limitations before the WBS 4.4 review gate. Per-game alternative is implemented and tested under 3.6; representative local results use the per-36 default.

**Proposed files once implementation is authorized:** `code/src/nba_player_similarity/similarity.py`, `code/tests/test_similarity.py`, project `README.md` and this `WORKPLAN.md`. Reuse `preparation.py`; change it only if a demonstrated interface issue requires it. No API, frontend, new data, shared framework, or committed derived outputs.

**Completion — 2026-11-08:** Implemented `similarity.py`, offline tests and CLI. The local fixed scaler uses 569 players; five representative queries (Anthony Edwards, Nikola Jokić, Alperen Sengun, Stephen Curry, LeBron James) each returned five distinct comparisons within the unchanged window. Full scores, exposures and feature explanations are in [BASELINE_RESULTS.md](artifacts/BASELINE_RESULTS.md). All 28 offline tests passed. No additional data, frontend or deployment. Generated caches remain untracked. WBS 3.1–3.6 complete for the season-scoped baseline only; WBS 1.6 remains open. Representative runs are observations, not completion of all WBS 4 evaluation tasks. No unresolved baseline methodology approval remains; user review at 4.4 is still required before application build.

### 4.0 Validation and review
- [x] **4.1** Evaluate rookies, veterans and limited-minute players for the requested 2024–25 scope. Cross-era model evaluation remains deferred; existing historical limitations reviewed only.
- [x] **4.2** Check sample-size sensitivity, missing features, duplicates, and unexpected rankings.
- [x] **4.3** Document limitations and proposed refinements.
- [x] **4.4 DECISION GATE:** User approved the exploratory 2024–25 baseline on 2026-11-08, explicitly retaining the original scaler and candidate eligibility. Authorized WBS 5.1–5.2 only; no frontend or deployment.

**Review completed 2026-11-08:** See [VALIDATION.md](artifacts/VALIDATION.md). All 569 latest-player queries passed uniqueness, self-exclusion, score explanation and minute-window checks. All had at least five candidates. Preparation reproduced all 26,306 derived rows exactly; 26,305 checkpoints eligible. No raw 2024–25 missing features or duplicate player/game groups; one zero-minute checkpoint excluded. All 28 offline tests passed. Rookie/veteran/limited-minute examples and fixed-scaler playing-time sensitivity documented. Material limitations: unstable tiny-sample rates and their influence on the reference scaler, candidate-pool changes, season-only scope and omitted style features. No methodology changes or new data. WBS 4.1–4.3 complete for this season only; 4.4 was subsequently approved for WBS 5.1–5.2 only. Full-history acquisition (1.6) remains open. Recommend transparent exploratory use; any exposure cutoffs or revised scaler need separate approval.

**Deliverable:** Season-scoped validation report; cross-era performance and comprehensive historical validation are not claimed.

#### Completed targeted scaler sensitivity experiment — 2026-11-08

User authorized an isolated experiment, not a production methodology change. Tested fixed scaler reference cutoffs of 0/50/100/250/500 minutes, retaining all query/candidate eligibility and the approved matching/scoring rules. Contributor counts: 569/523/496/442/375. Across 569 latest queries, mean top-five membership overlap with control was 5.000/4.510/4.408/4.316/4.202; candidate counts were unchanged. Representative Bronny/Curry/Jokić/Castle/Edwards outputs and time-sensitivity checks are in [SCALER_SENSITIVITY.md](artifacts/SCALER_SENSITIVITY.md). Bronny’s early-to-final overlap did not improve; established-player changes were mixed. Scaler filtering affects weighting but is insufficient to stabilize low-minute query/candidate rates. **Recommendation: retain the approved production baseline**; no threshold is demonstrably best. An exposure-eligibility experiment is a separately approvable next investigation, not authorization to change eligibility. All 31 offline tests passed. Production similarity code, source caches and methodology are unchanged; experiment JSON remains local/ignored. WBS 4.4 subsequently approved for local API work only; full-history acquisition remains open.

### 5.0 Application development

**Scope extension approved 2026-11-08:** User authorized the code/data/artifacts reorganization and WBS 5.3–5.5, then specified Next.js for the React frontend. Prior API-only authorization was extended by this request; deployment remains unauthorized.
- [x] **5.1** Design local FastAPI player search, selection, health and comparisons endpoints; documented modes, exposure, errors and local-cache lifecycle.
- [x] **5.2** Implement read-only API with the original model and local 2024–25 caches. Both modes preserve scores, explanations and eligibility; names and exposure warnings decorate copied responses.
  - Completed 2026-11-08: FastAPI/uvicorn dependencies and locked test transport; 35 offline tests passed, including four API tests. In-process real-cache integration verified 569 selectable players and exact IDs/scores/feature explanations versus direct model calls for Bronny James, Stephen Curry and Nikola Jokić in both modes. Raw/derived hashes unchanged. Startup fails on absent/wrong-season data without fetching. README includes loopback run instructions and API contract. No model methodology, datasets, frontend or deployment changes. TestClient emits an upstream httpx deprecation warning; no failures.

- [x] **5.3** Build Next.js React frontend with accessible searchable player selection and local API proxy (user explicitly requested Next.js).
- [x] **5.4** Show up to five distinct matches, distances, games/minutes/dates, six-stat tables and distance contributions, both modes, exposure warnings and 2024–25 season-only scope.
- [x] **5.5** Desktop/mobile responsive layout; search/comparison loading, error/retry and empty states; six Playwright integration cases passed with the real local API plus controlled failure/empty fixtures.

**Deliverable:** Working local Next.js + FastAPI app within `machine-learning/nba/`.

**Local MVP completion — 2026-11-08:** Stopped the verified original NBA API PID 49595 and confirmed port 8000 was free before reorganization. Moved Python source/tests into `code/src` and `code/tests`, Next.js frontend into `code/frontend`, evaluation Markdown into `artifacts/`, and existing generated experiment JSON to `artifacts/scaler_experiment.json`. Updated uv module-root, docs, ignores and CI test path/dependency sync. Root README/WORKPLAN/Python config remain accessible; no unnecessary model directory or empty framework. All local data/output hashes preserved, core model/API source unchanged, direct API/model scores and UI example results verified. All **35 Python tests** and **6 desktop/mobile Playwright tests** pass; Next.js production build passes. Desktop/mobile screenshots visually inspected, with no horizontal overflow. No methodology changes, extra NBA downloads, paid services or deployment. Local server launch commands and URLs are in README. Full-history acquisition and WBS 6 deployment remain open.

### 6.0 Public deployment
- [x] **6.1** Deployment architecture research completed 2026-11-08; comparison, sizing evidence and recommendation below. Research only; no deployment or architecture implementation.
- [x] **6.2 DECISION GATE:** User approved precomputed static Next.js with Cloudflare Pages preferred and a $0/month hosting target on 2026-11-08. Authorized local implementation/validation only; public deployment, purchases and recurring automation remain unauthorized.
- [ ] **6.3** Public deployment pending separate approval and redistribution review. Local static Next.js export/snapshot implementation is complete and validated; the retained FastAPI service is local-only, not required by the public/static architecture.
- [ ] **6.4** Link independent NBA app from existing portfolio.
- [ ] **6.5** Document deployment, operations, and reproducibility.

**Deliverable:** Publicly accessible NBA similarity app linked from portfolio.

## WBS 6.1 deployment architecture research — 2026-11-08

**Research recommendation (subsequently approved for local implementation):** Precompute the approved latest-checkpoint results for all 569 players in both modes locally; export Next.js as a static site and host the UI, small search index and per-player/mode JSON on Cloudflare Pages Free. Keep FastAPI/Python as the local development and reproducible computation path. A public runtime API, database, R2 bucket or serverless function is unnecessary for this fixed-season MVP. Implementation was subsequently approved for local validation only; public deployment remains unapproved.

### Comparison and estimated monthly cost

USD estimates for one low-traffic personal portfolio, before taxes, optional domain registration, usage overages or paid workspace features. Free tiers are conditional, not an uptime guarantee; recheck provider terms at deployment.

| Factor | Existing Next.js + FastAPI | Precomputed static Next.js frontend |
|---|---|---|
| Indicative hosting | Vercel Hobby frontend + Render Python web service | Cloudflare Pages Free; Vercel Hobby static hosting is an alternative |
| Monthly estimate | $0 with free backend but idle cold starts; roughly $7/month with smallest paid Python instance, or $25/month for 2 GB if memory requires it; frontend $0 only if Hobby-eligible. Two smallest Render services instead would start around $14/month, subject to sizing. | Expected $0/month for static hosting at this scale; no continuously running compute or database. Optional domain separate. |
| First useful response | Frontend shell can be fast; search and comparisons depend on backend wake-up, parsing/loading data and scoring. Current proxy times out after 10 seconds, incompatible with an approximately one-minute sleeping-backend wake-up. Paid backend avoids idle sleep but remains a second service dependency. | CDN serves UI/search index and selected result file; no Python cold start. Initial JS still hydrates, and network/device latency still matters. Fetch only the chosen player/mode JSON, not the full snapshot. |
| Maintenance | Two runtimes/deployments, backend URL configuration, health/logging, dependency patches, data packaging and backend memory sizing | One static deployment, Node build plus local Python export when model/data changes; add versioning/parity checks and coherent snapshot updates |
| Functionality | Existing search, selection, six-stat explanations, exposure warnings and both modes already work | All current features preserved with a local searchable 569-player index and the existing response-shaped records for both modes; browser handles query filtering/pagination |
| Flexibility | Easier to add arbitrary checkpoint queries or new data dynamically later | Limited to exported season, players, latest reference checkpoints, modes and current rules. Any new data/model/query capability needs regeneration or another architecture decision. This covers the current UI exactly. |
| Storage | Must ship local ignored raw name source (17,315,654 bytes) and derived checkpoints (27,529,349 bytes), or equivalent approved deployment inputs. JSON expands in Python memory; 512 MB adequacy is not verified. Read-only files can be bundled; runtime-generated files on ephemeral disk are not durable. | Only names/search fields and finished comparison records need publication; raw logs and all checkpoint histories remain local. Static assets are publicly downloadable: results are not private simply because raw logs are omitted. |

**Pricing/limits sources:** [Vercel pricing](https://vercel.com/pricing) lists Hobby $0 and Pro $20/month; [Hobby conditions](https://vercel.com/docs/plans/hobby) limit it to personal, non-commercial use, with usage caps. Verify portfolio eligibility rather than assume every commercial use qualifies. [Render pricing](https://render.com/pricing) lists smallest paid compute about $7/month (512 MB) and 2 GB about $25/month; [compute plans](https://render.com/docs/compute-plans) confirm plan sizing. These are starting estimates, not a verified capacity budget.

[Render Free documentation](https://render.com/docs/free) specifies sleep after 15 idle minutes, roughly one-minute wake-up, 750 shared free instance hours/month, ephemeral files and bandwidth/build allowances. Free hosting is feasible for demos but a poor match for this API’s current 10-second proxy timeout; maintaining functionality would require a deployment-specific timeout/retry decision. No such change was made.

[Cloudflare Pages pricing](https://developers.cloudflare.com/pages/functions/pricing/) states static requests are free and unlimited when no Functions run. [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) list 20,000 files, 25 MiB per asset and 500 builds/month on Free, with a 20-minute build timeout. The measured split result assets fit comfortably; full frontend build assets also count and must be verified on export. A precomputed serverless lookup is possible, but adds function quotas and runtime configuration without an evident benefit here. The simplest choice is static assets only.

### Local read-only sizing evidence

Research computed response sizes in memory using the unchanged model and existing 2024–25 caches; no exporter, public asset tree or deploy configuration was implemented. Names were added as in the API; sizes include model fields, both checkpoint exposures, six-feature explanations, scaler metadata and model warnings. The API’s extra exposure-policy warning fields would add a small amount. No NBA data was downloaded.

- 569 players × 2 modes = **1,138 result assets**; total compact JSON **15,770,664 bytes (15.04 MiB)**, before frontend assets.
- Per-result size: min 10,508, median 14,078, max 14,431 bytes. Individual gzip median **3,785 bytes**, max 4,037 bytes; total individually gzipped results 4,120,948 bytes (3.93 MiB).
- Search index of IDs, names, latest games/minutes/date: **53,620 bytes**, or **10,998 bytes gzipped**. Case-insensitive substring search and player selection can run entirely in the browser.
- All scoring/serialization/compression took about **5.6 seconds on this Mac**. This is a local sizing measurement, not a cloud build-time or network benchmark. Gzip measurements assume the eventual host negotiates compression; wire bytes will vary.
- Estimate only: 1,000 visits × 5 selected player/mode result requests ≈19 MB of gzipped result payload, plus index/UI assets. No initial full-snapshot download is needed. Cache effectiveness and actual usage were not measured.

### Required adaptation after approval (not implemented)

1. Generate response-compatible per-player/mode result JSON locally into ignored artifacts, plus a search index and manifest recording season, model/code version and source hashes. Validate all 1,138 records against direct model/API outputs; retain numeric precision and warnings. Publish a coherent immutable snapshot with the matching index/UI.
2. Keep the Next.js UI and components. Replace the dynamic request-based `/api/[...path]` proxy with a static data loader and browser search, then enable `output: 'export'`. [Next.js static export documentation](https://nextjs.org/docs/app/guides/static-exports) explains that request-dependent route handlers/proxies are unsupported in static exports. The existing app cannot be deployed unchanged as a static site; UI behavior can remain the same after this narrow adaptation.
3. Export HTML/CSS/JS and snapshot files together; verify asset count, file sizes, compression, error handling, both modes, reference stats and explanations. Avoid a monolithic initial JSON bundle. No client-side reimplementation of scoring is needed.
4. Preserve local raw/prepared data and Python/FastAPI tests; only approved public result assets enter a deploy bundle. Since datasets are Git-ignored, a fresh GitHub/cloud build cannot regenerate them automatically: use a locally generated deploy bundle or an explicitly approved artifact-input process, not a live NBA download. No storage service or automated acquisition is required.
5. Changes to season/data/methodology require a new snapshot and redeployment; the frozen 2024–25 scope makes this infrequent. Maintain rollback via versioned build artifacts, not a mutable runtime database.

### WBS 6.2 — approval required; stop here

Approve **precomputed results + static Next.js export + Cloudflare Pages Free** as the proposed architecture and a **$0 recurring hosting target**, with no paid upgrade, domain purchase or deployment yet. Approval to implement the export adapter is separate from approval to publish it. If retaining a live public API is a portfolio requirement, choose that explicitly and approve its hosting budget after memory sizing instead.

The existing source-research decision also leaves **public redistribution/licensing review unresolved**. Public comparison JSON includes NBA-derived statistics. Neither precomputation nor an API establishes publication permission. Resolve/document that existing gate before public upload; architecture research makes no legal conclusion. At the research checkpoint WBS 6.2 was pending; the subsequent local implementation approval is recorded below. Public deployment/linking/operations tasks remain uncompleted. No infrastructure was registered, purchased or deployed, and no production model/UI code was changed.

## Approved static architecture — local implementation complete (2026-11-08)

User approved the WBS 6.1 precomputed recommendation and $0/month Cloudflare Pages target. Added an offline snapshot CLI, immutable versioned releases and a final atomic activation pointer. Each release records generation timestamp, season, model/code version, source hashes and per-file checksums. Staged and validated **569 players × 2 modes = 1,138 individual result files**, plus a search index/manifest; no bulk-results browser bundle. Shared API/snapshot response decoration preserves all warnings, names, reference stats, mode values, distances and six-feature explanations; original scoring/preparation source is unchanged.

The validated export contains 1,171 files; the largest asset is 242,212 bytes (well below the researched 25 MiB limit). Next.js now statically exports with a browser search/result loader. Removed its runtime API proxy; FastAPI remains independently runnable locally with its original routes. Build-time staging verifies artifact integrity and includes only the selected release. Generator/build/refresh procedures are in README and support explicit invocation with paths, not a configured schedule. Failed generation preserves the last valid pointer/release; concurrent publication is locked. No deployment config, paid service, public upload or recurring automation was created.

**Validation:** 40 Python tests; 4 Node static-loader/staging tests; 8 desktop/mobile browser cases; fully static production build. All 1,138 actual result payloads exactly match FastAPI responses in both modes. Failure tests cover partial generation, parity mismatch, activation failure, corrupt build inputs and unchanged previous assets. Source data hashes unchanged. Static UI tested with the API listener stopped; no runtime API calls. WBS 6.3–6.5 stay open. The user must review this local result; public redistribution review and explicit publication approval remain required before any deployment.

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


## HIST-1 implementation — 2026-11-08

- [x] Reuse existing nba_api regular-season fetcher for the inclusive 1946–47 through 2025–26 range (80 seasons).
- [x] Read-only cache inventory, chronological batches (default five missing seasons), revalidation before skipping, and season-level interruption/resume.
- [x] Bounded retries/backoff, between-season delay, per-season quality reports and independently saved batch failure/progress summaries. Explicit refresh preserves old raw bytes; invalid caches are never silently replaced. Missing statistics and duplicate raw records remain untouched.
- [x] Offline tests for all range boundaries, batch limits, no-network/read-only planning, interrupted resume, transient and exhausted requests, corrupt caches, refresh preservation, all-row schema and wrong-season rejection.
- [ ] Execute full historical acquisition locally and independently assess coverage (WBS 1.6 remains open). No download was performed for HIST-1 implementation.

**Validation:** All 46 Python offline tests passed for this task (including six new historical batch tests). Read-only inventory revalidated existing 1946–47, 1977–78 and 2024–25 caches without failures, selecting 1947–48, 1948–49, 1949–50, 1950–51 and 1951–52 for the first five-season batch. There are 77 missing seasons total. Live endpoint availability, retries against the real service and full-history completeness remain untested. Existing httpx/Starlette test-transport deprecation warning persists. No model, frontend or dataset changes are included.

**Next action:** User runs the README five-season `--download` command on the MacBook, inspects local per-season and batch quality reports, then repeats manually. Missing early statistics are not zero-filled; structural success is not cross-era suitability or career completeness. HIST-2/HIST-3 remain separate; no methodology decisions were reopened.
