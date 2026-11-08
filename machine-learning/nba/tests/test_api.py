import json
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from nba_player_similarity.api import create_app
from nba_player_similarity.similarity import SeasonBaseline
from test_similarity import cp


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'raw').mkdir();(self.root/'derived').mkdir()
        self.points=[cp(p,100,p) for p in range(1,8)]
        self.raw=[dict(PLAYER_ID=p,PLAYER_NAME=f'Player {p}') for p in range(1,8)]
        (self.root/'raw/2024-25.json').write_text(json.dumps(self.raw))
        (self.root/'derived/2024-25.json').write_text(json.dumps(self.points))
        self.original={str(p):p.read_bytes() for p in self.root.glob('*/*.json')}

    def test_search_select_pagination_and_validation(self):
        with TestClient(create_app(self.root)) as client:
            self.assertEqual(client.get('/health').json()['players'],7)
            result=client.get('/players',params={'q':'PLAYER','limit':2,'offset':1}).json()
            self.assertEqual(result['total'],7)
            self.assertEqual([p['player_id'] for p in result['players']],['2','3'])
            self.assertEqual(client.get('/players/1').json()['minutes'],100)
            self.assertEqual(client.get('/players?q=unmatched').json()['players'],[])
            for url in ('/players?limit=0','/players?offset=-1','/players/1/comparisons?mode=bad'):
                self.assertEqual(client.get(url).status_code,422)
            self.assertEqual(client.get('/players/unknown').status_code,404)
            self.assertEqual(client.get('/players/unknown/comparisons').status_code,404)

    def test_both_modes_exactly_preserve_model_scores_and_explanations(self):
        with TestClient(create_app(self.root)) as client:
            for mode in ('per36','per_game'):
                result=client.get('/players/1/comparisons',params={'mode':mode}).json()
                expected=SeasonBaseline(self.points,mode=mode).compare('1')
                self.assertEqual(len(result['comparisons']),5)
                self.assertEqual(result['reference']['name'],'Player 1')
                for actual,original in zip(result['comparisons'],expected['comparisons']):
                    self.assertEqual(actual['features'],original['features'])
                    self.assertEqual(actual['distance'],original['distance'])
                    self.assertEqual(actual['checkpoint'],original['checkpoint'])
                self.assertEqual(result,client.get('/players/1/comparisons',params={'mode':mode}).json())
        for p,original in self.original.items():self.assertEqual(Path(p).read_bytes(),original)

    def test_low_exposure_and_sparse_candidates_remain_allowed(self):
        points=[cp(1,3,0),cp(2,3,0),cp(3,10,1)]
        (self.root/'derived/2024-25.json').write_text(json.dumps(points))
        with TestClient(create_app(self.root)) as client:
            result=client.get('/players/1/comparisons').json()
            self.assertEqual(result['candidate_count'],1)
            self.assertEqual(result['comparisons'][0]['distance'],0)
            self.assertTrue(any('Limited playing time' in w for w in result['warnings']))
            self.assertTrue(any('fewer than five' in w for w in result['warnings']))

    def test_missing_and_wrong_season_fail_without_fetch(self):
        for contents in (None,[dict(cp(1),SEASON_ID='21977')]):
            path=self.root/'derived/2024-25.json'
            if contents is None:path.unlink()
            else:path.write_text(json.dumps(contents))
            with self.assertRaisesRegex(RuntimeError,'No download attempted'):
                with TestClient(create_app(self.root)):pass
