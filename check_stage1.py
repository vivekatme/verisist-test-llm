#!/usr/bin/env python3
import json
from pathlib import Path

json_file = Path('results/batch_20251027_184839/results_Apollo247_251245831_labreport_20251027_185251.json')
with open(json_file) as f:
    data = json.load(f)

# Get Qwen template result
for r in data['results']:
    if 'Qwen' in r.get('model_display', ''):
        if 'raw_stage1' in r:
            print('=== ALL PARAMETERS EXTRACTED BY STAGE 1 ===\n')
            raw = r['raw_stage1']

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

                for i, p in enumerate(params, 1):
                    name = p.get('name', '')
                    value = p.get('value', '')
                    unit = p.get('unit', '')
                    print(f"{i:2d}. {name:<50} = {value} {unit}")

                print(f"\nTotal: {len(params)} parameters")
            except Exception as e:
                print(f'Failed to parse: {e}')
        else:
            print('raw_stage1 not saved in JSON')
        break