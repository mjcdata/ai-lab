# Scaler contributor sensitivity experiment — 2026-11-08

## Design

Control is the unchanged approved SeasonBaseline. Five fixed per-36 population scalers use one latest eligible 2024–25 checkpoint per player with at least 0, 50, 100, 250 or 500 season minutes (inclusive). Zero means all otherwise eligible positive-minute players. No candidate/query exposure filtering, window widening, feature changes or alternate scoring. A scorer copy replaces only mean/scale; production code is untouched. All 569 latest-player queries are evaluated at each cutoff. Raw output is local and Git-ignored.

Reproduce from the NBA directory:

```sh
uv run --offline python -m nba_player_similarity.scaler_experiment
uv run --offline python -m unittest discover -s code/tests -v
```

The experiment reuses approved checkpoint selection/scoring and retains even low-minute players as queries/candidates. It does not change production defaults. Three new offline tests verify exact zero-cutoff control equivalence, inclusive fitting cutoffs, unchanged candidates/control/input, empty reference handling and constant-feature behavior. All **31 offline tests passed**. Candidate counts remained identical for all 569 queries at every cutoff.

## Changes to the reference distribution

Population means / standard deviations are shown as mean / SD, feature order fixed. Mean shifts cancel in pairwise z-score differences; SD changes drive distance reweighting. Distances from different cutoffs are not directly comparable as confidence or accuracy scores.

| Minimum minutes | Contributors | PTS | AST | REB | STL | BLK | TOV |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 569 | 15.017 / 5.696 | 3.601 / 2.083 | 6.724 / 3.055 | 1.243 / 0.698 | 0.738 / 0.663 | 1.916 / 0.971 |
| 50 | 523 | 15.445 / 5.017 | 3.583 / 1.920 | 6.718 / 2.982 | 1.251 / 0.528 | 0.774 / 0.655 | 1.943 / 0.811 |
| 100 | 496 | 15.576 / 4.989 | 3.615 / 1.914 | 6.709 / 2.977 | 1.247 / 0.491 | 0.762 / 0.630 | 1.941 / 0.788 |
| 250 | 442 | 15.892 / 4.960 | 3.707 / 1.921 | 6.731 / 3.007 | 1.251 / 0.472 | 0.768 / 0.623 | 1.936 / 0.781 |
| 500 | 375 | 16.326 / 5.092 | 3.835 / 1.968 | 6.653 / 2.968 | 1.239 / 0.428 | 0.752 / 0.602 | 1.976 / 0.809 |

Filtering at 50 removes 46 players; PTS SD falls 5.696→5.017 (about 12%), steals SD 0.698→0.528 (24%), turnovers SD 0.971→0.811 (17%). Thus the unrestricted low-exposure tail materially influences scaling. At 500, steals SD is 0.428 (39% below control), but points SD rises slightly relative to 250: thresholds change the reference population, not just remove errors. Equal standardized weights remain unchanged; raw-unit feature influence changes through SD.

## Top-five changes across all players

Changed ordered lists include reranking the same five names. Mean overlap counts retained top-five names, out of five; these are agreement measures with control, not correctness or predictive stability. Exposure groups below describe query final minutes only and do not filter candidates.

| Minimum | Changed ordered lists / 569 | Mean shared names | Queries under 250 min (127): mean shared | Queries ≥1,000 min (270): mean shared |
|---|---:|---:|---:|---:|
| 0 | 0 | 5.000 | 5.000 | 5.000 |
| 50 | 462 | 4.510 | 4.496 | 4.500 |
| 100 | 491 | 4.408 | 4.346 | 4.411 |
| 250 | 507 | 4.316 | 4.268 | 4.333 |
| 500 | 521 | 4.202 | 4.134 | 4.226 |

## Representative final-checkpoint results

Each row lists all five comparisons and standardized distances, lower is closer. Queries and candidate minutes stay unchanged across cutoffs.

### Bronny James — 183 minutes; 464 candidates

| Scaler cutoff | Comparisons (distance) | Shared names with control |
|---|---|---:|
| 0 | Donte DiVincenzo (0.645); Markelle Fultz (0.756); KJ Simpson (0.758); Grant Williams (0.909); Patty Mills (0.916) | 5 / 5 |
| 50 | Donte DiVincenzo (0.741); Markelle Fultz (0.863); KJ Simpson (0.864); Patty Mills (1.007); Grant Williams (1.034) | 5 / 5 |
| 100 | Donte DiVincenzo (0.772); Markelle Fultz (0.889); KJ Simpson (0.898); Patty Mills (1.019); Grant Williams (1.062) | 5 / 5 |
| 250 | Donte DiVincenzo (0.786); Markelle Fultz (0.899); KJ Simpson (0.914); Patty Mills (1.022); Grant Williams (1.071) | 5 / 5 |
| 500 | Donte DiVincenzo (0.824); Markelle Fultz (0.907); KJ Simpson (0.961); Patty Mills (1.011); Grant Williams (1.072) | 5 / 5 |

