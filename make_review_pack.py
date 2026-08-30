# -*- coding: utf-8 -*-
"""make_review_pack.py — 生成人工复核包（按集分类，供人眼快速扫视）

分类定义：
  A_分歧待查：v5 文本触发过 VL 复核条件（≥2 连续英文字母 或 日文假名），
             但 VL 未替换（VL 输出为空/疑似幻觉），且该条仍在 clean 库中。
             属于"两轮机器意见分歧、无人裁决"的条目 —— 复核价值最高。
  B_ASCII残留：clean 库中仍含 3+ 英文字母的条目（水印类残留）。

输出结构：
  review/Pxx/index.html        # 该集复核清单（卡片：帧图 + v5 原文 + 当前文本 + 原因）
  review/Pxx/frames/*.jpg      # 每复核条目 1 帧（ts+0.8s 处整帧缩略 960x540）
  review/index.html            # 总览导航页
  review/README.md             # 分类说明与统计
  review/summary.json          # 结构化清单（程序可读）

用法: python make_review_pack.py          # 全部 25 集
      python make_review_pack.py P07      # 仅 P07
"""
import glob
import json
import os
import re
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
V5_DIR = os.path.join(BASE, 'subtitle_paddle_v5')   # v5 server 全量结果
HYB_DIR = os.path.join(BASE, 'subtitle_hybrid')     # VL 复核后（含 vl_rechecked 标记）
CLEAN_DIR = os.path.join(BASE, 'subtitle_clean')    # Web 数据源（最终入库文本）
VIDEO_DIR = os.path.join(BASE, 'Videos')
OUT_DIR = os.path.join(BASE, 'review')

WORKERS = 6      # 抽帧并行进程数
W, H = 960, 540  # 缩略帧尺寸
FRAME_OFFSET_MS = 800  # 字幕起点后 0.8s 取帧

ASCII2 = re.compile(r'[A-Za-z]{2,}')         # v5 复核触发条件（连续 2+ 字母）
ASCII3 = re.compile(r'[A-Za-z]{3,}')         # clean 残留判定（3+ 字母）
KANA = re.compile(r'[\u3040-\u30ff]')        # 日文假名

EP_RE = re.compile(r'^\[(P\d{2})\]')


def parse_ts(ts):
    """'5m15s' -> 315（秒）；失败返回 None"""
    m = re.match(r'(\d+)m(\d+)s', ts)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def load_json(path):
    """读取单集 JSON，返回条目列表"""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def collect():
    """返回 {ep: {'v5': {ts: text}, 'rechecked': {ts}, 'clean': [(ts, text)]}}"""
    data = {}
    for f in sorted(glob.glob(os.path.join(CLEAN_DIR, '*.json'))):
        ep = os.path.splitext(os.path.basename(f))[0].split(']')[0].lstrip('[')
        data.setdefault(ep, {'v5': {}, 'rechecked': set(), 'clean': []})

    for f in sorted(glob.glob(os.path.join(V5_DIR, '*.json'))):
        ep = os.path.splitext(os.path.basename(f))[0].split(']')[0].lstrip('[')
        if ep not in data:
            data[ep] = {'v5': {}, 'rechecked': set(), 'clean': []}
        for r in load_json(f):
            data[ep]['v5'][r.get('timestamp')] = r.get('text', '')

    for f in sorted(glob.glob(os.path.join(HYB_DIR, '*.json'))):
        ep = os.path.splitext(os.path.basename(f))[0].split(']')[0].lstrip('[')
        if ep not in data:
            data[ep] = {'v5': {}, 'rechecked': set(), 'clean': []}
        for r in load_json(f):
            if r.get('vl_rechecked'):
                data[ep]['rechecked'].add(r.get('timestamp'))

    for f in sorted(glob.glob(os.path.join(CLEAN_DIR, '*.json'))):
        ep = os.path.splitext(os.path.basename(f))[0].split(']')[0].lstrip('[')
        for r in load_json(f):
            data[ep]['clean'].append((r.get('timestamp'), r.get('text', '')))
    return data


def pick(data):
    """按 A/B 分类挑选复核条目，返回 {ep: [(cat, ts, v5_text, cur_text)]}"""
    picked = {}
    for ep, d in sorted(data.items()):
        items = []
        for ts, cur in d['clean']:
            if not ts:
                continue
            # B 类：clean 库中 ASCII 残留（最可疑，优先展示）
            if ASCII3.search(cur):
                items.append(('B_ASCII残留', ts, d['v5'].get(ts, ''), cur))
                continue
            # A 类：v5 曾触发复核但 VL 未替换
            v5t = d['v5'].get(ts, '')
            if (ASCII2.search(v5t) or KANA.search(v5t)) and ts not in d['rechecked']:
                items.append(('A_分歧待查', ts, v5t, cur))
        # 排序：B 在前 → 可疑度（ASCII 字数降序）→ 时间序
        def score(it):
            cat, ts, v5t, cur = it
            ascii_n = len(re.findall(r'[A-Za-z]', v5t + cur))
            return (0 if cat.startswith('B') else 1, -ascii_n, parse_ts(ts) or 0)
        items.sort(key=score)
        if items:
            picked[ep] = items
    return picked


