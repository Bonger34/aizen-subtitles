# -*- coding: utf-8 -*-
"""验证新入库的带外台词: 在 subtitle_db 中能搜到, 且配图帧存在。"""
import gzip
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
recs = json.loads(gzip.decompress(open(os.path.join(B, 'web', 'subtitle_db'), 'rb').read()).decode('utf-8'))
MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                           open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read(),
                           re.S).group(1))
print('subtitle_db 记录数:', len(recs), '| frames_map 键数:', len(MAP))
for q in ['明天我仍然会继续制作T恤', '这个蓝色表示的就是地球', '打败怪兽时的必杀技超帅',
          '奥特战士的爸爸哦', '没关系的', '制作恤也是为了隐居']:
    hits = [r for r in recs if q in r['x']]
    if not hits:
        print(f'  「{q}」 无')
        continue
    for r in hits:
        f = MAP.get(f"{r['f']}|{r['t']}")
        ok = os.path.exists(os.path.join(B, 'docs', 'frames', f)) if f else None
        print(f"  「{q}」 {r['f']} {r['t']}  x={r['x'][:34]}  -> {f} 帧存在={ok}")
