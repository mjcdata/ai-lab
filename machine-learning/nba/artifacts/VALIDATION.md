# Season baseline validation — 2026-11-08

## Scope and checks

Evaluation uses only existing 2024–25 caches and the approved baseline. No model code, scaler policy, features, thresholds, matching window or datasets were changed. Rookie/veteran examples are manually chosen review cases, not experience labels inferred by the model.

- Audited all 569 latest-player queries over 26,305 eligible checkpoints: every query returned five unique other players; no self-matches; all minutes satisfied inclusive ±10%; every score reconciled to feature squared contributions. No latest-query candidate shortage occurred; synthetic tests cover shortages.
- Recomputed preparation in memory from all 26,306 raw records and obtained exact equality with stored derived checkpoints. Raw 2024–25 records contain no duplicate player/game groups or missing values in MIN and the six features; one zero-minute checkpoint is correctly ineligible.
- Shuffled checkpoint order with fixed seed 42: fixed scaler parameters were exactly unchanged, and all selected example outputs were identical. This establishes deterministic input-order behavior, not predictive validity.
- Relevant offline suite: **28 tests passed, 0 failures**, including existing missingness, whole-duplicate-group exclusion, scoring, rates, checkpoint ties, and explanation checks. No new test files or implementation changes in this review.

## Representative latest-checkpoint queries

Scores are standardized Euclidean distances; lower is closer, not a probability. Candidate counts describe eligible other players, before selecting the top five.

| Selected player | Games / minutes | Candidates | Top five: player (distance) |
|---|---:|---:|---|
| Stephon Castle | 81 / 2162 | 98 | Austin Reaves (0.5967); Malik Monk (0.6978); Desmond Bane (0.7977); De'Aaron Fox (0.8330); Jaylen Brown (0.8545) |
| Zaccharie Risacher | 75 / 1844 | 151 | Klay Thompson (0.5723); Buddy Hield (0.7516); Julian Champagnie (0.8312); Bennedict Mathurin (0.8718); OG Anunoby (0.8810) |
| Zach Edey | 66 / 1419 | 215 | Walker Kessler (1.0910); Kel'el Ware (1.1683); Jalen Duren (1.3666); Donovan Clingan (1.4555); Goga Bitadze (1.4636) |
| LeBron James | 70 / 2447 | 59 | Cade Cunningham (1.1209); James Harden (1.2461); Stephen Curry (1.5565); Jayson Tatum (1.5672); Desmond Bane (1.8094) |
| Chris Paul | 82 / 2291 | 80 | Tyus Jones (1.6001); Tyrese Haliburton (1.6121); Dennis Schröder (1.8273); Spencer Dinwiddie (1.9990); Fred VanVleet (2.0202) |
| Stephen Curry | 70 / 2249 | 87 | Damian Lillard (0.8093); De'Aaron Fox (0.9041); Devin Booker (0.9624); Donovan Mitchell (1.0711); Darius Garland (1.1128) |
| Nikola Jokić | 70 / 2575 | 36 | LeBron James (2.1568); Jayson Tatum (2.6353); Alperen Sengun (2.6430); Cade Cunningham (2.7191); James Harden (2.8181) |
| Bronny James | 27 / 183 | 464 | Donte DiVincenzo (0.6453); Markelle Fultz (0.7565); KJ Simpson (0.7585); Grant Williams (0.9092); Patty Mills (0.9159) |
| Jahlil Okafor | 1 / 3 | 56 | Lester Quiñones (0.0000); Sidy Cissoko (0.0000); Malevy Leons (2.1069); Brandon Boston Jr. (3.9277); Jeff Green (3.9277) |
| Zyon Pullin | 3 / 3 | 56 | Richaun Holmes (0.0000); Jordan McLaughlin (0.0000); Jeff Dowtin Jr. (0.0000); Terrence Shannon Jr. (0.0000); E.J. Liddell (0.0000) |
| Alondes Williams | 1 / 4 | 45 | Pat Spencer (1.5802); Tyler Smith (5.2291); A.J. Lawson (5.3530); PJ Hall (6.4140); Adem Bona (7.0581) |

## Playing-time sensitivity

Diagnostic only: retained the original fixed end-of-season scaler and substituted each selected player’s actual checkpoint nearest 25%, 50%, 75% and 100% of final minutes as the query reference. Every candidate still used the approved closest-minute rule and ±10% window. Production default remains latest eligible checkpoint. This is not a historical backtest: candidates and scaler can use later calendar dates. Changes reflect both accumulating statistics and shifting eligible candidate pools; they do not isolate causal effects.

