import json
import os
import subprocess
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
        self.assertEqual(data['apps']['n8n']['healthUrl'], 'http://localhost:15678/healthz')
        self.assertEqual(data['apps']['ollama']['healthUrl'], 'http://127.0.0.1:11435/api/tags')
        self.assertEqual(data['apps']['plausible']['url'], 'http://localhost:18000')
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        for key in SECRET_KEYS:
            self.assertNotIn(key, text)
            self.assertNotIn(self.settings.get(key), text)

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
        before = path.read_text()
        for key, value in [('DASHBOARD_PORT', '0'), ('N8N_PORT', '65536'), ('FOOOCUS_PORT', 'x'),
                           ('DASHBOARD_HOST', '0.0.0.0'), ('DASHBOARD_HOST', '\";alert(1);//'),
                           ('OLLAMA_URL', 'http://user:secret@localhost:11434'),
                           ('PLAUSIBLE_BASE_URL', 'https://example.org/?token=secret')]:
            settings = Settings(self.root, environ={})
            settings.values[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                render(settings)
            self.assertEqual(path.read_text(), before)

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
        (dashboard / 'config.js').write_text('source local settings')
        destination = self.root / 'installed'
        (destination / 'dashboard').mkdir(parents=True)
        (destination / 'dashboard/config.js').write_text('user local settings')
        script = ROOT / 'scripts/copy-toolkit.sh'
        subprocess.run(['bash', str(script), str(source), str(destination)], check=True)
        self.assertEqual((destination / 'dashboard/index.html').read_text(), 'dashboard code')
        self.assertEqual((destination / 'dashboard/config.js').read_text(), 'user local settings')
        bundle = self.root / 'bundle'
        subprocess.run(['bash', str(script), str(source), str(bundle)], check=True)
        self.assertTrue((bundle / 'dashboard/index.html').exists())
        self.assertFalse((bundle / 'dashboard/config.js').exists())


if __name__ == '__main__':
    unittest.main()
