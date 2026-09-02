import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from personal_toolkit import pipeline
from personal_toolkit.config import DEFAULTS, SECRET_KEYS, Settings, initialize, read_env
from personal_toolkit.jobs import JobStore
from personal_toolkit.worker import make_server
from personal_toolkit.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='toolkit review ')
        self.root = Path(self.tmp.name).resolve()
        (self.root / '.env.example').write_text((ROOT / '.env.example').read_text())
        initialize(self.root)
        self.settings = Settings(self.root, environ={})

    def tearDown(self):
        self.tmp.cleanup()


class ConfigTests(Workspace):
    def test_repair_existing_placeholders_preserve_custom_values(self):
        (self.root / '.env').write_text('N8N_PORT=7777\nN8N_ENCRYPTION_KEY=change-me\nPENPOT_SECRET_KEY=' + 'a'*64 + '\n')
        changed = initialize(self.root)
        result = Settings(self.root, environ={})
        result.validate()
        self.assertEqual(result.get('N8N_PORT'), '7777')
        self.assertEqual(result.get('PENPOT_SECRET_KEY'), 'a'*64)
        self.assertIn('N8N_ENCRYPTION_KEY', changed)
        self.assertNotIn('PENPOT_SECRET_KEY', changed)

    def test_idempotent_and_private(self):
        before = (self.root / '.env').read_text()
        initialize(self.root)
        self.assertEqual(before, (self.root / '.env').read_text())
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)

    def test_custom_short_key_is_not_rotated(self):
        path=self.root/'.env'
        path.write_text(path.read_text().replace(self.settings.get('N8N_ENCRYPTION_KEY'),'existing-short-key'))
        initialize(self.root)
        settings=Settings(self.root,environ={})
        self.assertEqual(settings.get('N8N_ENCRYPTION_KEY'),'existing-short-key')
        with self.assertRaises(ValueError):settings.validate()

    def test_secret_values_unique(self):
        self.assertEqual(len({self.settings.get(k) for k in SECRET_KEYS}), len(SECRET_KEYS))

    def test_env_is_data_not_shell(self):
        marker = self.root / 'should-not-exist'
        (self.root / '.env').write_text('DOWNLOAD_DIR=$(touch ' + str(marker) + ')\n')
        result = Settings(self.root, environ={})
        self.assertTrue(result.get('DOWNLOAD_DIR').startswith('$(touch'))
        self.assertFalse(marker.exists())

    def test_paths_do_not_depend_on_working_directory(self):
        self.assertEqual(self.settings.path('DOWNLOAD_DIR'), self.root / 'downloads')
        other = self.root / 'other folder'
        other.mkdir()
        old = os.getcwd()
        try:
            os.chdir(other)
            self.assertEqual(self.settings.path('DOWNLOAD_DIR'), self.root / 'downloads')
        finally:
            os.chdir(old)

    def test_startup_rejects_placeholder(self):
        self.settings.values['WORKER_API_TOKEN'] = 'change-me'
        with self.assertRaises(ValueError):
            self.settings.validate()


