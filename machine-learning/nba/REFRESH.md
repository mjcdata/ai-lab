# Refresh NBA data

## Status and invocation

This manual Mac workflow was approved and merged in PR #14. Its first explicitly
requested live refresh and public verification succeeded on 2026-11-23; see
WORKPLAN.md for the actual deployment, snapshot and validation record. There is no schedule,
Git deployment hook, new service or changed similarity methodology.

Once approved, say **“Refresh NBA data”** in local Codex. Project AGENTS.md routes
that request through the coordinator, including publication and verification.
It refreshes only the configured 2026–27 regular season. Season rollover stops
for an explicit configuration decision; it does not silently change the model
or acquire another historical season.

From `machine-learning/nba/`, with Node 24 on PATH:

```sh
# One-time tooling, using existing repository locks and browser dependency.
uv sync --locked
(cd code/frontend && pnpm install --frozen-lockfile)
(cd code/frontend && pnpm exec playwright install chromium)
# Optional: export PLAYWRIGHT_BROWSERS_PATH to an existing browser cache.

# Safe plan only: no data requests, writes, build or Vercel calls.
uv run --offline python -m nba_player_similarity.refresh

# Explicit manual refresh, validate, build, publish and verify.
uv run --with nba_api --with pandas python -m nba_player_similarity.refresh --execute --publish
```

`nba_api`/pandas are the existing optional ingestion dependencies. Package/tool
installation may access registries; it is not an NBA request. Vercel CLI is
pinned to 65.14.0. Existing CLI authentication is required. If it expires, stop,
complete `npx --yes vercel@65.14.0 login` in the browser, then resume the same run.
Credentials remain outside the bundle and never enter Git.

Use the latest approved `origin/main`; a stale/unmerged HEAD or dirty Python,
test or configuration files stop execution. A separate clean worktree is safe:
add `--data-dir /absolute/existing/data --snapshots-dir /absolute/existing/artifacts/snapshots`
and, optionally, `--artifacts-dir /absolute/existing/artifacts/refresh`. Its locked
frontend dependencies must be installed. Frontend sources come from `git archive`
of approved main, so unrelated working-tree UI edits are not published.

## What runs locally

The coordinator journals stages atomically under ignored
`artifacts/refresh/runs/<run-id>/`. An OS lock prevents overlapping runs. It:

1. Verifies approved main, Node 24, offline Python tests, Vercel authentication,
   existing project identity, Hobby plan, public access and absence of Git
   integration. Checks the live canonical snapshot equals the local baseline.
2. Records the actual deployment behind the production alias, backs up current
   raw data/pointer, and hashes all 80 historical caches. Staging references those
   histories without modifying them. Original raw data and release remain active.
3. Uses the existing nba_api LeagueGameLog fetcher/retry policy to retrieve current
   player logs and team logs into isolated staging. Previously completed stages
   are reused on resume. No historical endpoint is called.
4. Runs quality checks, then the existing season snapshot generator. Builds the
   static Next.js export, runs frontend unit tests and uses the existing isolated
   Vercel packager. Runs mobile/desktop checks against the local packaged site.
5. Publishes only after those gates pass, verifies the staged release, promotes it,
   verifies the public site, then activates the local cache/pointer and release
   record. It preserves prior immutable snapshots and deployment receipts.

Omit `--publish` to stop after local preparation; this still makes NBA requests.
It does not activate canonical data or publish. Later use `--execute --publish
--resume <run-id>` with the same paths. Never use `--execute` merely to inspect
what would happen.

## Validation gates

- Player response must be nonempty, structurally valid, unique by player/game and
  retain every previously cached player/game key. All six current statistics and
  minutes must be finite/nonnegative; names, teams, season and dates must be valid.
- Independent team-mode retrieval from the **same approved nba_api endpoint**
  must contain two distinct teams with completed W/L results for each game.
  Team/game sets, dates and summed player points must reconcile exactly. Missing
  games, partial/in-progress responses or source inconsistencies stop publication.
- This is coverage relative to NBA's team logs and known cached rows, not an
  independent proof that the source is complete. A legitimate source correction
  removing prior rows also stops for review. Player/team calls straddling a game
  completion can disagree; retry a new run after investigating, never bypass.
- Historical hashes must remain unchanged. Historical missing statistics remain
  missing; original complete-case exclusions, per-36 calculations, own-season
  Z-scores, equal weights, self-exclusion and top-five ranking are unchanged.
  No new exposure cutoff is applied. Publication checks can reject bad current
  source data without redefining model eligibility. Existing reliability exclusions
  and exposure warnings remain visible in generated coverage reports.
