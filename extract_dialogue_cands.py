# -*- coding: utf-8 -*-
"""从带外(仅LOW)OCR 结果中筛出【台词字幕】候选。

排除规则(结构化, 不靠零散关键词):
  1. 版权声明卡   —— 文本含 版权/新创华/文化发展/中国大陆
  2. 片尾歌词     —— 落在 22m20s~23m45s 窗口
  3. 图鉴/预告解说 —— 落在 23m45s~24m15s 窗口
  4. 跨集重复文案 —— 同一文本在 >=3 集出现(歌词/固定字幕)
  5. 噪声         —— 中文 <3 字, 或数字占比过高
其余即"疑似台词", 并按集列出。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
d = json.load(open(os.path.join(B, 'review', 'ext_cands.json'), encoding='utf-8'))

COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新')
LYRIC_WIN = (22 * 60 + 20, 23 * 60 + 45)
GUIDE_WIN = (23 * 60 + 45, 24 * 60 + 15)


def sec(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2))


def cn(t):
    return re.sub(r'[^\u4e00-\u9fff]', '', t)


rows = []
for ep, v in sorted(d.items()):
    for c in v.get('all', []):
        t = c['text']
        rows.append({'ep': ep, 'ts': c['t'], 'sec': c['sec'], 'text': t, 'bef': c['bef']})

# 跨集重复统计
dup = collections.Counter(cn(r['text']) for r in rows if len(cn(r['text'])) >= 4)

tally = collections.Counter()
talk = []
for r in rows:
    t, s = r['text'], r['sec']
    n = cn(t)
    if COPY.search(t):
        k = '版权声明卡'
    elif LYRIC_WIN[0] <= s <= LYRIC_WIN[1]:
        k = '片尾歌词段'
    elif GUIDE_WIN[0] <= s <= GUIDE_WIN[1]:
        k = '图鉴/预告段'
    elif len(n) < 3:
        k = '噪声(过短)'
    elif dup.get(n, 0) >= 3:
        k = '跨集重复文案'
    else:
        k = '疑似台词'
        talk.append(r)
    tally[k] += 1

print('仅LOW 去重样本分类:')
for k, v in tally.most_common():
    print(f'   {k}: {v}')
print(f'\n疑似台词候选 {len(talk)} 条:')
for r in sorted(talk, key=lambda x: (x['ep'], x['sec'])):
    print(f"   {r['ep']} {r['ts']:>7s}  [{r['text']}]  (库匹配度={r['bef']})")

json.dump(talk, open(os.path.join(B, 'review', 'ext_dialogue_cands.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n写出 review/ext_dialogue_cands.json')