class PipelineTests(Workspace):
    def fake_whisper(self, segments=None):
        captured = {}
        segments = segments if segments is not None else [types.SimpleNamespace(start=12.1, end=15.2, text=' Bespreek het budget. ')]
        class WhisperModel:
            def __init__(self, *args, **kwargs):
                pass
            def transcribe(self, source, **kwargs):
                captured['source'] = source
                return iter(segments), types.SimpleNamespace(language='nl')
        return types.SimpleNamespace(WhisperModel=WhisperModel), captured

    def test_quoted_unicode_and_spaces_in_filename(self):
        source = self.root / 'Réunion "draft" \'final\'.wav'
        source.touch()
        fake, captured = self.fake_whisper()
        with patch.dict(sys.modules, {'faster_whisper': fake}):
            text = pipeline.transcribe(source, self.root / 'transcript.txt', self.settings)
        self.assertEqual(captured['source'], str(source))
        self.assertIn('[00:00:12–00:00:15]', text)
        self.assertEqual(json.loads((self.root / 'transcript.json').read_text())['language'], 'nl')

    def test_empty_audio_fails_without_fake_transcript(self):
        source = self.root / 'silent.wav'; source.touch()
        fake, _ = self.fake_whisper([])
        with patch.dict(sys.modules, {'faster_whisper': fake}), self.assertRaises(RuntimeError):
            pipeline.transcribe(source, self.root / 'empty.txt', self.settings)
        self.assertFalse((self.root / 'empty.txt').exists())

    def test_chunks_preserve_all_text_and_bound_long_lines(self):
        text = 'a'*30001 + '\n' + 'b'*11000
        parts = list(pipeline.chunks(text))
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(0 < len(part) <= 10000 for part in parts))

    def test_long_summary_is_reduced_and_preserves_instruction(self):
        seen = []
        def generate(text, settings, instruction):
            seen.append((text, instruction))
            return '- Budget [00:00:12]'
        with patch.object(pipeline, 'generate', side_effect=generate):
            result = pipeline.summarize('a'*25000, self.settings)
        self.assertEqual(len(seen), 4)
        self.assertTrue(all(len(text) <= 10000 for text, _ in seen))
        self.assertTrue(all('Nederlandse' in instruction for _, instruction in seen))
        self.assertIn('[00:00:12]', result)

    def test_download_passes_url_as_single_argument(self):
        media = self.root / 'media file.wav'; media.touch()
        with patch('subprocess.run', return_value=types.SimpleNamespace(stdout=str(media)+'\n')) as run:
            pipeline.download('https://example.org/video?a=1&b=2', self.root)
        args = run.call_args.args[0]
        self.assertEqual(args[-2:], ['--', 'https://example.org/video?a=1&b=2'])
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertIn('--no-playlist', args)

    def test_invalid_urls_rejected(self):
        for url in [None, 12, 'file:///etc/passwd', 'https://user:secret@example.org/', '--exec=touch foo']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                pipeline.validate_url(url)

    def test_pipeline_outputs_and_stages(self):
        source = self.root / 'source.wav'; source.touch()
        fake, _ = self.fake_whisper()
        stages=[]
        with patch.dict(sys.modules, {'faster_whisper':fake}), patch.object(pipeline, 'generate', return_value='- Budget [00:00:12]'):
            result = pipeline.run_pipeline(str(source), self.root / 'job', self.settings, stages.append)
        self.assertEqual(stages, ['transcribing', 'summarizing'])
        self.assertTrue(Path(result['summary']).exists())
        self.assertTrue(Path(result['segments']).exists())
        self.assertIn('Budget', Path(result['summary']).read_text())

    def test_ollama_http_json_handles_quotes_and_unicode(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        bodies=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                bodies.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'response':'Samenvatting [00:00:12]', 'done':True}).encode())
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.settings.values['OLLAMA_URL']=f'http://127.0.0.1:{server.server_port}'
        try:
            result=pipeline.summarize('[00:00:12] "Budget" €100\nTweede regel',self.settings)
            self.assertIn('Samenvatting',result)
            self.assertIn('€100',bodies[0]['prompt'])
            self.assertFalse(bodies[0]['stream'])
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_empty_incomplete_ollama_responses_fail(self):
        import io
        for data in [{'response':'','done':True},{'response':'partial','done':False},{'error':'missing model'},
                     {'response':None,'done':True}, []]:
            with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())), self.assertRaises(RuntimeError):
                pipeline.generate('text',self.settings,'summarize')


class JobTests(Workspace):
    def test_error_preserves_partial_output(self):
        store=JobStore(self.root/'jobs');job=store.create('source')
        def fail(source,folder,settings,progress):
            (folder/'transcript.txt').write_text('Already transcribed')
            progress('summarizing')
            raise RuntimeError('Ollama unavailable')
        result=store.execute(job['id'],self.settings,runner=fail)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['stage'],'summarizing')
        self.assertTrue((store.folder(job['id'])/'transcript.txt').exists())

    def test_recovery_marks_only_interrupted_jobs(self):
        store=JobStore(self.root/'jobs');a=store.create('a');b=store.create('b')
        store.update(b['id'],status='succeeded')
        store.recover()
        self.assertEqual(store.get(a['id'])['status'],'failed')
        self.assertEqual(store.get(b['id'])['status'],'succeeded')

    def test_worker_recovery_does_not_modify_native_jobs(self):
        store=JobStore(self.root/'jobs')
        local=store.create('local')
        remote=store.create('remote',owner='worker')
        store.recover(owner='worker')
        self.assertEqual(store.get(local['id'])['status'],'queued')
        self.assertEqual(store.get(remote['id'])['status'],'failed')

    def test_no_path_traversal(self):
        store=JobStore(self.root/'jobs')
        with self.assertRaises(ValueError): store.get('../../.env')