| Player | Reference minutes | Candidate count | Top match (distance) | Top-five overlap with final list |
|---|---:|---:|---|---:|
| Stephen Curry | 548 | 376 | Luka Dončić (0.9916) | 1 / 5 |
| Stephen Curry | 1137 | 266 | De'Aaron Fox (0.8288) | 2 / 5 |
| Stephen Curry | 1696 | 169 | Damian Lillard (0.6583) | 4 / 5 |
| Stephen Curry | 2249 | 87 | Damian Lillard (0.8093) | 5 / 5 |
| Stephon Castle | 538 | 378 | Terry Rozier (0.7812) | 1 / 5 |
| Stephon Castle | 1096 | 270 | Coby White (0.6533) | 1 / 5 |
| Stephon Castle | 1635 | 181 | Coby White (0.6102) | 2 / 5 |
| Stephon Castle | 2162 | 98 | Austin Reaves (0.5967) | 5 / 5 |
| Bronny James | 45 | 241 | Vít Krejčí (1.5582) | 0 / 5 |
| Bronny James | 93 | 405 | Dalen Terry (0.6658) | 0 / 5 |
| Bronny James | 137 | 457 | Stephon Castle (0.8413) | 1 / 5 |
| Bronny James | 183 | 464 | Donte DiVincenzo (0.6453) | 5 / 5 |
| Nikola Jokić | 642 | 354 | Luka Dončić (1.9394) | 2 / 5 |
| Nikola Jokić | 1290 | 241 | Luka Dončić (1.8002) | 3 / 5 |
| Nikola Jokić | 1948 | 135 | Luka Dončić (1.9800) | 2 / 5 |
| Nikola Jokić | 2575 | 36 | LeBron James (2.1568) | 5 / 5 |

## What works and what limits usefulness

- **High-exposure exploratory comparisons work as designed.** Castle’s final list starts with Reaves/Monk; Edey matches Kessler/Ware/Duren. These are plausible six-stat profiles, not validated predictions or complete style assessments. Veterans Paul and Curry receive recognizable guard comparisons.
- **Low exposure materially undermines interpretation.** Okafor has one game and three minutes and matches two other three-minute observations at distance zero. Pullin’s three-minute season yields five zero-distance matches. Zero distance means identical observed rates, not reliable player equivalence. Bronny James at 45 and 93 minutes has zero top-five overlap with his final 183-minute list; the final DiVincenzo match uses only seven candidate games. Matching minutes does not match games, role, age or development.
- **Tiny samples affect every query through the approved scaler.** Ten of 569 latest reference players have fewer than ten minutes. Without changing the scaler, their squared deviations account for 18.95% of the points variance sum, 18.13% for steals, 8.60% assists, 6.84% turnovers, 4.84% rebounds and 2.17% blocks. This is diagnostic attribution around the approved mean, not results from a replacement scaler. Okafor has 12 assists per-36 and Alondes Williams 45 points per-36 from very small samples. Equal feature weights after standardization do not eliminate this influence.
- **Minute eligibility can exclude intuitive matches.** Jokić’s 2,575-minute reference requires 2,317.5–2,832.5 candidate minutes. Dončić ends at 1,766 and Antetokounmpo at 2,291: neither qualifies. LeBron is the closest eligible match at 2.1568, still a larger distance than Castle/Reaves at 0.5967. Jokić–LeBron squared contributions are rebounds 2.110, steals 1.143, assists 0.554, points 0.444, turnovers 0.394 and blocks 0.007. A top rank is not a guarantee of a close match.
- **Rankings change with accumulated exposure.** Curry’s candidate pool contracts from 376 to 87; final top-five overlap grows from 1/5 at 548 minutes to 4/5 at 1,696. Castle’s pool shrinks 378 to 98 and overlaps only 2/5 at 1,635 minutes. Results must display the precise checkpoint and exposure rather than imply a permanent player identity.
- **Missingness/duplicates are controlled, not solved historically.** The 2024–25 audit finds none. Existing offline tests verify missing values are not zero-filled and all repeated player/game groups are excluded. Earlier pilot findings remain: two rows excluded in 1946–47 and four in 1977–78; no eligible early-era minute checkpoints in 1946–47 and extensive missingness in 1977–78. This review does not validate cross-era scoring or full historical coverage.
- **Omitted features matter.** Risacher matching Thompson does not demonstrate shooting similarity because shooting percentages, attempts, position and age are absent. LeBron/Curry or Jokić/guards are explainable counting-stat comparisons and must not be marketed as comprehensive style, skill, potential or career analogues.

## Recommendations and application gate

1. Keep this as a transparent exploratory **2024–25 season-to-date six-stat comparison**. Show games, minutes, dates, distance and feature explanations; retain existing exposure/precision warnings. Do not promise reliable low-minute or career comparisons. This implements the approved interpretation, not a methodology change.
2. Evidence justifies a future sensitivity experiment comparing an exposure-qualified scaler reference and optional query/candidate exposure thresholds against the current baseline. Do not select a cutoff, change the scaler or filter candidates without user approval. A low-exposure reliability indicator is also justified; avoid uncalibrated confidence percentages.
3. Preserve the ±10% window and six features now. The observed Jokić exclusions explain the behavior but do not establish that widening the window or adding position/shooting improves results. Those require separate approved evaluation.
4. WBS **4.1–4.3 is complete for the requested 2024–25 review**. Cross-era evaluation and full-history acquisition remain unvalidated/open; no claim of full WBS 4 historical coverage. WBS **4.4 remains pending user review/approval before application build**. Recommend approving only a clearly labeled exploratory season-scoped application with visible exposure caveats, or first authorizing the targeted exposure experiment if reliable low-minute comparisons are essential. No API/framework, frontend, hosting or public deployment is authorized by this review.
