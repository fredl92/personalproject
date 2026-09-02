const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { execFileSync } = require('node:child_process');
const { checkStatus, safeUrl, CLI_COMMANDS, createCommand } = require('../dashboard/app.js');

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

function commandArguments(command) {
  // Exercise actual shell parsing, with a harmless stand-in for the local CLI.
  const output = execFileSync('bash', ['-c', 'pt() { printf "%s\\0" "$@"; };\n' + command], { encoding: 'utf8' });
  return output.split('\0').slice(0, -1);
}

test('questions retain quotes, newlines and shell metacharacters as literal text', () => {
  for (const prompt of ["Leg Fré's budget uit", '$(printf INJECTED) `printf BAD` ; echo BAD',
                        '-help mij met mijn tekst', 'Eerste vraag\nTweede vraag "€100"']) {
    assert.deepEqual(commandArguments(createCommand('ask', prompt)), ['ask', '--', prompt]);
  }
});

test('video links retain query parameters and audio selection', () => {
  const url = 'https://www.youtube.com/watch?v=test&a=1#t=10';
  assert.deepEqual(commandArguments(createCommand('download', url, { audio: true })), ['download', url, '--audio']);
  assert.deepEqual(commandArguments(createCommand('pipeline', url)), ['pipeline', url]);
});

test('recording paths with spaces and apostrophes stay one argument', () => {
  const path = "/Users/Fré/Opnames/Vaders 'budget' $(printf BAD).m4a";
  assert.deepEqual(commandArguments(createCommand('transcribe', path)), ['transcribe', path]);
  assert.deepEqual(commandArguments(createCommand('pipeline', path, { source: 'file' })), ['pipeline', path]);
});

test('home-relative paths expand without evaluating their contents', () => {
  const path = "~/Opnames/Fré's $(printf BAD).wav";
  assert.deepEqual(commandArguments(createCommand('transcribe', path)), ['transcribe', process.env.HOME + path.slice(1)]);
});

test('invalid task input produces actionable errors instead of commands', () => {
  for (const [task, value, options] of [
    ['ask', '   '], ['constructor', 'text'], ['download', 'javascript:alert(1)'],
    ['download', 'http://user:secret@example.org/video'], ['download', 'not a link'],
    ['download', 'https://example.org/\nvideo'], ['transcribe', 'opname.wav'],
    ['transcribe', '/'], ['transcribe', '/tmp/a\0b'], ['pipeline', '/tmp/audio.wav', { source: 'other' }],
  ]) assert.throws(() => createCommand(task, value, options));
});