def grab_frame(args):
    """抽取单帧：返回 True/False。worker 专用，避免大对象传递"""
    video_path, ts, out_path = args
    sec = parse_ts(ts)
    if sec is None or not os.path.exists(video_path):
        return False
    cap = cv2.VideoCapture(video_path)
    ok = False
    try:
        for off in (FRAME_OFFSET_MS, 200):
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000 + off)
            ret, frame = cap.read()
            if ret and frame is not None:
                frame = cv2.resize(frame, (W, H))
                cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
                ok = True
                break
    finally:
        cap.release()
    return ok


def sanitize(name):
    """文件名安全化"""
    return re.sub(r'[^\w\u4e00-\u9fff.-]', '_', name)


def build_card(ep, cat, ts, v5t, cur, idx, prefix='frames/'):
    """生成单张复核卡片；prefix 控制帧图相对路径（分集页=frames/，总览页=Pxx/frames/）"""
    frame = f'{prefix}{sanitize(ts)}.jpg'
    v5_disp = v5t if v5t else '（无 v5 记录）'
    cur_disp = cur if cur else '（空）'
    if cat.startswith('B'):
        badge = '<span class="badge b">B·ASCII残留</span>'
    else:
        badge = '<span class="badge a">A·分歧待查</span>'
    return f'''<div class="card">
  <div class="num">{idx:03d}</div>
  <img src="{frame}" alt="{ts}" loading="lazy" onerror="this.style.display='none'">
  <div class="info">
    {badge}<div class="ts">⏱ {ts}（{parse_ts(ts)}s）· {ep}</div>
    <div class="row"><span class="lab">v5 原文</span><code>{v5_disp}</code></div>
    <div class="row"><span class="lab cur">当前文本</span><code>{cur_disp}</code></div>
  </div>
</div>'''


def build_html(ep, items, ep_title):
    """生成单集复核 HTML（卡片列表）"""
    cards = [build_card(ep, cat, ts, v5t, cur, i) for i, (cat, ts, v5t, cur) in enumerate(items, 1)]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{ep} 复核清单</title><style>
