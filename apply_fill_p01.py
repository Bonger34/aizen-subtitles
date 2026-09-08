# -*- coding: utf-8 -*-
"""
apply_fill_p01.py — P01 试点回填
1. 读 review/cont_fill_P01.json, 应用人工审查(修正文本/去重/排除)
2. 追加 subtitle_clean/[P01]...json
3. 更新 Web/frames_map.js(增量)
输出: 打印统计; 不重建 db(由 make_subtitle_db.py)
"""
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(BASE, 'subtitle_clean')
FMAP = os.path.join(BASE, 'Web', 'frames_map.js')

# 文本修正: (秒, 原文本) -> 修正文本
FIX = {
    (266, '谢谢关'): '谢谢关心',          # 4m26s
    (367, '已经过去年了'): '已经过去15年了',  # 6m07s
    (420, '是做出来的吧'): '是CG做出来的吧',   # 7m00s
    (539, '她很柔'): '她很温柔',          # 8m59s (8m57s/58s 被库占用已顺延)
    (1429, '是的勺今天的罗布水晶就是这个'): '是的今天的罗布水晶就是这个',  # 23m49s
}
# 排除(秒): 标题卡/广告画面/ED 名单/重复变体
DROP_TS = [119,                # 1m59s 标题卡
           336, 337, 340,      # 5m36s-5m40s 广告画面小字
           427,                # 7m07s 与 7m06s 同句变体
           529,                # 8m49s 与 8m48s 同句变体
           1371, 1372, 1373, 1374, 1375, 1376, 1377, 1378]  # 22m51s-22m58s ED 名单


def main():
    got = json.load(open(os.path.join(BASE, 'review', 'cont_fill_P01.json'), encoding='utf-8'))
    items = []
    for k in sorted(int(x) for x in got.keys()):
        info = got[str(k)]
        if k in DROP_TS:
            print(f'  排除 {info["ts"]} [{info["text"]}]', flush=True)
            continue
        text = info['text']
        for (sk, st), nt in FIX.items():
            if k == sk:
                text = nt
                print(f'  修正 {info["ts"]} [{st}] -> [{nt}]', flush=True)
        items.append({'sec': k, 'text': text, 'frame': info['frame'], 'ts': info['ts']})

    # 追加到 subtitle_clean
    f = [x for x in os.listdir(CLEAN) if x.startswith('[P01]') and x.endswith('.json')][0]
    path = os.path.join(CLEAN, f)
    arr = json.load(open(path, encoding='utf-8'))
    # 冲突检查: 同秒已存在? (extract 已顺延, 理论上无冲突)
    exist = {e['timestamp'] for e in arr}
    to_add = []
    for it in items:
        if it['ts'] in exist:
            print(f'  !! 秒冲突 {it["ts"]} [{it["text"]}] 跳过', flush=True)
            continue
        arr.append({'timestamp': it['ts'], 'text': it['text'], 'similarity': 0.0})
        to_add.append(it)
    # 排序(ts_key 升序)
    def tk(e):
        m = re.match(r'(\d+)m(\d+)s', e['timestamp'])
        return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
    arr.sort(key=tk)
    json.dump(arr, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'P01 库: 新增 {len(to_add)} 条 -> {len(arr)} 条', flush=True)

    # 更新 frames_map.js: 增量 key '[P01]标题|XmXXs' -> 'P01_XmXXs.jpg'
    # 标题 = 库文件标题([P01]1 罗布奥特曼登场)
    title = f[:-5]  # [P01]1 罗布奥特曼登场
    src = open(FMAP, encoding='utf-8').read()
    m = re.search(r'=\s*(\{.*?\})\s*;', src, re.S)
    fmap = json.loads(m.group(1))
    for it in to_add:
        key = f'[{title[1:4]}]{title}|{it["ts"]}'.replace('[P01]1 罗布奥特曼登场', title)
        # 直接: '{title}|{ts}' 格式
        key2 = f'{title}|{it["ts"]}'
        fmap[key2] = it['frame']
    # 重建 frames_map.js(保持原格式)
    body = 'const FRAME_MAP = ' + json.dumps(fmap, ensure_ascii=False) + ';\n'
    # 原文件开头变量名可能不同, 用正则替换整个赋值
    src2 = re.sub(r'=\s*\{.*?\}\s*;', '=' + json.dumps(fmap, ensure_ascii=False) + ';', src, count=1, flags=re.S)
    open(FMAP, 'w', encoding='utf-8').write(src2)
    print(f'frames_map.js 更新: +{len(to_add)} 键', flush=True)


if __name__ == '__main__':
    main()
