"""Manual refresh coordinator. Default invocation prints a plan; no live effects."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re
import uuid
from .ingestion import _atomic_json
from .seasonal import CURRENT

PROJECT = 'prj_1ElLC4mZqX42r6YHyej0vegnrSS6'
WORKSPACE = 'malcolmjconnors-projects'
ORG = 'team_3Yfk76aPqCGt1YvC7Xy30yV1'
PUBLIC_URL = 'https://nba-player-similarity.vercel.app'


@dataclass
class Config:
    root: Path
    data: Path
    artifacts: Path
    snapshots: Path

    def paths(self):
        return {k: str(Path(getattr(self, k)).resolve()) for k in ('root', 'data', 'artifacts', 'snapshots')}


@contextmanager
def exclusive(root):
    """OS releases this lock after interruption, including SIGKILL; never delete it."""
    root.mkdir(parents=True, exist_ok=True)
    with (root/'.refresh.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another NBA refresh is running') from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def run_refresh(config, ops, *, publish=False, resume=None):
    """Injected operations keep failure/recovery tests entirely offline.

    A network mutation is journaled BEFORE execution. Unknown upload results are
    reconciled by run metadata, never retried blindly. Promotion uses a verified
    staged release and preserves the previous production deployment for rollback.
    """
    with exclusive(config.artifacts):
        if resume and not re.fullmatch('[a-f0-9]{32}', resume):
            raise ValueError('Resume requires a recorded 32-character run ID')
        run_id = resume or uuid.uuid4().hex
        run = config.artifacts/'runs'/run_id
        path = run/'state.json'
        if resume:
            state = json.loads(path.read_text())
            if state['paths'] != config.paths():
                raise ValueError('Resume paths differ from the recorded run')
            if state.get('rollback_required') and not state.get('rolled_back'):
                raise RuntimeError('Rollback outcome is uncertain; verify/restore production manually before starting a new run')
            if state.get('rolled_back'):
                raise RuntimeError('Run was rolled back; inspect failure and start a new run')
            if state['phase'] == 'complete':
                return state
            if state.get("baseline"):
                ops.check_source(config, state)
            if state.get('candidate') and not publish:
                raise RuntimeError('Use --publish to reconcile an interrupted publishing run')
        else:
            run.mkdir(parents=True)
            state = dict(schema_version=1, id=run_id, paths=config.paths(), phase='preflight', completed=[],
                         started_at=datetime.now(timezone.utc).isoformat())

        def save():
            _atomic_json(path, state)

        def step(name, action):
            if name in state['completed']:
                return
            state['phase'] = name
            save()
            print(f'{run_id}: {name}', flush=True)
            result = action(config, run, state)
            if result:
                state.update(result)
            state['completed'].append(name)
            save()

        save()
        try:
            step('preflight', ops.preflight)
            step('stage', ops.stage)
            step('ingest', ops.acquire)
            step('quality', ops.quality)
            step('snapshot', ops.snapshot)
            step('build', ops.build)
            step('package', ops.package)
            # Always revalidate persisted artifacts when resuming, even if the
            # preceding validation succeeded before interruption.
            ops.validate_candidate(config, run, state)
            step('local_smoke', ops.local_smoke)
            if not publish:
                state['phase'] = 'prepared'
                save()
                return state

            if not state.get('candidate'):
                if state.get('uncertain_action') == 'candidate':
                    candidate = ops.recover_candidate(config, run, state)
                else:
                    state.update(phase='deploying_candidate', uncertain_action='candidate')
                    save()
                    candidate = ops.deploy_candidate(config, run, state)
                state.update(candidate=candidate, phase='candidate_ready', uncertain_action=None)
                save()
            ops.verify_candidate(config, run, state)
            ops.validate_candidate(config, run, state)
            current = ops.production_id(config, state)
            candidate = state['candidate']['id']
            previous = state['baseline']['production']['id']
            if current not in (candidate, previous):
                raise RuntimeError('Production changed concurrently; no promotion or rollback attempted')
            if current == previous:
                if state.get('promotion_completed'):
                    raise RuntimeError('Production was changed after promotion; operator decision required')
                state.update(phase='promoting', uncertain_action='promote')
                save()
                ops.promote(config, run, state)
            state.update(phase='promoted', promotion_completed=True, uncertain_action=None)
            save()
            try:
                if ops.production_id(config, state) != candidate:
                    raise RuntimeError('Production does not point at the validated candidate')
                live = ops.verify_live(config, run, state)
            except Exception:
                # Never overwrite another operator's newer production release.
                if ops.production_id(config, state) == candidate:
                    state.update(phase='rolling_back', rollback_required=True)
                    save()
                    ops.rollback(config, run, state)
                    state.update(phase='rolled_back', rolled_back=True)
                    save()
                raise
            state.update(phase='live_verified', live_verification=live)
            save()
            step('activate', ops.activate)
            state.pop('error', None)
            state.update(phase='complete', deployment=state['candidate'], public_url=PUBLIC_URL,
                         finished_at=datetime.now(timezone.utc).isoformat())
            save()
            _atomic_json(run/'release.json', state)
            _atomic_json(config.artifacts/'current.json', {'run_id': run_id, 'deployment': state['deployment'],
                                                          'snapshot': state['snapshot'], 'public_url': PUBLIC_URL})
            return state
        except BaseException as exc:
            state['error'] = f'{type(exc).__name__}: {exc}'
            save()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Opt into live current-season retrieval and local builds')
    parser.add_argument('--publish', action='store_true', help='Verify staged release, then promote to existing production')
    parser.add_argument('--resume', help='Resume a recorded run without blindly repeating uploads')
    root = Path(__file__).resolve().parents[3]
    parser.add_argument('--root', type=Path, default=root)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--artifacts-dir', type=Path)
    parser.add_argument('--snapshots-dir', type=Path)
    args = parser.parse_args(argv)
    if args.publish and not args.execute:
        parser.error('--publish requires --execute')
    config = Config(args.root.resolve(), (args.data_dir or args.root/'data').resolve(),
                    (args.artifacts_dir or args.root/'artifacts/refresh').resolve(),
                    (args.snapshots_dir or args.root/'artifacts/snapshots').resolve())
    if not args.execute:
        print(json.dumps(dict(mode='plan_only', season=CURRENT, paths=config.paths(), project=PROJECT,
                              stages=['preflight', 'stage current + immutable history references', 'ingest player/team logs',
                                      'coverage/quality validation', 'snapshot + parity', 'build + package + local smoke',
                                      'staged release + verify', 'promote + public verify or rollback', 'activate local release']), indent=2))
        return 0
    from .refresh_runtime import LocalOps
    try:
        result = run_refresh(config, LocalOps(), publish=args.publish, resume=args.resume)
    except (Exception, KeyboardInterrupt) as exc:
        parser.exit(1, f'Refresh stopped: {exc}. Inspect the run state before resuming.\n')
    print(json.dumps({k: result.get(k) for k in ('id', 'phase', 'snapshot', 'deployment', 'public_url')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
