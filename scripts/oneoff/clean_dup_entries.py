# -*- coding: utf-8 -*-
"""
clean_dup_entries.py — 清理全库"同集+同时间戳+同文本"的完全重复条目

判定标准(与之前核查一致):
  同一文件内 key=(timestamp, text) 出现 ≥2 次 → 保留第一条(idx 小),删除其余。
这样的条目是早期字幕切片/合并时同一条记录被写入两遍,搜索会返回重复结果。
"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')

total_del = 0
for f in sorted(os.listdir(CLEAN_DIR)):
    if not f.endswith('.json'):
        continue
    p = os.path.join(CLEAN_DIR, f)
    arr = json.load(open(p, encoding='utf-8'))

    # 分组: (timestamp, text) -> 索引列表
    groups = {}
    for i, e in enumerate(arr):
        key = (e.get('timestamp') or '').strip(), e.get('text') or ''
        if not key[0] or not key[1]:
            continue
        groups.setdefault(key, []).append(i)

    # 删除每组除第一条外的所有条目(倒序删避免索引偏移)
    del_idx = []
    for key, idxs in groups.items():
        if len(idxs) > 1:
            del_idx.extend(idxs[1:])   # 保留 idxs[0]
            print(f'  删除 {f[:-5]} @{key[0]}  ["{key[1]}"]  idx={idxs[1:]} (保留 idx={idxs[0]})')

    if del_idx:
        del_idx_set = set(del_idx)
        new_arr = [e for i, e in enumerate(arr) if i not in del_idx_set]
        json.dump(new_arr, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total_del += len(del_idx)
        print(f'  {f[:-5]}: {len(arr)} → {len(new_arr)} 条 (删 {len(del_idx)})')

print(f'\n共删除 {total_del} 条重复记录')
print('输出: subtitle_clean/*.json (已更新)')
