# -*- coding: utf-8 -*-
"""q_locate2_apply.py — 把人工看图后的 q_locate2 判定并入 q_manual_verdicts.json。

输入: review/q_locate2_verdicts.json
      {"accept": [{"ep","ts","old","new","why"}], "reject": [{"ep","ts","why"}]}
写入: review/q_manual_verdicts.json 的 frame_apply / reject (按 ep+ts 去重)
落盘: 之后由 q_apply2.py 真正改 subtitle_clean/*.json
用法: python q_locate2_apply.py [--dry]
"""
import json
import os
import sys

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEW = os.path.join(B, 'review')
MAN = os.path.join(REVIEW, 'q_manual_verdicts.json')
VER = os.path.join(REVIEW, 'q_locate2_verdicts.json')


def main():
    dry = '--dry' in sys.argv
    man = json.load(open(MAN, encoding='utf-8'))
    if not os.path.exists(VER):
        print(f'缺少 {VER}')
        return
    v = json.load(open(VER, encoding='utf-8'))
    have = {(r['ep'], r['ts']) for r in man.get('frame_apply', [])}
    have_r = {(r['ep'], r['ts']) for r in man.get('reject', [])}
    n_add = n_rej = 0
    for r in v.get('accept', []):
        if (r['ep'], r['ts']) in have:
            continue
        man.setdefault('frame_apply', []).append(
            {'ep': r['ep'], 'ts': r['ts'], 'old': r['old'], 'new': r['new'],
             'why': r.get('why', 'q_locate2 原帧重识别')})
        n_add += 1
    for r in v.get('reject', []):
        if (r['ep'], r['ts']) in have_r:
            continue
        man.setdefault('reject', []).append(
            {'ep': r['ep'], 'ts': r['ts'], 'why': r.get('why', 'q_locate2 判为噪声')})
        n_rej += 1
    print(f'并入 accept {n_add} 条 / reject {n_rej} 条'
          f'(现有 frame_apply {len(man.get("frame_apply", []))} / reject {len(man.get("reject", []))})')
    if dry:
        print('（预演, 未写盘）')
        return
    json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已写入', MAN)


if __name__ == '__main__':
    main()
