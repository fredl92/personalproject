const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { checkStatus, safeUrl, CLI_COMMANDS } = require('../dashboard/app.js');

test('HTTP success is reachable, without claiming app health', async () => {
  const result = await checkStatus('http://localhost:5678/healthz', async () => ({ status: 200, ok: true, type: 'cors' }));
  assert.equal(result.state, 'online');
  assert.equal(result.label, 'Bereikbaar');
});

test('real HTTP 500 is never online', async () => {
  const server = http.createServer((req, res) => { res.writeHead(500); res.end('unavailable'); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const result = await checkStatus(`http://127.0.0.1:${server.address().port}/`);
    assert.equal(result.state, 'error');
    assert.equal(result.label, 'HTTP 500');
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});

test('opaque replies cannot confirm a successful HTTP response', async () => {
  for (const type of ['opaque', 'opaqueredirect']) {
    const result = await checkStatus('http://localhost:5678', async () => ({ type, status: 0, ok: false }));
    assert.equal(result.state, 'unknown');
  }
});

test('network or CORS rejection is unconfirmed rather than a false offline claim', async () => {
  const result = await checkStatus('http://localhost:5678', async () => { throw new TypeError('Failed to fetch'); });
  assert.equal(result.state, 'unknown');
  assert.equal(result.label, 'Niet bevestigd');
});

test('timeout aborts the request and remains unconfirmed', async () => {
  let aborted = false;
  const fetcher = (_, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => { aborted = true; reject(new Error('abort')); }, { once: true });
  });
  const result = await checkStatus('http://localhost:5678', fetcher, 5);
  assert.equal(aborted, true);
  assert.equal(result.state, 'unknown');
});

test('links reject script URLs and credentials', () => {
  for (const value of ['javascript:alert(1)', 'file:///tmp/file', 'http://user:secret@localhost', 'https://example.org/?key=secret']) {
    assert.throws(() => safeUrl(value));
  }
  assert.equal(safeUrl('http://localhost:18080'), 'http://localhost:18080/');
});

test('copyable commands retain placeholders and quoted prompts', () => {
  assert.ok(CLI_COMMANDS.some(c => c.cmd === 'pt download <url>'));
  assert.ok(CLI_COMMANDS.some(c => c.cmd === 'pt ask "jouw vraag"'));
  assert.ok(CLI_COMMANDS.some(c => c.cmd === 'pt services up automation'));
});