### Stephen Curry — 2249 minutes; 87 candidates

| Scaler cutoff | Comparisons (distance) | Shared names with control |
|---|---|---:|
| 0 | Damian Lillard (0.809); De'Aaron Fox (0.904); Devin Booker (0.962); Donovan Mitchell (1.071); Darius Garland (1.113) | 5 / 5 |
| 50 | Damian Lillard (0.903); De'Aaron Fox (1.049); Devin Booker (1.113); Darius Garland (1.212); Anthony Edwards (1.243) | 4 / 5 |
| 100 | Damian Lillard (0.924); De'Aaron Fox (1.069); Devin Booker (1.151); Darius Garland (1.229); Anthony Edwards (1.253) | 4 / 5 |
| 250 | Damian Lillard (0.933); De'Aaron Fox (1.080); Devin Booker (1.168); Darius Garland (1.233); Anthony Edwards (1.252) | 4 / 5 |
| 500 | Damian Lillard (0.927); De'Aaron Fox (1.069); Devin Booker (1.190); Darius Garland (1.231); Anthony Edwards (1.238) | 4 / 5 |

### Nikola Jokić — 2575 minutes; 36 candidates

| Scaler cutoff | Comparisons (distance) | Shared names with control |
|---|---|---:|
| 0 | LeBron James (2.157); Jayson Tatum (2.635); Alperen Sengun (2.643); Cade Cunningham (2.719); James Harden (2.818) | 5 / 5 |
| 50 | LeBron James (2.450); Jayson Tatum (2.934); Alperen Sengun (2.949); Cade Cunningham (3.046); James Harden (3.059) | 5 / 5 |
| 100 | LeBron James (2.525); Alperen Sengun (2.989); Jayson Tatum (2.993); James Harden (3.093); Cade Cunningham (3.125) | 5 / 5 |
| 250 | LeBron James (2.555); Alperen Sengun (3.002); Jayson Tatum (3.011); James Harden (3.091); Cade Cunningham (3.149) | 5 / 5 |
| 500 | LeBron James (2.649); Alperen Sengun (2.986); Jayson Tatum (3.061); James Harden (3.078); Cade Cunningham (3.215) | 5 / 5 |

### Stephon Castle — 2162 minutes; 98 candidates

| Scaler cutoff | Comparisons (distance) | Shared names with control |
|---|---|---:|
| 0 | Austin Reaves (0.597); Malik Monk (0.698); Desmond Bane (0.798); De'Aaron Fox (0.833); Jaylen Brown (0.854) | 5 / 5 |
| 50 | Austin Reaves (0.689); Malik Monk (0.758); Desmond Bane (0.852); Jaylen Brown (0.948); De'Aaron Fox (0.974) | 5 / 5 |
| 100 | Austin Reaves (0.704); Malik Monk (0.781); Desmond Bane (0.859); Jaylen Brown (0.954); Quentin Grimes (0.996) | 4 / 5 |
| 250 | Austin Reaves (0.708); Malik Monk (0.789); Desmond Bane (0.857); Jaylen Brown (0.956); Quentin Grimes (0.998) | 4 / 5 |
| 500 | Austin Reaves (0.689); Malik Monk (0.809); Desmond Bane (0.858); Jaylen Brown (0.938); Quentin Grimes (0.978) | 4 / 5 |

### Anthony Edwards — 2868 minutes; 18 candidates

| Scaler cutoff | Comparisons (distance) | Shared names with control |
|---|---|---:|
| 0 | Jalen Green (1.090); Tyler Herro (1.163); Zach LaVine (1.185); Jayson Tatum (1.226); Devin Booker (1.557) | 5 / 5 |
| 50 | Jalen Green (1.234); Jayson Tatum (1.296); Tyler Herro (1.302); Zach LaVine (1.323); Devin Booker (1.698) | 5 / 5 |
| 100 | Jalen Green (1.259); Jayson Tatum (1.304); Tyler Herro (1.337); Zach LaVine (1.368); Devin Booker (1.728) | 5 / 5 |
| 250 | Jalen Green (1.270); Jayson Tatum (1.298); Tyler Herro (1.351); Zach LaVine (1.388); Devin Booker (1.735) | 5 / 5 |
| 500 | Jalen Green (1.265); Jayson Tatum (1.299); Tyler Herro (1.358); Zach LaVine (1.432); Devin Booker (1.743) | 5 / 5 |

## Playing-time stability diagnostics

For each cutoff separately, keep that scaler fixed and use actual query checkpoints nearest 25%, 50%, 75% of final season minutes. Compare each earlier list to that cutoff’s final list. Production default remains latest checkpoint. This is retrospective sensitivity, not an as-of-date backtest: it uses end-season reference contributors and permits later-date candidate observations. Changes reflect query rates and changing candidate pools together. No causal or statistical-significance claims; five selected players are illustrative, not a representative stability benchmark.

