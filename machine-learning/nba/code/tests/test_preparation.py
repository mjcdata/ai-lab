import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nba_player_similarity.preparation import cumulative, match_checkpoints, prepare_pilot, FEATURES
from nba_player_similarity.ingestion import PILOT


def row(game='1', day='2024-10-01', **changes):
    return dict(PLAYER_ID=1, GAME_ID=game, GAME_DATE=day, SEASON_ID='22024',
                MIN=18, **dict.fromkeys(FEATURES, 2)) | changes


class PreparationTests(unittest.TestCase):
    def test_order_rates_and_input_preservation(self):
        rows = [row('2', '2024-10-02', MIN=36, PTS=12), row(PTS=6)]
        original = copy.deepcopy(rows)
        points, report = cumulative(rows)
        self.assertEqual(rows, original)
        self.assertEqual([p['GAME_ID'] for p in points], ['1', '2'])
        self.assertEqual(points[-1]['games'], 2)
        self.assertEqual(points[-1]['cumulative_minutes'], 54)
        self.assertEqual(points[-1]['per36']['PTS'], 12)
        self.assertEqual(points[-1]['per_game']['PTS'], 9)
        self.assertEqual(report['output_rows'], 2)

    def test_whole_duplicate_group_excluded(self):
        points, report = cumulative([row(), row(PTS=9), row('2'), row('3'), row('3')])
        self.assertEqual([p['GAME_ID'] for p in points], ['2'])
        self.assertEqual(report['duplicate_rows_excluded'], 4)
        self.assertEqual(points[0]['games'], 1)

    def test_missing_and_invalid_values_never_complete(self):
        for value in (None, '', -1, float('nan'), float('inf'), 'bad', True):
            with self.subTest(value=value):
                points, _ = cumulative([row(AST=value), row('2', '2024-10-02')])
                last = points[-1]
                self.assertEqual(last['coverage']['AST'], 1)
                self.assertEqual(last['observed_totals']['AST'], 2)
                self.assertIsNone(last['per36']['AST'])
                self.assertIsNone(last['per_game']['AST'])
                self.assertNotIn('AST', last['eligible_features'])

    def test_zero_and_invalid_minutes(self):
        for value in (0, None, -1, float('inf')):
            points, _ = cumulative([row(MIN=value)])
            self.assertIsNone(points[0]['per36']['PTS'])
            self.assertEqual(match_checkpoints(points, 18), [])
        points, _ = cumulative([row(MIN=None), row('2', '2024-10-02')])
        self.assertIsNone(points[-1]['cumulative_minutes'])

    def test_missing_stat_is_null_observed_zero_is_zero(self):
        points, _ = cumulative([row(AST=None, STL=0)])
        self.assertIsNone(points[0]['observed_totals']['AST'])
        self.assertEqual(points[0]['per36']['STL'], 0)
        self.assertEqual(match_checkpoints(points, 18), [])
        self.assertEqual(len(match_checkpoints(points, 18, required_features=('PTS',))), 1)

    def test_checkpoint_boundaries_and_nearest(self):
        points, _ = cumulative([row(PLAYER_ID=1, MIN=90), row(PLAYER_ID=2, MIN=110),
                                row(PLAYER_ID=3, MIN=111), row('2', '2024-10-02', MIN=10)])
        matches = match_checkpoints(points, 100)
        self.assertEqual([p['PLAYER_ID'] for p in matches], ['1', '2'])
        self.assertEqual(matches[0]['cumulative_minutes'], 100)
        for target in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                match_checkpoints(points, target)

    def test_partial_history_resets_and_career_requires_confirmation(self):
        rows = [row(), row('2', '1977-10-01', SEASON_ID='21977')]
        points, _ = cumulative(rows)
        self.assertEqual([p['games'] for p in points], [1, 1])
        self.assertTrue(all(not p['history_complete'] for p in points))
        with self.assertRaises(ValueError):
            cumulative(rows, scope='career')
        with self.assertRaises(ValueError):
            match_checkpoints(points, 18)
        career, _ = cumulative(rows, scope='career', complete_history=True)
        self.assertEqual(career[-1]['cumulative_minutes'], 36)
        self.assertEqual(len(match_checkpoints(career, 36)), 1)
        damaged, _ = cumulative(rows+[row()], scope='career', complete_history=True)
        self.assertEqual(match_checkpoints(damaged, 18), [])

    def test_bad_identifiers_dates_and_empty_input(self):
        points, report = cumulative([row(PLAYER_ID=None), row('2', GAME_DATE='bad')])
        self.assertEqual(points, [])
        self.assertEqual(report['invalid_rows_excluded'], 2)
        self.assertEqual(cumulative([])[0], [])
        points, _ = cumulative([row(GAME_DATE='OCT 01, 2024')])
        self.assertEqual(points[0]['GAME_DATE'], '2024-10-01')

    def test_offline_pilot_reproducible_raw_unchanged(self):
        with tempfile.TemporaryDirectory() as directory, patch('socket.socket', side_effect=AssertionError('network forbidden')):
            root = Path(directory)
            (root/'raw').mkdir()
            before = {}
            for season in PILOT:
                path = root/'raw'/f'{season}.json'
                path.write_text(json.dumps([row(SEASON_ID='2'+season[:4], GAME_DATE=season[:4]+'-11-01')]))
                before[path] = path.read_bytes()
            report = prepare_pilot(root)
            first = {p.name: p.read_bytes() for p in (root/'derived').iterdir()}
            self.assertEqual(prepare_pilot(root), report)
            self.assertEqual(first, {p.name: p.read_bytes() for p in (root/'derived').iterdir()})
            self.assertTrue(all(p.read_bytes() == raw for p, raw in before.items()))
            self.assertTrue(all(r['output_rows'] == 1 for r in report.values()))

    def test_absent_cache_fails_without_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                prepare_pilot(Path(directory))
            self.assertFalse((Path(directory)/'derived').exists())
