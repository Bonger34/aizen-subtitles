# -*- coding: utf-8 -*-
"""
fix_dups.py — 处理库内同秒重复
1. 删除噪声条目: P16 24m08s 乱码, P22 0m26s 乱码
2. 其余 3 组: 后一条顺延到最近空闲秒(帧复制), 并重建 frames_map
"""
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
FRAMES = os.path.join(BASE, 'docs', 'frames')
FMAP = os.path.join(BASE, 'docs', 'frames_map.js')

DROP = [('P16', '24m08s', '佳用罗专业协会对抗任何敌'),
        ('P22', '0m26s', '0国星##国')]
# (集, 原秒, 要挪动的文本)
MOVE = [('P16', '9m27s', '为什么要找我'),
        ('P20', '4m40s', '有客人来了'),
        ('P20', '11m29s', '这刺激了古老的地层')]


def ts_str(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def ts_sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def main():
    # 1. 删除噪声
    for ep, ts, text in DROP:
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        p = os.path.join(CLEAN, f)
        arr = json.load(open(p, encoding='utf-8'))
        arr2 = [e for e in arr if not (e['timestamp'] == ts and e['text'] == text)]
        json.dump(arr2, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{ep} 删除 {ts} [{text}] -> {len(arr2)} 条')

    # 2. 顺延
    src = open(FMAP, encoding='utf-8').read()
    m = re.search(r'=\s*(\{.*\})\s*;', src, re.S)
    fmap = json.loads(m.group(1))
    for ep, ts, text in MOVE:
        f = [x for x in os.listdir(CLEAN) if x.startswith(f'[{ep}]') and x.endswith('.json')][0]
        p = os.path.join(CLEAN, f)
        arr = json.load(open(p, encoding='utf-8'))
        lib_ts = {e['timestamp'] for e in arr}
        used = set()
        for fn in os.listdir(FRAMES):
            mm = re.match(f'{re.escape(ep)}_(\\d+)m(\\d+)s\\.jpg$', fn)
            if mm:
                used.add(int(mm.group(1)) * 60 + int(mm.group(2)))
        base = ts_sec(ts)
        newsec = None
        for delta in [1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8]:
            cand = base + delta
            if cand >= 0 and ts_str(cand) not in lib_ts and cand not in used:
                newsec = cand
                break
        if newsec is None:
            print(f'!! {ep} {ts} [{text}] 无空闲秒')
            continue
        # 改库
        for e in arr:
            if e['timestamp'] == ts and e['text'] == text:
                e['timestamp'] = ts_str(newsec)
        arr.sort(key=lambda e: ts_sec(e['timestamp']))
        json.dump(arr, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # 复制帧
        title = f[:-5]
        old_frame = fmap.get(f'{title}|{ts}')
        newname = f'{ep}_{ts_str(newsec)}.jpg'
        if old_frame and os.path.exists(os.path.join(FRAMES, old_frame)):
            shutil.copyfile(os.path.join(FRAMES, old_frame), os.path.join(FRAMES, newname))
        else:
            print(f'!! {ep} {ts} 原帧缺失 {old_frame}')
        fmap[f'{title}|{ts_str(newsec)}'] = newname
        print(f'{ep} {ts} [{text}] -> {ts_str(newsec)} ({newname})')

    # 3. 重建映射(以库为基准, 清理孤儿)
    new = {}
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        title = fn[:-5]
        ep = fn[1:4]
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        for e in data:
            key = f'{title}|{e["timestamp"]}'
            fname = fmap.get(key)
            if fname and os.path.exists(os.path.join(FRAMES, fname)):
                new[key] = fname
            elif os.path.exists(os.path.join(FRAMES, f'{ep}_{e["timestamp"]}.jpg')):
                new[key] = f'{ep}_{e["timestamp"]}.jpg'
            else:
                print('缺帧', key)
    open(FMAP, 'w', encoding='utf-8').write('window.FRAMES_MAP = ' + json.dumps(new, ensure_ascii=False) + ';')
    print('映射键数', len(new))


if __name__ == '__main__':
    main()
