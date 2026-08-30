# -*- coding: utf-8 -*-
"""revise_qc.py — 复核修正 QC v2：仅回滚「真坏」修正

规则（先去除空格）：
  insert/delete 块内容含汉字或数字 → 坏（"批井"增字/"价值20万→万"删数字）
  仅字母/符号/空白的变化 → 好（去空格、去 .3 噪声）
"""
import difflib
import glob
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
APPLIED = os.path.join(BASE, 'review', 'ocr_revision_applied.json')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
DIGIT_RE = re.compile(r'[0-9]')


def op_ok(a, b):
    a2 = a.replace(' ', '')
    b2 = b.replace(' ', '')
    sm = difflib.SequenceMatcher(None, a2, b2, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('insert', 'delete'):
            seg = b2[j1:j2] if tag == 'insert' else a2[i1:i2]
            if CJK_RE.search(seg) or DIGIT_RE.search(seg):
                return False
    return True


def main():
    applied = json.load(open(APPLIED, encoding='utf-8'))
    good, bad = [], []
    for x in applied:
        if op_ok(x['from'], x['to']):
            good.append(x)
        else:
            bad.append(x)
    print(f'好修正 {len(good)} | 坏修正 {len(bad)}', flush=True)
    with open(os.path.join(BASE, 'review', 'ocr_revision_good.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(good, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, 'review', 'ocr_revision_bad.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(bad, fh, ensure_ascii=False, indent=1)

    by_ep = {}
    for x in bad:
        by_ep.setdefault(x['ep'], []).append(x)
    n_tot = 0
    for ep, items in by_ep.items():
        fs = [f for f in glob.glob(os.path.join(BASE, 'subtitle_clean', '*.json'))
              if os.path.basename(f).startswith(f'[{ep}]')]
        if not fs:
            continue
        data = json.load(open(fs[0], encoding='utf-8'))
        by_ts = {x['ts']: x['from'] for x in items}
        n = 0
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts and r.get('text') != by_ts[ts]:
                r['text'] = by_ts[ts]
                n += 1
        json.dump(data, open(fs[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep}: 回滚 {n} 条')
        n_tot += n
    print(f'合计回滚 {n_tot}')
    print('审计: review/ocr_revision_bad.json')


if __name__ == '__main__':
    main()
