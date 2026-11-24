from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nba_player_similarity.refresh import Config, PROJECT, PUBLIC_URL
from nba_player_similarity.refresh_runtime import LocalOps


class RefreshRuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.c=Config(self.root,self.root/'data',self.root/'artifacts',self.root/'snapshots')
        self.ops=LocalOps();self.state={'id':'a'*32,'baseline':{'commit':'abc','production':{'id':'old','url':'https://old.example'}}}

    def test_upload_must_be_prebuilt_production_candidate_without_domain_assignment(self):
        with patch.object(self.ops,'command',return_value='Production: https://nba-player-similarity-test-malcolmjconnors-projects.vercel.app') as command, \
             patch.object(self.ops,'deployment',return_value={'id':'new','url':'https://candidate.example'}), \
             patch.object(self.ops,'api',return_value={'id':'new','target':'production'}), \
             patch.object(self.ops,'production_id',return_value='old'):
            self.ops.deploy_candidate(self.c,self.root,self.state)
        args=command.call_args.args[0]
        for arg in ('--prebuilt','--prod','--skip-domain'):self.assertIn(arg,args)
        self.assertNotIn('link',args);self.assertNotIn('git',args)

    def test_production_resolution_uses_live_alias_not_latest_created_deployment(self):
        def api(endpoint,*args):
            if endpoint.startswith('/v4/aliases/'):
                return {'projectId':PROJECT,'deploymentId':'old'}
            self.assertEqual(endpoint,'/v13/deployments/old')
            return {'projectId':PROJECT,'readyState':'READY','id':'old','url':'old.example'}
        with patch.object(self.ops,'api',side_effect=api):
            self.assertEqual(self.ops.current_production(self.c,self.root,self.state)['id'],'old')

    def test_wrong_project_plan_git_or_auth_settings_are_not_modified_or_accepted(self):
        project={'id':PROJECT,'name':'nba-player-similarity'}
        team={'slug':'malcolmjconnors-projects','billing':{'plan':'hobby'}}
        for key,value in [('id','other'),('link',{'repo':'ai-lab'}),('ssoProtection',{'deploymentType':'all'}),('framework','nextjs')]:
            with patch.object(self.ops,'api',side_effect=[dict(project,**{key:value}),team]):
                with self.assertRaises(RuntimeError):self.ops.project(self.c,self.root,self.state)
        with patch.object(self.ops,'api',side_effect=[project,dict(team,billing={'plan':'pro'})]):
            with self.assertRaises(RuntimeError):self.ops.project(self.c,self.root,self.state)

    def test_unknown_network_response_is_not_interpreted_as_success(self):
        with self.assertRaises(ValueError):self.ops.json_output('Network disconnected')

    def test_no_blind_reupload_when_no_matching_run_found(self):
        with patch.object(self.ops,'api',return_value={'deployments':[]}):
            with self.assertRaisesRegex(RuntimeError,'uncertain'):self.ops.recover_candidate(self.c,self.root,self.state)

    def test_resume_refuses_a_still_running_child(self):
        self.state['active_child']={'pid':123}
        with patch('nba_player_similarity.refresh_runtime.os.kill',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'prior child'):self.ops.check_source(self.c,self.state)

    def test_staging_preserves_history_and_acquisition_fetches_only_current(self):
        from nba_player_similarity.refresh_runtime import CURRENT
        from nba_player_similarity.ingestion import _atomic_json
        raw=self.c.data/'raw';raw.mkdir(parents=True)
        _atomic_json(raw/'2025-26.json',[{'historical_missing':None}])
        self.state['baseline']['historical']={'2025-26':'unchanged'}
        run=self.root/'run';run.mkdir()
        self.ops.stage(self.c,run,self.state)
        link=run/'data/raw/2025-26.json'
        self.assertTrue(link.is_symlink());self.assertEqual(link.read_bytes(),(raw/'2025-26.json').read_bytes())
        with patch('nba_player_similarity.refresh_runtime.ingest') as ingest, \
             patch('nba_player_similarity.refresh_runtime.fetch_with_retries',return_value=[{'team':1}]) as fetch:
            self.ops.acquire(self.c,run,self.state)
            self.ops.acquire(self.c,run,self.state)
        self.assertEqual([c.args[0] for c in ingest.call_args_list],[CURRENT,CURRENT])
        fetch.assert_called_once()
        self.assertEqual((raw/'2025-26.json').read_text(),'[\n  {\n    "historical_missing": null\n  }\n]\n')

    def test_partial_package_is_rebuilt_in_its_own_run(self):
        run=self.root/'run';(run/'bundle/.vercel/output').mkdir(parents=True)
        (run/'bundle/.vercel/output/broken').write_text('incomplete')
        def command(*args,**kw):
            output=run/'bundle/.vercel/output';output.mkdir(parents=True)
            (output/'config.json').write_text('{"version":3}')
        with patch.object(self.ops,'command',side_effect=command):
            result=self.ops.package(self.c,run,self.state)
        self.assertFalse((run/'bundle/.vercel/output/broken').exists())
        self.assertEqual(set(result['bundle_sha']),{'config.json'})

    def test_model_snapshot_activation_is_idempotent_and_preserves_previous_release(self):
        from nba_player_similarity.ingestion import _atomic_json
        from nba_player_similarity.refresh_validation import read,sha
        from nba_player_similarity.season_snapshot import generate
        from test_seasonal import rows
        raw=self.c.data/'raw';raw.mkdir(parents=True)
        _atomic_json(raw/'2025-26.json',rows('2025-26'))
        _atomic_json(raw/'2026-27.json',rows('2026-27'))
        old=generate(self.c.data,self.c.snapshots,historical_seasons=['2025-26'])
        self.state['baseline'].update(current_sha=sha(raw/'2026-27.json'),pointer_sha=sha(self.c.snapshots/'current.json'))
        run=self.root/'run';(run/'data/raw').mkdir(parents=True)
        (run/'data/raw/2025-26.json').symlink_to(raw/'2025-26.json')
        updated=rows('2026-27');updated[0]['PTS']+=1
        _atomic_json(run/'data/raw/2026-27.json',updated)
        candidate=generate(run/'data',run/'snapshots',historical_seasons=['2025-26'])
        self.state['snapshot']=candidate['snapshot_id'];_atomic_json(run/'quality.json',{'rows':len(updated)})
        self.ops.activate(self.c,run,self.state)
        self.ops.activate(self.c,run,self.state)
        self.assertEqual(read(raw/'2026-27.json'),updated)
        self.assertEqual(read(self.c.snapshots/'current.json')['snapshot_id'],candidate['snapshot_id'])
        self.assertTrue((self.c.snapshots/'releases'/old['snapshot_id']).exists())
        self.assertEqual(sha(raw/'2026-27.json'),sha(run/'data/raw/2026-27.json'))
        _atomic_json(raw/'2026-27.json',[{'external':'change'}])
        with self.assertRaisesRegex(ValueError,'cache changed'):self.ops.activate(self.c,run,self.state)

    def test_substituted_staged_history_cannot_reach_publication(self):
        from nba_player_similarity.ingestion import _atomic_json
        from nba_player_similarity.refresh_validation import sha
        raw=self.c.data/'raw';raw.mkdir(parents=True)
        _atomic_json(raw/'2025-26.json',[]);_atomic_json(raw/'2026-27.json',[])
        run=self.root/'run';(run/'data/raw').mkdir(parents=True)
        _atomic_json(run/'data/raw/2026-27.json',[])
        self.state['baseline'].update(historical={'2025-26':sha(raw/'2025-26.json')},current_sha=sha(raw/'2026-27.json'))
        with patch.object(self.ops,'check_source'),patch.object(self.ops,'quality'), \
             patch('nba_player_similarity.refresh_runtime.validate_snapshot',return_value={'source_sha256':{'2025-26':'altered'}}):
            with self.assertRaisesRegex(ValueError,'Staged historical'):
                self.ops.validate_candidate(self.c,run,self.state)
