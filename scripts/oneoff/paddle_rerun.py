# paddle_rerun.py — 用 PaddleOCR 官方 PP-OCRv5 server 重跑字幕 OCR
# - 管线与 rerun_ocr.py 一致：分组(≤2s+LCS≥0.6) → ts±1 抽3帧 → 增强 → 取最长 → 合并 → 全局去重
# - 输出 subtitle_paddle_v5/（不覆盖原 subtitle/）
import cv2, os, re, json, sys, time
import numpy as np
from paddleocr import PaddleOCR
import os as _os, sys as _sys  # noqa: E402  -- 搬家后跨目录引用 scripts/pipeline 的共用库
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "scripts", "pipeline"))
from params import SUBTITLE_AREA

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(BASE, "Videos")
SRC_DIR = os.path.join(BASE, "subtitle")
DST_DIR = os.path.join(BASE, "subtitle_paddle_v5")  # 验证期独立目录
PATTERN = re.compile(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]')

LCS_THRESHOLD = 0.6   # 同句判定
TIME_GAP = 2          # 时间差阈值（秒）
OFFSETS = (-1, 0, 1)  # ts±1 窗口（投票乱序风险高，回归取最长）

print("加载 PaddleOCR PP-OCRv5 server（GPU）...")
os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "BOS")
ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_server_det",
    text_recognition_model_name="PP-OCRv5_server_rec",
    lang="ch", device="gpu",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    text_det_limit_side_len=960,   # 增强图 3440 宽，64 太小检测不到
)

def parse_ts(ts):
    m = re.match(r"(\d+)m(\d+)s", ts)
    if not m: return None
    return int(m.group(1))*60 + int(m.group(2))

def lcs_ratio(a, b):
    if not a or not b: return 0
    m, n = len(a), len(b)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1]+1
            else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]/m

