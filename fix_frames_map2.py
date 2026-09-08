# -*- coding: utf-8 -*-
"""fix_frames_map2.py — 用字符串替换修复(先诊断)"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Web\frames_map.js'
s = open(p, encoding='utf-8').read()
needle = '"jpg"}"'
print('count needle', s.count(needle))
i = s.find('"jpg"}"')
print('first at', i)
if i >= 0:
    seg = s[i - 20:i + 20]
    print(repr(seg))
    print([hex(ord(c)) for c in seg])
s2 = s.replace(needle, '"jpg","')
print('替换后 count', s2.count(needle))
m = re.search(r'=\s*(\{.*\})\s*;', s2, re.S)
try:
    d = json.loads(m.group(1))
    print('JSON OK, 键数', len(d))
    open(p, 'w', encoding='utf-8').write(s2)
    print('已写回')
except Exception as e:
    print('失败', str(e)[:150])
