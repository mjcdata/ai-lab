import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nba_player_similarity.ingestion import _atomic_json
from nba_player_similarity.refresh_validation import validate_current, validate_snapshot, read, sha
from nba_player_similarity.season_snapshot import generate
from test_seasonal import rows


def current_rows():
    data=rows('2026-27',range(1,7))
    for i,row in enumerate(data):row.update(GAME_ID='g1',TEAM_ID=10 if i<3 else 20)
    return data


def team_rows():
    return [dict(SEASON_ID='22026',GAME_ID='g1',TEAM_ID=10,PTS=6,WL='L',GAME_DATE='2026-11-01'),
            dict(SEASON_ID='22026',GAME_ID='g1',TEAM_ID=20,PTS=15,WL='W',GAME_DATE='2026-11-01')]


class RefreshDataValidationTests(unittest.TestCase):
    def check(self,data,teams=None,previous=None):
        return validate_current(data,current_rows() if previous is None else previous,
                                team_rows() if teams is None else teams,today=date(2026,11,23))

    def test_complete_coverage_preserves_previous_rows_without_exposure_cutoff(self):
        data=current_rows();data[0]['MIN']=.01
        report=self.check(data)
        self.assertEqual(report['completed_games'],1);self.assertEqual(report['rows'],6)
        self.assertEqual(data[0]['MIN'],.01)

    def test_missing_known_rows_or_entire_team_game_cannot_pass(self):
        with self.assertRaisesRegex(ValueError,'previously'):self.check(current_rows()[:-1])
        teams=team_rows()+[dict(r,GAME_ID='g2') for r in team_rows()]
        with self.assertRaisesRegex(ValueError,'coverage'):self.check(current_rows(),teams=teams)

    def test_duplicates_missing_nonfinite_negative_or_wrong_season_block(self):
        for changes in [{'PTS':None},{'AST':float('inf')},{'REB':-1},{'MIN':-1},{'SEASON_ID':'22025'}, {'PLAYER_NAME':''}]:
            data=current_rows();data[0].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.check(data)
        with self.assertRaises(ValueError):self.check(current_rows()+[current_rows()[0]])

    def test_team_coverage_must_be_complete_final_and_reconciled(self):
        cases=[[],team_rows()[:1],team_rows()+[team_rows()[0]],
               [dict(team_rows()[0],PTS=7),team_rows()[1]],
               [dict(team_rows()[0],WL=None),team_rows()[1]],
               [dict(team_rows()[0],GAME_DATE='2026-11-02'),team_rows()[1]]]
        for teams in cases:
            with self.subTest(teams=teams),self.assertRaises(ValueError):self.check(current_rows(),teams=teams)

    def test_future_or_malformed_dates_block_and_missing_values_remain_missing(self):
        data=current_rows();data[0]['GAME_DATE']='2027-01-01'
        with self.assertRaises(ValueError):self.check(data)
        data=current_rows();data[0]['STL']=None;original=copy.deepcopy(data)
        with self.assertRaises(ValueError):self.check(data)
        self.assertEqual(data,original)


class RefreshSnapshotValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'raw').mkdir()
        _atomic_json(self.root/'raw/2025-26.json',rows('2025-26'))
        _atomic_json(self.root/'raw/2026-27.json',current_rows())
        self.out=self.root/'snapshots'
        self.manifest=generate(self.root,self.out,historical_seasons=['2025-26'])
        self.release=self.out/'releases'/self.manifest['snapshot_id']

    def mutate_result_and_rehash(self,change):
        path=self.release/'results/per36/1.json';value=read(path);change(value);_atomic_json(path,value)
        self.manifest['files']['results/per36/1.json']={'sha256':sha(path),'bytes':path.stat().st_size}
        _atomic_json(self.release/'manifest.json',self.manifest)
        _atomic_json(self.out/'current.json',{'snapshot_id':self.manifest['snapshot_id'],'manifest_sha256':sha(self.release/'manifest.json')})

    def test_all_results_have_exact_direct_model_parity(self):
        value=validate_snapshot(self.out,data_dir=self.root,historical_seasons=['2025-26'])
        self.assertEqual(value['player_count'],6)

    def test_checksum_or_source_tampering_blocks_release(self):
        (self.release/'results/per36/1.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'checksum'):validate_snapshot(self.out)

    def test_rehashed_negative_distance_and_bad_z_explanation_still_block(self):
        self.mutate_result_and_rehash(lambda v:v['comparisons'][0].update(distance=-v['comparisons'][0]['distance']))
        with self.assertRaises(ValueError):validate_snapshot(self.out)

    def test_rehashed_modified_result_fails_full_model_parity(self):
        self.mutate_result_and_rehash(lambda v:v['warnings'].append('corrupted response'))
        with self.assertRaisesRegex(ValueError,'parity'):validate_snapshot(self.out,data_dir=self.root,historical_seasons=['2025-26'])

    def test_empty_candidate_snapshot_cannot_publish(self):
        _atomic_json(self.root/'raw/2026-27.json',[dict(row,MIN=0,PTS=0,AST=0,REB=0,STL=0,BLK=0,TOV=0) for row in current_rows()])
        empty=self.root/'empty';generate(self.root,empty,historical_seasons=['2025-26'])
        with self.assertRaisesRegex(ValueError,'Empty'):validate_snapshot(empty)
