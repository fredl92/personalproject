import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from personal_toolkit.__main__ import main
from personal_toolkit.config import SECRET_KEYS, Settings, initialize
from personal_toolkit.dashboard import configuration, render

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dashboard test ")
        self.root = Path(self.tmp.name).resolve()
        (self.root / '.env.example').write_text((ROOT / '.env.example').read_text())
        initialize(self.root)
        self.settings = Settings(self.root, environ={})

    def tearDown(self):
        self.tmp.cleanup()

    def test_generated_public_config_preserves_custom_urls_but_excludes_secrets(self):
        self.settings.values.update(DASHBOARD_PORT='18080', N8N_PORT='15678',
                                    OLLAMA_URL='http://127.0.0.1:11435',
                                    PLAUSIBLE_BASE_URL='http://localhost:18000')
        self.assertEqual(render(self.settings), 'http://localhost:18080')
        path = self.root / 'dashboard/config.js'
        text = path.read_text()
        data = json.loads(text.removeprefix('window.DASHBOARD_CONFIG = ').removesuffix(';\n'))
        self.assertEqual(data['apps']['n8n']['healthUrl'], 'http://localhost:18080/health/n8n')
        self.assertEqual(data['apps']['n8n']['healthKind'], 'n8n')
        self.assertEqual(data['apps']['ollama']['healthUrl'], 'http://localhost:18080/health/ollama')
        self.assertEqual(data['apps']['ollama']['url'], 'http://127.0.0.1:11435')
        self.assertEqual(data['apps']['plausible']['healthUrl'], 'http://localhost:18080/health/plausible')
        self.assertEqual(data['models']['ollama'], self.settings.get('OLLAMA_MODEL'))
        self.assertEqual(data['models']['whisper'], 'base')
        self.assertEqual(data['models']['whisperLanguage'], 'nl')
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        for key in SECRET_KEYS:
            self.assertNotIn(key, text)
            self.assertNotIn(self.settings.get(key), text)
        proxy = (self.root / 'dashboard/status-proxy.conf').read_text()
        self.assertIn('location = /health/ollama', proxy)
        self.assertIn('proxy_pass http://host.docker.internal:11435/api/tags;', proxy)
        self.assertIn('proxy_pass http://host.docker.internal:15678/healthz;', proxy)
        self.assertIn('limit_except GET HEAD', proxy)
        for key in SECRET_KEYS:
            self.assertNotIn(self.settings.get(key), proxy)
        self.assertNotIn('0.0.0.0', proxy)

    def test_renderer_treats_env_as_data_and_rejects_injected_port(self):
        marker = self.root / 'executed'
        with (self.root / '.env').open('a') as stream:
            stream.write('\nDASHBOARD_PORT=$(touch "' + str(marker) + '")\n')
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}):
            self.assertEqual(main(['dashboard-config']), 1)
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / 'dashboard/config.js').exists())

    def test_invalid_ports_hosts_and_credential_urls_leave_existing_config_unchanged(self):
        render(self.settings)
        path = self.root / 'dashboard/config.js'
        proxy_path = self.root / 'dashboard/status-proxy.conf'
        before = path.read_text()
        proxy_before = proxy_path.read_text()
        for key, value in [('DASHBOARD_PORT', '0'), ('N8N_PORT', '65536'), ('FOOOCUS_PORT', 'x'),
                           ('DASHBOARD_HOST', '0.0.0.0'), ('DASHBOARD_HOST', '\";alert(1);//'),
                           ('OLLAMA_URL', 'http://user:secret@localhost:11434'),
                           ('OLLAMA_URL', 'https://example.org'),
                           ('PLAUSIBLE_BASE_URL', 'https://example.org/?token=secret'),
                           ('OLLAMA_MODEL', '../../etc/passwd'),
                           ('WHISPER_LANGUAGE', 'nl;alert(1)')]:
            settings = Settings(self.root, environ={})
            settings.values[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                render(settings)
            self.assertEqual(path.read_text(), before)
            self.assertEqual(proxy_path.read_text(), proxy_before)

    def test_dashboard_starts_only_its_profile_and_respects_no_open(self):
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}), \
                patch('personal_toolkit.__main__.compose') as compose, patch('webbrowser.open') as browser:
            self.assertEqual(main(['dashboard', '--no-open']), 0)
        args = compose.call_args.args[1]
        self.assertEqual(args[:3], ['--profile', 'dashboard', 'up'])
        self.assertEqual(compose.call_count, 1)
        browser.assert_not_called()
        self.assertTrue((self.root / 'dashboard/config.js').exists())

    def test_dashboard_failure_does_not_open_browser(self):
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}), \
                patch('personal_toolkit.__main__.compose', side_effect=subprocess.CalledProcessError(1, 'docker')), \
                patch('webbrowser.open') as browser:
            self.assertEqual(main(['dashboard']), 1)
        browser.assert_not_called()

    def test_services_dashboard_renders_config_before_start(self):
        def compose(settings, args):
            self.assertTrue((self.root / 'dashboard/config.js').exists())
            self.assertTrue((self.root / 'dashboard/status-proxy.conf').exists())
            self.assertEqual(args[:3], ['--profile', 'dashboard', 'up'])
        with patch.dict(os.environ, {'PERSONAL_TOOLKIT_HOME': str(self.root)}), \
                patch('personal_toolkit.__main__.compose', side_effect=compose) as call:
            self.assertEqual(main(['services', 'up', 'dashboard']), 0)
        self.assertEqual(call.call_count, 1)

    def test_installer_includes_dashboard_but_preserves_local_generated_settings(self):
        source = self.root / 'source'
        dashboard = source / 'dashboard'
        dashboard.mkdir(parents=True)
        (dashboard / 'index.html').write_text('dashboard code')
        (dashboard / 'status-proxy.stub.conf').write_text('# stub')
        (dashboard / 'config.js').write_text('source local settings')
        (dashboard / 'status-proxy.conf').write_text('source generated proxy')
        destination = self.root / 'installed'
        (destination / 'dashboard').mkdir(parents=True)
        (destination / 'dashboard/config.js').write_text('user local settings')
        (destination / 'dashboard/status-proxy.conf').write_text('user generated proxy')
        script = ROOT / 'scripts/copy-toolkit.sh'
        subprocess.run(['bash', str(script), str(source), str(destination)], check=True)
        self.assertEqual((destination / 'dashboard/index.html').read_text(), 'dashboard code')
        self.assertEqual((destination / 'dashboard/status-proxy.stub.conf').read_text(), '# stub')
        self.assertEqual((destination / 'dashboard/config.js').read_text(), 'user local settings')
        self.assertEqual((destination / 'dashboard/status-proxy.conf').read_text(), 'user generated proxy')
        bundle = self.root / 'bundle'
        subprocess.run(['bash', str(script), str(source), str(bundle)], check=True)
        self.assertTrue((bundle / 'dashboard/index.html').exists())
        self.assertTrue((bundle / 'dashboard/status-proxy.stub.conf').exists())
        self.assertFalse((bundle / 'dashboard/config.js').exists())
        self.assertFalse((bundle / 'dashboard/status-proxy.conf').exists())

    def test_remote_plausible_is_not_proxied(self):
        from personal_toolkit.dashboard import configuration, attach_same_origin_health, status_proxy_conf
        self.settings.values['PLAUSIBLE_BASE_URL'] = 'https://stats.example.org'
        config = attach_same_origin_health(configuration(self.settings))
        self.assertEqual(config['apps']['plausible']['url'], 'https://stats.example.org')
        self.assertNotIn('healthUrl', config['apps']['plausible'])
        self.assertNotIn('location = /health/plausible', status_proxy_conf(config))

    def test_compose_pins_worker_cache_and_host_gateway(self):
        text = (ROOT / 'docker-compose.yml').read_text()
        self.assertIn('WHISPER_CACHE_DIR: /cache', text)
        self.assertIn('JOBS_DIR: /data/jobs', text)
        self.assertIn('host.docker.internal:host-gateway', text)
        dockerfile = (ROOT / 'docker/worker.Dockerfile').read_text()
        self.assertIn('WHISPER_CACHE_DIR=/cache', dockerfile)

    def test_plausible_setup_binds_localhost_and_keeps_secrets_out_of_output(self):
        dest = self.root / 'plausible'
        dest.mkdir()
        env = {**os.environ, 'PERSONAL_TOOLKIT_HOME': str(self.root),
               'PYTHONPATH': str(ROOT / 'src')}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/configure-plausible.py'), str(dest)],
                                capture_output=True, text=True, env=env, check=True)
        self.assertIn('127.0.0.1:8000', (dest / 'compose.override.yml').read_text())
        self.assertIn('SECRET_KEY_BASE=', (dest / '.env').read_text())
        self.assertNotIn(self.settings.get('PLAUSIBLE_SECRET_KEY_BASE'), result.stdout)
        self.assertNotIn(self.settings.get('PLAUSIBLE_SECRET_KEY_BASE'), result.stderr)


if __name__ == '__main__':
    unittest.main()