class WorkerTests(Workspace):
    def setUp(self):
        super().setUp()
        self.server=make_server(self.settings,'127.0.0.1',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.server.executor.shutdown(wait=True);self.thread.join()
        super().tearDown()

    def request(self,path,data=None,auth=True):
        headers={'Content-Type':'application/json'}
        if auth:headers['X-Toolkit-Token']=self.settings.get('WORKER_API_TOKEN')
        req=urllib.request.Request(self.url+path,headers=headers,data=json.dumps(data).encode() if data is not None else None)
        return urllib.request.urlopen(req,timeout=5)

    def test_unauthorized_rejected_before_processing(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/jobs',{'url':'https://example.org'},auth=False)
        self.assertEqual(error.exception.code,401)

    def test_invalid_payload_rejected(self):
        for data in [{'url':'file:///etc/passwd'},{'url':123},[],{}]:
            with self.subTest(data=data), self.assertRaises(urllib.error.HTTPError) as error:self.request('/jobs',data)
            self.assertEqual(error.exception.code,400)

    def test_async_submit_poll_results(self):
        def execute(store,job_id,settings):
            store.update(job_id,status='succeeded',result={'summary_text':'Samenvatting'})
        with patch.object(JobStore,'execute',execute):
            with self.request('/jobs',{'url':'https://example.org/video'}) as response:
                self.assertEqual(response.status,202);job=json.load(response)
            with self.request('/jobs/'+job['id']) as response:result=json.load(response)
            # The worker is deliberately async; await a terminal state with a bounded deadline.
            deadline=time.monotonic()+3
            while result['status']=='queued' and time.monotonic()<deadline:
                time.sleep(.01)
                with self.request('/jobs/'+job['id']) as response:result=json.load(response)
            self.assertEqual(result['status'],'succeeded')
            self.assertEqual(result['result']['summary_text'],'Samenvatting')


class InstallerTests(Workspace):
    def test_upgrade_preserves_state_and_excludes_state_from_bundle(self):
        source=self.root/'source';destination=self.root/'destination';bundle=self.root/'bundle'
        source.mkdir();destination.mkdir()
        (source/'README.md').write_text('new code')
        for base in [source,destination]:
            for name in ['.env','data/jobs/job.json','services/fooocus/models/model.bin','downloads/recording.wav','transcripts/meeting.txt','custom.txt']:
                path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('user state')
        script=ROOT/'scripts/copy-toolkit.sh'
        subprocess.run(['bash',str(script),str(source),str(destination)],check=True)
        self.assertEqual((destination/'README.md').read_text(),'new code')
        for path in ['.env','data/jobs/job.json','services/fooocus/models/model.bin','custom.txt']:
            self.assertEqual((destination/path).read_text(),'user state')
        subprocess.run(['bash',str(script),str(source),str(bundle)],check=True)
        self.assertEqual([p.name for p in bundle.iterdir()],['README.md'])

    def test_cli_from_other_directory(self):
        p=subprocess.run([str(ROOT/'bin/pt'),'--help'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('pipeline',p.stdout)

    def test_cursor_merge_preserves_other_servers(self):
        project=self.root/'Auraxis';config=project/'.cursor/mcp.json';config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'mcpServers':{'existing':{'url':'https://example.org'}},'custom':True}))
        with patch.dict(os.environ,{'PERSONAL_TOOLKIT_HOME':str(self.root)}):
            self.assertEqual(main(['cursor-config',str(project)]),0)
        data=json.loads(config.read_text())
        self.assertTrue(data['custom']);self.assertIn('existing',data['mcpServers'])
        self.assertEqual(data['mcpServers']['penpot']['url'],'http://localhost:4401/mcp')

    def test_cursor_conflicting_config_not_overwritten(self):
        project=self.root/'project';config=project/'.cursor/mcp.json';config.parent.mkdir(parents=True)
        original=json.dumps({'mcpServers':{'penpot':{'url':'https://custom.example.org'}}});config.write_text(original)
        with patch.dict(os.environ,{'PERSONAL_TOOLKIT_HOME':str(self.root)}):
            self.assertEqual(main(['cursor-config',str(project)]),1)
        self.assertEqual(config.read_text(),original)


if __name__=='__main__':unittest.main()