| Player | Cutoff | Earlier reference minutes (25/50/75%) | Top-five overlaps with own final list (out of 5) |
|---|---:|---|---|
| Bronny James | 0 | 45 / 93 / 137 | 0 / 0 / 1 |
| Bronny James | 50 | 45 / 93 / 137 | 0 / 0 / 1 |
| Bronny James | 100 | 45 / 93 / 137 | 0 / 0 / 1 |
| Bronny James | 250 | 45 / 93 / 137 | 0 / 0 / 1 |
| Bronny James | 500 | 45 / 93 / 137 | 0 / 0 / 0 |
| Stephen Curry | 0 | 548 / 1137 / 1696 | 1 / 2 / 4 |
| Stephen Curry | 50 | 548 / 1137 / 1696 | 1 / 2 / 4 |
| Stephen Curry | 100 | 548 / 1137 / 1696 | 1 / 2 / 4 |
| Stephen Curry | 250 | 548 / 1137 / 1696 | 1 / 2 / 4 |
| Stephen Curry | 500 | 548 / 1137 / 1696 | 1 / 3 / 4 |
| Nikola Jokić | 0 | 642 / 1290 / 1948 | 2 / 3 / 2 |
| Nikola Jokić | 50 | 642 / 1290 / 1948 | 2 / 3 / 2 |
| Nikola Jokić | 100 | 642 / 1290 / 1948 | 1 / 3 / 2 |
| Nikola Jokić | 250 | 642 / 1290 / 1948 | 1 / 2 / 2 |
| Nikola Jokić | 500 | 642 / 1290 / 1948 | 1 / 2 / 2 |
| Stephon Castle | 0 | 538 / 1096 / 1635 | 1 / 1 / 2 |
| Stephon Castle | 50 | 538 / 1096 / 1635 | 1 / 1 / 2 |
| Stephon Castle | 100 | 538 / 1096 / 1635 | 1 / 1 / 3 |
| Stephon Castle | 250 | 538 / 1096 / 1635 | 1 / 1 / 3 |
| Stephon Castle | 500 | 538 / 1096 / 1635 | 1 / 1 / 3 |
| Anthony Edwards | 0 | 710 / 1418 / 2155 | 2 / 2 / 1 |
| Anthony Edwards | 50 | 710 / 1418 / 2155 | 2 / 2 / 2 |
| Anthony Edwards | 100 | 710 / 1418 / 2155 | 2 / 2 / 2 |
| Anthony Edwards | 250 | 710 / 1418 / 2155 | 2 / 2 / 2 |
| Anthony Edwards | 500 | 710 / 1418 / 2155 | 1 / 2 / 2 |

## Findings and recommendation

- **Low-minute reference players affect standardization, but the evidence does not establish an optimal cutoff.** With 50 minutes, 462/569 ordered lists change, yet an average 4.510 of five names remain. At 500 the mean is 4.202. Larger changes are not proof of improvement. There are no ground-truth similarity labels here.
- **Scaler filtering alone does not fix low-exposure comparisons.** Bronny (183 minutes) retains all five final comparison names under every scaler, but early-to-final overlap is 0/0/1 under cutoffs 0–250 and 0/0/0 at 500. A fixed reference cannot remove volatility in the query/candidate rates. His DiVincenzo comparison still uses seven games / 189 minutes. More established players remain candidates at early sparse checkpoints regardless of their final exposure.
- **Established-player examples are mostly stable across cutoffs, not uniformly more stable across time.** Curry keeps four of five names under each filtered scaler (Edwards replaces Mitchell); Lillard remains first. His temporal overlaps are 1/2/4 at 0–250 and 1/3/4 at 500. Jokić retains the same five names at every cutoff with order changes, but temporal overlaps shift from 2/3/2 at control to 1/2/2 at 250–500. Edwards retains all five final names; Castle loses Fox for Grimes from 100 upward. There is no consistent time-stability gain across players.
- **An exposure requirement for scaler contributors would not enforce candidate reliability.** Eligibility still admits tiny season-minute or early checkpoint samples and whole-minute precision amplifies rate changes there. Candidate/query exposure thresholds or reliability flags merit a separately authorized experiment if low-minute usefulness matters. Such an experiment should test checkpoint exposure, not merely candidate final-season minutes. Do not silently add a cutoff.
- **Recommendation: retain the original approved baseline for now.** Filtering removes extreme reference observations and is a plausible alternative, but stability results are mixed and no accuracy criterion chooses 50 vs 100 vs 250 vs 500. Do not adopt a particular threshold solely because rankings look familiar. Next, if desired, approve a focused query/candidate exposure experiment with explicit evaluation criteria, coverage tradeoffs and a validation sample beyond these five players.
- Any production scaler-contributor threshold, query/candidate exclusion rule, or changed reliability policy requires user approval. None has been adopted. Existing warnings, six features, equal weights, Euclidean metric and ±10% matching remain approved and unchanged. Application development still awaits WBS 4.4 review.
