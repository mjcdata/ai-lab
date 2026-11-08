"""Retrospective season-only similarity; no network or data mutation."""
import argparse
import json
import math
from pathlib import Path
from .preparation import FEATURES, match_checkpoints, number


class SeasonBaseline:
    """Fixed population scaler, one latest eligible observation per player."""

    def __init__(self, checkpoints, *, mode='per36'):
        if mode not in ('per36', 'per_game'):
            raise ValueError('mode must be per36 or per_game')
        if not checkpoints or any(c['scope'] != 'season' for c in checkpoints):
            raise ValueError('Nonempty season-scoped checkpoints required')
        if len({c['SEASON_ID'] for c in checkpoints}) != 1:
            raise ValueError('Use one season only')
        self.mode = mode
        self.checkpoints = [c for c in checkpoints
                            if number(c['cumulative_minutes']) is not None
                            and c['cumulative_minutes'] > 0
                            and set(FEATURES) <= set(c['eligible_features'])
                            and all(number(c[mode].get(f)) is not None for f in FEATURES)]
        self.latest = {}
        for c in self.checkpoints:
            player = str(c['PLAYER_ID'])
            prior = self.latest.get(player)
            if prior is None or (c['GAME_DATE'], c['GAME_ID']) > (prior['GAME_DATE'], prior['GAME_ID']):
                self.latest[player] = c
        if not self.latest:
            raise ValueError('No eligible checkpoints')
        reference = list(self.latest.values())
        self.mean = {f: math.fsum(c[mode][f] for c in reference)/len(reference) for f in FEATURES}
        self.scale = {f: math.sqrt(math.fsum((c[mode][f]-self.mean[f])**2
                                           for c in reference)/len(reference)) or 1.0
                      for f in FEATURES}

    def compare(self, player_id):
        player_id = str(player_id)
        if player_id not in self.latest:
            raise ValueError('Selected player has no eligible checkpoint')
        target = self.latest[player_id]
        candidates = match_checkpoints(self.checkpoints, target['cumulative_minutes'])
        results = []
        for candidate in candidates:
            if str(candidate['PLAYER_ID']) == player_id:
                continue
            explanations = {}
            for f in FEATURES:
                left, right = target[self.mode][f], candidate[self.mode][f]
                delta = (right-left)/self.scale[f]
                explanations[f] = dict(reference=left, comparison=right,
                                       difference=right-left,
                                       reference_z=(left-self.mean[f])/self.scale[f],
                                       comparison_z=(right-self.mean[f])/self.scale[f],
                                       standardized_difference=delta,
                                       squared_distance_contribution=delta**2)
            distance = math.sqrt(math.fsum(e['squared_distance_contribution'] for e in explanations.values()))
            raw_distance = math.sqrt(math.fsum(e['difference']**2 for e in explanations.values()))
            minutes_difference = candidate['cumulative_minutes']-target['cumulative_minutes']
            results.append(dict(player_id=str(candidate['PLAYER_ID']), distance=distance,
                                unstandardized_distance=raw_distance, checkpoint=candidate,
                                minute_difference=minutes_difference,
                                minute_difference_percent=100*minutes_difference/target['cumulative_minutes'],
                                features=explanations))
        results.sort(key=lambda r: (r['distance'], r['player_id']))
        warnings = ['Season-to-date observations, not career history or predictive evaluation.',
                    'No minimum exposure threshold: small game/minute samples can produce unstable rates; inspect exposure for both players.',
                    'Source minutes have accepted whole-minute precision.']
        if len(results) < 5:
            warnings.append(f'Only {len(results)} valid other players within the fixed ±10% minute window; returning fewer than five.')
        return dict(reference=target, mode=self.mode, candidate_count=len(results),
                    scaler=dict(players=len(self.latest), mean=self.mean, scale=self.scale),
                    comparisons=results[:5], warnings=warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('player_id')
    parser.add_argument('--checkpoints', type=Path, default=Path('data/derived/2024-25.json'))
    parser.add_argument('--mode', choices=('per36', 'per_game'), default='per36')
    args = parser.parse_args()
    baseline = SeasonBaseline(json.loads(args.checkpoints.read_text()), mode=args.mode)
    print(json.dumps(baseline.compare(args.player_id), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
