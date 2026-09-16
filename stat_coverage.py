# -*- coding: utf-8 -*-
"""stat_coverage.py — 最终覆盖率统计（无帧图台词清单）"""
import glob
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FMAP_JS = os.path.join(BASE, 'docs', 'frames_map.js')

m = re.search(r'=\s*(\{.*?\})\s*;', open(FMAP_JS, encoding='utf-8').read(), re.S)
FMAP = json.loads(m.group(1))

total = miss = 0
miss_list = []
for f in sorted(glob.glob(os.path.join(BASE, 'subtitle_clean', '*.json'))):
    name = os.path.basename(f)[:-5]
    d = json.load(open(f, encoding='utf-8'))
    total += len(d)
    for r in d:
        key = name + '|' + r.get('timestamp', '')
        if key not in FMAP:
            miss += 1
            miss_list.append({'f': name, 't': r.get('timestamp', ''), 'x': r.get('text', '')[:30]})

print(f'字幕 {total} 条 | 有帧 {total - miss} 条 | 无帧 {miss} 条 | 覆盖率 {(total - miss) / total * 100:.1f}%')
for it in miss_list[:10]:
    print('  无帧:', it)
with open(os.path.join(BASE, 'review', 'coverage_final.json'), 'w', encoding='utf-8') as fh:
    json.dump({'total': total, 'miss': miss, 'miss_list': miss_list}, fh,
              ensure_ascii=False, indent=1)
