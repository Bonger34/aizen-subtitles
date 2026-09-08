# -*- coding: utf-8 -*-
"""
cont_gap.py — 库覆盖率差距分析(用 cont_*.json 的 seqs 全量文本)
对每集: 区间文本序列 → 去重 → 与库 ±8s 匹配(字符重叠≥0.6 视为已覆盖)
输出: 每集已覆盖/未覆盖句数 + review/cont_gap.json(未覆盖清单)
"""
import glob
import json
import os
import re
import sys

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
REVIEW = os.path.join(BASE, 'review')


def norm(s):
    return re.sub(r'[，。！？、；：“”‘’\s]', '', s)


def overlap(a, b):
    if not a or not b:
        return 0
    return sum(1 for c in a if c in b) / len(a)


def main():
    lib_by_ep = {}
    for f in os.listdir(CLEAN):
        if f.endswith('.json'):
            ep = f[1:4]
            arr = json.load(open(os.path.join(CLEAN, f), encoding='utf-8'))
            lib_by_ep[ep] = []
            for e in arr:
                ts = e.get('timestamp') or ''
                m = re.match(r'(\d+)m(\d+)s', ts)
                if m:
                    lib_by_ep[ep].append((int(m.group(1)) * 60 + int(m.group(2)), norm(e.get('text') or '')))

    out = {}
    tot_seq = tot_uniq = tot_hit = tot_miss = 0
    for fp in sorted(glob.glob(os.path.join(REVIEW, 'cont_P*.json'))):
        ep = os.path.basename(fp)[5:8]
        d = json.load(open(fp, encoding='utf-8'))
        seqs = d.get('seqs', [])
        lib = lib_by_ep.get(ep, [])
        uniq_seen = set()
        covered = []
        extra = []
        seen_extra = set()

        def key(s):
            return norm(s['text'])

        for s in seqs:
            k = key(s)
            if len(k) < 2 or k in uniq_seen:
                continue
            uniq_seen.add(k)
            m = re.match(r'(\d+)m(\d+)s', s['t'])
            sec = int(m.group(1)) * 60 + int(m.group(2))
            win = [lt for ts, lt in lib if abs(ts - sec) <= 8]
            if win:
                best = max(overlap(k, w) for w in win)
                if best >= 0.6:
                    covered.append((s['t'], s['text'], best))
                    continue
            else:
                best = 0
            if k not in seen_extra:
                seen_extra.add(k)
                extra.append({'t': s['t'], 'text': s['text'], 'best': round(best, 2)})
        out[ep] = extra
        tot_seq += len(seqs)
        tot_uniq += len(uniq_seen)
        tot_hit += len(covered)
        tot_miss += len(extra)
        print(f'{ep}: 序列{len(seqs)} 唯一{len(uniq_seen)} 已覆盖{len(covered)} 未覆盖{len(extra)}', flush=True)

    json.dump(out, open(os.path.join(REVIEW, 'cont_gap.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, default=str)
    print(f'\n总: 序列{tot_seq} 唯一{tot_uniq} 已覆盖{tot_hit} 未覆盖{tot_miss}', flush=True)
    print('保存 review/cont_gap.json')


if __name__ == '__main__':
    main()
