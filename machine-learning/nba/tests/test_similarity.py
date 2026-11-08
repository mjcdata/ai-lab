"""Synthetic offline checks for approved season baseline."""
import math
import unittest
from nba_player_similarity.preparation import cumulative, FEATURES
from nba_player_similarity.similarity import SeasonBaseline


def cp(player, minutes=100, value=1, game='1', day='2025-01-01'):
    return dict(PLAYER_ID=str(player), GAME_ID=game, GAME_DATE=day, SEASON_ID='22024',
                scope='season', cumulative_minutes=minutes, games=10,
                eligible_features=list(FEATURES), per36=dict.fromkeys(FEATURES, value),
                per_game=dict.fromkeys(FEATURES, value/2))


class SimilarityTests(unittest.TestCase):
    def test_population_scaling_one_latest_per_player(self):
        b = SeasonBaseline([cp(1, value=0), cp(1, value=2, game='2', day='2025-02-01'), cp(2, value=4)])
        self.assertEqual(b.mean['PTS'], 3)
        self.assertEqual(b.scale['PTS'], 1)
        result = b.compare(1)
        self.assertEqual(result['reference']['GAME_ID'], '2')
        self.assertAlmostEqual(result['comparisons'][0]['distance'], math.sqrt(24))

    def test_closest_checkpoint_precedes_scoring_and_excludes_self(self):
        rows = [cp(1), cp(1, 99, 0, '0'), cp(2, 95, 1), cp(2, 100, 5, '2'), cp(3, 111)]
        r = SeasonBaseline(rows).compare(1)
        self.assertEqual(r['candidate_count'], 1)
        self.assertEqual(r['comparisons'][0]['checkpoint']['GAME_ID'], '2')
        self.assertEqual(r['comparisons'][0]['player_id'], '2')
        self.assertTrue(any('fewer than five' in w for w in r['warnings']))

    def test_boundaries_unique_five_and_ties(self):
        rows = [cp(1)] + [cp(p, 90 if p % 2 else 110) for p in range(2, 9)]
        r = SeasonBaseline(rows).compare(1)
        self.assertEqual(r['candidate_count'], 7)
        self.assertEqual([x['player_id'] for x in r['comparisons']], ['2','3','4','5','6'])
        self.assertTrue(all(x['distance'] == 0 for x in r['comparisons']))

    def test_explanations_reconcile_and_mode(self):
        for mode in ('per36','per_game'):
            r = SeasonBaseline([cp(1), cp(2, value=3)], mode=mode).compare(1)
            c = r['comparisons'][0]
            self.assertAlmostEqual(c['distance']**2, sum(x['squared_distance_contribution'] for x in c['features'].values()))
            for e in c['features'].values():
                self.assertAlmostEqual(e['comparison_z']-e['reference_z'],e['standardized_difference'])
            self.assertEqual(c['minute_difference_percent'], 0)

    def test_ineligible_missing_zero_nonfinite(self):
        bad = [cp(2,0),cp(3),cp(4)]
        bad[1]['per36']['PTS'] = None
        bad[2]['per36']['AST'] = float('inf')
        r = SeasonBaseline([cp(1)]+bad).compare(1)
        self.assertEqual(r['comparisons'], [])
        with self.assertRaises(ValueError):
            SeasonBaseline([cp(1)]+bad).compare(3)

    def test_scope_and_mode_rejected(self):
        c = cp(2); c['SEASON_ID']='21977'
        for rows in ([], [cp(1),c], [dict(cp(1),scope='career')]):
            with self.assertRaises(ValueError): SeasonBaseline(rows)
        with self.assertRaises(ValueError): SeasonBaseline([cp(1)], mode='other')

    def test_real_preparation_interface_and_earliest_minute_tie(self):
        rows = [dict(PLAYER_ID=p,GAME_ID=str(g),GAME_DATE=f'2025-01-0{g}',
                     SEASON_ID='22024',MIN=m,**dict.fromkeys(FEATURES,2))
                for p, games in ((1,[(1,100)]),(2,[(1,90),(2,20)])) for g,m in games]
        checkpoints,_ = cumulative(rows)
        r = SeasonBaseline(checkpoints).compare(1)
        self.assertEqual(r['comparisons'][0]['checkpoint']['GAME_ID'],'1')

    def test_equal_weights_and_fixed_scaler(self):
        a,b,c = cp(1,value=0),cp(2,value=0),cp(3,value=0)
        b['per36']['PTS']=2
        c['per36']['AST']=2
        baseline=SeasonBaseline([a,b,c])
        before=(baseline.mean.copy(),baseline.scale.copy())
        results=baseline.compare(1)['comparisons']
        self.assertAlmostEqual(results[0]['distance'],results[1]['distance'])
        baseline.compare(2)
        self.assertEqual(before,(baseline.mean,baseline.scale))