def enhance_subtitle(frame_bgr):
    """裁剪字幕区 + 放大2x + 灰度 + CLAHE + 锐化（回退用）"""
    crop = frame_bgr[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
    h, w = crop.shape[:2]
    up = cv2.resize(crop, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    blur = cv2.GaussianBlur(enhanced, (0,0), 1.5)
    sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

def extract_white_text(frame_bgr):
    """亮色文字提取：白字黑描边 → 黑底白字；极端情况回退原增强"""
    crop = frame_bgr[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
    h, w = crop.shape[:2]
    up = cv2.resize(crop, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
    hsv = cv2.cvtColor(up, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:,:,2] >= 235) & (hsv[:,:,1] <= 60)).astype(np.uint8) * 255
    ratio = float(mask.mean()) / 255.0
    if ratio < 0.005 or ratio > 0.25:  # 无白字(OP歌词)/亮白背景 → 回退
        return enhance_subtitle(frame_bgr)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)  # 黑底白字

def vote_text(texts):
    """多帧逐字投票：多数胜出；无多数取最长帧；空帧跳过；最差=取最长
    相似度门控：3 帧两两 LCS<0.6 视为不同句（跨句污染）→ 直接取最长，不投票"""
    import difflib
    nonempty = [t for t in texts if t and t.strip()]
    if not nonempty:
        return ""
    if len(nonempty) == 1:
        return nonempty[0]
    longest = max(nonempty, key=len)
    if len(nonempty) == 2:
        return longest if nonempty[0] != nonempty[1] else nonempty[0]
    # 3 帧：先做相似度门控（防止跨句污染）
    sims = []
    for i in range(len(nonempty)):
        for j in range(i+1, len(nonempty)):
            a, b = nonempty[i].replace(" ",""), nonempty[j].replace(" ","")
            sm = difflib.SequenceMatcher(None, a, b)
            sims.append(sm.ratio())
    if max(sims) < 0.6:  # 帧间差异大 → 不同句 → 不投票
        return longest
    # 3 帧同句：以最长帧为基准，其余两帧对齐到其坐标，逐位投票（≥2 次胜出）
    votes = {}
    for t in nonempty:
        sm = difflib.SequenceMatcher(None, longest, t)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                for k in range(i2 - i1):
                    votes.setdefault(i1 + k, []).append(longest[i1 + k])
    out = []
    for i, ch in enumerate(longest):
        cands = votes.get(i, [])
        if len(cands) >= 2 and len(set(cands)) == 1:
            out.append(cands[0])
        else:
            out.append(ch)
    return "".join(out).strip()

def ocr_frame(frame_bgr):
    """OCR 单帧，返回识别文本（含空白清理）
    注：亮色提取在滚动/复杂字幕帧上产生白噪点被识别为汉字，已回退 CLAHE"""
    enhanced = enhance_subtitle(frame_bgr)  # CLAHE 增强（验证为最稳）
    try:
        res = ocr.predict(enhanced)
    except Exception as e:
        return ""
    if not res or res[0] is None:
        return ""
    # PaddleOCR 3.x: 文本在 json["res"]["rec_texts"]
    texts = []
    if hasattr(res[0], "json"):
        r = res[0].json.get("res", {})
        if isinstance(r, dict):
            texts = r.get("rec_texts", [])
    joined = "".join(t for t in texts if isinstance(t, str) and t.strip())
    return joined.strip()

def group_entries(entries):
    """链式分组：时间差≤2s 且 LCS≥0.6 视为同句"""
    groups = []
    cur = [entries[0]]
    for e in entries[1:]:
        prev = cur[-1]
        t_diff = e["sec"] - prev["sec"]
        lcs = lcs_ratio(prev["text"].replace(" ",""), e["text"].replace(" ",""))
        if 0 <= t_diff <= TIME_GAP and lcs >= LCS_THRESHOLD:
            cur.append(e)
        else:
            groups.append(cur)
            cur = [e]
    groups.append(cur)
    return groups

def merge_group(group):
    """组内合并：取文本最长+相似度最高者；timestamp 取第一条；similarity 取 max"""
    best = max(group, key=lambda e: (len(e["text"]), e["similarity"]))
    return {
        "timestamp": group[0]["timestamp"],
        "similarity": max(e["similarity"] for e in group),
        "text": best["text"],
    }

def process_one(video_title, entries):
    """处理一集：分组 → 每组合并 → 每组重 OCR → 全局相邻去重"""
    parsed = []
    for e in entries:
        sec = parse_ts(e.get("timestamp", ""))
        if sec is None: continue
        parsed.append({**e, "sec": sec})
    parsed.sort(key=lambda x: x["sec"])
    if not parsed:
        return []
    groups = group_entries(parsed)
    video_path = os.path.join(VIDEO_DIR, video_title + ".mp4")
    cap = cv2.VideoCapture(video_path) if os.path.exists(video_path) else None
    results = []
    for g in groups:
        base_sec = g[0]["sec"]
        best_text = ""
        if cap is not None:
            for off in OFFSETS:
                sec = base_sec + off
                if sec < 0: continue
                cap.set(cv2.CAP_PROP_POS_MSEC, int(sec*1000))
                ret, frame = cap.read()
                if not ret: continue
                t = ocr_frame(frame)
                if len(t) > len(best_text):
                    best_text = t
        merged = merge_group(g)
        if best_text:
            merged["text"] = best_text
        results.append(merged)
    if cap is not None:
        cap.release()
    # 全局相邻去重：时间差≤3s 且文本相同的记录只保留一条
    deduped = []
    for e in results:
        sec = parse_ts(e["timestamp"])
        e["sec"] = sec if sec is not None else 999
        if deduped:
            last = deduped[-1]
            t_diff = e["sec"] - last["sec"]
            if 0 <= t_diff <= 3 and e["text"] == last["text"]:
                last["similarity"] = max(last["similarity"], e["similarity"])
                continue
        deduped.append(e)
    for e in deduped:
        e.pop("sec", None)
    return deduped

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total_in = total_out = 0
    for fname in sorted(os.listdir(SRC_DIR)):
        if not (fname.endswith(".json") and PATTERN.match(fname)):
            continue
        if only and only not in fname:
            continue
        video_title = fname[:-5]
        with open(os.path.join(SRC_DIR, fname), encoding="utf-8") as f:
            entries = json.load(f)
        total_in += len(entries)
        t0 = time.time()
        results = process_one(video_title, entries)
        total_out += len(results)
        with open(os.path.join(DST_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  {video_title[:20]}: {len(entries)} → {len(results)} ({time.time()-t0:.0f}s)")
    print(f"\n合计: {total_in} → {total_out} 条")
    print(f"输出: {DST_DIR}")

if __name__ == "__main__":
    main()
