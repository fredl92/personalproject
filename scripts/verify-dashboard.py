"""Exercise the actual nginx dashboard started by CI."""
import json
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip('/')
for asset in ('/', '/app.js', '/style.css', '/config.js'):
    with urllib.request.urlopen(base + asset, timeout=5) as response:
        assert response.status == 200, asset
        body = response.read().decode()
        assert len(body) > 50, asset
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        if asset == '/config.js':
            config = json.loads(body.removeprefix('window.DASHBOARD_CONFIG = ').removesuffix(';\n'))
            assert config['apps']['dashboard']['url'] == base
            assert 'WORKER_API_TOKEN' not in body
for asset in ('/.env', '/missing-file'):
    try:
        urllib.request.urlopen(base + asset, timeout=5)
    except urllib.error.HTTPError as error:
        assert error.code in (403, 404), error.code
    else:
        raise AssertionError('Unexpected public file: ' + asset)
print('Dashboard assets, public settings, headers and missing-file responses verified.')
