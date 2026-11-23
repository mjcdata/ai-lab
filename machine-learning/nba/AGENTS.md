# NBA project operations

Follow the root AGENTS.md and current WORKPLAN.md. The season model and datasets
must not be changed as a side effect of operational work.

## “Refresh NBA data”

After the refresh-workflow PR is approved and merged, treat this explicit phrase
as a manually initiated current-season refresh **and publication** request. Use
the Mac and the guarded coordinator documented in [REFRESH.md](REFRESH.md):

```sh
uv run --with nba_api --with pandas python -m nba_player_similarity.refresh --execute --publish
```

Read REFRESH.md and the latest work plan first. Use current approved main in a
clean worktree; preserve unrelated local edits and point to existing local data
and snapshots with the documented flags if necessary. Do not bypass checks,
refresh history, change eligibility/scoring, create projects, enable Git deploys,
upgrade hosting, or schedule anything. No additional routine production prompt
is needed for this explicit request once the workflow is approved. Stop for
failed validation, unexpected project/cost/settings, authentication, concurrent
changes, uncertain upload/rollback status or season rollover.

For an interrupted run, inspect its local state and resume the same ID instead
of starting another upload. Never infer success from CLI exit status alone.
Only after verified public success, summarize the release.json evidence in
WORKPLAN.md (deployment ID, snapshot, source commit, data date/counts, quality
and mobile/desktop verification). Commit documentation only, using the root
sync/test rules. Never commit generated data, run journals, logs or bundles.
Report failures and recovery instructions using the root reporting format.

This is an on-demand workflow, not a scheduled monitor. This implementation
task does not authorize a live refresh or deployment.
