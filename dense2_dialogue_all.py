# -*- coding: utf-8 -*-
"""补漏: 对 B 档(与库双向分 0.4~0.6)以及全部 765 条疑似台词, 做"像中文台词"筛选并输出, 逐类人工复核。

判据(偏宽, 宁可多列):
  * 排除版权/制作卡、歌词特征词、纯数字噪声
  * 要求: 含中文, 长度 3~40, 且至少含 1 个中文虚词 **或** 长度>=5(短句如「休想得逞」无虚词)
"""
import json
import os
import re

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
rows = json.load(open(os.path.join(B, 'review', 'dense2_clusters.json'), encoding='utf-8'))
STOP = ['的', '了', '是', '我', '你', '他', '她', '不', '在', '吗', '吧', '呢', '啊', '什么',
        '怎么', '这', '那', '们', '和', '就', '都', '也', '还', '要', '会', '有', '没', '很',
        '好', '来', '去', '给', '把', '被', '让', '说', '看', '想', '知道', '一个', '这么', '那么',
        '为', '对', '从', '到', '着', '过', '能', '可', '得', '又', '再', '才', '只', '自己']
LYRIC = ('何万回', '何百回', '何千回', '愛情', '友情', '交差', '繫', '未來', '未来', '絆', '諦',
         '絶対', '家族', '物語', '奇跡', '帰', '場所', '君', '僕', '笑顔', '笑顏', '勇気', '希望',
         '離', '結', '堅', '手手', '明日', '強', '羽', '声', '飛', '作詞', '作曲', '編曲', '操演',
         '監督', '撮影', '照明', '造形', '衣裳', '美術', '制作', '演技', '選曲', '整音', '効果',
         '応援', '協力', '設定', '監修', '進行', '助手')
COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新|株式会社|电视台|集罗布奥特曼|第\d+集')


def plen(t):
    return len(re.sub(r'[^\u4e00-\u9fff]', '', t))


def digit_ratio(t):
    return len(re.sub(r'[^0-9]', '', t)) / max(1, len(t))


out = []
for r in rows:
    t = r['rep']
    if COPY.search(t) or any(w in t for w in LYRIC):
        continue
    if plen(t) < 3 or len(t) > 40 or digit_ratio(t) > 0.35:
        continue
    ns = sum(1 for w in STOP if w in t)
    if ns < 1 and plen(t) < 5:
        continue
    out.append((r, ns))

out.sort(key=lambda x: (x[0]['best_score'], -x[0]['n']))
print(f'像中文台词的类: {len(out)}(全部 461 类中)')
lines = ['全部候选中"像中文台词"的类(逐类复核用):', '']
for r, ns in out:
    loc = ' '.join(f"{i['ep']}{i['t']}" for i in r['items'][:5])
    lines.append(f"  [{r['rep']}] ×{r['n']}  {loc}   最近库={r['best_lib']}({r['best_score']}) 虚词={ns}")
txt = '\n'.join(lines)
open(os.path.join(B, 'review', 'dense2_dialogue_all.txt'), 'w', encoding='utf-8').write(txt)
print(txt[:9000])
