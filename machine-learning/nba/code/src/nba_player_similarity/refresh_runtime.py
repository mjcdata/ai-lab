"""Mac-local adapters for the refresh coordinator; invoked only with --execute."""
from datetime import date
import io
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from urllib.parse import urlparse
from urllib.request import urlopen
from .ingestion import ingest, fetch_season, fetch_with_retries, season_range, _atomic_json
from .refresh import CURRENT, PROJECT, WORKSPACE, ORG, PUBLIC_URL
from .refresh_validation import read, sha, validate_current, validate_snapshot
from .season_snapshot import generate


def atomic_copy(source, destination):
    """Replace canonical bytes exactly, preserving checksums across resume."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.refresh-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output, source.open('rb') as incoming:
            shutil.copyfileobj(incoming, output)
            output.flush(); os.fsync(output.fileno())
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)


class LocalOps:
    def command(self, args, cwd, run, state, *, env=None, timeout=900):
        """Journal process ownership; terminate our child group on caught interruption."""
        logs = run/'logs'; logs.mkdir(exist_ok=True)
        log = logs/f'{len(list(logs.glob("*.log"))):03d}.log'
        with log.open('w') as output:
            process = subprocess.Popen([str(a) for a in args], cwd=cwd, env=env,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            state['active_child'] = {'pid': process.pid, 'log': str(log)}
            _atomic_json(run/'state.json', state)
            try:
                code = process.wait(timeout=timeout)
            except BaseException:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
                raise
            finally:
                state.pop('active_child', None)
                _atomic_json(run/'state.json', state)
        text = log.read_text()
        if code:
            raise RuntimeError(f'Command failed ({code}); inspect private local log {log}')
        return text

    @staticmethod
    def json_output(text):
        for index, char in enumerate(text):
            if char == '{':
                try:
                    value, _ = json.JSONDecoder().raw_decode(text[index:])
                except ValueError:
                    continue
                if isinstance(value, dict):
                    return value
        raise ValueError('CLI returned no structured JSON; do not guess deployment status')

    def vc(self, args, config, run, state):
        return self.command(['npx', '--yes', 'vercel@65.14.0', *args, '--scope', WORKSPACE], config.root, run, state)

    def api(self, endpoint, config, run, state):
        return self.json_output(self.vc(['api', endpoint], config, run, state))

    def project(self, config, run, state):
        project = self.api(f'/v9/projects/{PROJECT}', config, run, state)
        team = self.api(f'/v2/teams/{ORG}', config, run, state)
        if (project['id'] != PROJECT or project['name'] != 'nba-player-similarity'
                or team.get('slug') != WORKSPACE or team.get('billing', {}).get('plan') != 'hobby'
                or project.get('link') or project.get('ssoProtection') or project.get('passwordProtection')
                or project.get('trustedIps') or project.get('framework') is not None):
            raise RuntimeError('Unexpected project, cost/plan, Git integration or access settings; operator decision required')
        return project

    def source_commit(self, config):
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=config.root, text=True, timeout=60).strip()
        head = git('rev-parse', 'HEAD')
        remote = git('ls-remote', '--exit-code', 'origin', 'refs/heads/main').split()[0]
        if head != remote:
            raise RuntimeError('Use current approved main, not an unmerged/stale branch')
        if git('status', '--porcelain', '--', 'code/src', 'code/tests', 'pyproject.toml', 'uv.lock'):
            raise RuntimeError('Uncommitted Python/config changes could alter the workflow; use a clean worktree')
        return head

    def check_source(self, config, state):
        child = state.get('active_child')
        if child:
            try:
                os.kill(child['pid'], 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError('A prior child PID still exists; inspect it before resuming')
            state.pop('active_child', None)
        if state.get('baseline') and self.source_commit(config) != state['baseline']['commit']:
            raise RuntimeError('Source commit changed; start a new reviewed run')

    def preflight(self, config, run, state):
        year = date.today().year if date.today().month >= 10 else date.today().year-1
        if f'{year}-{(year+1)%100:02d}' != CURRENT:
            raise RuntimeError('Season rollover requires a separately approved model/UI configuration update')
        for executable in ('node', 'npm', 'npx'):
            if not shutil.which(executable):
                raise RuntimeError(f'{executable} missing from PATH; activate Node 24 first')
        if not subprocess.check_output(['node', '--version'], text=True).startswith('v24.'):
            raise RuntimeError('Activate the documented Node 24 runtime')
        commit = self.source_commit(config)
        self.project(config, run, state)  # Also checks auth without initiating login.
        self.command([sys.executable, '-m', 'unittest', 'discover', '-s', 'code/tests', '-q'],
                     config.root, run, state)
        manifest = validate_snapshot(config.snapshots)
        if manifest['season'] != CURRENT:
            raise ValueError('Local snapshot season mismatch')
        prior = read(config.snapshots/'current.json')
        current_path = config.data/'raw'/f'{CURRENT}.json'
        historical = {s: sha(config.data/'raw'/f'{s}.json') for s in season_range()}
        if manifest['source_sha256'] != {**historical, CURRENT: sha(current_path)}:
            raise ValueError('Working snapshot does not match canonical local raw caches')
        deployment = self.current_production(config, run, state)
        with urlopen(PUBLIC_URL+'/snapshots/current.json', timeout=30) as response:
            public = json.load(response)
        if public != prior:
            raise ValueError('Local baseline differs from live snapshot; reconcile before refreshing')
        baseline = dict(commit=commit, production=deployment, historical=historical,
                        current_sha=sha(current_path), pointer_sha=sha(config.snapshots/'current.json'))
        (run/'baseline').mkdir(exist_ok=True)
        shutil.copyfile(current_path, run/'baseline'/f'{CURRENT}.json')
        shutil.copyfile(config.snapshots/'current.json', run/'baseline/current.json')
        return {'baseline': baseline}

    def stage(self, config, run, state):
        raw = run/'data/raw'; raw.mkdir(parents=True, exist_ok=True)
        for season in state['baseline']['historical']:
            path = raw/f'{season}.json'
            if not path.exists():
                path.symlink_to((config.data/'raw'/f'{season}.json').resolve())

    def acquire(self, config, run, state):
        # A completed candidate cache survives a crash before this stage's journal.
        ingest(CURRENT, run/'data')
        teams = run/'teams.json'
        if not teams.exists():
            values = fetch_with_retries(CURRENT, fetcher=lambda s: fetch_season(s, player_or_team='T'))
            _atomic_json(teams, values)

    def quality(self, config, run, state):
        report = validate_current(read(run/'data/raw'/f'{CURRENT}.json'),
                                  read(run/'baseline'/f'{CURRENT}.json'), read(run/'teams.json'))
        _atomic_json(run/'quality.json', report)
        return {'quality': {k: report[k] for k in ('rows', 'completed_games', 'latest_date', 'previous_rows_preserved')}}

    def snapshot(self, config, run, state):
        root = run/'snapshots'
        if (root/'current.json').exists():
            manifest = validate_snapshot(root, data_dir=run/'data')
        else:
            # Only this run's unpublished partial generator output; OS workflow
            # lock ensures no second coordinator can own this directory.
            shutil.rmtree(root, ignore_errors=True)
            manifest = generate(run/'data', root)
        validate_snapshot(root, data_dir=run/'data')
        return {'snapshot': manifest['snapshot_id']}

    def build(self, config, run, state):
        frontend = run/'frontend'
        shutil.rmtree(frontend, ignore_errors=True)
        repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=config.root, text=True, timeout=60).strip())
        relative = str((config.root/'code/frontend').relative_to(repo))
        archive = subprocess.check_output(['git', 'archive', state['baseline']['commit'], relative], cwd=repo, timeout=120)
        extraction = run/'source'; shutil.rmtree(extraction, ignore_errors=True); extraction.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(extraction, filter='data')
        shutil.move(str(extraction/relative), frontend)
        dependencies = config.root/'code/frontend/node_modules'
        if not dependencies.is_dir():
            raise RuntimeError('Install locked frontend dependencies locally before refreshing')
        (frontend/'node_modules').symlink_to(dependencies.resolve(), target_is_directory=True)
        env = os.environ.copy(); env['NBA_SNAPSHOT_DIR'] = str(run/'snapshots')
        self.command(['npm', 'run', 'test:unit'], frontend, run, state, env=env)
        self.command(['npm', 'run', 'build'], frontend, run, state, env=env)

    def package(self, config, run, state):
        bundle = run/'bundle'
        # An interrupted packager may leave a partial directory. This stage has
        # not completed, so discard only this run's unpublished package.
        shutil.rmtree(bundle, ignore_errors=True)
        self.command(['npm', 'run', 'package:vercel', '--', str(bundle)], run/'frontend', run, state)
        _atomic_json(bundle/'.vercel/project.json', {'projectId': PROJECT, 'orgId': ORG, 'projectName': 'nba-player-similarity'})
        return {'bundle_sha': self.bundle_hashes(bundle)}

    @staticmethod
    def bundle_hashes(bundle):
        root = bundle/'.vercel/output'
        if (root/'functions').exists() or any(p.is_symlink() for p in root.rglob('*')):
            raise ValueError('Unexpected function/symlink in static bundle')
        return {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}

    def validate_candidate(self, config, run, state):
        self.check_source(config, state)
        if any(sha(config.data/'raw'/f'{s}.json') != h for s, h in state['baseline']['historical'].items()):
            raise ValueError('Historical caches changed; refusing mixed data or publication')
        candidate = run/'data/raw'/f'{CURRENT}.json'
        if sha(config.data/'raw'/f'{CURRENT}.json') not in (state['baseline']['current_sha'], sha(candidate)):
            raise ValueError('Canonical current cache changed concurrently')
        self.quality(config, run, state)
        manifest = validate_snapshot(run/'snapshots', data_dir=run/'data')
        if any(manifest['source_sha256'].get(s) != h for s, h in state['baseline']['historical'].items()):
            raise ValueError('Staged historical sources differ from the recorded baseline')
        if sha(config.snapshots/'current.json') not in (state['baseline']['pointer_sha'], sha(run/'snapshots/current.json')):
            raise ValueError('Canonical snapshot changed concurrently')
        if manifest['snapshot_id'] != state['snapshot']:
            raise ValueError('Candidate snapshot identity changed')
        bundle = run/'bundle'
        if self.bundle_hashes(bundle) != state['bundle_sha']:
            raise ValueError('Validated static bundle changed')
        static = bundle/'.vercel/output/static'
        pointer = read(static/'snapshots/current.json')
        if pointer != read(run/'snapshots/current.json'):
            raise ValueError('Bundle uses a different snapshot')
        published = static/'snapshots/releases'/state['snapshot']
        for path, info in manifest['files'].items():
            if sha(published/path) != info['sha256']:
                raise ValueError('Packaged data differs from validated snapshot')

    def smoke(self, url, config, run, state):
        report = self.command(['node', 'scripts/refresh-smoke.mjs', url, state['snapshot'],
                               read(run/'snapshots/current.json')['manifest_sha256']],
                              run/'frontend', run, state)
        result = self.json_output(report)
        if result.get('snapshot') != state['snapshot'] or not result.get('passed'):
            raise ValueError('Browser/static smoke verification failed')
        return result

    def local_smoke(self, config, run, state):
        handler = partial(SimpleHTTPRequestHandler, directory=str(run/'bundle/.vercel/output/static'))
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            result = self.smoke(f'http://127.0.0.1:{server.server_port}', config, run, state)
            _atomic_json(run/'local-smoke.json', result)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def current_production(self, config, run, state):
        alias = self.api('/v4/aliases/'+urlparse(PUBLIC_URL).hostname, config, run, state)
        if alias.get('projectId') != PROJECT:
            raise RuntimeError('Production alias belongs to an unexpected project')
        value = self.api(f'/v13/deployments/{alias["deploymentId"]}', config, run, state)
        if value.get('projectId') != PROJECT or value.get('readyState') != 'READY':
            raise RuntimeError('Current production alias is not a READY release')
        return {'id': value['id'], 'url': 'https://'+value['url'].removeprefix('https://')}

    def production_id(self, config, state):
        run = config.artifacts/'runs'/state['id']
        self.project(config, run, state)
        return self.current_production(config, run, state)['id']

    def deployment(self, did, config, run, state):
        value = self.api(f'/v13/deployments/{did}', config, run, state)
        url = 'https://'+value['url'].removeprefix('https://')
        host = urlparse(url).hostname or ''
        if (value.get('projectId') != PROJECT or value.get('readyState') != 'READY'
                or value.get('target') != 'production'
                or value.get('meta', {}).get('refreshRun') != state['id']
                or value.get('meta', {}).get('sourceCommit') != state['baseline']['commit']
                or not host.startswith('nba-player-similarity-') or not host.endswith('-malcolmjconnors-projects.vercel.app')):
            raise ValueError('Deployment project/status/source/run mismatch')
        return {'id': value['id'], 'url': url}

    def deploy_candidate(self, config, run, state):
        text = self.command(['npx', '--yes', 'vercel@65.14.0', 'deploy', '--prebuilt', '--prod', '--skip-domain', '--scope', WORKSPACE,
                             '--meta', f'refreshRun={state["id"]}', '--meta', f'sourceCommit={state["baseline"]["commit"]}'],
                            run/'bundle', run, state)
        # Deploy's human output is not JSON. Resolve its deployment URL through
        # the API, then verify project/run/source metadata before accepting it.
        urls = re.findall(r'https://(nba-player-similarity-[a-z0-9-]+-malcolmjconnors-projects\.vercel\.app)', text)
        if not urls:
            raise RuntimeError('No deployment URL received; resume will reconcile by run metadata')
        value = self.api('/v13/deployments/'+urls[-1], config, run, state)
        did = value['id']
        result = self.deployment(did, config, run, state)
        value = self.api(f'/v13/deployments/{did}', config, run, state)
        if value.get('target') != 'production':
            raise RuntimeError('Expected a production-environment candidate with alias assignment skipped')
        if self.production_id(config, state) != state['baseline']['production']['id']:
            raise RuntimeError('Production alias changed during staged upload; stop for operator review')
        return result

    def recover_candidate(self, config, run, state):
        values = self.api(f'/v6/deployments?projectId={PROJECT}&limit=100', config, run, state)['deployments']
        matches = []
        for value in values:
            detail = self.api(f'/v13/deployments/{value["uid"]}', config, run, state)
            if detail.get('meta', {}).get('refreshRun') == state['id']:
                matches.append(detail['id'])
        if len(matches) != 1:
            raise RuntimeError('Upload status uncertain: inspect Vercel; no duplicate upload attempted')
        return self.deployment(matches[0], config, run, state)

    def verify_candidate(self, config, run, state):
        self.project(config, run, state)
        self.deployment(state['candidate']['id'], config, run, state)
        _atomic_json(run/'candidate-smoke.json', self.smoke(state['candidate']['url'], config, run, state))

    def promote(self, config, run, state):
        self.vc(['promote', state['candidate']['url'], '--yes'], config, run, state)

    def verify_live(self, config, run, state):
        result = self.smoke(PUBLIC_URL, config, run, state)
        _atomic_json(run/'production-smoke.json', result)
        return result

    def rollback(self, config, run, state):
        self.vc(['rollback', state['baseline']['production']['url'], '--yes'], config, run, state)
        if self.production_id(config, state) != state['baseline']['production']['id']:
            raise RuntimeError('Rollback could not be verified; operator intervention required')

    def activate(self, config, run, state):
        # Reconcile partial local activation after interruption; never overwrite
        # unexpected operator changes. Production has already passed verification.
        candidate = run/'data/raw'/f'{CURRENT}.json'
        current = config.data/'raw'/f'{CURRENT}.json'
        if sha(current) not in (state['baseline']['current_sha'], sha(candidate)):
            raise ValueError('Local cache changed; refusing activation')
        target = config.snapshots/'current.json'
        new = run/'snapshots/current.json'
        if sha(target) not in (state['baseline']['pointer_sha'], sha(new)):
            raise ValueError('Local snapshot pointer changed; refusing activation')
        release = config.snapshots/'releases'/state['snapshot']
        if not release.exists():
            shutil.copytree(run/'snapshots/releases'/state['snapshot'], release)
        # If copying was interrupted, complete it safely before pointer activation.
        shutil.copytree(run/'snapshots/releases'/state['snapshot'], release, dirs_exist_ok=True)
        atomic_copy(candidate, current)
        atomic_copy(new, target)
        validate_snapshot(config.snapshots)
        shutil.copyfile(run/'data/reports/season-profiles.json', config.data/'reports/season-profiles.json')
        shutil.copyfile(run/'quality.json', config.data/'reports'/f'{CURRENT}.json')
