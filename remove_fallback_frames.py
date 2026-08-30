# -*- coding: utf-8 -*-
"""remove_fallback_frames.py — 撤销兜底帧（宁缺毋滥）

用户要求：帧图必须与台词一一对应，宁可空着也不用相邻句画面顶替。
删除 extract_frames_dense 产生的 kind='fallback' 帧文件，保留本句命中帧。
"""
import json
import os

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FRAMES_DIR = os.path.join(BASE, 'web', 'frames')
LOG = os.path.join(BASE, 'review', 'frames_dense_fix.json')


def main():
    log = json.load(open(LOG, encoding='utf-8'))
    fallback = [r for r in log if r.get('kind') == 'fallback']
    match_names = {r['frame'] for r in log if r.get('kind') == 'match'}
    removed, conflict = [], []
    for r in fallback:
        fp = os.path.join(FRAMES_DIR, r['frame'])
        if os.path.exists(fp):
            os.remove(fp)
            removed.append(r)
        # 若该帧名同时被某条本句命中记录引用（同秒冲突），该条目也一并回空
        if r['frame'] in match_names:
            conflict.append(r['frame'])
    with open(os.path.join(BASE, 'review', 'fallback_removed.json'), 'w', encoding='utf-8') as fh:
        json.dump({'removed_fallback': len(removed),
                   'same_second_conflict_frames': sorted(set(conflict))},
                  fh, ensure_ascii=False, indent=2)
    print(f'删除兜底帧 {len(removed)} 张；与本句帧同秒冲突的帧名 {len(set(conflict))} 个（一并回空）')


if __name__ == '__main__':
    main()
