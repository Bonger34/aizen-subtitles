# -*- coding: utf-8 -*-
"""merge_vl.py — 将 vl_out/（VL 增量复核输出，基于快照）合并回 subtitle_clean/

匹配键：文本（校准只改 timestamp 不改 text，因此按 text 匹配）
  - vl_out 中 vl_rechecked 条目（before=快照文本, after=VL 文本）
  - 在 subtitle_clean（校准后）中找 text == before 的条目 → 替换 text = after
  - 找不到（条目被校准去重删除）→ 跳过并计数
合并后：相邻 ±3s 同文本再次去重（VL 可能把变体对统一）
用法: python merge_vl.py
"""
import json
import os
import re

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')
VL_OUT = os.path.join(BASE, 'archive/datasets/vl_out')
SNAP_DIR = os.path.join(BASE, 'archive', 'datasets', 'vl_input_snapshot')

# VL 输出可能把画面文字拼入头尾（如「…郊游Schallplatt」「CH₄谁会…」）：
# 切掉文本头/尾的 ASCII 字母段（>=2 字母），剩余为有效中文则用切后文本
ASCII_SEG_RE = re.compile(r'[A-Za-z]{2,}')


def parse_ts(ts):
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i][j - 1], dp[i - 1][j])
    return dp[m][n]


def similar_enough(before, after, min_lcs=0.3):
    """VL 替换保护：短句/低相似度替换大概率是 VL 误读画面文字（如「好了」→「凉州府」）
    要求替换前后文本 LCS>=0.3（按 before 归一），否则拒绝此次 VL 替换"""
    if not before or not after:
        return True
    return lcs(before, after) / len(before) >= min_lcs


def strip_ascii_edges(t):
    """去除文本头/尾的 ASCII 字母段（>=2 字母）；剩余纯中文有效则返回切后文本，否则原样返回"""
    m = re.match(r'^[A-Za-z\d₀-₉\- ]+', t) or re.match(r'.*', t)
    # 头：连续 ASCII（含数字/下划线/空格）段
    head = re.match(r'^[A-Za-z\d\s₀-₉\-_]{2,}?', t)
    tail = re.search(r'[A-Za-z\d\s₀-₉\-_]{2,}$', t)
    cands = []
    if head and head.group(0):
        cands.append(t[head.end():])
    if tail and tail.group(0):
        cands.append(t[:tail.start()])
    for c in cands:
        c = c.strip()
        cjk = len(re.findall(r'[\u4e00-\u9fff]', c))
        if c and cjk / len(c) >= 0.6 and cjk >= 2:
            return c
    return t


def dedup(data):
    data.sort(key=lambda r: parse_ts(r.get('timestamp', '')) or 0)
    out = []
    for r in data:
        dup = False
        for o in out[-4:]:
            if o.get('text', '') and o.get('text') == r.get('text') and \
               abs((parse_ts(o.get('timestamp', '')) or 0) - (parse_ts(r.get('timestamp', '')) or 0)) <= 3:
                dup = True
                break
        if not dup:
            out.append(r)
    return out


def main():
    n_applied = n_missed = n_rejected = 0
    rejected_all = []
    for fname in sorted(os.listdir(VL_OUT)):
        if not fname.endswith('.json'):
            continue
        ep = fname.split(']')[0].lstrip('[')
        cur_path = os.path.join(CLEAN_DIR, fname)
        snap_path = os.path.join(SNAP_DIR, fname)
        if not os.path.exists(cur_path) or not os.path.exists(snap_path):
            continue
        vl_data = json.load(open(os.path.join(VL_OUT, fname), encoding='utf-8'))
        snap = {r.get('timestamp'): r.get('text', '') for r in json.load(open(snap_path, encoding='utf-8'))}
        cur = json.load(open(cur_path, encoding='utf-8'))
        # 建立 text → 条目索引（校准后文本未变，按文本匹配）
        by_text = {}
        for r in cur:
            by_text.setdefault(r.get('text', ''), []).append(r)
        ep_applied = ep_missed = ep_rejected = 0
        for r in vl_data:
            if not r.get('vl_rechecked'):
                continue
            before = snap.get(r.get('timestamp'), '')   # 快照中的复核前文本
            after = r.get('text', '')
            if not before or not after:
                continue
            # 保护：低相似度替换（短句被 VL 误读画面文字）→ 拒绝，保留原文本
            if not similar_enough(before, after):
                ep_rejected += 1
                rejected_all.append({'ep': ep, 'ts': r.get('timestamp'), 'before': before, 'after': after})
                print(f'  [拒] {ep} {r.get("timestamp")}「{before}」→「{after}」(LCS 过低，保留原文)', flush=True)
                continue
            targets = by_text.get(before, [])
            if not targets:
                ep_missed += 1
                continue
            for t in targets:
                t['text'] = after
                t['vl_rechecked'] = True
            ep_applied += 1
        # VL 输出头尾 ASCII 清理（如「…郊游Schallplatt」「CH₄谁会…」）
        n_strip = 0
        for r in cur:
            t = r.get('text', '')
            if ASCII_SEG_RE.search(t):
                clean_t = strip_ascii_edges(t)
                if clean_t != t:
                    print(f'  [清] {r.get("timestamp")}「{t}」→「{clean_t}」', flush=True)
                    r['text'] = clean_t
                    n_strip += 1
        cur = dedup(cur)
        json.dump(cur, open(cur_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        n_applied += ep_applied
        n_missed += ep_missed
        n_rejected += ep_rejected
        print(f'{ep}: 应用VL替换 {ep_applied} 条，未找到 {ep_missed} 条，拒绝 {ep_rejected} 条，合并后 {len(cur)} 条')
    json.dump(rejected_all, open(os.path.join(BASE, 'review', 'merge_vl_rejected.json'),
                                   'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n总计: 应用 {n_applied}，未找到 {n_missed}，拒绝 {n_rejected}')


if __name__ == '__main__':
    main()
