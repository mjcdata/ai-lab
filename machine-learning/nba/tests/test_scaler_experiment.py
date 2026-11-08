import copy
import unittest
from nba_player_similarity.scaler_experiment import variant
from nba_player_similarity.similarity import SeasonBaseline
from test_similarity import cp


class ScalerExperimentTests(unittest.TestCase):
    def test_zero_is_control_and_input_unchanged(self):
        points=[cp(1,30,20),cp(2,100,2),cp(3,500,4)]
        original=copy.deepcopy(points);control=SeasonBaseline(points)
        scorer,n=variant(control,0)
        self.assertEqual(n,3)
        self.assertEqual(scorer.compare(2),control.compare(2))
        self.assertEqual(points,original)

    def test_only_contributors_change_inclusive_boundary(self):
        control=SeasonBaseline([cp(1,90,20),cp(2,100,2),cp(3,100,4)])
        before=copy.deepcopy(control.compare(2))
        scorer,n=variant(control,100)
        self.assertEqual(n,2)
        self.assertEqual(scorer.mean['PTS'],3)
        self.assertEqual(scorer.scale['PTS'],1)
        self.assertIs(scorer.checkpoints,control.checkpoints)
        self.assertIs(scorer.latest,control.latest)
        self.assertEqual(scorer.compare(2)['candidate_count'],2)
        self.assertIn('1',[c['player_id'] for c in scorer.compare(2)['comparisons']])
        self.assertEqual(control.compare(2),before)

    def test_zero_variance_and_empty_reference(self):
        control=SeasonBaseline([cp(1,100,2),cp(2,500,2)])
        scorer,n=variant(control,500)
        self.assertEqual(n,1)
        self.assertEqual(scorer.scale['PTS'],1)
        with self.assertRaises(ValueError): variant(control,501)
        with self.assertRaises(ValueError): variant(control,-1)
