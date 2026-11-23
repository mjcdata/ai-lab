"""Fail-closed refresh publication checks. Does not change scoring eligibility."""
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from .ingestion import STATS, validate_rows
from .preparation import game_date, number
from .season_snapshot import validate_result
from .seasonal import CURRENT, FEATURES, MODEL_VERSION, load


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_current(rows, previous, teams, *, today=None):
    """Reconcile all player/team games, points, dates and known prior row keys.

    Team logs are the coverage authority, not an assertion of NBA source infallibility.
    Missing current-season values stop publication; historical missingness is untouched.
    Zero/tiny exposures are handled by the existing model, without new cutoffs.
    """
    today = today or date.today()
    report = validate_rows(rows, CURRENT)
    if report['warnings'] or report['duplicate_player_game_rows']:
        raise ValueError('Current player logs fail structural/duplicate validation')
    keys = {(str(r['PLAYER_ID']), str(r['GAME_ID'])) for r in rows}
    old = {(str(r['PLAYER_ID']), str(r['GAME_ID'])) for r in previous}
    if not old <= keys:
        raise ValueError('Refreshed response lost previously cached player/game rows')
    if any(number(r.get(f)) is None for r in rows for f in STATS):
        raise ValueError('Missing, negative or nonfinite current-season statistics')
    if not isinstance(teams, list) or not teams:
        raise ValueError('Empty/malformed team-game coverage response')
    team_points, team_dates, game_teams, outcomes = {}, {}, defaultdict(set), defaultdict(set)
    for row in teams:
        if str(row.get('SEASON_ID')) != f'2{CURRENT[:4]}' or any(not str(row.get(f) or '').strip() for f in ('TEAM_ID', 'GAME_ID')):
            raise ValueError('Wrong season or missing team/game identity')
        key = (str(row['TEAM_ID']), str(row['GAME_ID']))
        if key in team_points or number(row.get('PTS')) is None:
            raise ValueError('Duplicate team/game or invalid team points')
        if row.get('WL') not in ('W', 'L'):
            raise ValueError('Team coverage includes a game without a completed result')
        outcomes[key[1]].add(row['WL'])
        team_points[key] = number(row['PTS'])
        team_dates[key] = game_date(row.get('GAME_DATE'))
        game_teams[key[1]].add(key[0])
    if any(len(ids) != 2 for ids in game_teams.values()) or any(v != {'W', 'L'} for v in outcomes.values()):
        raise ValueError('Completed-game coverage lacks two distinct teams')
    player_points = defaultdict(float)
    dates = []
    for row in rows:
        if not str(row.get('TEAM_ID') or '').strip() or not str(row.get('PLAYER_NAME') or '').strip():
            raise ValueError('Missing team ID or player name')
        key = (str(row['TEAM_ID']), str(row['GAME_ID']))
        day = game_date(row.get('GAME_DATE'))
        if key not in team_points or day != team_dates[key]:
            raise ValueError('Player/team game-date coverage mismatch')
        parsed = date.fromisoformat(day)
        if not date(int(CURRENT[:4]), 7, 1) <= parsed <= min(today, date(int(CURRENT[:4])+1, 6, 30)):
            raise ValueError('Out-of-season or future game date')
        dates.append(day)
        player_points[key] += number(row['PTS'])
    if set(player_points) != set(team_points) or player_points != team_points:
        raise ValueError('Incomplete team-game player coverage or point-total mismatch')
    return {**report, 'completed_games': len(game_teams), 'team_games': len(team_points),
            'previous_rows_preserved': len(old), 'first_date': min(dates), 'latest_date': max(dates),
            'coverage_basis': 'NBA LeagueGameLog team/player game sets, dates and point totals'}


def validate_snapshot(snapshot_root, *, data_dir=None, historical_seasons=None):
    root = Path(snapshot_root)
    pointer = read(root/'current.json')
    sid = pointer.get('snapshot_id', '')
    if not re.fullmatch('[a-f0-9]{32}', sid):
        raise ValueError('Invalid snapshot identity')
    release = root/'releases'/sid
    if sha(release/'manifest.json') != pointer['manifest_sha256']:
        raise ValueError('Snapshot manifest checksum mismatch')
    manifest = read(release/'manifest.json')
    players = read(release/'players.json')
    ids = [p['player_id'] for p in players]
    if (manifest.get('model_version') != MODEL_VERSION or manifest.get('model_code_sha256') != sha(Path(__file__).with_name('seasonal.py'))
            or manifest['snapshot_id'] != sid or manifest['schema_version'] != 2 or manifest['season'] != CURRENT or manifest['modes'] != ['per36']
            or not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r'\d+', p) for p in ids)
            or manifest['player_count'] != len(ids) or manifest['result_count'] != len(ids)):
        raise ValueError('Empty or inconsistent snapshot inventory')
    expected = {'players.json', *(f'results/per36/{pid}.json' for pid in ids)}
    if set(manifest['files']) != expected:
        raise ValueError('Unexpected snapshot file inventory')
    model = None
    if data_dir is not None:
        model, hashes = load(data_dir, historical_seasons=historical_seasons)
        if hashes != manifest['source_sha256'] or set(model.latest) != set(ids) or not model.candidates:
            raise ValueError('Snapshot sources, current players or historical pool disagree')
    for name in expected:
        info = manifest['files'][name]
        path = release/name
        if path.is_symlink() or path.stat().st_size != info['bytes'] or sha(path) != info['sha256']:
            raise ValueError('Snapshot asset checksum mismatch')
        if name == 'players.json':
            continue
        value = read(path)
        pid = path.stem
        validate_result(value, pid)
        if model is not None and value != model.compare(pid):
            raise ValueError('Snapshot/direct-model parity failure')
        distances = [c['distance'] for c in value['comparisons']]
        if any(not math.isfinite(d) or d < 0 for d in distances) or distances != sorted(distances):
            raise ValueError('Nonfinite/negative/unsorted similarity distances')
        for c in value['comparisons']:
            for f in FEATURES:
                e = c['features'][f]
                if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in e.values()):
                    raise ValueError('Nonfinite explanation')
                if not math.isclose(e['standardized_difference'], e['comparison_z']-e['reference_z'], abs_tol=1e-10):
                    raise ValueError('Inconsistent Z-score explanation')
    return manifest
