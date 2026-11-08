import json
from pathlib import Path
import tempfile
import unittest
from nba_player_similarity.snapshot import generate
from nba_player_similarity.responses import comparison_response
from fastapi.testclient import TestClient
from nba_player_similarity.api import create_app
from test_similarity import cp


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.data=self.root/'data'; self.out=self.root/'snapshots'
        (self.data/'raw').mkdir(parents=True); (self.data/'derived').mkdir()
        (self.data/'raw/2024-25.json').write_text(json.dumps([dict(PLAYER_ID=p,PLAYER_NAME=f'Player {p}') for p in range(1,8)]))
        (self.data/'derived/2024-25.json').write_text(json.dumps([cp(p,value=p) for p in range(1,8)]))

    def test_snapshot_matches_real_api_both_modes_and_metadata(self):
        m=generate(self.data,self.out)
        self.assertEqual(m['result_count'],14);self.assertEqual(m['player_count'],7)
        self.assertTrue(m['generated_at']);self.assertTrue(m['model_version'])
        release=self.out/'releases'/m['snapshot_id']
        with TestClient(create_app(self.data)) as client:
            for mode in ('per36','per_game'):
                for p in range(1,8):
                    saved=json.loads((release/f'results/{mode}/{p}.json').read_text())
                    self.assertEqual(saved,client.get(f'/players/{p}/comparisons?mode={mode}').json())

    def test_failed_partial_generation_keeps_previous_snapshot(self):
        generate(self.data,self.out);before={p.relative_to(self.out):p.read_bytes() for p in self.out.rglob('*.json')}
        calls=[]
        def broken(*args):
            calls.append(1)
            if len(calls)==3:raise RuntimeError('simulated mid-generation failure')
            return comparison_response(*args)
        with self.assertRaisesRegex(RuntimeError,'simulated'):generate(self.data,self.out,producer=broken)
        self.assertEqual(before,{p.relative_to(self.out):p.read_bytes() for p in self.out.rglob('*.json')})
        self.assertFalse((self.out/'.generation-lock').exists())

    def test_parity_failure_is_not_published(self):
        generate(self.data,self.out);before=(self.out/'current.json').read_bytes()
        def corrupt(*args):
            result=comparison_response(*args);result['comparisons'][0]['distance']=999;return result
        with self.assertRaisesRegex(ValueError,'parity'):generate(self.data,self.out,producer=corrupt)
        self.assertEqual(before,(self.out/'current.json').read_bytes())

    def test_new_generation_retains_previous_release_and_lock_prevents_concurrency(self):
        a=generate(self.data,self.out);b=generate(self.data,self.out)
        self.assertNotEqual(a['snapshot_id'],b['snapshot_id'])
        self.assertTrue((self.out/'releases'/a['snapshot_id']/'manifest.json').exists())
        (self.out/'.generation-lock').mkdir()
        with self.assertRaises(FileExistsError):generate(self.data,self.out)
        self.assertEqual(json.loads((self.out/'current.json').read_text())['snapshot_id'],b['snapshot_id'])

    def test_pointer_activation_failure_keeps_valid_pointer(self):
        from unittest.mock import patch
        generate(self.data,self.out);before=(self.out/'current.json').read_bytes()
        with patch('nba_player_similarity.snapshot.os.replace',side_effect=OSError('activation failed')):
            with self.assertRaisesRegex(OSError,'activation failed'):generate(self.data,self.out)
        self.assertEqual(before,(self.out/'current.json').read_bytes())
        self.assertFalse((self.out/'.generation-lock').exists())
        self.assertEqual(list(self.out.glob('.current-*.tmp')),[])
