# -*- coding: utf-8 -*-
"""restore_misaligned.py — 恢复 4 条被时间错位"误删"的真实台词

用户复核发现部分条目时间戳偏了 1-3 秒，其中 4 条是真实台词且库中无重复，
经用户确认恢复：修正 ts 后加回 subtitle_clean/（similarity 取自修正前快照）。
"""
import json, os, re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
BACKUP_DIR = os.path.join(BASE, 'archive', 'datasets', 'subtitle_clean_prereview')
FIXES = os.path.join(BASE, 'review', 'user_fixes.json')

# 待恢复清单：(ep, 新ts, 文本) —— 新 ts 为 OCR 探查校准后的字幕真实时刻
RESTORE = [
    ('P11', '11m15s', '你先等一下'),
    ('P17', '17m56s', '将军大人'),
    ('P22', '9m17s', '天亮咯'),
    ('P23', '14m42s', '那个方向不就是'),
]

def sec(s):
    m = re.match(r'(\d+)m(\d+)s', s)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0

def clean_of(ep):
    for fname in os.listdir(CLEAN_DIR):
        if fname.startswith(f'[{ep}]') and fname.endswith('.json'):
            return os.path.join(CLEAN_DIR, fname)
    return None

def backup_text_sim(ep, old_ts):
    """从修正前快照取被删条目的文本与 similarity"""
    for fname in os.listdir(BACKUP_DIR):
        if fname.startswith(f'[{ep}]') and fname.endswith('.json'):
            for r in json.load(open(os.path.join(BACKUP_DIR, fname), encoding='utf-8')):
                if r.get('timestamp') == old_ts:
                    return r.get('text', ''), r.get('similarity', 0.0)
    return '', 0.0

def main():
    # 用户修正清单里的原 ts（remove 项）→ 用于取快照数据
    with open(FIXES, encoding='utf-8') as f:
        fixes = json.load(f)
    for ep, new_ts, text in RESTORE:
        old_ts = None
        for ts, fx in fixes.get(ep, {}).items():
            if fx['action'] == 'remove':
                old_ts = ts
        path = clean_of(ep)
        if path is None:
            print(f'{ep}: 未找到 json，跳过'); continue
        data = json.load(open(path, encoding='utf-8'))
        # 防重复：同 ts 视为重复；同文本且 ts 相差 ≤3s 视为重复（与流水线全局去重规则一致）
        if any(r.get('timestamp') == new_ts for r in data):
            print(f'{ep} {new_ts}: 已存在同 ts，跳过'); continue
        if any(r.get('text', '').strip() == text and abs(sec(r.get('timestamp', '')) - sec(new_ts)) <= 3
               for r in data):
            print(f'{ep} {new_ts}: 3s 内已有同文本，跳过'); continue
        old_text, sim = backup_text_sim(ep, old_ts) if old_ts else ('', 0.0)
        data.append({'timestamp': new_ts, 'similarity': sim, 'text': text})
        data.sort(key=lambda r: sec(r.get('timestamp', '')))
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep} {new_ts}: 恢复「{text}」(sim={sim:.3f})')

if __name__ == '__main__':
    main()
