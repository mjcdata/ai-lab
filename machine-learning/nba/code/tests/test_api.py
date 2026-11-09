from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from nba_player_similarity.api import create_app
from nba_player_similarity.seasonal import load
from test_seasonal import fixture


class APITests(unittest.TestCase):
    def test_current_search_select_per36_parity_and_legacy_mode_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root)
            model,hashes=load(root,historical_seasons=['2025-26'])
            with TestClient(create_app(root,historical_seasons=['2025-26'])) as client:
                self.assertEqual(client.get('/health').json()['season'],'2026-27')
                result=client.get('/players?q=PLAYER&limit=2&offset=1').json()
                self.assertEqual(result['total'],7)
                self.assertEqual([p['player_id'] for p in result['players']],['2','3'])
                self.assertEqual(client.get('/players/1').json()['minutes'],36)
                self.assertEqual(client.get('/players/1/comparisons').json(),model.compare('1'))
                self.assertEqual(client.get('/coverage').json(),model.reports)
                for url in ['/players?limit=0','/players?offset=-1','/players/1/comparisons?mode=per_game']:
                    self.assertEqual(client.get(url).status_code,422)
                self.assertEqual(client.get('/players/unknown').status_code,404)
            self.assertEqual(load(root,historical_seasons=['2025-26'])[1],hashes)

    def test_missing_current_fails_without_fetch(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError,'No download attempted'):
                with TestClient(create_app(temp,historical_seasons=['2025-26'])):pass
