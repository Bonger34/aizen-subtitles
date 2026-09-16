# -*- coding: utf-8 -*-
"""输出三区域检测汇总表。"""
import json
import os

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
d = json.load(open(os.path.join(B, 'review', 'ext_regions', '_summary.json'), encoding='utf-8'))
lines = ['三区域检测汇总(仅LOW = 字幕带全程无字、只有带下方有白字的时长)', '']
tot = 0.0
for r in d:
    lines.append(f"  {r['ep']}: 仅LOW {len(r['low_only'])}段/{r['low_only_sec']}s | "
                 f"仅TOP {r['top_only_sec']}s")
    tot += r['low_only_sec']
lines.append(f'\n  25 集合计 仅LOW {round(tot, 1)}s')
open(os.path.join(B, 'review', 'ext_regions_summary.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:3]))
print(lines[-1])
