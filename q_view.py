# -*- coding: utf-8 -*-
"""q_view.py — 打印重扫结果的逐条对照(支持 q_rescan / q_web / q_locate / q_online 四种产物)。

用法: python q_view.py P02 [起始下标] [条数] [--below 0.6] [--src online|rescan|web|final]
不指定 --src 时按 online > final > rescan > web 顺序取存在的文件。
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import sim  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
SRCS = ['online', 'final', 'rescan', 'web']


def load(ep, src):
    pats = [f'q_{src}_{ep}.json'] if src else [f'q_{s}_{ep}.json' for s in SRCS]
    for p in pats:
        fp = os.path.join(B, 'review', p)
        if os.path.exists(fp):
            return json.load(open(fp, encoding='utf-8')), p
    raise SystemExit(f'找不到 {ep} 的重扫结果 ({glob.glob(os.path.join(B, "review", f"q_*_{ep}.json"))})')


def norm_frames(it):
    """把各脚本不同的存放方式统一为 [(标签, segs), ...]。"""
    out = []
    if 'hits' in it:
        for h in it['hits']:
            out.append((f"命中f{h['fno']} t{h.get('t')} mae{h.get('mae')}", h['segs']))
    elif 'frames' in it:
        fr = it['frames']
        if isinstance(fr, dict):
            for k, v in fr.items():
                out.append((f'帧{k}', v['segs']))
        else:
            for k, v in enumerate(fr):
                if v:
                    out.append((f'帧{k}', v['segs']))
    elif 'segs' in it:
        out.append((f"帧{it.get('frame')}", it['segs']))
    return out


def main():
    ep = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
    cnt = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 30
    below = float(sys.argv[sys.argv.index('--below') + 1]) if '--below' in sys.argv else 1.01
    src = sys.argv[sys.argv.index('--src') + 1] if '--src' in sys.argv else None
    d, name = load(ep, src)
    paths = d.get('paths', ['bin', 'raw'])
    extra = f" 定位 {d['n_located']}" if 'n_located' in d else ''
    print(f"{name} | {d['ep']} {d['n_entries']} 条{extra} / {d['elapsed']}s(OCR {d['elapsed_ocr']}s)")
    shown = 0
    for i, it in enumerate(d['items']):
        if i < start or shown >= cnt:
            continue
        best = (0.0, '')
        lines = [f"--- #{i} {it['ts']} 旧[{it['old']}]"]
        if it.get('offset') is not None:
            lines[0] += f" 偏移{it['offset']:+.2f}s"
        for lab, segs in norm_frames(it):
            for s in segs:
                cells = []
                for p in paths:
                    v = s.get(p, '')
                    sv = sim(v, it['old'])
                    cells.append(f'{p}[{v}]({s.get(p + "_score")},{sv:.2f})')
                    if sv > best[0]:
                        best = (sv, v)
                lines.append(f"    {lab} y{s['y0']}-{s['y1']} x{s['x0']}-{s['x1']} f{s['fill']} "
                             + ' '.join(cells))
        if best[0] >= below:
            continue
        lines.append(f"    => 最佳 sim={best[0]:.2f} [{best[1]}]")
        print('\n'.join(lines))
        shown += 1


if __name__ == '__main__':
    main()