body{{margin:0;background:#171720;color:#e8e8f0;font-family:"Microsoft YaHei",sans-serif}}
header{{padding:16px 24px;background:#232334;border-bottom:1px solid #3a3a55}}
header a{{color:#8ab4ff;text-decoration:none}}
h1{{font-size:20px;margin:4px 0}}
.cat-list{{padding:4px 24px;font-size:13px;color:#aaa}}
.card{{display:flex;gap:16px;align-items:flex-start;margin:14px 24px;background:#262638;border-radius:10px;padding:12px}}
.card img{{width:460px;max-width:44%;border-radius:8px;background:#000}}
.num{{font-size:14px;color:#7f8;width:34px;font-weight:bold}}
.info{{flex:1;min-width:0}}
.badge{{font-size:12px;padding:2px 8px;border-radius:10px;color:#fff}}
.badge.a{{background:#8a6d3b}} .badge.b{{background:#a94442}}
.ts{{font-size:13px;color:#9fd;margin:6px 0}}
.row{{margin:4px 0;font-size:14px}}
.lab{{color:#8a8aa0;margin-right:8px}}
.lab.cur{{color:#7cc}}
code{{background:#1d1d2b;padding:2px 6px;border-radius:4px;color:#e5e5f0;font-size:14px}}
</style></head><body>
<header><a href="../index.html">← 返回总览</a><h1>{ep}《{ep_title}》复核清单（{len(items)} 条）</h1></header>
<div class="cat-list">A=两轮机器分歧（VL 未替换）· B=clean 后仍有 ASCII 残留</div>
{''.join(cards)}
</body></html>'''


def main():
    args = sys.argv[1:]
    targets = set(a for a in args if EP_RE.match(a)) or set()
    data = collect()
    picked = pick(data)

    os.makedirs(OUT_DIR, exist_ok=True)
    summary = {}
    n_a = n_b = 0
    for ep, items in picked.items():
        if targets and ep not in targets:
            continue
        frames_dir = os.path.join(OUT_DIR, ep, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        ep_title = ''
        for f in sorted(glob.glob(os.path.join(VIDEO_DIR, '*.mp4'))):
            if f.startswith(os.path.join(VIDEO_DIR, f'[{ep}]')):
                ep_title = os.path.splitext(os.path.basename(f))[0].split(']', 1)[1].lstrip()
                break
        # 并行抽帧
        jobs = []
        for _i, (cat, ts, _v5t, _cur) in enumerate(items):
            out = os.path.join(frames_dir, sanitize(ts) + '.jpg')
            video = None
            for f in sorted(glob.glob(os.path.join(VIDEO_DIR, '*.mp4'))):
                if f.startswith(os.path.join(VIDEO_DIR, f'[{ep}]')):
                    video = f
                    break
            jobs.append((video or '', ts, out))
        # 顺序抽帧（沙箱禁止 multiprocessing 管道；282 帧约 2-4 分钟可接受）
        results = [grab_frame(j) for j in jobs]
        ok_n = sum(1 for r in results if r)
        # 写 HTML
        with open(os.path.join(OUT_DIR, ep, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(build_html(ep, items, ep_title))
        cnt_a = sum(1 for c, *_ in items if c.startswith('A'))
        cnt_b = len(items) - cnt_a
        n_a += cnt_a
        n_b += cnt_b
        summary[ep] = {'title': ep_title, 'total': len(items), 'A': cnt_a, 'B': cnt_b, 'frames_ok': ok_n}
        print(f'{ep} {ep_title}: 共{len(items)} 条 (A={cnt_a}, B={cnt_b}), 帧成功 {ok_n}/{len(items)}')

    # 总览 README + summary.json
    with open(os.path.join(OUT_DIR, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('# 人工复核包\n\n')
        f.write('## 分类说明\n- **A·分歧待查**：v5 触发过 VL 复核但 VL 未替换（两轮机器意见分歧），复核价值最高。\n')
        f.write('- **B·ASCII残留**：clean 库中仍含 3+ 英文字母（水印类残留），基本可判定为错。\n\n')
        f.write(f'## 统计\n| 集 | 标题 | A | B | 帧成功 |\n|---|---|---|---|---|\n')
        for ep, s in sorted(summary.items()):
            f.write(f'| {ep} | {s["title"]} | {s["A"]} | {s["B"]} | {s["frames_ok"]}/{s["total"]} |\n')
        f.write(f'\n**合计：A={n_a} 条，B={n_b} 条，共 {n_a+n_b} 条**。打开 `index.html` 全览。\n')

    # 总览页：一页全量卡片流（按集分段），打开即可直接看全部帧图
    sections = []
    for ep, s in sorted(summary.items()):
        items = picked[ep]
        # 顺序编号：每集内一条编号，整页累计编号
        cards = [build_card(ep, cat, ts, v5t, cur, i, prefix=f'{ep}/frames/')
                 for i, (cat, ts, v5t, cur) in enumerate(items, 1)]
        sections.append(f'<section><h2>{ep} 《{s["title"]}》 — {len(items)} 条（A:{s["A"]} B:{s["B"]}）</h2>{chr(10).join(cards)}</section>')
    with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>字幕人工复核全览</title>
<style>body{{margin:0;background:#171720;color:#e8e8f0;font-family:"Microsoft YaHei",sans-serif}}
header{{padding:16px 24px;background:#232334;border-bottom:1px solid #3a3a55}}
h1{{font-size:20px;margin:4px 0}}
.info{{color:#aaa;font-size:13px}}
section{{margin:0 0 10px 0}}
section>h2{{font-size:16px;margin:18px 24px 4px;color:#cde;border-left:4px solid #8ab4ff;padding-left:10px}}
.card{{display:flex;gap:16px;align-items:flex-start;margin:10px 24px;background:#262638;border-radius:10px;padding:12px}}
.card img{{width:460px;max-width:44%;border-radius:8px;background:#000}}
.num{{font-size:14px;color:#7f8;width:34px;font-weight:bold}}
.info{{flex:1;min-width:0}}
.badge{{font-size:12px;padding:2px 8px;border-radius:10px;color:#fff}}
.badge.a{{background:#8a6d3b}} .badge.b{{background:#a94442}}
.ts{{font-size:13px;color:#9fd;margin:6px 0}}
.row{{margin:4px 0;font-size:14px}}
.lab{{color:#8a8aa0;margin-right:8px}}
.lab.cur{{color:#7cc}}
code{{background:#1d1d2b;padding:2px 6px;border-radius:4px;color:#e5e5f0;font-size:14px}}
</style></head><body>
<header><h1>🤖 R/B 字幕人工复核全览（{n_a+n_b} 条）</h1>
<div class="info">A·分歧待查 = v5 触发复核查但 VL 未替换；B·ASCII残留 = clean 后仍含 3+ 英文字母。所有图片直接显示，无需点进分集页。</div></header>
{chr(10).join(sections)}
</body></html>''')
    with open(os.path.join(OUT_DIR, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'\n完成: A={n_a}, B={n_b}, 输出到 {OUT_DIR}')


if __name__ == '__main__':
    main()
