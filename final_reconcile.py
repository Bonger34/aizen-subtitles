# -*- coding: utf-8 -*-
"""final_reconcile.py — 复核修正最终裁定

原则（宁缺毋滥）：只保留「纯清洗」修正（to 是 from 去掉空格/ASCII 噪声，
内容零变化 → 100% 安全）；凡涉及内容变化（含替换/增删字）一律转候选，
保持库文本 = 回滚后的原文本。另扫描 P01-P03（无审计记录的可疑字）。
"""
import difflib
import glob
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
APPLIED = os.path.join(BASE, 'review', 'ocr_revision_applied.json')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def pure_clean(a, b):
    """b 是否为 a 的纯清洗（仅移除空格与 ASCII 噪音）"""
    a2 = re.sub(r'[\sA-Za-z0-9.\-_]+', '', a)
    b2 = re.sub(r'[\sA-Za-z0-9.\-_]+', '', b)
    return a2 == b2


def main():
    applied = json.load(open(APPLIED, encoding='utf-8'))
    safe, risky = [], []
    for x in applied:
        if pure_clean(x['from'], x['to']):
            safe.append(x)
        else:
            risky.append(x)
    print(f'安全清洗 {len(safe)} | 内容变化(转候选) {len(risky)}', flush=True)

    # 应用安全清洗（库当前应为 from 状态）
    by_ep = {}
    for x in safe:
        by_ep.setdefault(x['ep'], []).append(x)
    n_app = 0
    for ep, items in by_ep.items():
        fs = [f for f in glob.glob(os.path.join(BASE, 'subtitle_clean', '*.json'))
              if os.path.basename(f).startswith(f'[{ep}]')]
        if not fs:
            continue
        data = json.load(open(fs[0], encoding='utf-8'))
        by_ts = {x['ts']: x['to'] for x in items}
        n = 0
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts:
                r['text'] = by_ts[ts]
                n += 1
        json.dump(data, open(fs[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        n_app += n
    print(f'已应用纯清洗 {n_app} 条', flush=True)

    with open(os.path.join(BASE, 'review', 'ocr_final_safe.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(safe, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, 'review', 'ocr_final_risky.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(risky, fh, ensure_ascii=False, indent=1)

    # P01-P03 无审计记录：扫描可疑字（常见噪声/错字特征）
    BAD_CHARS = ('批井', '备位', '不子', '目快乐', '生自', '正版', '正饭', '正服', '脂版',
                 'MSelect', 'クワトロ', 'TURBINE', 'Lilbi', 'bilibil')
    bad_p = []
    for fname in sorted(glob.glob(os.path.join(BASE, 'subtitle_clean', '*.json'))):
        ep = os.path.basename(fname)[:3]
        if ep not in ('[P0', '[P1', '[P2'):
            continue
        d = json.load(open(fname, encoding='utf-8'))
        for r in d:
            t = r.get('text', '')
            for b in BAD_CHARS:
                if b in t:
                    bad_p.append({'ep': ep, 'ts': r.get('timestamp'), 'text': t[:40],
                                  'flag': b})
                    break
    with open(os.path.join(BASE, 'review', 'ocr_p01p03_needs.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(bad_p, fh, ensure_ascii=False, indent=1)
    print(f'P01-P25 可疑字扫描: {len(bad_p)} 条（见 ocr_p01p03_needs.json）')


if __name__ == '__main__':
    main()
