# -*- coding: utf-8 -*-
"""apply_user_verdicts.py — 应用用户核对页标记

verdict=ok（6 条）：采纳修订（risky 用 to；cand 用 ocr 净化后）
verdict=no（30 条）：保持原文本（原本未应用，无需改动，仅审计）
未标记：保持原样
"""
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
RESULT = os.path.join(BASE, 'review', 'ocr_check', 'ocr_check_result.json')
RISKY = os.path.join(BASE, 'review', 'ocr_final_risky.json')
CANDS = os.path.join(BASE, 'review', 'ocr_revision_candidates.json')

CJK_RE = re.compile(r'[\u4e00-\u9fff]')
PUNCT_RE = re.compile(r'[，。！？、：；“”‘’《》—…\u3000]')
NOISE_WORDS = ('bilibili', 'lipilibili', 'shou', '正版', '正饭', '正服', '脂', '張',
               'Magnetic', 'No.3', '閲覧', '注意', 'RCER')


def denoise(t):
    from opencc import OpenCC
    cc = OpenCC('t2s')
    s = cc.convert(t)
    for w in NOISE_WORDS:
        s = s.replace(w, '')
    s = ''.join(ch for ch in s if CJK_RE.search(ch) or PUNCT_RE.search(ch))
    return re.sub(r'\s+', '', s).strip()


def main():
    result = json.load(open(RESULT, encoding='utf-8'))
    risky = json.load(open(RISKY, encoding='utf-8'))
    cands = json.load(open(CANDS, encoding='utf-8'))
    # id(ep_ts) → (kind, old, new)
    info = {}
    for x in risky:
        info[f"{x['ep']}_{x['ts']}"] = ('risky', x['from'], x['to'])
    for x in cands:
        info.setdefault(f"{x['ep']}_{x['ts']}", ('cand', x['lib'], x['ocr']))

    ok_ids, no_ids = [], []
    for x in result:
        v = x.get('verdict', '')
        if v == 'ok':
            ok_ids.append(x['id'])
        elif v == 'no':
            no_ids.append(x['id'])
    print(f'采纳 {len(ok_ids)} | 拒绝 {len(no_ids)}', flush=True)

    # 应用 ok
    by_ep = {}
    for i in ok_ids:
        if i in info:
            kind, old, new = info[i]
            ep = i.rsplit('_', 1)[0]
            by_ep.setdefault(ep, []).append((i, kind, old, new))
    n_app = 0
    applied_log = []
    for ep, items in by_ep.items():
        fs = [f for f in os.listdir(CLEAN_DIR) if f.startswith(f'[{ep}]') and f.endswith('.json')]
        if not fs:
            continue
        data = json.load(open(os.path.join(CLEAN_DIR, fs[0]), encoding='utf-8'))
        by_ts = {i.split('_', 1)[1]: (kind, old, new) for i, kind, old, new in items}
        n = 0
        for r in data:
            ts = r.get('timestamp')
            if ts in by_ts:
                kind, old, new = by_ts[ts]
                new_final = new if kind == 'risky' else denoise(new)
                if new_final and r.get('text') == old:
                    r['text'] = new_final
                    n += 1
                    applied_log.append({'ep': ep, 'ts': ts, 'from': old[:30],
                                        'to': new_final[:30], 'kind': kind})
        json.dump(data, open(os.path.join(CLEAN_DIR, fs[0]), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        n_app += n
    print(f'已应用 {n_app} 条', flush=True)
    with open(os.path.join(BASE, 'review', 'user_verdict_applied.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(applied_log, fh, ensure_ascii=False, indent=1)
    # no 审计
    no_log = []
    for i in no_ids:
        if i in info:
            kind, old, new = info[i]
            no_log.append({'id': i, 'kind': kind, 'old': old[:40], 'new': new[:40]})
    with open(os.path.join(BASE, 'review', 'user_verdict_rejected.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(no_log, fh, ensure_ascii=False, indent=1)
    print(f'拒绝清单: review/user_verdict_rejected.json（{len(no_log)} 条，库保持原文本）')


if __name__ == '__main__':
    main()
