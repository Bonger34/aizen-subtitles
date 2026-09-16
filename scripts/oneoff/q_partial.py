# -*- coding: utf-8 -*-
"""q_partial.py — 用"帧图读数是旧文本的子集"来部分证实读不出的条目。

帧图只有 960x540, 字幕约 30px 高, OCR 的失败模式是**漏字**而不是造错字:
  好痛 -> 痛      银河奥特曼 -> 银河特      布鲁奥特曼跃水形态 -> 布告奥
因此"帧读里落在旧文本内的字符占比高"足以说明读到的是同一句, 只是没读全。
用法: python q_partial.py [--src review/q_final.json] [--min-ratio 0.6]
输出: review/q_partial.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import norm  # noqa: E402

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')


def main():
    src = sys.argv[sys.argv.index('--src') + 1] if '--src' in sys.argv else 'q_final.json'
    min_ratio = float(sys.argv[sys.argv.index('--min-ratio') + 1]) if '--min-ratio' in sys.argv else 0.6
    items = json.load(open(os.path.join(REVIEW, src), encoding='utf-8'))
    if isinstance(items, dict):
        items = items['items']
    todo = [r for r in items if r.get('band', 'unreadable') == 'unreadable'
            or (r.get('sim_old', 0) < 0.35)]
    partial, none, empty = [], [], []
    for r in todo:
        a, b = norm(r['old']), norm(r.get('frame_text') or '')
        if len(b) < 2:
            empty.append(r)
            continue
        cnt = {}
        for ch in a:
            cnt[ch] = cnt.get(ch, 0) + 1
        hit = 0
        for ch in b:
            if cnt.get(ch, 0) > 0:
                cnt[ch] -= 1
                hit += 1
        ratio = hit / len(b)
        r['partial_ratio'] = round(ratio, 2)
        if ratio >= min_ratio:
            partial.append(r)
        else:
            none.append(r)
    print(f'{src}: 读不出 {len(todo)} 条 -> 部分证实 {len(partial)} / '
          f'帧图几乎没读出字 {len(empty)} / 读到的字与旧文本不符 {len(none)}')
    from collections import Counter
    print('部分证实按集:', dict(sorted(Counter(r['ep'] for r in partial).items())))
    print('\n部分证实样例(旧文本 | 帧图读):')
    for r in partial[:30]:
        print(f"  {r['ep']} {r['ts']:>7s} [{r['old']}] | [{r.get('frame_text')}] "
              f"ratio={r['partial_ratio']}")
    json.dump({'partial': partial, 'empty': empty, 'mismatch': none},
              open(os.path.join(REVIEW, 'q_partial.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n输出: review/q_partial.json')


if __name__ == '__main__':
    main()
