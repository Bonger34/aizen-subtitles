# -*- coding: utf-8 -*-
"""q_tsread_stat.py — 汇总"按库时间戳直接读原片"的结果, 给出文本对错的权威分档。

与 q_locate2 的区别: q_locate2 拿帧图去视频里找同一帧, 一旦帧图本身错位(实测 seek 漂移 +
frames_map ±3s 回退), 读到的就是相邻台词 —— 会把对的文本改错(实测 泰罗奥特曼/银河奥特曼
这类轮唱句就被系统性带偏)。本脚本只看"该条目自己的时间戳上画面写的是什么", 不含帧图。

分档:
  same  该时刻读数与库文本一致(sim>=0.95) —— 文本正确
  add   库文本是读数的子序列且读数更长 —— 补全型候选
  del   读数是库文本的子序列 —— 多为画面遮挡, 不作依据
  diff  其余不一致
  empty ts±0.8s 五点都没读到字幕 —— 条目时刻无字幕(时间戳可疑或为多帧残留)
用法: python q_tsread_stat.py [--tag all]
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import diff_rel, norm, to_simp  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(B, 'review')
FR = os.path.join(B, 'docs', 'frames')
FRAME_PAT = re.compile(r'^P(\d{1,2})_(\d+)m(\d+)s([+-]\d+s)?\.jpg$')


def sim(a, b):
    """**先繁简归一再比对** —— 库里与识别结果混用繁体(別/奧/強/裡), 不归一会把
    「朝阳你千万别过来 vs 朝阳你千万別过来」这类同句判成不一致。实测核验集 1364 条里
    有 17 条、150 条疑似正片台词里有 15 条, 只有归一后才被证实。"""
    a, b = norm(to_simp(a)), norm(to_simp(b))
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return 1.0 - prev[n] / min(m, n)


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_map():
    s = open(os.path.join(B, 'docs', 'frames_map.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def main():
    tag = 'all'
    if '--tag' in sys.argv:
        tag = sys.argv[sys.argv.index('--tag') + 1]
    rows = json.load(open(os.path.join(REVIEW, f'q_tsread{tag}.json'), encoding='utf-8'))
    mapv = load_map()

    for r in rows:
        cands = [t for rd in r['reads'] for t in rd['texts']]
        uniq = sorted(set(cands), key=lambda t: (-cands.count(t), -len(t)))
        r['uniq'] = uniq
        r['n_read'] = len(cands)
        if not uniq:
            r['rel'], r['best'], r['sbest'] = 'empty', '', 0.0
        else:
            best = max(uniq, key=lambda t: sim(t, r['old']))
            r['best'], r['sbest'] = best, round(sim(best, r['old']), 3)
            if r['sbest'] >= 0.95:
                r['rel'] = 'same'
            else:
                rel = diff_rel(r['old'], best)
                r['rel'] = rel if rel in ('add', 'del') else 'diff'
        # 帧图偏移
        key = next((k for k in mapv if k.endswith('|' + r['ts']) and k.startswith(f"[{r['ep']}]")), None)
        r['frame'] = mapv.get(key) if key else None
        r['foff'] = None
        if r['frame']:
            m = FRAME_PAT.match(r['frame'])
            if m:
                r['foff'] = int(m.group(2)) * 60 + int(m.group(3)) - (parse_ts(r['ts']) or 0)

    n = len(rows)
    c = Counter(r['rel'] for r in rows)
    print(f'全库 {n} 条按自身时间戳读原片:')
    for k in ('same', 'add', 'diff', 'del', 'empty'):
        print(f'  {k:6s} {c.get(k, 0):5d}  {c.get(k, 0) / n:6.1%}')
    print(f'  -> 文本与该时刻画面一致 {c.get("same", 0)}/{n} = {c.get("same", 0) / n:.1%}')

    # 帧图偏移 vs 一致性
    print('\n按帧图偏移交叉(只统计有帧图的条目):')
    grid = {}
    for r in rows:
        if r['foff'] is None:
            continue
        b = f'{r["foff"]:+d}s' if r['foff'] else '精确'
        grid.setdefault(b, Counter())[r['rel']] += 1
    for b in sorted(grid, key=lambda x: (x != '精确', x)):
        cc = grid[b]
        tot = sum(cc.values())
        print(f'  {b:>5s} 共{tot:5d}  一致 {cc.get("same", 0):5d} ({cc.get("same", 0) / tot:5.1%})  '
              f'add {cc.get("add", 0):3d} diff {cc.get("diff", 0):3d} del {cc.get("del", 0):3d} '
              f'无字幕 {cc.get("empty", 0):3d}')
    noframe = [r for r in rows if not r['frame']]
    print(f'  无帧图映射: {len(noframe)} 条 (其中一致 {sum(1 for r in noframe if r["rel"] == "same")})')

    json.dump(rows, open(os.path.join(REVIEW, f'q_tsread_stat_{tag}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n输出: review/q_tsread_stat_{tag}.json')


if __name__ == '__main__':
    main()