- Every snapshot result must exactly equal direct model output. Check all source,
  model and asset hashes, nonempty inventory/historical pool, schema, finite sorted
  distances and consistent six-stat explanations. Sparse results follow the
  existing model; no invented comparisons are added.
- Package hashes and snapshot identity must agree. Existing packaging rejects
  unexpected/private files, credentials, symlinks and runtime functions. Only
  allowed static assets and the active snapshot are uploaded, not raw data.
- Local, staged and public smoke checks verify every snapshot asset's size/hash,
  index, anonymous access, actual search/selection, reference stats, comparison
  explanations and responsive layout at 390px and 1440px. Selection is taken from
  the generated index rather than hardcoded player availability. No live API is
  allowed. Browser tests use Chromium, not physical devices/Safari.

## Publishing and evidence

Only existing project `nba-player-similarity` (`prj_1ElLC4mZqX42r6YHyej0vegnrSS6`)
in `malcolmjconnors-projects` is accepted. Settings are checked, never changed.
The local package receives only that existing project link; no `vercel link`,
project creation, environment edit or Git integration command runs.

The coordinator uses the documented manual **prebuilt static** deployment:

```sh
# Run by the coordinator in the isolated package, not directly in source.
npx --yes vercel@65.14.0 deploy --prebuilt --prod --skip-domain --scope malcolmjconnors-projects --meta refreshRun=<id> --meta sourceCommit=<sha>
# Only after deployment-specific smoke and integrity checks succeed:
npx --yes vercel@65.14.0 promote <verified-candidate-url> --yes --scope malcolmjconnors-projects
```

`--skip-domain` stages a production-environment release without switching the
live alias. This avoids promoting a Preview through a new production rebuild;
the exact tested static production artifact is promoted. The coordinator reads
the canonical alias, not the most recently created deployment, to determine what
is live. An unexpected concurrent production release stops it without overwriting
another operator's work. There remains a short external-service race between
checking the alias and promoting; do not run other production releases concurrently.

Public target: https://nba-player-similarity.vercel.app . Success requires public
checks, not just a READY upload. `release.json` records actual deployment ID/URL,
source commit, snapshot ID, quality counts/date, stage completion and live results.
`artifacts/refresh/current.json` points to the successful run. Local logs, reports,
packages, backups and journals stay ignored. Codex records a concise verified
summary in WORKPLAN.md; only documentation is committed afterward.

## Failure, interruption and recovery

Any failed gate stops the run; canonical data remain unchanged before verified
publication. Inspect `state.json`, `quality.json` and numbered private `logs/` in
the run directory. Do not copy secrets from CLI logs into Git/PRs.

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.refresh --execute --publish --resume <recorded-run-id>
```

Use identical paths/source commit. Completed retrieval/build stages are reused,
while data/snapshot/package integrity is checked again. Interrupted packaging is
rebuilt in its own staging directory. A lost upload response is reconciled by
run/source metadata on Vercel, never blindly uploaded again. If no unique READY
candidate can be established, stop for an operator decision. A recorded child
PID still alive requires inspection; never kill unrelated processes or delete a
lock file to bypass overlap protection. OS locking releases on process exit.

If public verification fails after promotion, the coordinator rolls back to the
recorded previous deployment and verifies the alias. That run cannot be promoted
again. Hobby rollback supports the previous production release; older archived
bundles are recovery inputs, not a guarantee of unlimited instant rollbacks.
If rollback status is uncertain, stop: verify the canonical alias and recover
manually before starting a new reviewed run. Never overwrite a concurrent release.

Manual recovery, using the recorded baseline URL, only when it is still the
immediately previous production and recovery is authorized:

```sh
npx --yes vercel@65.14.0 rollback <baseline-production-url> --yes --scope malcolmjconnors-projects
```

Verify public snapshot and browser behavior afterward. Do not claim recovery
from CLI output alone. Local backups are under `baseline/`; old snapshots are
retained. Interrupted local activation after successful publication is idempotent
and resumes without another upload/promotion. Unexpected local changes stop
activation. Do not delete a run until its public and local states are reconciled.
There is deliberately no automatic garbage collection of recovery evidence.

## Future weekly scheduling (not enabled)

A later approved Mac launchd job or equivalent can invoke this same CLI with its
lock, journals, explicit paths and verification gates. It would need a logged-in
Mac, stable Node/uv/browser paths, authenticated Vercel tooling, logs/notifications
and a decision about sleep/network failures. No scheduler, cron entry, GitHub
Action, external data runner or recurring deployment is installed by this change.

Reference: [Vercel staged production uploads](https://vercel.com/docs/cli/deploy),
[promotion](https://vercel.com/docs/cli/promote),
[rollback](https://vercel.com/docs/cli/rollback),
[nba_api LeagueGameLog](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamelog.md).
