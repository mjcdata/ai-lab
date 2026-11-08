"""Offline, season-scoped pilot preparation and explicit full-history support."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from .ingestion import PILOT, _atomic_json, exclude_unresolved_duplicates

FEATURES = ('PTS', 'AST', 'REB', 'STL', 'BLK', 'TOV')


def number(value):
    if isinstance(value, bool) or value is None or value == '':
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def game_date(value):
    for fmt in ('%Y-%m-%d', '%b %d, %Y'):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Invalid GAME_DATE: {value!r}')


def cumulative(rows, *, scope='season', complete_history=False):
    """Copy, filter and sort records; partial sums always carry coverage counts.

    Career scope requires caller confirmation of full chronological history.
    Excluded records invalidate career matching eligibility conservatively.
    """
    if scope not in ('season', 'career') or (scope == 'career' and not complete_history):
        raise ValueError('Career scope requires explicitly confirmed complete history')
    clean = exclude_unresolved_duplicates(rows)
    report = {'input_rows': len(rows), 'duplicate_rows_excluded': len(rows)-len(clean),
              'invalid_rows_excluded': 0, 'scope': scope}
    ordered = []
    for row in clean:
        if any(row.get(k) is None or not str(row.get(k)).strip()
               for k in ('PLAYER_ID', 'GAME_ID', 'SEASON_ID')):
            report['invalid_rows_excluded'] += 1
            continue
        try:
            day = game_date(row.get('GAME_DATE'))
        except ValueError:
            report['invalid_rows_excluded'] += 1
            continue
        ordered.append((str(row['PLAYER_ID']), day, str(row['GAME_ID']), row))
    ordered.sort(key=lambda item: item[:3])
    states, checkpoints = {}, []
    for player, day, game, row in ordered:
        season = str(row['SEASON_ID'])
        key = (player, season) if scope == 'season' else (player,)
        state = states.setdefault(key, {'games': 0, 'totals': dict.fromkeys(('MIN',)+FEATURES, 0.0),
                                        'coverage': dict.fromkeys(('MIN',)+FEATURES, 0)})
        state['games'] += 1
        for field in state['totals']:
            value = number(row.get(field))
            if value is not None:
                state['totals'][field] += value
                state['coverage'][field] += 1
        games = state['games']
        totals, coverage = state['totals'].copy(), state['coverage'].copy()
        minutes = totals['MIN'] if coverage['MIN'] == games else None
        usable = minutes is not None and minutes > 0
        eligible = [f for f in FEATURES if usable and coverage[f] == games]
        checkpoints.append({'PLAYER_ID': player, 'GAME_ID': game, 'SEASON_ID': season,
                            'GAME_DATE': day, 'scope': scope, 'games': games,
                            'observed_totals': {f: totals[f] if coverage[f] else None for f in totals},
                            'coverage': coverage, 'cumulative_minutes': minutes,
                            'eligible_features': eligible,
                            'history_complete': scope == 'career' and not (
                                report['duplicate_rows_excluded'] or report['invalid_rows_excluded']),
                            'per36': {f: totals[f]*36/minutes if f in eligible else None for f in FEATURES},
                            'per_game': {f: totals[f]/games if coverage[f] == games else None for f in FEATURES}})
    report.update(output_rows=len(checkpoints), player_scopes=len(states),
                  usable_minute_checkpoints=sum(c['cumulative_minutes'] is not None and c['cumulative_minutes'] > 0 for c in checkpoints),
                  unusable_counts={f: sum(number(r.get(f)) is None for _, _, _, r in ordered) for f in ('MIN',)+FEATURES})
    return checkpoints, report


def match_checkpoints(checkpoints, target_minutes, *, required_features=FEATURES):
    """Nearest eligible checkpoint per player within approved ±10% of target.

    One season scope or confirmed career history only. No similarity scoring.
    """
    target = number(target_minutes)
    if target is None or target <= 0:
        raise ValueError('Target minutes must be positive and finite')
    if not required_features or not set(required_features) <= set(FEATURES):
        raise ValueError('Specify a nonempty subset of approved features')
    scopes = {(c['scope'], c['SEASON_ID'] if c['scope'] == 'season' else None) for c in checkpoints}
    if len(scopes) > 1:
        raise ValueError('Do not mix season or history scopes')
    best = {}
    for c in checkpoints:
        minutes = c['cumulative_minutes']
        if c['scope'] == 'career' and not c['history_complete']:
            continue
        if minutes is None or minutes <= 0 or not .9*target <= minutes <= 1.1*target:
            continue
        if not set(required_features) <= set(c['eligible_features']):
            continue
        rank = (abs(minutes-target), c['GAME_DATE'], c['GAME_ID'])
        player = c['PLAYER_ID']
        if player not in best or rank < best[player][0]:
            best[player] = rank, c
    return [best[p][1] for p in sorted(best)]


def prepare_pilot(root):
    """Read all three caches first; write only reproducible derived outputs."""
    root = Path(root)
    sources = {}
    for season in PILOT:
        raw = (root / 'raw' / f'{season}.json').read_bytes()
        rows = json.loads(raw)
        if not isinstance(rows, list) or not rows or any(not isinstance(r, dict) for r in rows):
            raise ValueError(f'{season}: expected a list of records')
        if any(str(r.get('SEASON_ID')) != '2'+season[:4] for r in rows):
            raise ValueError(f'{season}: unexpected regular-season SEASON_ID')
        sources[season] = rows, hashlib.sha256(raw).hexdigest()
    summaries = {}
    for season, (rows, digest) in sources.items():
        checkpoints, report = cumulative(rows)
        report.update(raw_sha256=digest, season=season,
                      limitation='Season-scoped pilot sample; not career history or proof of completeness')
        _atomic_json(root / 'derived' / f'{season}.json', checkpoints)
        summaries[season] = report
    _atomic_json(root / 'derived' / 'quality.json', summaries)
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    args = parser.parse_args()
    print(json.dumps(prepare_pilot(args.data_dir), indent=2))


if __name__ == '__main__':
    main()
