# Vercel deployment readiness — 2026-11-09

## Superseding launch decision

The user now authorizes a free, noncommercial, public personal portfolio release on Vercel Hobby if eligible. The user explicitly accepts the remaining NBA licensing uncertainty and directs no further licensing research; this does not assert publication permission. Prior rights-clearance blocker text below records the readiness-review state and is superseded for execution by this decision. Guide login/linking and verify hosting settings, but **obtain final user confirmation before production upload**. Then verify the actual public URL and update WORKPLAN. No paid services or automation. The launch bundle is `artifacts/vercel/2026-11-09-launch/`, freshly built with the accepted intro removal; the earlier readiness bundle is retained unchanged.

## Latest recheck

The existing linked project was rechecked: Hobby, public/no-login settings, Other/static and manual prebuilt configuration remain valid. A subsequently added GitHub connection to `mjcdata/ai-lab` on `main` was disconnected from this project to prevent automatic deployments. No repository or global GitHub integration was changed, no new project was created, and deployment history is empty. Launch bundle bytes match the latest local export; all 457 result checksums pass. Final production confirmation remains pending. See the latest WORKPLAN entry for the exact pinned command.

## Verified launch setup — awaiting final production confirmation

Authenticated as `malcolmjconnor`; personal workspace `malcolmjconnors-projects` reports Hobby. Isolated `2026-11-09-launch` bundle is linked to `nba-player-similarity` (project `prj_1ElLC4mZqX42r6YHyej0vegnrSS6`). Framework is Other/static, bundle root `.`, output `.vercel/output/static`, Node 24 tooling, remote build/install disabled, Vercel Authentication disabled, no password or trusted-IP restriction, and no Git connection. No deployment has been made. The CLI-generated local OIDC env file was removed and was never public. Use pinned CLI `65.14.0` for the final `deploy --prebuilt --prod --scope malcolmjconnors-projects` command **only after final user confirmation**. The launch bundle has 491 public files / 6,594,527 bytes and the same accepted snapshot/results; the original readiness bundle below is retained unchanged.

## Decision and current status

The user reports CEO acceptance of the MVP and approval for public deployment. That product/deployment decision is recorded; it does not need to be requested again. This task authorizes review, local packaging and documentation **only**. No Vercel login, project creation/link, upload, deployment, paid service, domain or refresh automation was performed. There is no verified public URL.

Technical verdict: the Next.js application is compatible with Vercel static hosting. Recommend **manual prebuilt static upload from the Mac**, not a Git-connected remote build. Raw/prepared NBA caches and generated snapshots remain Git-ignored. A fresh clone cannot run the current frontend build successfully until a validated snapshot artifact is supplied. Do not fix this by committing raw datasets, adding live NBA requests to builds, or introducing an API service.

## Correct roots and settings

| Setting | Value |
| --- | --- |
| Next.js source application root | `machine-learning/nba/code/frontend` |
| Node version for local/source builds | `24.x` (declared in package.json) |
| Dependency installation | `pnpm install --frozen-lockfile` |
| Build | `pnpm build` |
| Static export directory | `out` relative to the frontend root |
| Recommended Vercel project preset | **Other**, deliberately serving a static export rather than invoking a Next.js server adapter |
| Runtime/API environment variables | None |
| Remote Git build | Not configured/recommended; missing ignored snapshots are a blocker for this path |
| Actual recommended upload root | The isolated generated bundle, not the repository or source application root |
| Prebuilt artifact | `<bundle>/.vercel/output/config.json` (v3) and `<bundle>/.vercel/output/static/` |
| Production server/build step | None for `vercel deploy --prebuilt --prod`; the completed local build is uploaded |

The source project is Next.js (`output: 'export'`), so Vercel can detect its Next.js preset. We intentionally use **Other** for the manual static project: there is no need for Next.js runtime functions, SSR, ISR, server actions, API routes or a Python service. If a future artifact-input process enables Vercel source builds, use the source root above, install/build commands above, and output `out`. That is a separate workflow, not enabled here. Do not connect GitHub auto-deployments under this task's no-automation scope.

`NBA_SNAPSHOT_DIR` is an optional **local build-time** snapshot source override. Its default is `../../artifacts/snapshots`; do not configure a Mac filesystem path in Vercel. No `NEXT_PUBLIC_*`, API URL, OpenAI key, NBA credentials, database, storage account or Python environment is needed at runtime. Vercel CLI login/project credentials are operator tooling, not frontend environment variables; never put them in the static bundle.

## Local preparation — safe to run before public release

From the NBA project root, use existing validated caches. Regeneration is optional when the accepted snapshot already exists; it is offline and does not acquire or refresh data:

```sh
uv run --offline python -m nba_player_similarity.season_snapshot
uv run --offline python -m unittest discover -s code/tests -v
cd code/frontend
pnpm run test:unit
pnpm build
pnpm run package:vercel -- ../../artifacts/vercel/2026-11-09-readiness
```

The reviewed bundle already exists at that last path. For another packaging run, supply a **new** directory name. The packager refuses to overwrite a previous bundle or linked project. It performs no Vercel command or network request. `artifacts/` and generated snapshots remain ignored; do not force-add them to Git.

