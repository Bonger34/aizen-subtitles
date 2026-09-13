# -*- coding: utf-8 -*-
"""q_listv.py — 打印帧图验证的严格候选(帧图读数=新文本、≠旧文本), 文字版便于逐条核对。
用法: python q_listv.py [review] [--min-new 0.98] [--max-old 0.98]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q_common import sim  # noqa: E402

B = os.path.dirname(os.path.abspath(__file__))
import json  # noqa: E402

kind = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'review'
mn = float(sys.argv[sys.argv.index('--min-new') + 1]) if '--min-new' in sys.argv else 0.98
mo = float(sys.argv[sys.argv.index('--max-old') + 1]) if '--max-old' in sys.argv else 0.98
d = json.load(open(os.path.join(B, 'review', f'q_verify_{kind}.json'), encoding='utf-8'))
n = 0
for r in d['items']:
    so, sn = r['sim_frame_old'], r.get('sim_frame_new', 0)
    if sn >= mn and so < mo and r.get('new_tl'):
        n += 1
        dlt = sim(r['old'], r['new_tl'])
        print(f"{n:3d}. {r['ep']} {r['ts']:>7s} [{r.get('kind')}] "
              f"帧旧={so:.2f} 帧新={sn:.2f} 时间线={r.get('sim_tl') or 0:.2f} 新旧={dlt:.2f}")
        print(f"     旧  [{r['old']}]")
        print(f"     新  [{r['new_tl']}]")
        print(f"     帧读[{r['frame_text']}]")
print(f'共 {n} 条')
