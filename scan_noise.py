# -*- coding: utf-8 -*-
"""scan_noise.py — 确定性噪声净化（提升计划 · 阶段 1）

规则（宁少勿误，只做绝对确定的）：
  R2  数字尾/头噪声：t 去掉尾(头)部 1-3 个数字后 == 相邻 ±7s 某条 t' 的文本
      → 删 t（如「…的时候1」「…东西78」「…啊03」，数字为画面噪声）
  R3  同 ts 多条：时间戳相同且 LCS>=0.6 → 保留最长一条，删其余
  其余未定项（非数字字的互含残句、近重复变体、孤立短句）仅标记，
  交由阶段 2 VL 复核判断（避免误删真实台词如「妈妈」「好痛好痛啊」）

用法: python scan_noise.py --ep P01        # dry-run 预览该集
      python scan_noise.py --ep P01 --apply  # 应用
"""
import json
import os
import re
import shutil
import sys

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
BACKUP_DIR = os.path.join(BASE, 'archive', 'datasets', 'subtitle_clean_v1_noise')


def sec(s):
    m = re.match(r'(\d+)m(\d+)s', s)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def clean_of(ep):
    for fname in os.listdir(CLEAN_DIR):
        if fname.startswith(f'[{ep}]') and fname.endswith('.json'):
            return os.path.join(CLEAN_DIR, fname)
    return None


def find_neighbors(data, idx, window=3):
    """返回 ±window 秒内、文本长度 >= cur*0.6 的相邻条目列表"""
    out = []
    s = sec(data[idx]['timestamp'])
    for j, r in enumerate(data):
        if j == idx or abs(sec(r['timestamp']) - s) > window:
            continue
        out.append((j, r['text'].strip()))
    return out


def classify(data):
    """返回 (删除集 {index: 原因}, 标记集 [(idx, 类型)])"""
    drop = {}
    marks = []
    for i, r in enumerate(data):
        t = r.get('text', '').strip()
        if not t:
            continue
        # R3: 同 ts 且 LCS>=0.6 → 保留最长
        same_ts = [j for j, o in enumerate(data) if j != i and o.get('timestamp') == r.get('timestamp')]
        if same_ts:
            for j in same_ts:
                if len(data[j].get('text', '')) <= len(t) and lcs(t, data[j].get('text', '')) >= 0.6:
                    drop[j] = 'R3同ts重复(保留最长)'
            continue
        dropped = False
        # R2: 数字尾/头噪声（仅数字，避免误伤「好痛好痛啊」类真实台词）
        for j, to in find_neighbors(data, i, 7):
            if to == t:
                continue
            for k in (1, 2, 3):
                if len(t) > k and re.fullmatch(r'\d{' + str(k) + r'}', t[-k:]) and t[:-k] == to:
                    drop[i] = 'R2数字尾噪'
                    dropped = True
                    break
                if len(t) > k and re.fullmatch(r'\d{' + str(k) + r'}', t[:k]) and t[k:] == to:
                    drop[i] = 'R2数字头噪'
                    dropped = True
                    break
            if dropped:
                break
        if i in drop:
            continue
        # 未定项标记（交阶段2 VL）：
        #  V2 互含待决：与相邻 ±3s 条目互为子串（非数字尾，可能真句）
        #  V1 近重复变体：±3s LCS>=0.85 且文本不同
        #  V3 孤立超短句：<=2 字
        v2 = v1 = False
        for j, to in find_neighbors(data, i, 3):
            if to == t:
                continue
            if len(t) >= 2 and len(to) >= 2 and (t in to or to in t):
                v2 = True
                break
        if not v2:
            for j, to in find_neighbors(data, i, 3):
                if len(to) >= 4 and len(t) >= 4 and lcs(t, to) / min(len(t), len(to)) >= 0.85 and to != t:
                    v1 = True
                    break
        if v2:
            marks.append((i, 'V2互含待决'))
        elif v1:
            marks.append((i, 'V1近重复变体'))
        elif len(t) <= 2:
            marks.append((i, 'V3孤立超短句'))
    return drop, marks


def main():
    """无 --ep 时全量处理；dry-run 输出摘要+候选JSON，--apply 应用"""
    args = sys.argv[1:]
    ep = None
    apply = False
    if '--ep' in args:
        ep = args[args.index('--ep') + 1]
    if '--apply' in args:
        apply = True
    targets = [os.path.join(CLEAN_DIR, f) for f in sorted(os.listdir(CLEAN_DIR))
               if f.endswith('.json') and re.match(r'^\[P\d{2}\]', f)
               and (ep is None or f.startswith(f'[{ep}]'))]

    if not apply and not os.path.exists(BACKUP_DIR):
        # 应用前先整体备份，保证可回滚
        shutil.copytree(CLEAN_DIR, BACKUP_DIR)
        print(f'备份 -> {BACKUP_DIR}')

    all_drop = []
    all_marks = []
    for path in targets:
        epx = os.path.basename(path)[:5]
        data = json.load(open(path, encoding='utf-8'))
        data.sort(key=lambda r: sec(r.get('timestamp', '')))
        drop, marks = classify(data)
        print(f'{epx}: 共{len(data)} 待删{len(drop)} 待VL{len(marks)}'
              + (f'  删除: ' + '; '.join(f'{data[i]["timestamp"]}「{data[i]["text"][:18]}」({drop[i][:14]})'
                                         for i in drop) if drop else ''))
        for i, r in enumerate(data):
            if i in drop:
                all_drop.append({'ep': epx, 'ts': r['timestamp'], 'text': r['text'], 'reason': drop[i]})
            elif any(i == mi for mi, _ in marks):
                typ = dict(marks)[i]
                all_marks.append({'ep': epx, 'ts': r['timestamp'], 'text': r['text'], 'type': typ})
        if apply and drop:
            kept = [r for i, r in enumerate(data) if i not in drop]
            json.dump(kept, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 候选明细落盘供审阅/后续 VL 使用
    os.makedirs(os.path.join(BASE, 'review'), exist_ok=True)
    json.dump({'drop': all_drop, 'marks': all_marks},
              open(os.path.join(BASE, 'review', 'noise_candidates_all.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'\n总计: 待删 {len(all_drop)} 条' + ('（已应用）' if apply else '（dry-run，加 --apply 执行）')
          + f'，待 VL 判断 {len(all_marks)} 条 → review/noise_candidates_all.json')


if __name__ == '__main__':
    main()
