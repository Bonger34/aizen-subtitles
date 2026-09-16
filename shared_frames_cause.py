# -*- coding: utf-8 -*-
"""确认成因: 出错的那条条目, 它"自己名字的帧"是否存在?"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
FR = os.path.join(B, 'docs', 'frames')
rows = json.load(open(os.path.join(B, 'review', 'shared_frames_ocr.json'), encoding='utf-8'))
files = set(os.listdir(FR))

stat = collections.Counter()
for r in rows:
    ep = r['frame'][:3]
    ts_list = [t for t, _ in r['entries']]
    v = r['verdict']
    if '后一条配图错' in v:
        bad = ts_list[1]
    elif '前一条配图错' in v:
        bad = ts_list[0]
    else:
        stat['无需判断(' + v + ')'] += 1
        continue
    own = f'{ep}_{bad}.jpg'
    stat['出错条目"自己名字的帧"不存在' if own not in files else '出错条目"自己名字的帧"存在(仍被错配)'] += 1

print('成因核对:')
for k, v in stat.most_common():
    print(f'   {k}: {v}')

# 出错条目的时间戳跨度
gaps = collections.Counter()
for r in rows:
    ts_list = [t for t, _ in r['entries']]
    sec = lambda t: int(t.split('m')[0]) * 60 + int(t.split('m')[1].rstrip('s'))
    if '配图错' in r['verdict']:
        gaps[sec(ts_list[1]) - sec(ts_list[0])] += 1
print('\n出错的组内时间戳间隔:', dict(sorted(gaps.items())))
