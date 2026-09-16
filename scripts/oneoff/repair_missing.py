# -*- coding: utf-8 -*-
"""修复"库里有条目但配图缺失"的情况: 用同集时间上最近的条目配图补上(优先取靠后的)。

背景: 部分条目共用同一张配图(同一画面的相邻秒), 重命名帧时会把共用文件挪走,
      导致另一条失去配图。补回最近帧即可恢复。
用法: python repair_missing.py [--apply]
"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
FR = os.path.join(B, 'docs', 'frames')
FMAP = os.path.join(B, 'docs', 'frames_map.js')


def sec_of(ts):
    m = re.match(r'(\d+)m(\d+)s', ts or '')
    return None if not m else int(m.group(1)) * 60 + int(m.group(2))


def ts_of(sec):
    return f'{sec // 60}m{sec % 60:02d}s'


def main():
    apply = '--apply' in __import__('sys').argv
    MAP = json.loads(re.search(r'=\s*(\{.*\})\s*;',
                               open(FMAP, encoding='utf-8').read(), re.S).group(1))
    fixed = []
    for fn in sorted(os.listdir(CLEAN)):
        if not fn.endswith('.json'):
            continue
        title, ep = fn[:-5], fn[1:4]
        data = json.load(open(os.path.join(CLEAN, fn), encoding='utf-8'))
        have = {e['timestamp']: MAP.get(f'{title}|{e["timestamp"]}') for e in data}
        for e in data:
            key = f'{title}|{e["timestamp"]}'
            cur = MAP.get(key)
            if cur and os.path.exists(os.path.join(FR, cur)):
                continue
            sec = sec_of(e['timestamp'])
            # 同集已可用的配图, 按时间距离排序(同距优先靠后)
            cands = sorted(
                ((abs(sec_of(t) - sec), -(sec_of(t)), f, t) for t, f in have.items()
                 if f and os.path.exists(os.path.join(FR, f))),
                key=lambda x: (x[0], x[1]))
            if not cands:
                print(f'  !! {key} 无任何可用配图')
                continue
            _, _, f, t = cands[0]
            fixed.append((key, f, f'取自 {t}'))
            if apply:
                MAP[key] = f
    for key, f, why in fixed:
        print(f'  {key} -> {f}  ({why})')
    if apply and fixed:
        open(FMAP, 'w', encoding='utf-8').write(
            'window.FRAMES_MAP = ' + json.dumps(MAP, ensure_ascii=False) + ';')
        print(f'已补 {len(fixed)} 条并写回 {FMAP}')
    elif not fixed:
        print('无缺失配图')


if __name__ == '__main__':
    main()
