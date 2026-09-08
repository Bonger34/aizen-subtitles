# -*- coding: utf-8 -*-
"""apply_fill_p01_fix.py — 删除库 P01 15m24s(好痛)错误条目及其 frames_map 键"""
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')


def main():
    f = [x for x in os.listdir(CLEAN) if x.startswith('[P01]') and x.endswith('.json')][0]
    path = os.path.join(CLEAN, f)
    arr = json.load(open(path, encoding='utf-8'))
    before = len(arr)
    arr2 = [e for e in arr if not (e['timestamp'] == '15m24s' and e['text'] == '好痛')]
    print(f'库条目: {before} -> {len(arr2)}')
    json.dump(arr2, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    src = open(FMAP, encoding='utf-8').read()
    # 删除键 "[P01]1 罗布奥特曼登场|15m24s"
    key = '[P01]1 罗布奥特曼登场|15m24s'
    if f'"{key}"' in src:
        src = re.sub(r'"[^"]*\|15m24s": "[^"]*",?\n?', '', src, count=1)
        # 可能在同一行内, 用更稳的方式: 正则删除该键值对(含可能的前导逗号)
        src2 = re.sub(r'(,?)"' + re.escape(key) + r'": "[^"]*"', '', src, count=1)
        if src2 != src:
            src = src2
        open(FMAP, 'w', encoding='utf-8').write(src)
        print('frames_map 键已删除')
    else:
        print('frames_map 无该键')


if __name__ == '__main__':
    main()
