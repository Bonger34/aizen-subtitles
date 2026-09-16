# -*- coding: utf-8 -*-
"""q_outscope_delete.py — 删除可证的"带外条目"(版权卡/日文/演职员表/标题卡乱码)。

边界说明(重要): 本轮实测发现**不能用时间位置当判据** —— `≥21m30s` 的 819 条里有大量真台词
(P01 21m30s「你怎么会在这里」、21m48s「今晚吃寿喜锅」)。因此判据全部基于**画面证据**:

  A 版权卡      文本含 版权/中国大陆
  B 日文        该条目时间戳附近的画面读数是日文(假名占比 >0.15)
  C 演职员表    画面读数含职员表关键词(制作/進行/脚本/監督/撮影/編集/構成/音楽/主題歌/
                キャスト/仕上げ/ドローン/画コンテ/衣装/ヘアメイク/助監督/プロデューサー/
                制作主任/制作進行/製作 等), 或文本本身是日式姓名碎片(≥2 个姓名用字且 ≤12 字)
  D 标题卡乱码  画面读数为「第N集...」而库文本并不含该标题

**不删**: 时间在片尾段但画面读数是中文台词/下集预告旁白的条目(如「下集也要收看哦」), 以及
P25 这种 ED 与台词叠在一起的集 —— 那些需要逐条判断, 不属"可证带外"。

用法: python q_outscope_delete.py [--dry]
输出: review/q_outscope_delete.json + 改 subtitle_clean/*.json
"""
import json
import os
import re
import shutil
import sys
import time
from collections import Counter

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
CLEAN = os.path.join(B, 'subtitle_clean')
KANA = set(range(0x3040, 0x30FF))
CREDIT = ('制作', '製作', '進行', '脚本', '監督', '撮影', '編集', '構成', '音楽', '主題歌',
          'キャスト', '仕上げ', 'ドローン', '画コンテ', '衣装', 'ヘアメイク', '助監督',
          'プロデューサー', 'アニメーション', '美術', '音響', '効果', '協力', '技術',
          '制作主任', '制作進行', '制作応援', 'VFX', 'CG', 'オープニング', 'エンディング')
NAME_CHARS = set('本祥渡太春演稲垣技事井田山川口黒林藤岡坂野池谷大森中村西東南北裕輔泰')

# 文本自身看着像真台词、被判据误伤的 —— 逐条看过后排除, 不删
KEEP = {
    ('P06', '4m11s'),    # 让T恤大卖让T恤大卖   (命中"大"等姓名用字)
    ('P11', '9m17s'),    # 大家要看清事实       (同上)
    ('P15', '3m04s'),    # 现在怪兽已经被爱染科技公司捕获 (D 规则误伤)
    ('P16', '3m22s'),    # 你抽什么风啊         (D 规则误伤)
    ('P25', '23m34s'),   # 开工干活吧原田笙太    (真台词+职员表混在一起, 转人工)
    ('P25', '22m28s'),   # 小神野黄爸爸面川忠久  (同上)
}


def kana_ratio(s):
    return sum(1 for c in s if ord(c) in KANA) / max(1, len(s))


def main():
    dry = '--dry' in sys.argv
    reads = {}
    for f in os.listdir(REVIEW):
        if f.startswith('q_tsreada') and f.endswith('.json'):
            for r in json.load(open(os.path.join(REVIEW, f), encoding='utf-8')):
                reads[(r['ep'], r['ts'])] = [t for rd in r['reads'] for t in rd['texts']]

    lib = {}
    files = {}
    for f in sorted(os.listdir(CLEAN)):
        if not (f.endswith('.json') and re.match(r'^\[P\d+\]', f)):
            continue
        ep = re.search(r'\[(P\d+)\]', f).group(1)
        files[ep] = f
        for e in json.load(open(os.path.join(CLEAN, f), encoding='utf-8')):
            lib[(ep, e.get('timestamp'))] = e.get('text', '')

    hits, by_why = [], Counter()
    for (ep, ts), old in lib.items():
        if (ep, ts) in KEEP:
            continue
        u = reads.get((ep, ts), [])
        joined = ' '.join(u)
        pure = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', old or '')
        why = None
        # 只用**文本自身**作判据 —— 基于"该时刻读数"的判据(B/C)实测会大量误伤:
        # P18 1m22s「制作T恤吗」被"制作"命中, P05 5m10s「要勒紧这里对吗」被邻句假名带偏。
        if '版权' in old or '中国大陆' in old:
            why = 'A 版权卡'
        elif (len(pure) <= 12 and sum(1 for c in pure if c in NAME_CHARS) >= 2
              and not re.search(r'[的了是我你他不在有]', pure)):
            why = 'C2 日式姓名碎片'
        elif re.search(r'^\s*[集下卞]\s*罗布奥特曼', old or '') or \
                re.fullmatch(r'[一二三四五六七八九十]{1,3}', pure or ''):
            why = 'D 标题卡/预告乱码'
        if why:
            hits.append({'ep': ep, 'ts': ts, 'old': old, 'why': why})
            by_why[why] += 1

    print(f'可证带外条目 {len(hits)} 条:')
    for k, v in by_why.most_common():
        print(f'   {k}: {v}')
    print('\n抽样 15 条:')
    for h in hits[:15]:
        print(f"   {h['ep']} {h['ts']:>7s} [{h['old'][:30]}]  ({h['why']})")

    by_ep = {}
    for h in hits:
        by_ep.setdefault(h['ep'], set()).add(h['ts'])
    removed = 0
    for ep, tss in sorted(by_ep.items()):
        p = os.path.join(CLEAN, files[ep])
        data = json.load(open(p, encoding='utf-8'))
        keep = [e for e in data if e.get('timestamp') not in tss]
        removed += len(data) - len(keep)
        if not dry:
            shutil.copy2(p, p + '.bak_outscope')
            json.dump(keep, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  {ep}: -{len(data) - len(keep)} 条 (剩 {len(keep)})')
    out = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dry': dry,
           'n': len(hits), 'n_removed': removed, 'by_why': dict(by_why), 'hits': hits}
    json.dump(out, open(os.path.join(REVIEW, 'q_outscope_delete.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\n合计删除 {removed} 条{'（预演）' if dry else ''}")
    print('输出: review/q_outscope_delete.json')


if __name__ == '__main__':
    main()
