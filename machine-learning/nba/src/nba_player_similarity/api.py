"""Read-only local HTTP adapter for the approved season baseline."""
from contextlib import asynccontextmanager
import copy
import json
import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from .similarity import SeasonBaseline


def create_app(data_dir=None):
    """Load local files once at startup, never fetch or modify datasets."""
    root=Path(data_dir if data_dir is not None else os.environ.get('NBA_DATA_DIR','data'))

    @asynccontextmanager
    async def lifespan(app):
        try:
            checkpoints=json.loads((root/'derived/2024-25.json').read_text())
            raw=json.loads((root/'raw/2024-25.json').read_text())
            if any(c.get('SEASON_ID')!='22024' for c in checkpoints):
                raise ValueError('Expected only 2024–25 regular-season checkpoints')
            names={str(r['PLAYER_ID']):str(r['PLAYER_NAME']) for r in raw}
            baselines={mode:SeasonBaseline(checkpoints,mode=mode) for mode in ('per36','per_game')}
            if not set(baselines['per36'].latest)<=set(names):
                raise ValueError('Player names missing from local raw cache')
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise RuntimeError('Cannot load NBA local caches. Set NBA_DATA_DIR to prepared data with raw/2024-25.json and derived/2024-25.json. No download attempted.') from exc
        app.state.baselines=baselines
        app.state.names=names
        yield
        app.state.baselines={}

    app=FastAPI(title='NBA season similarity',version='0.1.0',lifespan=lifespan,
                description='Exploratory 2024–25 season-to-date comparisons; not career or predictive results.')

    def player(player_id,mode):
        baseline=app.state.baselines[mode]
        if player_id not in baseline.latest:
            raise HTTPException(404,'Player not found or has no eligible checkpoint')
        c=baseline.latest[player_id]
        return dict(player_id=player_id,name=app.state.names[player_id],season='2024-25',
                    games=c['games'],minutes=c['cumulative_minutes'],date=c['GAME_DATE'])

    @app.get('/health')
    def health():
        return dict(status='ready',season='2024-25',players=len(app.state.baselines['per36'].latest))

    @app.get('/players')
    def search(q:str=Query('',max_length=100),limit:int=Query(25,ge=1,le=100),
               offset:int=Query(0,ge=0),mode:Literal['per36','per_game']='per36'):
        needle=q.strip().casefold()
        rows=[player(pid,mode) for pid in app.state.baselines[mode].latest
              if needle in app.state.names[pid].casefold() or needle in pid]
        rows.sort(key=lambda r:(r['name'].casefold(),r['player_id']))
        return dict(players=rows[offset:offset+limit],total=len(rows),offset=offset,limit=limit)

    @app.get('/players/{player_id}')
    def select(player_id:str,mode:Literal['per36','per_game']='per36'):
        return player(player_id,mode)

    @app.get('/players/{player_id}/comparisons')
    def comparisons(player_id:str,mode:Literal['per36','per_game']='per36'):
        player(player_id,mode)
        # Copy response before adding names/exposure warnings; never mutate model state.
        result=copy.deepcopy(app.state.baselines[mode].compare(player_id))
        result['reference']['name']=app.state.names[player_id]
        for comparison in result['comparisons']:
            comparison['name']=app.state.names[comparison['player_id']]
        result['season']='2024-25'
        result['exposure_policy']='No extra games/minutes cutoff; compare exact games and cumulative season minutes for each checkpoint.'
        result['warnings'].append('Limited playing time can produce unstable rates or zero-distance matches without reliable player equivalence. Scaler filtering is not adopted; all eligible players still contribute.')
        return result

    return app


app=create_app()
