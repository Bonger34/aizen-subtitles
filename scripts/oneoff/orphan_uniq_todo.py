# -*- coding: utf-8 -*-
"""对"独有内容"的孤儿帧补齐 OCR(未在 A/B 抽样中出现的), 并给出最终定性。"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
hash_txt = open(os.path.join(B, 'review', 'orphan_hash.txt'), encoding='utf-8').read()
uniq = re.findall(r'^  (P\d+_\S+\.jpg)$', hash_txt, re.M)
print('独有内容孤儿帧', len(uniq))

ocr = json.load(open(os.path.join(B, 'review', 'orphan_ocr.json'), encoding='utf-8'))
done = {x['f']: x for x in ocr['A'] + ocr['B']}
todo = [f for f in uniq if f not in done]
print('已 OCR', len(uniq) - len(todo), '待补', len(todo))
json.dump(todo, open(os.path.join(B, 'review', 'orphan_uniq_todo.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

lines = ['独有内容孤儿帧分类:']
for f in uniq:
    x = done.get(f)
    if x:
        lines.append(f"  {f:18s} [{x.get('verdict', '未判')}] ocr=[{x['ocr']}]")
    else:
        lines.append(f'  {f:18s} [待补 OCR]')
open(os.path.join(B, 'review', 'orphan_uniq_list.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:5]))
