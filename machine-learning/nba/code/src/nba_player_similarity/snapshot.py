"""Offline, immutable, validated snapshots with an atomic current pointer."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import uuid
from .preparation import FEATURES
from .similarity import SeasonBaseline
from .responses import comparison_response

MODES = ('per36', 'per_game')
SCHEMA_VERSION = 1


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate(data_dir, output_dir, *, producer=comparison_response):
    """Generate all records before publishing; exceptions preserve current.json.

    A lock prevents concurrent publishers. Immutable releases remain for rollback.
    No acquisition, preparation, server, clock-based scheduling or network calls.
    """
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / '.generation-lock'
    lock.mkdir()  # Fail clearly if another publisher (or a stale lock) exists.
    stage = None
    pointer_temp = None
    try:
        raw_bytes = (data_dir/'raw/2024-25.json').read_bytes()
        checkpoint_bytes = (data_dir/'derived/2024-25.json').read_bytes()
        raw, checkpoints = json.loads(raw_bytes), json.loads(checkpoint_bytes)
        if not checkpoints or any(c.get('scope') != 'season' or c.get('SEASON_ID') != '22024' for c in checkpoints):
            raise ValueError('Only prepared 2024–25 season checkpoints are supported')
        names = {str(r['PLAYER_ID']): str(r['PLAYER_NAME']) for r in raw}
        baselines = {mode: SeasonBaseline(checkpoints, mode=mode) for mode in MODES}
        players = sorted(baselines['per36'].latest)
        if set(players) != set(baselines['per_game'].latest) or not set(players) <= set(names):
            raise ValueError('Player sets/names do not agree across modes')
        if any(not pid.isdecimal() for pid in players):
            raise ValueError('Expected numeric player identifiers')
        source_hashes = {'raw': digest(raw_bytes), 'derived': digest(checkpoint_bytes)}
        code_hash = digest(b''.join((Path(__file__).parent/name).read_bytes() for name in
                                   ('similarity.py', 'preparation.py', 'responses.py')))
        now = datetime.now(timezone.utc).isoformat()
        release_id = uuid.uuid4().hex
        stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=output_dir))
        files = {}

        def write(relative, value):
            payload = encoded(value)
            path = stage/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            files[relative] = {'sha256': digest(payload), 'bytes': len(payload)}

        index = []
        for pid in players:
            c = baselines['per36'].latest[pid]
            index.append(dict(player_id=pid, name=names[pid], season='2024-25', games=c['games'],
                              minutes=c['cumulative_minutes'], date=c['GAME_DATE']))
        index.sort(key=lambda p: (p['name'].casefold(), p['player_id']))
        write('players.json', index)
        for mode, baseline in baselines.items():
            for pid in players:
                payload = producer(baseline, names, pid)
                # Full parity check, not merely matching IDs or rounded scores.
                if payload != comparison_response(baseline, names, pid):
                    raise ValueError(f'API/model parity failure: {pid}/{mode}')
                validate_result(payload, pid, mode)
                write(f'results/{mode}/{pid}.json', payload)
        manifest = dict(schema_version=SCHEMA_VERSION, snapshot_id=release_id, generated_at=now,
                        season='2024-25', model_version='season-baseline-0.1.0+'+code_hash[:12],
                        model_code_sha256=code_hash, source_sha256=source_hashes,
                        modes=list(MODES), player_count=len(players), result_count=2*len(players), files=files)
        manifest_bytes = encoded(manifest)
        (stage/'manifest.json').write_bytes(manifest_bytes)
        # Re-read each persisted file and its JSON before activation.
        for relative, info in files.items():
            data = (stage/relative).read_bytes()
            if len(data) != info['bytes'] or digest(data) != info['sha256']:
                raise ValueError('Snapshot integrity failure')
            json.loads(data)
        # Do not publish mixed source versions if local caches changed during generation.
        if digest((data_dir/'raw/2024-25.json').read_bytes()) != source_hashes['raw'] or digest((data_dir/'derived/2024-25.json').read_bytes()) != source_hashes['derived']:
            raise ValueError('Sources changed during generation')
        releases = output_dir/'releases'
        releases.mkdir(exist_ok=True)
        stage.rename(releases/release_id)
        stage = None
        pointer = dict(snapshot_id=release_id, manifest_sha256=digest(manifest_bytes))
        pointer_temp = output_dir/('.current-'+release_id+'.tmp')
        with pointer_temp.open('wb') as file:
            file.write(encoded(pointer))
            file.flush()
            os.fsync(file.fileno())
        os.replace(pointer_temp, output_dir/'current.json')  # Last operation that changes the active version.
        return manifest
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        if pointer_temp is not None:
            pointer_temp.unlink(missing_ok=True)
        lock.rmdir()


def validate_result(result, pid, mode):
    reference = result['reference']
    comparisons = result['comparisons']
    if str(reference['PLAYER_ID']) != pid or result['mode'] != mode or result['season'] != '2024-25':
        raise ValueError('Result identity mismatch')
    if len(comparisons) != min(5, result['candidate_count']):
        raise ValueError('Unexpected comparison count')
    if len({c['player_id'] for c in comparisons}) != len(comparisons):
        raise ValueError('Duplicate comparison players')
    for c in comparisons:
        if c['player_id'] == pid or not .9*reference['cumulative_minutes'] <= c['checkpoint']['cumulative_minutes'] <= 1.1*reference['cumulative_minutes']:
            raise ValueError('Invalid comparison eligibility')
        if set(c['features']) != set(FEATURES) or not math.isclose(c['distance']**2, sum(e['squared_distance_contribution'] for e in c['features'].values()), abs_tol=1e-12):
            raise ValueError('Invalid distance explanation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/snapshots'))
    args = parser.parse_args()
    manifest = generate(args.data_dir, args.output_dir)
    print(json.dumps({key: manifest[key] for key in ('snapshot_id','generated_at','season','model_version','player_count','result_count')}, indent=2))


if __name__ == '__main__':
    main()
