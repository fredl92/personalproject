"""Small dependency-free gate for configuration and executable source files."""
import ast
import json
import re
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
skip={'.git','.venv','services','data','downloads','transcripts','generated','dist','.cache','__pycache__'}
count=0
for path in root.rglob('*'):
    if not path.is_file() or set(path.relative_to(root).parts)&skip or path.name=='.env':continue
    try:text=path.read_text(encoding='utf-8')
    except UnicodeDecodeError:continue
    for number,line in enumerate(text.splitlines(),1):
        if re.match(r'^(<{7} |={7}$|>{7} )',line):raise SystemExit(f'Conflict marker: {path}:{number}')
    if path.suffix=='.py':ast.parse(text,filename=str(path))
    if path.suffix=='.json':json.loads(text)
    if text.startswith(('#!/bin/bash','#!/usr/bin/env bash')):
        subprocess.run(['bash','-n',str(path)],check=True)
    count+=1
print(f'Checked {count} source/configuration files: syntax and conflict markers OK')
