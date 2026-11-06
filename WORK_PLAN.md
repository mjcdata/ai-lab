# AI Lab work plan

## Completed

- [x] Create the minimal lab structure and README.
- [x] Document agent instructions and development workflow in AGENTS.md.
- [x] Publish the repository at https://github.com/mjcdata/ai-lab.
- [x] Define the NBA player-similarity project and its work breakdown structure.

## Current project

The active project is **NBA player similarity**. Its scope, deliverables, progress, and decision gates live in [the NBA work plan](machine-learning/nba/WORKPLAN.md). Update that plan rather than duplicating its task list here.

Historical source selection (WBS 1.1–1.5) is approved. The local three-season ingestion pilot completed on 2026-11-05, and WBS 1.7 documentation and offline tests are complete. The next approved implementation is **DATA-2 (WBS 2.1–2.6)**: pilot-only data preparation. Full-history acquisition (WBS 1.6) remains open. Large downloads, substantial processing, and training run locally and are initiated by the user. Codex is launched manually through ChatGPT/Codex for approved implementation tasks; GitHub Actions runs tests only, without an OpenAI API key or scheduled Codex execution.

## Future project ideas (not yet approved for implementation)

- **Retail machine learning** (`machine-learning/retail/` when started): explore customer churn prediction as the initial ML use case. Candidate features include purchase recency, frequency, and spend.
- **Customer acquisition cost (CAC):** explore acquisition-cost analysis and potentially predictive modeling later. CAC requires marketing spend and customer acquisition/channel data beyond retail transaction records.
- **Customer lifetime value (CLV):** possible extension to connect retention, acquisition cost, and customer value.
- Investigate whether the existing Retail Revenue Intelligence transaction dataset can support churn research. Confirm labels, data coverage, and methodology before implementation. Do not create a retail project folder, download data, or assign Codex work yet.

## Coordination

- Read the latest GitHub commits, AGENTS.md, and the relevant project work plan before acting.
- Keep approved decisions and progress in repository documentation so other chats can pick up the work.
- Manually initiate Codex implementation on approved tasks tagged `[CODEX-READY]`; Codex commits and pushes tested changes to `main` when authorized.
- GitHub Actions CI runs offline tests on pushes to `main` and on manual dispatch; it never implements tasks or pushes commits.
- Use commit monitoring to identify meaningful changes and required decisions; avoid duplicate work and self-triggering loops.
- A scheduled monitor is configured separately in the app; this document does not itself enable monitoring.
