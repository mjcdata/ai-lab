"""Offline static snapshots for current-to-historical player-season comparisons."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import uuid
from .seasonal import load, CURRENT, MODEL_VERSION, FEATURES
from .snapshot import encoded, digest
from .ingestion import _atomic_json


def validate_result(result, pid):
    if result['reference']['PLAYER_ID'] != pid or result['season'] != CURRENT or result['mode'] != 'per36':
        raise ValueError('Result identity mismatch')
    comparisons=result['comparisons']
    if len(comparisons) != min(5, result['candidate_count']):
        raise ValueError('Invalid comparison count')
    if len({(c['player_id'],c['season']) for c in comparisons}) != len(comparisons):
        raise ValueError('Duplicate player-season match')
    for c in comparisons:
        if c['player_id'] == pid or c['season'] >= CURRENT or set(c['features']) != set(FEATURES):
            raise ValueError('Invalid historical match')
        if not math.isclose(c['distance']**2, sum(e['squared_distance_contribution'] for e in c['features'].values()), abs_tol=1e-10):
            raise ValueError('Explanation mismatch')


def generate(data_dir, output_dir, *, historical_seasons=None, producer=None):
    data_dir, output_dir=Path(data_dir),Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    lock=output_dir/'.generation-lock';lock.mkdir()
    stage=None;pointer_temp=None
    try:
        model,hashes=load(data_dir,historical_seasons=historical_seasons)
        _atomic_json(data_dir/'reports/season-profiles.json',model.reports)
        stage=Path(tempfile.mkdtemp(prefix='.staging-',dir=output_dir))
        release_id=uuid.uuid4().hex;files={}
        def write(relative,value):
            payload=encoded(value);path=stage/relative
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
            files[relative]=dict(bytes=len(payload),sha256=digest(payload))
        players=model.players();write('players.json',players)
        for player in players:
            pid=player['player_id'];expected=model.compare(pid)
            result=producer(model,pid) if producer else expected
            if result != expected:raise ValueError('API/model parity failure')
            validate_result(result,pid);write(f'results/per36/{pid}.json',result)
        code_hash=digest((Path(__file__).with_name('seasonal.py')).read_bytes())
        manifest=dict(schema_version=2,snapshot_id=release_id,season=CURRENT,
                      generated_at=datetime.now(timezone.utc).isoformat(),model_version=MODEL_VERSION,
                      model_code_sha256=code_hash,source_sha256=hashes,modes=['per36'],
                      player_count=len(players),result_count=len(players),files=files,
                      coverage={s:{k:r[k] for k in ('player_seasons','eligible','excluded')} for s,r in model.reports.items()})
        manifest_bytes=encoded(manifest);(stage/'manifest.json').write_bytes(manifest_bytes)
        for relative,info in files.items():
            payload=(stage/relative).read_bytes()
            if len(payload)!=info['bytes'] or digest(payload)!=info['sha256']:raise ValueError('Snapshot integrity failure')
            json.loads(payload)
        for season,h in hashes.items():
            if digest((data_dir/'raw'/f'{season}.json').read_bytes())!=h:raise ValueError('Sources changed during generation')
        releases=output_dir/'releases';releases.mkdir(exist_ok=True)
        stage.rename(releases/release_id);stage=None
        pointer_temp=output_dir/f'.current-{release_id}.tmp'
        with pointer_temp.open('wb') as f:
            f.write(encoded(dict(snapshot_id=release_id,manifest_sha256=digest(manifest_bytes))))
            f.flush();os.fsync(f.fileno())
        os.replace(pointer_temp,output_dir/'current.json')
        return manifest
    finally:
        if stage is not None:shutil.rmtree(stage,ignore_errors=True)
        if pointer_temp is not None:pointer_temp.unlink(missing_ok=True)
        lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    parser.add_argument('--output-dir',type=Path,default=Path('artifacts/snapshots'))
    args=parser.parse_args()
    manifest=generate(args.data_dir,args.output_dir)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','source_sha256')},indent=2))


if __name__=='__main__':main()
