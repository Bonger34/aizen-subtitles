# -*- coding: utf-8 -*-
"""以字幕库为唯一真源重建 frames_map.js(不含 clean_map.py 里的一次性 P02 修改)。

每条库条目 -> 优先沿用原映射帧名(文件仍存在), 否则用 {集}_{时刻}.jpg, 再否则记为缺帧。
"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
FMAP = os.path.join(B, 'docs', 'frames_map.js')

src = open(FMAP, encoding='utf-8').read()
orig = json.loads(re.search(r'=\s*(\{.*\})\s*;', src, re.S).group(1))

new, missing, reused = {}, [], 0
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    title = fn[:-5]
    ep = fn[1:4]
    for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
        key = f'{title}|{e["timestamp"]}'
        fname = orig.get(key)
        if fname and os.path.exists(os.path.join(FR, fname)):
            new[key] = fname
            reused += 1
            continue
        cand = f'{ep}_{e["timestamp"]}.jpg'
        if os.path.exists(os.path.join(FR, cand)):
            new[key] = cand
            continue
        missing.append(key)

open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(new, ensure_ascii=False) + ';')
print(f'映射重建: {len(orig)} -> {len(new)} 键(沿用原帧名 {reused}), 缺帧 {len(missing)}')
for k in missing[:20]:
    print('  缺帧', k)
