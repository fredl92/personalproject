"""Assert actual inference wrote usable files; deliberately no quality claim."""
import json
from pathlib import Path
jobs=[json.loads(p.read_text()) for p in Path('data/jobs').glob('*/job.json')]
assert jobs, 'No pipeline job was recorded'
job=jobs[-1]
assert job['status']=='succeeded', job
folder=Path('data/jobs')/job['id']
assert len((folder/'transcript.txt').read_text().strip())>20, 'No useful transcript'
assert len((folder/'summary.md').read_text().strip())>30, 'No useful summary'
assert json.loads((folder/'transcript.json').read_text())['segments'], 'No timestamps'
print('Real-model smoke test produced transcript, segment timestamps and summary.')
