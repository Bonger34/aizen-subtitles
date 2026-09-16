# -*- coding: utf-8 -*-
"""q_frames_audit.py — 全库"画面 ↔ 文本"一致性审计。

以 q_reframe 全库跑完的结果为准:
  有匹配帧 -> 该条目已换成"画面就是这句话"的帧(可视为画面侧已解决)
  无匹配帧 -> t±1.6s 内没有任何一帧的字幕与库文本一致, 分两类:
      a) 该条目本身不是台词(片头/片尾/版权卡/标题卡/预告) —— 按既定口径属带外
      b) 库文本可疑或该句难以被 OCR 读出 —— 需人工看图

用法: python q_frames_audit.py
输出: review/q_frames_audit.json + 控制台汇总
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')
KANA = set(range(0x3040, 0x30FF))
TAIL = 21 * 60 + 30


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def classify(old, ts, readings):
    """粗分带外类别; readings 为该条目时间戳附近的实际画面读数。"""
    t = old or ''
    kana = sum(1 for c in t if ord(c) in KANA) / max(1, len(t))
    txt = ' '.join(readings)
    if '版权' in t or '中国大陆' in t:
        return '版权卡'
    if kana > 0.15 or (sum(1 for c in txt if ord(c) in KANA) / max(1, len(txt)) > 0.15):
        return '日文(片头片尾/演职员表)'
    if re.search(r'第\s*\d*\s*集', txt) and '集' not in t:
        return '下集预告/标题卡'
    if parse_ts(ts) >= TAIL:
        return '片尾段(≥21m30s)'
    if len(''.join(re.findall(r'[0-9A-Za-z\u4e00-\u9fff]', t))) <= 2:
        return '碎片(≤2字)'
    return '疑似正片台词'


def main():
    lib = {}
    for f in sorted(os.listdir(CLEAN)):
        if not (f.endswith('.json') and re.match(r'^\[P\d+\]', f)):
            continue
        ep = re.search(r'\[(P\d+)\]', f).group(1)
        for e in json.load(open(os.path.join(CLEAN, f), encoding='utf-8')):
            lib[(ep, e.get('timestamp'))] = e.get('text', '')

    # 判据用"docs/frames_fix/ 里有没有这条的新帧" —— q_reframe 的 report 只在全部集跑完时才写,
    # 中途停止时没有 report, 只能以产物为准。
    tg = json.load(open(os.path.join(REVIEW, 'q_allframes_tg.json'), encoding='utf-8'))
    got = set(os.listdir(os.path.join(B, 'docs', 'frames_fix')))
    hits, full_eps = set(), set()
    for r in tg:
        if r.get('frame') in got:
            hits.add((r['ep'], r['ts']))
            full_eps.add(r['ep'])
    # 只保留"整集都跑过"的集, 否则半集的会被误判为"未找到匹配帧"
    per_ep = defaultdict(lambda: [0, 0])
    for r in tg:
        per_ep[r['ep']][1] += 1
        if r.get('frame') in got:
            per_ep[r['ep']][0] += 1
    full_eps = set()
    for ep, (h, t) in per_ep.items():
        if h >= t * 0.5:          # 命中率 >=50% 视为整集跑过(半途中断的集命中率会低得多)
            full_eps.add(ep)

    # 该条目自身时间戳附近的实际读数(来自全库时间戳复核), 用于区分带外类别
    reads = defaultdict(list)
    for f in os.listdir(REVIEW):
        if re.fullmatch(r'q_tsreada\d+_P\d+\.json', f):
            for r in json.load(open(os.path.join(REVIEW, f), encoding='utf-8')):
                reads[(r['ep'], r['ts'])] += [t for rd in r['reads'] for t in rd['texts']]

    # 只审计**已跑过全库重抽**的集(未跑的集其条目本来就不在 hits 里, 混进来会虚增"未找到")
    scope = {(ep, ts) for (ep, ts) in lib if ep in full_eps}
    print(f'本次已重抽的集: {sorted(full_eps)}')
    miss = [(ep, ts) for (ep, ts) in scope if (ep, ts) not in hits]
    c = Counter()
    rows = []
    for ep, ts in sorted(miss):
        k = classify(lib[(ep, ts)], ts, reads.get((ep, ts), []))
        c[k] += 1
        rows.append({'ep': ep, 'ts': ts, 'old': lib[(ep, ts)], 'kind': k})

    print(f'已重抽范围 {len(scope)} 条: 找到"画面即该句"的匹配帧 {len(hits & scope)} 条 = '
          f'{len(hits & scope) / max(1, len(scope)):.1%}')
    print(f'未找到匹配帧 {len(miss)} 条, 分类:')
    for k, v in c.most_common():
        print(f'   {k}: {v}')
    json.dump({'n_total': len(lib), 'n_scope': len(scope), 'n_hit': len(hits & scope),
               'n_miss': len(miss), 'full_eps': sorted(full_eps),
               'by_kind': dict(c), 'miss': rows},
              open(os.path.join(REVIEW, 'q_frames_audit.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('输出: review/q_frames_audit.json')


if __name__ == '__main__':
    main()
