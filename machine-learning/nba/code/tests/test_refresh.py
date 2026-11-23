"""Offline state-machine tests: all external operations are injected fakes."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nba_player_similarity.refresh import Config, run_refresh, exclusive, main, PUBLIC_URL
from nba_player_similarity.refresh_validation import read


class FakeOps:
    def __init__(self):
        self.calls=[];self.fail=None;self.production='old';self.uploads=[];self.canonical='old'

    def hit(self, name):
        self.calls.append(name)
        if self.fail==name:raise RuntimeError(name+' failed')
        if self.fail=='interrupt_'+name:raise KeyboardInterrupt(name)

    def check_source(self,c,s):self.hit('check_source')
    def preflight(self,c,r,s):
        self.hit('preflight');return {'baseline':{'commit':'approved-main','production':{'id':'old','url':'https://old.example'}}}
    def stage(self,c,r,s):self.hit('stage')
    def acquire(self,c,r,s):self.hit('ingest')
    def quality(self,c,r,s):self.hit('quality');return {'quality':{'rows':7}}
    def snapshot(self,c,r,s):self.hit('snapshot');return {'snapshot':'a'*32}
    def build(self,c,r,s):self.hit('build')
    def package(self,c,r,s):self.hit('package');return {'bundle_sha':{'index':'sha'}}
    def validate_candidate(self,c,r,s):self.hit('validate')
    def local_smoke(self,c,r,s):self.hit('local_smoke')
    def deploy_candidate(self,c,r,s):
        self.hit('upload');value={'id':'new','url':'https://candidate.example'};self.uploads.append(value)
        if self.fail=='lost_upload_response':raise ConnectionError('response lost after upload')
        return value
    def recover_candidate(self,c,r,s):
        self.hit('recover')
        if len(self.uploads)!=1:raise RuntimeError('uncertain status; no upload retry')
        return self.uploads[0]
    def verify_candidate(self,c,r,s):self.hit('verify_candidate')
    def production_id(self,c,s):return self.production
    def promote(self,c,r,s):
        self.hit('promote');self.production='new'
        if self.fail=='interrupt_after_promote':raise KeyboardInterrupt('after promotion')
    def verify_live(self,c,r,s):self.hit('verify_live');return {'passed':True,'url':PUBLIC_URL}
    def rollback(self,c,r,s):self.hit('rollback');self.production='old'
    def activate(self,c,r,s):
        self.hit('activate');self.canonical='new'


class RefreshCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.config=Config(self.root,self.root/'data',self.root/'artifacts',self.root/'snapshots')
        self.ops=FakeOps()

    def run_job(self,**kw):
        with redirect_stdout(StringIO()):return run_refresh(self.config,self.ops,**kw)

    def last(self):return read(next((self.config.artifacts/'runs').glob('*/state.json')))

    def test_success_orders_validation_before_alias_promotion_and_records_release(self):
        result=self.run_job(publish=True)
        self.assertEqual(result['phase'],'complete');self.assertEqual(result['deployment']['id'],'new')
        for before,after in [('quality','snapshot'),('validate','upload'),('local_smoke','upload'),('verify_candidate','promote'),('verify_live','activate')]:
            self.assertLess(self.ops.calls.index(before),self.ops.calls.index(after))
        self.assertEqual(read(self.config.artifacts/'current.json')['snapshot'],'a'*32)
        self.assertEqual(read(self.config.artifacts/'runs'/result['id']/'release.json')['deployment']['id'],'new')
        self.assertEqual(self.ops.canonical,'new')

    def test_build_only_does_not_upload_or_touch_canonical_release(self):
        state=self.run_job();self.assertEqual(state['phase'],'prepared')
        self.assertNotIn('upload',self.ops.calls);self.assertEqual(self.ops.canonical,'old')
        resumed=self.run_job(publish=True,resume=state['id']);self.assertEqual(resumed['phase'],'complete')
        self.assertEqual(self.ops.calls.count('ingest'),1)

    def test_all_local_failures_block_upload_and_preserve_previous_release(self):
        for stage in ['preflight','stage','ingest','quality','snapshot','build','package','validate','local_smoke']:
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as t:
                c=Config(Path(t),Path(t)/'data',Path(t)/'artifacts',Path(t)/'snapshots');ops=FakeOps();ops.fail=stage
                with redirect_stdout(StringIO()),self.assertRaises(RuntimeError):run_refresh(c,ops,publish=True)
                self.assertNotIn('upload',ops.calls);self.assertEqual(ops.production,'old');self.assertEqual(ops.canonical,'old')
                self.assertFalse((c.artifacts/'current.json').exists())

    def test_failed_candidate_smoke_never_promotes(self):
        self.ops.fail='verify_candidate'
        with self.assertRaises(RuntimeError):self.run_job(publish=True)
        self.assertNotIn('promote',self.ops.calls);self.assertEqual(self.ops.production,'old')
        self.assertEqual(self.ops.canonical,'old')

    def test_post_publish_failure_rolls_back_and_keeps_canonical_data(self):
        self.ops.fail='verify_live'
        with self.assertRaises(RuntimeError):self.run_job(publish=True)
        self.assertEqual(self.ops.production,'old');self.assertEqual(self.ops.canonical,'old')
        self.assertTrue(self.last()['rolled_back'])
        self.ops.fail=None
        with self.assertRaisesRegex(RuntimeError,'rolled back'):self.run_job(publish=True,resume=self.last()['id'])
        self.assertEqual(self.ops.calls.count('upload'),1)

    def test_failed_rollback_requires_operator_review_and_never_repromotes(self):
        original=self.ops.rollback
        def fail_rollback(*args):
            raise ConnectionError('rollback status unknown')
        self.ops.rollback=fail_rollback;self.ops.fail='verify_live'
        with self.assertRaises(ConnectionError):self.run_job(publish=True)
        self.assertTrue(self.last()['rollback_required'])
        self.ops.fail=None;self.ops.rollback=original
        with self.assertRaisesRegex(RuntimeError,'Rollback outcome'):
            self.run_job(publish=True,resume=self.last()['id'])
        self.assertEqual(self.ops.calls.count('promote'),1)

    def test_interrupted_build_reuses_completed_ingestion_and_no_stale_lock(self):
        self.ops.fail='interrupt_build'
        with self.assertRaises(KeyboardInterrupt):self.run_job(publish=True)
        state=self.last();self.assertEqual(state['phase'],'build')
        self.ops.fail=None;result=self.run_job(publish=True,resume=state['id'])
        self.assertEqual(result['phase'],'complete');self.assertEqual(self.ops.calls.count('ingest'),1)
        self.assertEqual(self.ops.calls.count('build'),2)

    def test_lost_upload_response_reconciles_without_duplicate_deployment(self):
        self.ops.fail='lost_upload_response'
        with self.assertRaises(ConnectionError):self.run_job(publish=True)
        state=self.last();self.assertEqual(state['uncertain_action'],'candidate')
        self.ops.fail=None;result=self.run_job(publish=True,resume=state['id'])
        self.assertEqual(result['phase'],'complete');self.assertEqual(self.ops.calls.count('upload'),1)
        self.assertEqual(self.ops.calls.count('recover'),1)

    def test_unknown_upload_status_requires_decision_no_retry(self):
        self.ops.fail='interrupt_upload'
        with self.assertRaises(KeyboardInterrupt):self.run_job(publish=True)
        self.ops.fail=None
        with self.assertRaisesRegex(RuntimeError,'uncertain'):self.run_job(publish=True,resume=self.last()['id'])
        self.assertEqual(self.ops.calls.count('upload'),1)

    def test_interruption_after_alias_move_does_not_repeat_promotion(self):
        self.ops.fail='interrupt_after_promote'
        with self.assertRaises(KeyboardInterrupt):self.run_job(publish=True)
        self.ops.fail=None;result=self.run_job(publish=True,resume=self.last()['id'])
        self.assertEqual(result['phase'],'complete');self.assertEqual(self.ops.calls.count('promote'),1)

    def test_interrupted_local_activation_reconciles_without_uploading_again(self):
        self.ops.fail='interrupt_activate'
        with self.assertRaises(KeyboardInterrupt):self.run_job(publish=True)
        self.ops.fail=None;result=self.run_job(publish=True,resume=self.last()['id'])
        self.assertEqual(result['phase'],'complete');self.assertEqual(self.ops.calls.count('upload'),1)
        self.assertEqual(self.ops.calls.count('promote'),1)

    def test_external_production_change_is_not_overwritten_or_rolled_back(self):
        self.ops.production='someone-elses-release'
        with self.assertRaisesRegex(RuntimeError,'concurrently'):self.run_job(publish=True)
        self.assertNotIn('promote',self.ops.calls);self.assertNotIn('rollback',self.ops.calls)

    def test_complete_resume_is_noop_and_paths_or_run_ids_cannot_change(self):
        result=self.run_job(publish=True);before=list(self.ops.calls)
        self.assertEqual(self.run_job(publish=True,resume=result['id']),result)
        self.assertEqual(before,self.ops.calls)
        with self.assertRaises(ValueError):self.run_job(resume='../bad')
        config=Config(self.root/'other',self.config.data,self.config.artifacts,self.config.snapshots)
        with self.assertRaises(ValueError):run_refresh(config,self.ops,resume=result['id'],publish=True)

    def test_os_lock_rejects_overlapping_runs(self):
        with exclusive(self.config.artifacts):
            with self.assertRaisesRegex(RuntimeError,'Another'):self.run_job(publish=True)
        self.assertEqual(self.ops.calls,[])

    def test_default_cli_is_read_only_and_publish_requires_explicit_execute(self):
        with patch('nba_player_similarity.refresh.run_refresh',side_effect=AssertionError('live execution')):
            with redirect_stdout(StringIO()):self.assertEqual(main(['--root',str(self.root)]),0)
            with self.assertRaises(SystemExit):main(['--publish'])
        self.assertEqual(list(self.root.iterdir()),[])