The packager checks snapshot inventory/checksums, copies only the active snapshot and allowed Next.js export assets, rejects symlinks/unexpected files, and checks for common credential/private-path patterns. It emits only `.vercel/output/`, with **no functions**. A filesystem route serves static assets; unknown paths use the exported 404 page. No catch-all rewrite to index.html is used, so missing JSON cannot masquerade as a successful page response. This is a narrow exposure check, not a comprehensive secret-scanner guarantee.

## Publication blockers and licensing

**Rights clearance remains unresolved.** NBA terms require attribution and restrict publication and comprehensive statistics databases. See [NBA terms](https://www.nba.com/termsofuse). CEO acceptance is an internal product decision; the repository contains no NBA redistribution permission or other clearance evidence. Obtain and record the rights holder's permission, or a qualified determination that this particular public use is permitted, before uploading these NBA-derived assets. This review does not make that legal determination. Do not change data sources or strip explanatory statistics as an unapproved workaround.

Added visible NBA.com source attribution and included the repository's MIT software license in the export. Neither grants rights to NBA data. Public assets include athlete names, per-36 statistics, exposures, Z-scores and model explanations; they are downloadable, not private merely because raw logs are excluded. No headshots, NBA logos, ads, sponsorship, gambling features or paid services were added. Third-party framework notices should remain intact in generated bundles; the MIT license covers repository software, not every third-party dependency or NBA content.

**Vercel plan eligibility is not verified.** Hobby is for personal, noncommercial use; confirm that description fits this project/account. If it is a company/commercial release, obtain approval for an appropriate plan rather than assuming the earlier $0 target applies. No account, billing status or paid upgrade was inspected or changed.

## Exact upload steps — instructions only, do not run until blockers are resolved

The reviewed bundle contains the deployment inputs; it does not need repository data after packaging. Use a Vercel account/project you are authorized to manage. With Node 24 available:

```sh
cd "/Users/mj/Documents/Archive/Codex/AI Lab/machine-learning/nba/artifacts/vercel/2026-11-09-readiness"
npx vercel login
npx vercel link
npx vercel deploy --prebuilt --prod
```

During linking, choose the intended account/team, a dedicated `nba-player-similarity` project, and **this bundle directory (`.`)**. Use Framework Preset **Other**. Do not point Root Directory at `machine-learning/nba/code/frontend` inside this bundle: that source path is not present. Do not connect a Git repository, add API/environment settings, enable paid options, or run `vercel build` in the bundle. The Build Output API artifact is already complete. `npx` may download CLI tooling; it does not need to download NBA data. Inspect the selected project/account before the deployment command. CLI/project creation and public upload have deliberately not been exercised for this readiness task.

After the CLI returns a real URL, verify its HTTP status and open it in a browser: search/select a current player, load five historical matches, inspect six-stat explanations/exposure warnings and test a mobile viewport. Fetch `/snapshots/current.json` and an actual referenced result URL; verify unknown paths return 404 and that no runtime API requests occur. Confirm the intended public-access/protection setting and final domain. Record the verified URL, deployment ID, code commit and snapshot ID in WORKPLAN. Until then, report **not deployed**, not success. Keep the prior immutable bundle for rollback; no recurring refresh is configured.

## Measured artifact and validation

Reviewed snapshot: `32de55821ff743229801f546838596b9`; 457 current players and 457 individual per-36 result files. Snapshot assets total **5,613,560 bytes** (460 JSON files); individually gzipped result payloads total **1,476,837 bytes**. Whole export after attribution/license changes: **491 files, 6,595,528 bytes (6.29 MiB)**, excluding the small Vercel routing config. Largest file: **242,212 bytes**. Raw/prepared local data are approximately 935 MiB and **are not in the upload bundle**; old snapshot releases are also excluded.

No tracked raw datasets, snapshots or env files were found. A high-confidence tracked-file credential scan found no matches; the actual isolated bundle passed its stricter file/credential/private-path checks. Manifest source/code hashes and coverage counts are intentional public provenance, not raw files or local absolute paths. No score or similarity calculation changed.

Validation run for this review: 51 Python tests; 7 Node loader/staging/packaging tests; production static build. Desktop/mobile browser checks are run against an isolated copy of the bundle at loopback port 3001, outside the source tree, with no model/API dependency. All 8 browser cases passed against that isolated static directory, including source attribution, search, selected-player statistics, explanations, warnings, retries and desktop/mobile layout. Local serving validates the content; Vercel routing/account behavior remains unverified until a real deployment. Local tests do not establish Vercel account access, plan eligibility, rights clearance or successful public deployment.

Sources checked 2026-11-09: [Vercel build settings](https://vercel.com/docs/builds/configure-a-build), [Node versions](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions), [static Build Output API files](https://vercel.com/docs/build-output-api/primitives), [routing configuration](https://vercel.com/docs/build-output-api/configuration), [prebuilt CLI deployment](https://vercel.com/docs/cli/deploy), [upload limits](https://vercel.com/docs/limits), [Hobby eligibility](https://vercel.com/docs/plans/hobby). The current Hobby CLI upload limit is 100 MB, so the reviewed artifact is comfortably below it; bandwidth and account eligibility remain separate constraints.
