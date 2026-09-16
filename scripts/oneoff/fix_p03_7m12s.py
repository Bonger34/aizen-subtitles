# -*- coding: utf-8 -*-
"""fix_p03_7m12s.py — 按人工核定修正 P03 7m12s 并登记帧

人工核定（用户）：
  画面字幕 = 「到了我这一代后扩大了规模」（7m10s~7m18s 之间持续显示）
  库文本   = 「到了我这一代后扩了规模」（差一个"大"字，OCR 漏字）
动作：
  1. 库文本修正为「到了我这一代后扩大了规模」
  2. 将人工核定的显示期帧复制入 docs/frames/P03_7m12s.jpg
     （取 432.0s 帧：位于 7m10s~7m18s 字幕显示期内，画面即该句）
"""
import json
import os
import shutil

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean', '[P03]3 欢迎来到爱染科技.json')
SRC = os.path.join(BASE, 'review', 'p03_7m12s_frames', '7m12s_0.jpg')
DST = os.path.join(BASE, 'docs', 'frames', 'P03_7m12s.jpg')
NEW_TEXT = '到了我这一代后扩大了规模'

d = json.load(open(CLEAN, encoding='utf-8'))
hit = [r for r in d if r.get('timestamp') == '7m12s']
assert hit, '未找到 7m12s 条目'
hit[0]['text'] = NEW_TEXT
json.dump(d, open(CLEAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'库文本已修正: {hit[0]["text"]!r}')

if os.path.exists(SRC):
    shutil.copy(SRC, DST)
    print(f'帧已登记: P03_7m12s.jpg（取自 432.0s，字幕显示期 430~438.8s 内）')
else:
    print(f'警告: 源帧不存在 {SRC}')
