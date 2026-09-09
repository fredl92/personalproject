"""Assert actual inference wrote usable files; deliberately no quality claim."""
import json
from pathlib import Path

jobs = []
for path in Path('data/jobs').glob('*/job.json'):
    try:
        jobs.append(json.loads(path.read_text()))
    except (OSError, UnicodeError, json.JSONDecodeError):
        continue
jobs.sort(key=lambda job: job.get('updated_at') or '', reverse=True)
assert jobs, 'No pipeline job was recorded'
job = next((item for item in jobs if item.get('status') == 'succeeded'), None)
assert job, jobs
folder = Path('data/jobs') / job['id']
assert len((folder / 'transcript.txt').read_text().strip()) > 20, 'No useful transcript'
assert len((folder / 'summary.md').read_text().strip()) > 30, 'No useful summary'
assert json.loads((folder / 'transcript.json').read_text())['segments'], 'No timestamps'
print('Real-model smoke test produced transcript, segment timestamps and summary.')
