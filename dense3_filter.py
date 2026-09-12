# -*- coding: utf-8 -*-
"""密集扫描(修正版)候选后处理: 全库匹配 -> 按"只算台词"过滤 -> 输出待补清单。

过滤规则:
  1. 去掉首尾的帧计数器数字(画面右下有计数器, 会被一并读入);
  2. 排除: 纯数字/噪声、版权制作卡、片头片尾日文歌词与演职员表、图鉴/预告解说;
  3. 与**全库**双向包含度 >=0.7 -> 已收录;
  4. 与 ±8s 内库条目双向 >=0.6 -> 视为同句差异读取(已收录);
  5. 其余为"疑似漏句台词"。
"""
import json
import os
import re
import collections

B = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN = os.path.join(B, 'subtitle_clean')
D2 = os.path.join(B, 'review', 'dense2')
RES = os.path.join(B, 'review', 'dense3_dialogue.txt')

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
         '美術', '持道', '特殊', '視覚', '音響', '編集', '宣伝', '広報')
COPY = re.compile(r'版权|新创华|文化发展|中国大陆|上海新|株式会社|第\d+集|集罗布奥特曼')


def cn(s):
    return re.sub(r'[^\u4e00-\u9fff0-9]', '', s or '')


def strip_digits(s):
    s = re.sub(r'^\d+', '', s)
    s = re.sub(r'\d+$', '', s)
    return s


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

cands, tally = [], collections.Counter()
for f in sorted(os.listdir(D2)):
    if not f.endswith('.json'):
        continue
    d = json.load(open(os.path.join(D2, f), encoding='utf-8'))
    ep = d['ep']
    for c in d['cands']:
        t = cn(c['text'])
        s = strip_digits(t)
        if len(s) < 2 or len(re.sub(r'[^0-9]', '', s)) / max(1, len(s)) > 0.34:
            tally['噪声/纯数字'] += 1
            continue
        # 全库 / 邻域匹配
        best_all, best_all_arg = 0.0, None
        for lt in allt:
            if abs(len(lt) - len(s)) > 10:
                continue
            sc = score(s, lt)
            if sc > best_all:
                best_all, best_all_arg = sc, lt
                if sc >= 0.95:
                    break
        near = [lt for sec, lt in lib.get(ep, []) if abs(sec - c['sec']) <= 8]
        best_near = max((score(s, lt) for lt in near), default=0.0)
        if best_all >= 0.7 or best_near >= 0.6:
            tally['已收录'] += 1
            continue
        if COPY.search(s):
            tally['版权/标题卡'] += 1
            continue
        if any(w in s for w in LYRIC):
            tally['歌词/演职员表'] += 1
            continue
        if not any(w in s for w in STOP) and len(s) < 5:
            tally['不像中文台词'] += 1
            continue
        tally['疑似漏句台词'] += 1
        cands.append({'ep': ep, 't': c['t'], 'sec': c['sec'], 'text': s, 'raw': c['text'],
                      'frame': c.get('frame'), 'near': near[:3], 'best_near': round(best_near, 2),
                      'best_all': round(best_all, 2)})

print('候选分类:')
for k, v in tally.most_common():
    print(f'   {k}: {v}')
print(f'\n疑似漏句台词 {len(cands)} 条')
json.dump(cands, open(os.path.join(B, 'review', 'dense3_dialogue.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
lines = [f'疑似漏句台词 {len(cands)} 条(按集):', '']
byep = collections.defaultdict(list)
for c in cands:
    byep[c['ep']].append(c)
for ep in sorted(byep):
    lines.append(f'== {ep} ({len(byep[ep])} 条)')
    for c in sorted(byep[ep], key=lambda x: x['sec']):
        lines.append(f"   {c['t']:>7s}  [{c['text']}]   邻域最相近={c['best_near']} 库近邻={c['near'][:2]}")
open(RES, 'w', encoding='utf-8').write('\n'.join(lines))
print(f'写出 {RES}')
print('\n'.join(lines[:80]))
