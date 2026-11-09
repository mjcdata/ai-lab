"""Local read-only 2026–27 to historical player-season API; per-36 only."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from .seasonal import load, CURRENT


def create_app(data_dir=None, *, historical_seasons=None):
    root = Path(data_dir if data_dir is not None else os.environ.get('NBA_DATA_DIR', 'data'))
    @asynccontextmanager
    async def lifespan(app):
        try:
            app.state.model, _ = load(root, historical_seasons=historical_seasons)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError('Cannot load local historical/current raw caches. No download attempted.') from exc
        yield
        app.state.model = None
    app = FastAPI(title='NBA Player Similarity', version='1.0.0', lifespan=lifespan)
    def selected(pid):
        if pid not in app.state.model.latest:
            raise HTTPException(404, 'Player not found or excluded; inspect coverage report')
        return next(p for p in app.state.model.players() if p['player_id'] == pid)
    @app.get('/health')
    def health():
        return dict(status='ready', season=CURRENT, players=len(app.state.model.latest))
    @app.get('/coverage')
    def coverage():
        return app.state.model.reports
    @app.get('/players')
    def players(q: str=Query('',max_length=100), limit: int=Query(25,ge=1,le=100),
                offset: int=Query(0,ge=0), mode: Literal['per36']='per36'):
        needle=q.strip().casefold()
        rows=[p for p in app.state.model.players() if needle in p['name'].casefold() or needle in p['player_id']]
        return dict(players=rows[offset:offset+limit], total=len(rows),offset=offset,limit=limit)
    @app.get('/players/{player_id}')
    def player(player_id: str, mode: Literal['per36']='per36'):
        return selected(player_id)
    @app.get('/players/{player_id}/comparisons')
    def comparisons(player_id: str, mode: Literal['per36']='per36'):
        selected(player_id)
        return app.state.model.compare(player_id)
    return app


app=create_app()
