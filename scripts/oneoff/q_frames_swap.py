# -*- coding: utf-8 -*-
"""q_frames_swap.py — 把 docs/frames_fix/ 里重抽的帧按原文件名覆盖到 docs/frames/。

文件名不变, 所以 frames_map.js / subtitle_db 都不需要重建; 只统计到底换了多少张、
其中多少张内容其实与原来相同(可用作"原来就是对的"的判据)。

用法: python q_frames_swap.py [--dry]
输出: review/q_frames_swap.json
"""
import hashlib
import json
import os
import shutil
import sys
import time

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FR = os.path.join(B, 'docs', 'frames')
FIX = os.path.join(B, 'docs', 'frames_fix')
REVIEW = os.path.join(B, 'review')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    dry = '--dry' in sys.argv
    files = sorted(f for f in os.listdir(FIX) if f.endswith('.jpg'))
    replaced, same, new = [], [], []
    for f in files:
        src, dst = os.path.join(FIX, f), os.path.join(FR, f)
        if not os.path.exists(dst):
            new.append(f)
        elif md5(src) == md5(dst):
            same.append(f)
            continue
        else:
            replaced.append(f)
        if not dry:
            shutil.copy2(src, dst)
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
           'n_fix': len(files), 'n_replaced': len(replaced), 'n_identical': len(same),
           'n_new': len(new), 'replaced': replaced}
    json.dump(out, open(os.path.join(REVIEW, 'q_frames_swap.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"frames_fix {len(files)} 个: 覆盖 {len(replaced)} / 内容本来就相同 {len(same)} / "
          f"原本不存在 {len(new)}{'（预演）' if dry else ''}")
    print(f"docs/frames 现有 {len([f for f in os.listdir(FR) if f.endswith('.jpg')])} 个 jpg")
    print('输出: review/q_frames_swap.json')


if __name__ == '__main__':
    main()
