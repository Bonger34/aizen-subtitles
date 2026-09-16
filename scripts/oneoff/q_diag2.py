# -*- coding: utf-8 -*-
"""q_diag2.py — 诊断 unmatched("无任何匹配")条目的成因: 该时间窗里时间线到底发生了什么。

背景: q_align_tl 判定"无任何匹配"要求窗口内所有事件与旧文本相似度都是 0(完全无共同字符),
这说明窗口内根本没有可用的读数。本脚本按成因分档, 决定下一步该补采样还是该换阈值。
用法: python q_diag2.py [--win 5]
输出: review/q_diag2.json + 控制台分档统计
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from q_common import sim  # noqa: E402

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def main():
    win = float(sys.argv[sys.argv.index('--win') + 1]) if '--win' in sys.argv else 5.0
    align = json.load(open(os.path.join(REVIEW, 'q_align_tl.json'), encoding='utf-8'))
    causes = Counter()
    rows = []
    for ep in sorted(align):
        tl_p = os.path.join(REVIEW, f'q_timeline_{ep}.json')
        if not os.path.exists(tl_p):
            continue
        tl = json.load(open(tl_p, encoding='utf-8'))
        paths = tl.get('paths', ['bin', 'raw'])
        pts = tl['points']
        for r in align[ep]['items']:
            if r['verdict'] != 'unmatched' or r.get('best_sim') is not None:
                continue
            sec = parse_ts(r['ts'])
            if sec is None:
                continue
            lo, hi = sec - win, sec + win
            inw = [p for p in pts if lo <= p['t'] <= hi]
            n_white = sum(1 for p in inw if p['white'] > 0)
            n_ocr = sum(1 for p in inw if p.get('ocr'))
            texts = [s.get(pp, '') for p in inw if p.get('segs')
                     for s in p['segs'] for pp in paths]
            scored = sorted(((sim(t, r['old']), t) for t in texts), key=lambda z: -z[0])
            best = scored[0][0] if scored else 0.0
            best_text = scored[0][1] if scored else ''
            # 成因分档
            if not inw:
                cause = '窗口内无采样点'
            elif n_white == 0:
                cause = '窗口内无纯白像素(字幕非纯白或画面全暗)'
            elif n_ocr == 0:
                cause = '有白像素但签名未变化(未触发OCR)'
            elif not texts:
                cause = '触发OCR但段切分为空'
            elif best <= 0.0:
                cause = '读到文本与旧文本无共同字符'
            else:
                cause = '读到部分匹配(与互斥分配结果不符)'
            causes[cause] += 1
            rows.append({'ep': ep, 'ts': r['ts'], 'old': r['old'], 'cause': cause,
                         'n_pts': len(inw), 'n_white': n_white, 'n_ocr': n_ocr,
                         'n_texts': len(texts), 'best_sim_unexcl': round(best, 3),
                         'best_text': best_text,
                         'sample': [t for _, t in scored[:6]]})
    print('成因分档:')
    for k, v in causes.most_common():
        print(f'  {v:5d}  {k}')
    json.dump(rows, open(os.path.join(REVIEW, 'q_diag2.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n合计 {len(rows)} 条 -> review/q_diag2.json')
    for c in causes:
        ex = [r for r in rows if r['cause'] == c][:3]
        print(f'\n-- {c} 例:')
        for r in ex:
            print(f"   {r['ep']} {r['ts']:>7s} 采样{r['n_pts']} 白{r['n_white']} OCR{r['n_ocr']} "
                  f"文本{r['n_texts']} 非互斥最佳={r['best_sim_unexcl']}")
            print(f"      旧[{r['old']}] 样本{r['sample']}")


if __name__ == '__main__':
    main()
