# -*- coding: utf-8 -*-
"""收敛检验: 用扩充后的库重新判定全部扫描候选, 看还剩多少"库中没有的台词"。

并把"不像中文台词"这一类(短句/无虚词)单独列出, 因为真漏句可能藏在这里(如「好痛」「喂」)。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
D2 = os.path.join(B, 'review', 'dense2')
STOP = ['的', '了', '是', '我', '你', '他', '她', '不', '在', '吗', '吧', '呢', '啊', '什么',
        '怎么', '这', '那', '们', '和', '就', '都', '也', '还', '要', '会', '有', '没', '很',
        '好', '来', '去', '给', '把', '被', '让', '说', '看', '想', '知道', '一个', '这么',
        '那么', '为', '对', '从', '到', '着', '过', '能', '可', '得', '又', '再', '才', '只',
        '自己', '大家', '一起', '现在', '已经', '因为', '所以', '但是', '可是', '如果', '应该']
LYRIC = ('何万回', '何百回', '何千回', '愛情', '友情', '交差', '繫', '未來', '未来', '絆', '諦',
         '絶対', '家族', '物語', '奇跡', '帰', '場所', '僕', '笑顔', '笑顏', '勇気', '希望',
         '離', '結', '堅', '手手', '明日', '強', '羽', '声', '飛', '瞬間', '嘘', '君',
         '作詞', '作曲', '編曲', '操演', '監督', '撮影', '照明', '造形', '衣裳', '美術', '制作',
         '演技', '選曲', '整音', '効果', '応援', '協力', '設定', '監修', '進行', '助手', '装飾',
         '持道', '特殊', '視覚', '音響', '編集', '宣伝', '広報', '不经意地翻开相册', '仿若能天长地久',
         '夕阳西下', '望而却步', '牵绊', '那句谢谢', '说不出口', '没有永恒', '夕阳下的笑容')
GUIDE = ('奥特曼', '奥特战士', '怪兽', '骨兽', '必杀技', '水晶', '身高', '体重', '图鉴', '形态',
         '变身', '巨型生物', '哥莫拉', '格尔吉欧', '传说', '雷德王', '金古桥', '达达', '巴萨',
         '罗索', '布鲁', '泰罗', '赛文', '银河', '迪迦', '欧布', '维克特利', '艾克斯', '赛罗')
COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新|株式会社|第\d+集|集罗布奥特曼')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def strip_digits(s):
    return re.sub(r'\d+$', '', re.sub(r'^\d+', '', s))


def score(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return min(sum(1 for ch in a if ch in sb) / len(a), sum(1 for ch in b if ch in sa) / len(b))


lib = {}
allt = []
for fn in sorted(os.listdir(CLEAN)):
    if fn.endswith('.json'):
        ep = fn[1:4]
        lib[ep] = []
        for e in json.load(open(os.path.join(CLEAN, fn), encoding='utf-8')):
            t = cn(e.get('text'))
            if t:
                sec = int(e['timestamp'].split('m')[0]) * 60 + int(e['timestamp'].split('m')[1].rstrip('s'))
                lib[ep].append((sec, t))
                allt.append(t)
print('新库条目', len(allt))

n_all = 0
tally = collections.Counter()
dial, short = [], []
for f in sorted(os.listdir(D2)):
    if not f.endswith('.json'):
        continue
    d = json.load(open(os.path.join(D2, f), encoding='utf-8'))
    ep = d['ep']
    for c in d['cands']:
        n_all += 1
        t = strip_digits(cn(c['text']))
        if len(t) < 2 or len(re.sub(r'[^0-9]', '', t)) / max(1, len(t)) > 0.34:
            tally['噪声/纯数字'] += 1
            continue
        best = 0.0
        for lt in allt:
            if abs(len(lt) - len(t)) > 10:
                continue
            sc = score(t, lt)
            if sc > best:
                best = sc
                if best >= 0.95:
                    break
        near = [lt for sec, lt in lib.get(ep, []) if abs(sec - c['sec']) <= 8]
        bn = max((score(t, lt) for lt in near), default=0.0)
        if best >= 0.7 or bn >= 0.6:
            tally['已收录'] += 1
            continue
        if COPY.search(t):
            tally['版权/标题卡'] += 1
            continue
        if any(w in t for w in LYRIC):
            tally['歌词/演职员表'] += 1
            continue
        if any(w in t for w in GUIDE):
            tally['图鉴/预告解说'] += 1
            continue
        if not any(w in t for w in STOP) and len(t) < 5:
            tally['短文本(无虚词, 需人工判断)'] += 1
            short.append({'ep': ep, 't': c['t'], 'text': t, 'best_all': round(best, 2),
                          'near': near[:2]})
            continue
        tally['疑似漏句台词'] += 1
        dial.append({'ep': ep, 't': c['t'], 'sec': c['sec'], 'text': t,
                     'best_all': round(best, 2), 'near': near[:2]})

print(f'候选 {n_all}')
for k, v in tally.most_common():
    print(f'   {k}: {v}')
json.dump({'dialogue': dial, 'short': short},
          open(os.path.join(B, 'review', 'converge.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\n疑似漏句台词 {len(dial)} 条:')
for c in sorted(dial, key=lambda x: (x['ep'], x['sec']))[:60]:
    print(f"   {c['ep']} {c['t']:>7s}  [{c['text']}]  全库最高分={c['best_all']} 邻域={c['near']}")
print(f'\n短文本 {len(short)} 条(前 60):')
for c in sorted(short, key=lambda x: (x['ep'], x['t']))[:60]:
    print(f"   {c['ep']} {c['t']:>7s}  [{c['text']}]  全库最高分={c['best_all']}")
