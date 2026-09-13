# -*- coding: utf-8 -*-
"""q_judge.py — 重扫结果判定: 哪些条目该替换文本, 哪些被画面证实, 哪些无法同源定位。

判定原则(与全库既有教训一致):
  * 只有"新文本与旧文本字符级高度相似"才说明读到了同一句字幕(同源), 此时差异才可信;
    读到别句时 sim 通常 <0.5 —— 这是区分"修正"与"读错位置"的核心判据, 不靠时间戳。
  * 多帧/多路独立识别给出一致的新文本 -> 支持度; 支持度低的只列为待核, 不自动改。
用法: python q_judge.py P01 [P02 ...] [--src online|rescan|final] [--lo 0.55] [--dry]
输出: review/q_judge_<EP>.json + review/q_judge_<EP>.txt(逐条摘要)
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import kana_ratio, norm, sim  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
SRCS = ['online', 'final', 'rescan', 'web']
LO = 0.55        # 同源下限: 低于此认为"读到的不是这一句"
HI = 0.95        # 证实上限: 高于此认为旧文本被画面证实
SUP = 0.90       # 支持度判定的"两条结果算同一句"的相似度门槛


def iter_segs(it):
    if 'hits' in it:
        for h in it['hits']:
            yield from h['segs']
    elif 'frames' in it:
        fr = it['frames']
        vals = fr.values() if isinstance(fr, dict) else [v for v in fr if v]
        for v in vals:
            yield from v['segs']
    elif 'segs' in it:
        yield from it['segs']


def gather(it, paths):
    out = []
    for seg in iter_segs(it):
        for p in paths:
            t = (seg.get(p) or '').strip()
            if t:
                out.append(t)
    return out


def judge_item(it, paths, lo=LO, hi=HI):
    old = it.get('old', '')
    texts = gather(it, paths)
    rec = {'ts': it['ts'], 'old': old, 'n_read': len(texts)}
    if not texts:
        rec['verdict'] = 'empty'
        return rec
    scored = sorted(((sim(t, old), t) for t in texts), key=lambda z: -z[0])
    rec['best_sim'] = round(scored[0][0], 3)
    rec['best'] = scored[0][1]
    if scored[0][0] >= hi:
        rec['verdict'] = 'confirmed'
        return rec
    if scored[0][0] < lo:
        rec['verdict'] = 'unmatched'
        return rec
    best = scored[0][1]
    rec['support'] = sum(1 for _, t in scored if sim(t, best) >= SUP)
    rec['kana'] = round(kana_ratio(best), 2)
    rec['len_ratio'] = round(len(norm(best)) / max(1, len(norm(old))), 2)
    flags = []
    if rec['support'] < 2:
        flags.append('low_support')
    if rec['kana'] > 0.15:
        flags.append('kana')
    if rec['len_ratio'] > 1.8 or rec['len_ratio'] < 0.5:
        flags.append('len_out')
    rec['flags'] = flags
    rec['verdict'] = 'apply' if not flags else 'review'
    return rec


def load(ep, src):
    pats = [f'q_{src}_{ep}.json'] if src else [f'q_{s}_{ep}.json' for s in SRCS]
    for p in pats:
        fp = os.path.join(REVIEW, p)
        if os.path.exists(fp):
            return json.load(open(fp, encoding='utf-8')), p
    return None, None


def main():
    args = sys.argv[1:]
    src = args[args.index('--src') + 1] if '--src' in args else None
    lo = float(args[args.index('--lo') + 1]) if '--lo' in args else LO
    eps = [a for a in args if not a.startswith('-') and not a.replace('.', '').isdigit()]
    if not eps:
        eps = sorted({f.split('_')[-1][:-5] for f in os.listdir(REVIEW)
                      if f.startswith('q_rescan_') and f.endswith('.json')})
    summary = defaultdict(int)
    detail = {}
    for ep in eps:
        d, name = load(ep, src)
        if d is None:
            print(f'{ep}: 无重扫结果')
            continue
        paths = d.get('paths', ['bin', 'raw'])
        recs = [judge_item(it, paths, lo) for it in d['items']]
        for r in recs:
            summary[r['verdict']] += 1
        detail[ep] = {'src': name, 'items': recs}
        n = len(recs)
        print(f"{ep}: {n} 条 | " + ' | '.join(
            f"{k} {sum(1 for r in recs if r['verdict'] == k)}" for k in
            ('confirmed', 'apply', 'review', 'unmatched', 'empty')))
    json.dump(detail, open(os.path.join(REVIEW, 'q_judge.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    txt = []
    for ep, dd in detail.items():
        txt.append(f"===== {ep} ({dd['src']})")
        for r in dd['items']:
            if r['verdict'] in ('apply', 'review'):
                txt.append(f"  [{r['verdict']}] {r['ts']:>7s} sim={r['best_sim']:.2f} "
                           f"sup={r.get('support')} flags={','.join(r.get('flags', []))}")
                txt.append(f"        旧[{r['old']}]")
                txt.append(f"        新[{r['best']}]")
            elif r['verdict'] == 'unmatched':
                txt.append(f"  [unmatched] {r['ts']:>7s} 最佳 sim={r['best_sim']:.2f} "
                           f"旧[{r['old']}] 读[{r['best'][:30]}]")
    open(os.path.join(REVIEW, 'q_judge.txt'), 'w', encoding='utf-8').write('\n'.join(txt))
    print('\n汇总:', dict(summary))
    print('明细: review/q_judge.json + review/q_judge.txt')


if __name__ == '__main__':
    main()
