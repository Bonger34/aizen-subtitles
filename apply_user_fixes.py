# -*- coding: utf-8 -*-
"""apply_user_fixes.py — 应用人工复核修正（review/user_fixes.json）到 subtitle_clean/

操作（可回滚）：
  1. 先把 subtitle_clean/ 整体备份到 archive/datasets/subtitle_clean_prereview/
  2. 按 (ep, timestamp) 执行 set_text（替换入库文本）或 remove（从库中删除）
  3. 打印每个动作的影响摘要

用法: python apply_user_fixes.py [--dry-run]   # --dry-run 只预览不落盘
"""
import json
import os
import re
import shutil
import sys

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
FIXES = os.path.join(BASE, 'review', 'user_fixes.json')
BACKUP_DIR = os.path.join(BASE, 'archive', 'datasets', 'subtitle_clean_prereview')

EP_RE = re.compile(r'^\[(P\d{2})\]')


def main():
    dry = '--dry-run' in sys.argv
    with open(FIXES, encoding='utf-8') as f:
        fixes = json.load(f)
    fixes.pop('_meta', None)

    # 1) 备份
    if not dry and not os.path.exists(BACKUP_DIR):
        shutil.copytree(CLEAN_DIR, BACKUP_DIR)
        print(f'备份 -> {BACKUP_DIR}')

    n_set = n_del = 0
    for fname in sorted(os.listdir(CLEAN_DIR)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        if ep not in fixes or not fixes[ep]:
            continue
        path = os.path.join(CLEAN_DIR, fname)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        ep_fixes = fixes[ep]
        changed = False
        for entry in data:
            ts = entry.get('timestamp', '')
            fx = ep_fixes.get(ts)
            if not fx:
                continue
            if fx['action'] == 'set_text':
                old = entry.get('text', '')
                if old != fx['text']:
                    print(f'  {ep} {ts}: [改] "{old}" -> "{fx["text"]}"')
                    if not dry:
                        entry['text'] = fx['text']
                    n_set += 1
                    changed = True
            elif fx['action'] == 'remove':
                print(f'  {ep} {ts}: [删] "{entry.get("text","")}"')
                n_del += 1
                changed = True
                entry['_removed'] = True  # 先标记，统一过滤
        # 过滤删除项后写回
        if changed:
            data = [e for e in data if not e.get('_removed')]
            for e in data:
                e.pop('_removed', None)
            if not dry:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
    print(f'\n完成: set_text={n_set} 条, remove={n_del} 条' + ('（dry-run，未落盘）' if dry else ''))


if __name__ == '__main__':
    main()
