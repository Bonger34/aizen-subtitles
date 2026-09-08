# -*- coding: utf-8 -*-
"""fix_frames_map.py — 修复 frames_map.js 追加时缺失的逗号"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Web\frames_map.js'
s = open(p, encoding='utf-8').read()
# 坏模式: ..."P01_x.jpg"}"[P02]... (值右引号 + } + 下一键的左引号, 缺逗号)
pat = re.compile(r'("jpg")\}(")')
n = len(pat.findall(s))
s2 = pat.sub(r'\1,\2', s)
print('替换次数', n)
m = re.search(r'=\s*(\{.*\})\s*;', s2, re.S)
try:
    d = json.loads(m.group(1))
    print('修复后 JSON OK, 键数', len(d))
    open(p, 'w', encoding='utf-8').write(s2)
    print('已写回')
except Exception as e:
    print('仍失败', str(e)[:200])
    # 打印失败点上下文
    i = 210500
    print(repr(s2[i-60:i+60]))
