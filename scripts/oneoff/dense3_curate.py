# -*- coding: utf-8 -*-
"""对复核通过的 750 条做最后策展: 剔除片尾歌词/演职员表/图鉴预告解说/跨集重复, 输出待入库清单。"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
d = json.load(open(os.path.join(B, 'review', 'dense3_verified.json'), encoding='utf-8'))
ver = d['verified']
print('复核通过', len(ver))

LYRIC = ('不经意地翻开相册', '仿若能天长地久', '所以在夕阳西下前定要说给你听',
         '就算遇到挫折也决不望而却步', '因为你我的牵绊永不间断', '内心深藏的那句谢谢',
         '却始终说不出口', '这世上没有永恒', '照片中夕阳下的笑容格外灿烂', '一如往常',
         '曾在墙壁的角落里比过身高', '虽然痕迹已经褪色我已长大成人', '但如今尚未实现遥远的梦想',
         '因为我仍在不断长高', '始终向着倾诉', '口城商', '稻城商店街')
CREDIT = ('制作', '進行', '进行', '演技', '装飾', '装饰', '撮影', '照明', '造形', '衣裳', '美術',
          '美术', '選曲', '整音', '効果', '协助', '協力', '設定', '监修', '監修', '助手', '操演',
          '监督', '監督', '特撮', '視覚', '音響', '編集', '宣伝', '広報', '番組', '岡本', '坂井',
          '島田', '及川', '青井', '万理子', '渡邊', '渡邊', '亮太', '稲垣', '稻垣', '千春')
GUIDE = ('奥特曼', '奥特战士', '怪兽', '必杀技', '水晶', '身高', '体重', '图鉴', '形态', '变身',
         '罗布水晶', '光线技能')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


creps = collections.Counter(cn(v['text']) for v in ver)
# 跨集重复: 同一文本(或高相似)出现在 >=3 集
bytext = collections.defaultdict(set)
for v in ver:
    bytext[cn(v['text'])].add(v['ep'])
reps = {t for t, eps in bytext.items() if len(eps) >= 3}

keep, drop = [], collections.Counter()
for v in ver:
    t = cn(v['text'])
    if any(w in t for w in LYRIC):
        drop['片尾歌词'] += 1
    elif any(w in t for w in CREDIT):
        drop['演职员表'] += 1
    elif any(w in t for w in GUIDE):
        drop['图鉴/预告解说'] += 1
    elif t in reps:
        drop['跨集重复'] += 1
    elif len(t) < 3:
        drop['过短'] += 1
    else:
        keep.append(v)
print('剔除:', dict(drop))
print('待入库台词:', len(keep))
json.dump(keep, open(os.path.join(B, 'review', 'dense3_final.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
lines = [f'待入库台词 {len(keep)} 条:', '']
byep = collections.defaultdict(list)
for v in keep:
    byep[v['ep']].append(v)
for ep in sorted(byep):
    lines.append(f'== {ep} ({len(byep[ep])})')
    for v in sorted(byep[ep], key=lambda x: x['sec']):
        lines.append(f"   {v['t']:>7s}  [{v['text']}]")
open(os.path.join(B, 'review', 'dense3_final.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:60]))
