# -*- coding: utf-8 -*-
"""列出指定集指定时间之后的所有库条目及其【已映射配图】, 供批量视频定位验真。"""
import json
import os
import re
import sys

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
fm = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
MAP = json.loads(fm[fm.index('{'):fm.rindex('}') + 1])

ep = sys.argv[1] if len(sys.argv) > 1 else 'P25'
lo = (int(sys.argv[2]) if len(sys.argv) > 2 else 23) * 60

fn = [f for f in os.listdir(CLEAN) if f.startswith(f'[{ep}]')][0]
rows = []
for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
    t = re.match(r'(\d+)m(\d+)s', e.get('timestamp') or '')
    if not t:
        continue
    sec = int(t.group(1)) * 60 + int(t.group(2))
    if sec < lo:
        continue
    cand = [v for k, v in MAP.items() if k.startswith(f'[{ep}]') and k.endswith('|' + e['timestamp'])]
    rows.append((sec, e['timestamp'], cand[0] if cand else '(无)', e.get('text')))

rows.sort()
lines = [f'{ep} ≥{lo // 60}m 条目 {len(rows)} 条:']
for sec, ts, fr, tx in rows:
    ok = os.path.exists(os.path.join(FR, fr))
    lines.append(f'  {ts:>7s}  {fr:16s} 存在={ok}  {tx}')
txt = '\n'.join(lines)
open(os.path.join(B, 'review', f'mapped_{ep}_tail.txt'), 'w', encoding='utf-8').write(txt)
json.dump([fr for _, _, fr, _ in rows], open(os.path.join(B, 'review', f'mapped_{ep}_tail.json'), 'w',
          encoding='utf-8'), ensure_ascii=False)
print(txt)
