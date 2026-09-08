# -*- coding: utf-8 -*-
"""fix_frames_map3.py — 修复 frames_map.js: .jpg"}"  ->  .jpg"," """
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Web\frames_map.js'
s = open(p, encoding='utf-8').read()
needle = '.jpg"}"'
print('出现次数', s.count(needle))
s2 = s.replace(needle, '.jpg","')
m = re.search(r'=\s*(\{.*\})\s*;', s2, re.S)
try:
    d = json.loads(m.group(1))
    print('JSON OK, 键数', len(d))
    open(p, 'w', encoding='utf-8').write(s2)
    print('已写回')
except Exception as e:
    print('失败', str(e)[:200])
    i = 210500
    print(repr(s2[i-80:i+80]))
