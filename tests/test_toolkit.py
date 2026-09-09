import importlib.util
import json
import os
import shutil
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


def write_silence_wav(path, seconds=0.3):
    import wave
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))
    return path


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
                captured['init_args'] = args
                captured['init_kwargs'] = kwargs
            def transcribe(self, source, **kwargs):
                captured['source'] = source
                captured['kwargs'] = kwargs
                return iter(segments), types.SimpleNamespace(language='nl')
        return types.SimpleNamespace(WhisperModel=WhisperModel), captured

    def test_quoted_unicode_and_spaces_in_filename(self):
        source = self.root / 'Réunion "draft" \'final\'.wav'
        source.touch()
        fake, captured = self.fake_whisper()
        with patch.dict(sys.modules, {'faster_whisper': fake}):
            text = pipeline.transcribe(source, self.root / 'transcript.txt', self.settings)
        self.assertEqual(captured['source'], str(source))
        self.assertEqual(captured['init_kwargs']['device'], 'cpu')
        self.assertEqual(captured['init_kwargs']['compute_type'], 'int8')
        self.assertEqual(captured['init_kwargs']['cpu_threads'], 0)
        self.assertEqual(captured['init_kwargs']['download_root'], str(self.settings.path('WHISPER_CACHE_DIR')))
        self.assertTrue(self.settings.path('WHISPER_CACHE_DIR').is_dir())
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
        stages = []
        def generate(text, settings, instruction):
            seen.append((text, instruction))
            return '- Budget [00:00:12]'
        with patch.object(pipeline, 'generate', side_effect=generate):
            result = pipeline.summarize('a'*25000, self.settings, stages.append)
        self.assertEqual(len(seen), 4)
        self.assertTrue(all(len(text) <= 10000 for text, _ in seen))
        self.assertTrue(all('Nederlandse' in instruction for _, instruction in seen))
        self.assertTrue(any('Kernpunten' in instruction for _, instruction in seen))
        self.assertTrue(any('deelsamenvattingen' in instruction for _, instruction in seen))
        self.assertIn('[00:00:12]', result)
        self.assertIn('Kernpunten', result)
        self.assertIn('summarizing 1/3', stages)
        self.assertIn('summarizing 1/1', stages)

    def test_normalize_summary_adds_missing_dutch_headings(self):
        wrapped = pipeline.normalize_summary('- Budget [00:00:12]')
        self.assertIn('## Kernpunten', wrapped)
        self.assertIn('## Beslissingen of conclusies', wrapped)
        self.assertIn('## Open punten of vervolgstappen', wrapped)
        self.assertIn('- Budget [00:00:12]', wrapped)
        structured = pipeline.normalize_summary('## Kernpunten\n- a\n## Beslissingen of conclusies\ngeen\n## Open punten of vervolgstappen\ngeen')
        self.assertTrue(structured.startswith('## Kernpunten'))
        partial = pipeline.normalize_summary('## Kernpunten\n- alleen dit')
        self.assertIn('## Beslissingen of conclusies', partial)
        empty_bullets = pipeline.normalize_summary('## Kernpunten\n\n-\n\n## Beslissingen of conclusies\n*\n## Open punten of vervolgstappen\n')
        self.assertEqual(empty_bullets.count('geen'), 3)
        self.assertNotIn('\n-\n', '\n' + empty_bullets + '\n')
        with self.assertRaises(RuntimeError):
            pipeline.normalize_summary('   ')

    def test_file_url_and_resume_skip_completed_stages(self):
        source = self.root / 'clip file.wav'
        source.write_bytes(b'')
        resolved = pipeline.resolve_media_source(source.as_uri())
        self.assertEqual(resolved, source.resolve())
        with self.assertRaises(ValueError):
            pipeline.resolve_media_source('file://example.org/tmp/clip.wav')
        with self.assertRaises(ValueError):
            pipeline.resolve_media_source('file:///tmp/clip.wav?x=1')
        with self.assertRaises(ValueError):
            pipeline.resolve_media_source('https://example.org/video.mp4')
        job = self.root / 'job'
        (job / 'media').mkdir(parents=True)
        write_silence_wav(job / 'media' / 'clip.wav')
        (job / 'transcript.txt').write_text('[00:00:01] Hallo daar.\n')
        stages = []
        with patch.object(pipeline, 'generate', return_value='- Hallo [00:00:01]') as generate:
            result = pipeline.run_pipeline('https://example.org/video', job, self.settings, stages.append)
        generate.assert_called()
        self.assertEqual(stages, ['reusing-transcript', 'summarizing 1/1'])
        self.assertIn('Hallo', Path(result['summary']).read_text())
        (job / 'transcript.txt').unlink()
        stages.clear()
        fake, captured = self.fake_whisper()
        with patch.dict(sys.modules, {'faster_whisper': fake}), \
                patch.object(pipeline, 'generate', return_value='- Budget [00:00:12]'), \
                patch.object(pipeline, 'download') as download:
            pipeline.run_pipeline('https://example.org/video', job, self.settings, stages.append)
        download.assert_not_called()
        self.assertEqual(stages[0], 'reusing-media')
        self.assertIn('transcribing', stages)
        self.assertEqual(stages[-1], 'summarizing 1/1')
        self.assertTrue(captured['source'].endswith('clip.wav'))

    def test_resume_skips_tiny_corrupt_and_partial_media(self):
        job = self.root / 'job'
        media = job / 'media'
        media.mkdir(parents=True)
        (media / 'clip.m4a.part').write_bytes(b'x' * 5000)
        (media / 'tiny.m4a').write_bytes(b'\x00' * 40)
        self.assertEqual(pipeline.media_candidates(job), [])
        self.assertIsNone(pipeline.existing_media(job))
        junk = media / 'corrupt.m4a'
        junk.write_bytes(b'not a media file' * 80)
        self.assertEqual([path.name for path in pipeline.media_candidates(job)], ['corrupt.m4a'])
        with patch.object(pipeline, 'probe_media', return_value=False):
            self.assertIsNone(pipeline.existing_media(job))
        audio = write_silence_wav(media / 'good.wav')
        leftover_video = media / 'source.mp4'
        leftover_video.write_bytes(b'\x00' * 20000)

        def readable(path):
            return Path(path).suffix.lower() == '.wav'

        with patch.object(pipeline, 'probe_media', side_effect=readable):
            self.assertEqual(pipeline.existing_media(job), audio)
        pipeline.clear_partial_downloads(job)
        self.assertFalse((media / 'clip.m4a.part').exists())
        downloaded = self.root / 'fresh.wav'
        write_silence_wav(downloaded)
        stages = []
        fake, _ = self.fake_whisper()
        with patch.dict(sys.modules, {'faster_whisper': fake}), \
                patch.object(pipeline, 'generate', return_value='- Budget [00:00:12]'), \
                patch.object(pipeline, 'existing_media', return_value=None), \
                patch.object(pipeline, 'download', return_value=downloaded) as download:
            pipeline.run_pipeline('https://example.org/video', job, self.settings, stages.append)
        download.assert_called()
        self.assertEqual(stages[0], 'downloading')

    def test_probe_media_requires_size_and_uses_ffmpeg_when_present(self):
        missing = self.root / 'missing.wav'
        self.assertFalse(pipeline.probe_media(missing))
        tiny = self.root / 'tiny.wav'
        tiny.write_bytes(b'\x00' * 10)
        self.assertFalse(pipeline.probe_media(tiny))
        junk = self.root / 'junk.m4a'
        junk.write_bytes(b'not a media file' * 80)
        wav = write_silence_wav(self.root / 'ok.wav')
        with patch.object(pipeline.shutil, 'which', return_value=None):
            self.assertTrue(pipeline.probe_media(junk))
            self.assertTrue(pipeline.probe_media(wav))
        if shutil.which('ffmpeg') is None:
            return
        self.assertFalse(pipeline.probe_media(junk))
        self.assertTrue(pipeline.probe_media(wav))

    def test_heartbeat_emits_elapsed_notes(self):
        from io import StringIO
        buf = StringIO()
        with pipeline.heartbeat('still waiting on Ollama', interval=0.05, output=buf):
            time.sleep(0.2)
        text = buf.getvalue()
        self.assertIn('still waiting on Ollama', text)
        self.assertIn('s)…', text)

    def test_download_passes_url_as_single_argument(self):
        media = self.root / 'media file.wav'; media.touch()
        with patch('subprocess.run', return_value=types.SimpleNamespace(stdout=str(media)+'\n', returncode=0, stderr='')) as run:
            pipeline.download('https://example.org/video?a=1&b=2', self.root)
        args = run.call_args.args[0]
        self.assertEqual(args[-2:], ['--', 'https://example.org/video?a=1&b=2'])
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertIn('--no-playlist', args)
        self.assertIn('--retries', args)
        self.assertIn('-x', args)
        self.assertIn('m4a', args)
        self.assertNotIn('--cookies-from-browser', args)

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
        self.assertEqual(stages[0], 'transcribing')
        self.assertEqual(stages[-1], 'summarizing 1/1')
        self.assertTrue(any(item.startswith('transcribing') for item in stages))
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

    def test_concurrent_execute_is_rejected(self):
        store = JobStore(self.root / 'jobs')
        job = store.create('source')
        started = threading.Event()
        release = threading.Event()

        def hold(source, folder, settings, progress):
            started.set()
            self.assertTrue(release.wait(3))
            (folder / 'summary.md').write_text('ok')
            return {'summary_text': 'ok'}

        first = threading.Thread(target=lambda: store.execute(job['id'], self.settings, runner=hold))
        first.start()
        self.assertTrue(started.wait(3))
        with self.assertRaises(ValueError) as error:
            store.execute(job['id'], self.settings, runner=lambda *args: None)
        self.assertIn('already running', str(error.exception))
        live = store.create('live')
        store.update(live['id'], status='running', pid=os.getpid(), owner='local')
        active_ids = {job['id'] for job in store.running_local()}
        self.assertIn(live['id'], active_ids)
        self.assertIn(job['id'], active_ids)
        self.assertNotIn(live['id'], {item['id'] for item in store.running_local(exclude_id=live['id'])})
        release.set()
        first.join(3)
        self.assertEqual(store.get(job['id'])['status'], 'succeeded')

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
        def execute(store, job_id, settings, **_kwargs):
            store.update(job_id, status='succeeded', result={'summary_text':'Samenvatting'})
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
        self.assertIn('jobs',p.stdout)
        self.assertIn('retry',p.stdout)

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


