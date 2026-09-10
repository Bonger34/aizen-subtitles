# -*- coding: utf-8 -*-
"""cross_check.py — 交叉验证 0.17s 与 0.35s 扫描的一致性"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
REVIEW = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob\review'
TARGETS = ['晚安', '可恶', '跳踢', '明白了', '朝阳', '后来', '男人嘛']

for ep in ['P01', 'P13']:
    dp = os.path.join(REVIEW, f'deep_cont_{ep}.json')
    sp = os.path.join(REVIEW, f'dense_cont_{ep}.json')
    if not os.path.exists(dp):
        print(f'{ep}: 0.17s 数据未生成')
        continue
    deep = json.load(open(dp, encoding='utf-8'))
    dense = json.load(open(sp, encoding='utf-8'))
    dt = {s['text'] for s in deep['seqs']}
    st = {s['text'] for s in dense['seqs']}
    print(f'== {ep}: 0.35s 唯一句 {len(st)}, 0.17s 唯一句 {len(dt)} ==')
    for t in TARGETS:
        if t in st or t in dt:
            print(f'   {t}: 0.35s={"有" if t in st else "无"}, 0.17s={"有" if t in dt else "无"}')
    missing = st - dt
    print(f'   0.35s 有而 0.17s 无: {len(missing)} 条 -> {list(missing)[:8]}')
