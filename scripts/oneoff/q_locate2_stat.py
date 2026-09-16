# -*- coding: utf-8 -*-
"""q_locate2_stat.py — 汇总 q_locate2 的逐集结果, 分档并挑出"补全型"候选。

分档:
  same  新读数与旧文本一致(sim>=0.95) —— 画面证实旧文本
  add   旧文本是新读数的子序列且新读数更长 —— 方向可靠的补全型候选(仍需人工看图)
  del   新读数是旧文本的子序列 —— 多数是画面遮挡导致漏读, 不作修正依据
  diff  其余不一致 —— 多为片头版权卡/片尾演职员表/歌词(带外)
  none  定位到了帧但没有字幕行

带外判定: 读数假名占比高(日文演职员表/歌词) 或 命中时段在片尾(>=21m30s 且非 same)。
用法: python q_locate2_stat.py
输出: review/q_locate2_stat.json + 控制台分档表
"""
import json
import os
import re
from collections import Counter

import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import kana_ratio, norm

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
TAIL_SEC = 21 * 60 + 30


def parse_ts(ts):
    try:
        m, s = ts.rstrip('s').split('m')
        return int(m) * 60 + int(s)
    except Exception:
        return -1


def load_rows():
    rows = []
    for f in sorted(os.listdir(REVIEW)):
        # 只认逐集文件 q_locate2_P01.json …; 排除 q_locate2.json / q_locate2_stat.json 等汇总文件
        if re.fullmatch(r'q_locate2_P\d+\.json', f):
            rows.extend(json.load(open(os.path.join(REVIEW, f), encoding='utf-8')))
    return rows


def scope_of(r):
    """判断该条是否属于"台词字幕"范围。返回 'in' 或带外原因。"""
    txt = r['text'] or ''
    if '版权' in r['old'] or '版权' in txt:
        return '版权卡'
    if kana_ratio(txt) > 0.15 or kana_ratio(r['old']) > 0.15:
        return '日文(演职员表/歌词)'
    if r['rel'] == 'diff' and parse_ts(r['ts']) >= TAIL_SEC:
        return '片尾(>=21m30s)'
    return 'in'


def main():
    rows = load_rows()
    for r in rows:
        r['scope'] = scope_of(r)
    c = Counter(r['rel'] or 'none' for r in rows)
    print(f'已扫描 {len(rows)} 条')
    print('关系分档:', dict(c))
    print('带外分档:', dict(Counter(r['scope'] for r in rows if r['scope'] != 'in')))
    inscope = [r for r in rows if r['scope'] == 'in']
    print(f'范围内 {len(inscope)} 条:', dict(Counter(r['rel'] or 'none' for r in inscope)))

    adds = [r for r in inscope if r['rel'] == 'add']
    print(f'\n补全型候选 {len(adds)} 条(需人工看图确认多出的字):')
    for r in sorted(adds, key=lambda x: (x['ep'], parse_ts(x['ts']))):
        d = len(norm(r['text'])) - len(norm(r['old']))
        print(f"  {r['ep']} {r['ts']:>7s} iou={r['iou']:.2f} +{d}  [{r['old']}] -> [{r['text']}]")

    others = [r for r in inscope if r['rel'] in ('diff', 'del')]
    print(f'\n范围内其他不一致 {len(others)} 条(多为画面遮挡/误定位, 逐条看过再定):')
    for r in sorted(others, key=lambda x: (x['ep'], parse_ts(x['ts'])))[:60]:
        print(f"  [{r['rel']}] {r['ep']} {r['ts']:>7s} iou={r['iou']:.2f} sim={r['sim']:.2f} "
              f"[{r['old']}] -> [{r['text']}]")

    json.dump({'rows': rows, 'adds': adds}, open(os.path.join(REVIEW, 'q_locate2_stat.json'),
              'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n输出: review/q_locate2_stat.json')


if __name__ == '__main__':
    main()
