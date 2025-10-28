#!/usr/bin/env python3
import json
from pathlib import Path

# Find most recent lipid profile result
import os
files = [f for f in os.listdir('results') if f.startswith('results_Apollo247_251863663') and f.endswith('.json')]
if not files:
    print("No results found")
    exit(1)

latest = sorted(files)[-1]
print(f"Reading: {latest}\n")

json_file = Path('results') / latest
with open(json_file) as f:
    data = json.load(f)

result = data['results'][0]
if 'raw_stage1' in result:
    raw = result['raw_stage1']

    # Clean markdown
    if raw.startswith('```json'):
        raw = raw[7:]
    elif raw.startswith('```'):
        raw = raw[3:]
    if raw.endswith('```'):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        stage1_data = json.loads(raw)
        params = stage1_data.get('parameters', [])

        print('=== ALL PARAMETERS EXTRACTED BY STAGE 1 ===\n')
        for i, p in enumerate(params, 1):
            name = p.get('name', '')
            value = p.get('value', '')
            unit = p.get('unit', '')
            print(f"{i:2d}. {name:<50} = {value} {unit}")

        print(f"\nTotal: {len(params)} parameters")
    except Exception as e:
        print(f"Failed to parse: {e}")
        print("Raw output:")
        print(raw[:500])
else:
    print('raw_stage1 not found in result')
