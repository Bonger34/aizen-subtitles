# -*- coding: utf-8 -*-
"""diag_map.py — 逐字符诊断 frames_map 坏点"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\Web\frames_map.js'
s = open(p, encoding='utf-8').read()
for i in range(210480, 210530):
    c = s[i]
    print(i, repr(c), hex(ord(c)))
