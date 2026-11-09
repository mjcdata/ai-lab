import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nba_player_similarity.seasonal import profiles, HistoricalSeasons, load, CURRENT
from nba_player_similarity.season_snapshot import generate, validate_result


def rows(season, players=range(1,8), multiplier=1):
    return [dict(SEASON_ID=f'2{season[:4]}',PLAYER_ID=p,PLAYER_NAME=f'Player {p}',
                 GAME_ID=f'{season}-{p}',GAME_DATE=f'{season[:4]}-11-01',MIN=36,
                 **{f:p*multiplier for f in ('PTS','REB','AST','STL','BLK','TOV')}) for p in players]


def fixture(root):
    (root/'raw').mkdir()
    for s in ['2025-26',CURRENT]:
        (root/'raw'/f'{s}.json').write_text(json.dumps(rows(s)))


class SeasonalTests(unittest.TestCase):
    def test_season_aggregation_and_population_z_no_minutes_matching(self):
        data=rows('2025-26');extra=copy.deepcopy(data[0]);extra['GAME_ID']='second';data.append(extra)
        records, report=profiles(data,'2025-26')
        p=records[0]
        self.assertEqual((p['games'],p['cumulative_minutes'],p['per36']['PTS']),(2,72,1))
        self.assertAlmostEqual(sum(p['z']['PTS'] for p in records),0)
        self.assertAlmostEqual(sum(p['z']['PTS']**2 for p in records)/len(records),1)
        current,_=profiles(rows(CURRENT,multiplier=10),CURRENT)
        model=HistoricalSeasons(records+current,{'2025-26':report,CURRENT:report})
        result=model.compare('1')
        self.assertEqual(len(result['comparisons']),5)
        self.assertTrue(all(c['player_id']!='1' for c in result['comparisons']))
        self.assertNotIn('minute_difference',result['comparisons'][0])
        validate_result(result,'1')
        for c in result['comparisons']:
            self.assertAlmostEqual(c['distance']**2,sum(f['squared_distance_contribution'] for f in c['features'].values()))

    def test_scale_invariance_to_season_units(self):
        a,_=profiles(rows('2025-26'),'2025-26');b,_=profiles(rows(CURRENT,multiplier=12),CURRENT)
        for x,y in zip(a,b):
            for f in x['z']:self.assertAlmostEqual(x['z'][f],y['z'][f])

    def test_exclusions_preserve_input_no_partial_profile_or_zero_imputation(self):
        data=rows('2025-26');data[0]['AST']=None;data[1]['MIN']=0
        data.append(copy.deepcopy(data[2]));data[3]['GAME_DATE']='bad';original=copy.deepcopy(data)
        eligible,report=profiles(data,'2025-26')
        self.assertEqual([p['PLAYER_ID'] for p in eligible],['5','6','7'])
        self.assertEqual(report['excluded'],4)
        self.assertIn('unresolved_duplicate_game',report['exclusions']['3']['reasons'])
        self.assertEqual(data,original)

    def test_tiny_exposure_allowed_constants_and_sparse_pool(self):
        data=rows(CURRENT,[1]);data[0]['MIN']=.01
        current,report=profiles(data,CURRENT)
        history,hreport=profiles(rows('2025-26',[2]),'2025-26')
        model=HistoricalSeasons(history+current,{'2025-26':hreport,CURRENT:report})
        result=model.compare('1')
        self.assertEqual(result['candidate_count'],1)
        self.assertEqual(result['comparisons'][0]['distance'],0)
        self.assertTrue(any('fewer than five' in w for w in result['warnings']))
        self.assertTrue(all(math.isfinite(v) for v in current[0]['z'].values()))

    def test_multiple_seasons_same_candidate_allowed_deterministic_ties(self):
        records=[];reports={}
        for s in ['2024-25','2025-26',CURRENT]:
            r,report=profiles(rows(s,[1,2]),s);records+=r;reports[s]=report
        result=HistoricalSeasons(records,reports).compare('1')
        self.assertEqual([(c['player_id'],c['season']) for c in result['comparisons']], [('2','2024-25'),('2','2025-26')])

    def test_snapshot_parity_integrity_and_failed_generation_preserves_pointer(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root);output=root/'snapshots'
            model,hashes=load(root,historical_seasons=['2025-26'])
            manifest=generate(root,output,historical_seasons=['2025-26'])
            pointer=(output/'current.json').read_bytes()
            self.assertEqual(manifest['modes'],['per36'])
            self.assertEqual(manifest['result_count'],7)
            release=output/'releases'/manifest['snapshot_id']
            for pid in model.latest:
                result=json.loads((release/f'results/per36/{pid}.json').read_text())
                self.assertEqual(result,model.compare(pid));validate_result(result,pid)
            def bad(model,pid):
                raise RuntimeError('interrupted generation')
            with self.assertRaises(RuntimeError):generate(root,output,historical_seasons=['2025-26'],producer=bad)
            self.assertEqual((output/'current.json').read_bytes(),pointer)
            with patch('nba_player_similarity.season_snapshot.os.replace',side_effect=OSError('activation failure')):
                with self.assertRaises(OSError):generate(root,output,historical_seasons=['2025-26'])
            self.assertEqual((output/'current.json').read_bytes(),pointer)
            self.assertEqual(load(root,historical_seasons=['2025-26'])[1],hashes)

    def test_missing_current_cache_never_falls_back_to_2024(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root);(root/'raw/2026-27.json').unlink()
            with self.assertRaises(FileNotFoundError):load(root,historical_seasons=['2025-26'])