class DoctorAndJobsTests(Workspace):
    def test_whisper_defaults_to_dutch_and_supports_autodetect(self):
        source = self.root / 'opname.wav'
        source.touch()
        fake, captured = PipelineTests.fake_whisper(self)
        with patch.dict(sys.modules, {'faster_whisper': fake}):
            pipeline.transcribe(source, self.root / 't.txt', self.settings)
        self.assertEqual(captured['kwargs']['language'], 'nl')
        self.settings.values['WHISPER_LANGUAGE'] = ''
        with patch.dict(sys.modules, {'faster_whisper': fake}):
            pipeline.transcribe(source, self.root / 't2.txt', self.settings)
        self.assertNotIn('language', captured['kwargs'])
        self.settings.values['WHISPER_LANGUAGE'] = 'nl;rm'
        with self.assertRaises(ValueError):
            pipeline.whisper_language(self.settings)

    def test_whisper_runtime_uses_cache_and_rejects_cuda_on_macos(self):
        runtime = pipeline.whisper_runtime(self.settings)
        self.assertEqual(runtime['device'], 'cpu')
        self.assertEqual(runtime['download_root'], str(self.settings.path('WHISPER_CACHE_DIR')))
        self.settings.values['WHISPER_DEVICE'] = 'cuda'
        with patch('personal_toolkit.pipeline.sys.platform', 'darwin'), self.assertRaises(ValueError) as error:
            pipeline.whisper_runtime(self.settings)
        self.assertIn('Metal', str(error.exception))
        self.settings.values['WHISPER_DEVICE'] = 'tpu'
        with self.assertRaises(ValueError):
            pipeline.whisper_runtime(self.settings)
        self.settings.values['WHISPER_DEVICE'] = 'cpu'
        self.settings.values['WHISPER_CPU_THREADS'] = '8'
        self.assertEqual(pipeline.whisper_runtime(self.settings)['cpu_threads'], 8)
        self.settings.values['WHISPER_CPU_THREADS'] = '99'
        with self.assertRaises(ValueError):
            pipeline.whisper_cpu_threads(self.settings)

    def test_download_error_uses_yt_dlp_message_and_rejects_cookie_injection(self):
        with patch('subprocess.run', return_value=types.SimpleNamespace(
                stdout='', returncode=1, stderr='WARNING: sleep\nERROR: Private video\n')):
            with self.assertRaises(RuntimeError) as error:
                pipeline.download('https://example.org/video', self.root)
        self.assertIn('Private video', str(error.exception))
        self.settings.values['YTDLP_COOKIES_FROM_BROWSER'] = 'chrome; rm -rf /'
        with self.assertRaises(ValueError):
            pipeline.download('https://example.org/video', self.root, settings=self.settings)
        media = self.root / 'clip.m4a'
        media.touch()
        self.settings.values['YTDLP_COOKIES_FROM_BROWSER'] = 'safari'
        with patch('subprocess.run', return_value=types.SimpleNamespace(
                stdout=str(media) + '\n', returncode=0, stderr='')) as run:
            pipeline.download('https://example.org/video', self.root, audio=False, settings=self.settings)
        args = run.call_args.args[0]
        self.assertEqual(args[args.index('--cookies-from-browser') + 1], 'safari')
        self.assertNotIn('-x', args)

    def test_missing_downloader_is_actionable(self):
        with patch('subprocess.run', side_effect=FileNotFoundError('yt-dlp')):
            with self.assertRaises(RuntimeError) as error:
                pipeline.download('https://example.org/video', self.root)
        self.assertIn('yt-dlp', str(error.exception))
        self.assertIn('make setup', str(error.exception))

    def test_download_cli_forwards_cookie_setting(self):
        (self.root / '.env').write_text((self.root / '.env').read_text() + '\nYTDLP_COOKIES_FROM_BROWSER=firefox\n')
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}), \
                patch('personal_toolkit.__main__.download', return_value=self.root / 'clip.m4a') as dl:
            self.assertEqual(main(['download', 'https://example.org/video', '--audio']), 0)
        self.assertEqual(dl.call_args.kwargs['audio'], True)
        self.assertEqual(dl.call_args.kwargs['settings'].get('YTDLP_COOKIES_FROM_BROWSER'), 'firefox')

    def test_ollama_retries_transient_errors_but_not_http_client_errors(self):
        import io
        ok = io.BytesIO(json.dumps({'response': 'ok', 'done': True}).encode())
        with patch('time.sleep') as slept, \
                patch('urllib.request.urlopen', side_effect=[urllib.error.URLError('temporary'), ok]):
            self.assertEqual(pipeline.generate('text', self.settings, 'summarize'), 'ok')
        self.assertTrue(slept.called)
        client = urllib.error.HTTPError('http://127.0.0.1/api/generate', 400, 'bad', None, io.BytesIO())
        with patch('time.sleep') as slept, patch('urllib.request.urlopen', side_effect=client):
            with self.assertRaises(RuntimeError):
                pipeline.generate('text', self.settings, 'summarize')
        slept.assert_not_called()
        ok = io.BytesIO(json.dumps({'response': 'ok', 'done': True}).encode())
        server = urllib.error.HTTPError('http://127.0.0.1/api/generate', 500, 'busy', None, io.BytesIO())
        with patch('time.sleep') as slept, \
                patch('urllib.request.urlopen', side_effect=[server, ok]):
            self.assertEqual(pipeline.generate('text', self.settings, 'summarize'), 'ok')
        self.assertTrue(slept.called)

    def test_jobs_list_and_prefix_lookup(self):
        store = JobStore(self.settings.path('JOBS_DIR'))
        store.update('a' * 32, source='first', status='queued', stage='queued')
        store.update('a' * 31 + 'b', source='second', status='succeeded', result={'summary': '/tmp/summary.md'})
        store.update('c' * 32, source='third', status='queued', stage='queued')
        corrupt = store.directory / ('b' * 32)
        corrupt.mkdir()
        (corrupt / 'job.json').write_text('{')
        listed = store.list(10)
        self.assertEqual([job['id'] for job in listed], ['c' * 32, 'a' * 31 + 'b', 'a' * 32])
        self.assertNotIn('b' * 32, [job['id'] for job in listed])
        self.assertEqual(store.get('c' * 8)['source'], 'third')
        with self.assertRaises(ValueError):
            store.resolve('a' * 8)
        with self.assertRaises(FileNotFoundError):
            store.resolve('dddddddd')
        with self.assertRaises(ValueError):
            store.list(0)
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}):
            self.assertEqual(main(['jobs', '-n', '5']), 0)
            self.assertEqual(main(['job', 'c' * 8]), 0)
            self.assertEqual(main(['job', '--json', 'c' * 8]), 0)

    def test_interrupt_retry_and_corrupt_recovery(self):
        store = JobStore(self.root / 'jobs')
        stopped = store.create('source')
        def stop(source, folder, settings, progress):
            (folder / 'transcript.txt').write_text('[00:00:01] Hallo\n')
            progress('summarizing')
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            store.execute(stopped['id'], self.settings, runner=stop)
        saved = store.get(stopped['id'])
        self.assertEqual(saved['status'], 'failed')
        self.assertIn('Ctrl-C', saved['error'])
        self.assertIsNone(saved.get('pid'))
        with patch.object(pipeline, 'generate', return_value='- Hallo [00:00:01]'):
            result = store.retry(stopped['id'], self.settings)
        self.assertEqual(result['status'], 'succeeded')
        self.assertTrue((store.folder(stopped['id']) / 'summary.md').exists())
        live = store.create('live')
        dead = store.create('dead')
        store.update(live['id'], status='running', pid=os.getpid())
        store.update(dead['id'], status='running')
        store.recover(owner='local', stale=True)
        self.assertEqual(store.get(live['id'])['status'], 'running')
        self.assertEqual(store.get(dead['id'])['status'], 'failed')
        done = store.create('done')
        store.update(done['id'], status='succeeded', result={'summary': 'x'})
        with self.assertRaises(ValueError):
            store.retry(done['id'], self.settings)
        with self.assertRaises(ValueError):
            store.retry(live['id'], self.settings)
        corrupt = store.directory / ('d' * 32)
        corrupt.mkdir()
        (corrupt / 'job.json').write_text('{')
        queued = store.create('queued')
        store.recover()
        self.assertEqual(store.get(queued['id'])['status'], 'failed')
        self.assertTrue((corrupt / 'job.json').exists())
        from io import StringIO
        settings_store = JobStore(self.settings.path('JOBS_DIR'))
        job = settings_store.create(str(self.root / 'missing.wav'))
        (settings_store.folder(job['id']) / 'transcript.txt').write_text('[00:00:01] Hallo\n')
        settings_store.update(job['id'], status='failed', stage='summarizing', error='Ollama unavailable')
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}), \
                patch.object(pipeline, 'generate', return_value='- Hallo [00:00:01]'), \
                patch('sys.stdout', StringIO()) as out:
            self.assertEqual(main(['retry', job['id'][:8]]), 0)
            self.assertIn('reusing-transcript', out.getvalue())
        self.assertEqual(settings_store.get(job['id'])['status'], 'succeeded')

    def test_doctor_tolerates_malformed_model_lists(self):
        from personal_toolkit.__main__ import doctor, model_installed
        self.assertTrue(model_installed([{'model': 'llama3.2:3b'}], 'llama3.2:3b'))
        self.assertFalse(model_installed([{'unexpected': True}, 'skip'], 'llama3.2:3b'))
        payload = json.dumps({'models': [{'unexpected': True}]}).encode()
        with patch('urllib.request.urlopen', return_value=__import__('io').BytesIO(payload)):
            self.assertEqual(doctor(self.settings), 1)

    def test_doctor_reports_path_and_optional_docker_without_failing_core(self):
        from io import StringIO
        from personal_toolkit.__main__ import doctor
        payload = json.dumps({'models': [{'name': self.settings.get('OLLAMA_MODEL')}]}).encode()
        real_which = shutil.which
        real_find = importlib.util.find_spec

        def which(name):
            if name in ('pt', 'docker'):
                return None
            if name in ('yt-dlp', 'ffmpeg'):
                return '/bin/' + name
            return real_which(name)

        def find_spec(name, package=None):
            if name == 'faster_whisper':
                return object()
            return real_find(name, package)

        with patch('urllib.request.urlopen', return_value=__import__('io').BytesIO(payload)), \
                patch('shutil.which', side_effect=which), \
                patch('importlib.util.find_spec', side_effect=find_spec), \
                patch('sys.stdout', StringIO()) as out:
            self.assertEqual(doctor(self.settings), 0)
        text = out.getvalue()
        self.assertIn('NOTE pt is not on PATH', text)
        self.assertIn('export PATH=', text)
        self.assertIn('Docker is not installed', text)
        self.assertIn('Accelerate', text)
        self.assertIn('OK   Ollama model', text)

    def test_doctor_distinguishes_connection_refused(self):
        from io import StringIO
        from personal_toolkit.__main__ import doctor
        refused = urllib.error.URLError(ConnectionRefusedError('refused'))
        with patch('urllib.request.urlopen', side_effect=refused), patch('sys.stdout', StringIO()) as out:
            self.assertEqual(doctor(self.settings), 1)
        self.assertIn('brew services start ollama', out.getvalue())
        self.assertIn('FAIL Ollama reachable', out.getvalue())

    def test_register_path_is_idempotent_and_quotes_spaces(self):
        home = self.root / 'home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'SHELL': '/bin/bash'}
        script = str(ROOT / 'scripts/register-path.sh')
        toolkit = str(self.root / 'toolkit root')
        subprocess.run(['bash', script, toolkit], check=True, env=env)
        subprocess.run(['bash', script, toolkit], check=True, env=env)
        written = [path for path in (home / '.bashrc', home / '.bash_profile', home / '.profile')
                   if path.exists() and 'Personal Toolkit PATH' in path.read_text()]
        self.assertEqual(len(written), 1)
        text = written[0].read_text()
        self.assertEqual(text.count('Personal Toolkit PATH'), 1)
        line = next(row for row in text.splitlines() if row.startswith('export PATH='))
        expanded = subprocess.run(['bash', '-c', line + '\nprintf %s "$PATH"'],
                                  capture_output=True, text=True, check=True,
                                  env={**env, 'PATH': '/bin:/usr/bin'})
        self.assertEqual(expanded.stdout.split(':')[0], str(Path(toolkit) / 'bin'))

    def test_register_path_updates_moved_install(self):
        home = self.root / 'home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'SHELL': '/bin/bash'}
        script = str(ROOT / 'scripts/register-path.sh')
        first = str(self.root / 'old toolkit')
        second = str(self.root / 'new toolkit')
        subprocess.run(['bash', script, first], check=True, env=env)
        subprocess.run(['bash', script, second], check=True, env=env)
        text = (home / '.bashrc').read_text()
        self.assertEqual(text.count('Personal Toolkit PATH'), 1)
        line = next(row for row in text.splitlines() if row.startswith('export PATH='))
        expanded = subprocess.run(['bash', '-c', line + '\nprintf %s "$PATH"'],
                                  capture_output=True, text=True, check=True,
                                  env={**env, 'PATH': '/bin:/usr/bin'})
        self.assertEqual(expanded.stdout.split(':')[0], str(Path(second) / 'bin'))
        self.assertNotIn(str(Path(first) / 'bin'), expanded.stdout.split(':')[0])


if __name__=='__main__':unittest.main()
