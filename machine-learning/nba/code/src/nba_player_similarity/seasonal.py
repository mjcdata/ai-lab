"""Complete player-season per-36 profiles and within-season population Z-scores.

No acquisition, career checkpoints, minute matching, imputation or exposure cutoff.
"""
import hashlib
import heapq
import json
import math
from collections import defaultdict, Counter
from pathlib import Path
from .ingestion import season_range, validate_rows
from .preparation import FEATURES, number, game_date

CURRENT = '2026-27'
MODEL_VERSION = 'season-z-per36-1.0.0'


def profiles(rows, season):
    quality = validate_rows(rows, season)
    if quality['warnings']:
        raise ValueError(f'{season}: invalid raw cache: {quality["warnings"]}')
    groups = defaultdict(list)
    counts = Counter((str(r['PLAYER_ID']), str(r['GAME_ID'])) for r in rows)
    for row in rows:
        groups[str(row['PLAYER_ID'])].append(row)
    eligible, exclusions = [], {}
    for pid, games in sorted(groups.items()):
        reasons = set()
        totals = dict.fromkeys(('MIN',) + FEATURES, 0.0)
        dates = []
        for row in games:
            if counts[(pid, str(row['GAME_ID']))] > 1:
                reasons.add('unresolved_duplicate_game')
            try:
                dates.append(game_date(row['GAME_DATE']))
            except ValueError:
                reasons.add('invalid_game_date')
            values = {f: number(row.get(f)) for f in totals}
            if any(v is None for v in values.values()):
                reasons.add('missing_or_invalid_statistics')
            # Rounded zero minutes with positive box-score counts cannot support
            # reliable season rates. Do not silently discard these contributions.
            if values['MIN'] == 0 and any(values[f] is not None and values[f] > 0 for f in FEATURES):
                reasons.add('positive_statistics_with_zero_minutes')
            for field, value in values.items():
                if value is not None:
                    totals[field] += value
        if totals['MIN'] <= 0:
            reasons.add('nonpositive_season_minutes')
        if any(not math.isfinite(v) for v in totals.values()):
            reasons.add('nonfinite_totals')
        rates = {f: totals[f] * 36 / totals['MIN'] for f in FEATURES} if totals['MIN'] > 0 else {}
        if rates and any(not math.isfinite(v) for v in rates.values()):
            reasons.add('nonfinite_rates')
        if reasons:
            exclusions[pid] = {'name': str(games[-1].get('PLAYER_NAME', pid)), 'reasons': sorted(reasons)}
            continue
        eligible.append(dict(PLAYER_ID=pid, name=str(games[-1].get('PLAYER_NAME', pid)),
                             season=season, SEASON_ID=f'2{season[:4]}', games=len(games),
                             cumulative_minutes=totals['MIN'], GAME_DATE=max(dates), per36=rates))
    mean, scale, constant = {}, {}, []
    for f in FEATURES:
        mean[f] = math.fsum(p['per36'][f] for p in eligible)/len(eligible) if eligible else 0.0
        sd = math.sqrt(math.fsum((p['per36'][f]-mean[f])**2 for p in eligible)/len(eligible)) if eligible else 0.0
        if sd == 0:
            constant.append(f)
        scale[f] = sd
    for p in eligible:
        p['z'] = {f: (p['per36'][f]-mean[f])/scale[f] if scale[f] else 0.0 for f in FEATURES}
    return eligible, dict(season=season, input_rows=len(rows), player_seasons=len(groups),
                         eligible=len(eligible), excluded=len(exclusions), exclusions=exclusions,
                         scaler=dict(players=len(eligible), mean=mean, scale=scale, constant_features=constant),
                         duplicate_excess_rows=quality['duplicate_player_game_rows'], missing_counts=quality['missing_counts'])


class HistoricalSeasons:
    def __init__(self, records, reports):
        self.records = records
        self.reports = reports
        self.latest = {p['PLAYER_ID']: p for p in records if p['season'] == CURRENT}
        self.candidates = [(p, tuple(p['z'][f] for f in FEATURES)) for p in records if p['season'] < CURRENT]

    def players(self):
        return sorted([dict(player_id=p['PLAYER_ID'], name=p['name'], season=CURRENT,
                            games=p['games'], minutes=p['cumulative_minutes'], date=p['GAME_DATE'])
                       for p in self.latest.values()], key=lambda p:(p['name'].casefold(),p['player_id']))

    def compare(self, player_id):
        target = self.latest[str(player_id)]
        z = tuple(target['z'][f] for f in FEATURES)
        candidates = [(math.fsum((a-b)**2 for a,b in zip(z, vector)), p)
                      for p,vector in self.candidates if p['PLAYER_ID'] != target['PLAYER_ID']]
        nearest = heapq.nsmallest(5, candidates, key=lambda item:(item[0],item[1]['season'],item[1]['PLAYER_ID']))
        comparisons = []
        for squared, p in nearest:
            features = {f:dict(reference=target['per36'][f], comparison=p['per36'][f],
                               difference=p['per36'][f]-target['per36'][f], reference_z=target['z'][f],
                               comparison_z=p['z'][f], standardized_difference=p['z'][f]-target['z'][f],
                               squared_distance_contribution=(p['z'][f]-target['z'][f])**2) for f in FEATURES}
            comparisons.append(dict(player_id=p['PLAYER_ID'], season=p['season'], name=p['name'],
                                    distance=math.sqrt(squared), checkpoint=p, features=features))
        warnings = ['Limited playing time can produce unstable per-36 rates; no minimum games or minutes cutoff is imposed.',
                    'Each profile is standardized against eligible players in its own season; this does not remove all era or role effects.',
                    'Historical game-log completeness has not been independently established. Missing-stat and unreliable-minute player-seasons are excluded.',
                    'Source minutes have whole-minute precision. This is descriptive similarity, not prediction.']
        if len(comparisons) < 5:
            warnings.append(f'Only {len(comparisons)} valid historical player-season matches; returning fewer than five.')
        if self.reports[CURRENT]['scaler']['constant_features']:
            warnings.append('Current-season constant features receive Z-score zero; inspect the coverage report.')
        return dict(reference=target, mode='per36', season=CURRENT, model_version=MODEL_VERSION,
                    candidate_count=len(candidates), comparisons=comparisons, warnings=warnings,
                    exposure_policy='No minimum games/minutes cutoff. No career-stage or minute-window matching.',
                    coverage=dict(historical_eligible=len(self.candidates),
                                  excluded_player_seasons=sum(r['excluded'] for r in self.reports.values())))


def load(root, *, historical_seasons=None):
    root = Path(root)
    seasons = list(historical_seasons if historical_seasons is not None else season_range()) + [CURRENT]
    records, reports, hashes = [], {}, {}
    for season in seasons:
        path = root/'raw'/f'{season}.json'
        payload = path.read_bytes()  # Missing seasons fail explicitly; never acquire here.
        hashes[season] = hashlib.sha256(payload).hexdigest()
        values, report = profiles(json.loads(payload), season)
        records.extend(values)
        reports[season] = report
    return HistoricalSeasons(records, reports), hashes
