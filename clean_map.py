# -*- coding: utf-8 -*-
"""
clean_map.py — 以库为基准重建 frames_map.js
1. 删除 P02 4m50s 重复条目与帧
2. 每条库条目 → 优先沿用原映射帧名(文件存在), 否则用 {ep}_{ts}.jpg(存在), 否则记为缺帧
3. 丢弃孤儿键
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
FRAMES = os.path.join(BASE, 'Web', 'frames')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')

# 1. 删除 P02 4m50s 重复条目
p02 = [x for x in os.listdir(CLEAN) if x.startswith('[P02]') and x.endswith('.json')][0]
p02p = os.path.join(CLEAN, p02)
arr = json.load(open(p02p, encoding='utf-8'))
before = len(arr)
arr = [e for e in arr if not (e['timestamp'] == '4m50s' and e['text'] == '好看吧')]
json.dump(arr, open(p02p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'P02 库: {before} -> {len(arr)}')
for f in ['P02_4m50s.jpg']:
    fp = os.path.join(FRAMES, f)
    if os.path.exists(fp):
        os.remove(fp)
        print('删除帧', f)

# 2. 重建映射
src = open(FMAP, encoding='utf-8').read()
m = re.search(r'=\s*(\{.*\})\s*;', src, re.S)
orig = json.loads(m.group(1))
new = {}
missing = []
for fn in sorted(os.listdir(CLEAN)):
    if not fn.endswith('.json'):
        continue
    title = fn[:-5]
    ep = fn[1:4]
    data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
    for e in data:
        key = f'{title}|{e["timestamp"]}'
        fname = orig.get(key)
        if fname and os.path.exists(os.path.join(FRAMES, fname)):
            new[key] = fname
            continue
        cand = f'{ep}_{e["timestamp"]}.jpg'
        if os.path.exists(os.path.join(FRAMES, cand)):
            new[key] = cand
            continue
        missing.append(key)
body = 'window.FRAMES_MAP = ' + json.dumps(new, ensure_ascii=False) + ';'
open(FMAP, 'w', encoding='utf-8').write(body)
print(f'映射重建: {len(orig)} -> {len(new)} 键, 缺帧 {len(missing)}')
for k in missing[:20]:
    print('  缺帧', k)
