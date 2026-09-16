# 全量抽帧脚本（F-1 定稿参数 v2）
# - 窗口: ts±1s（3 候选帧）
# - 字幕匹配: LCS ≥ 0.5 或包含
# - 人脸: sim ≥ 0.4 且 面积占比 ≥ 0.05%（v2 放宽 sim 至 0.4 救回 no_face）
# - 幽灵记录标记: 无帧通过时写入 frames_missing.json（含原因统计）
# - 支持 LIMIT 参数用于小批量测试
import cv2, os, re, json, sys, time
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from insightface.app import FaceAnalysis

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUBTITLE_DIR = os.path.join(BASE, "subtitle")
VIDEO_DIR = os.path.join(BASE, "Videos")
FRAMES_DIR = os.path.join(BASE, "web", "frames")
MISSING_FILE = os.path.join(BASE, "web", "frames_missing.json")
PATTERN = re.compile(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]')

W, H = 960, 540
SUBTITLE_AREA = (100, 895, 1820, 985)
MATCH_THRESHOLD = 0.5
FACE_SIM_THRESHOLD = 0.4
FACE_MIN_RATIO = 0.0005
OFFSETS = (-1, 0, 1)  # F-1

# 命令行参数: LIMIT（测试前 N 条）、START（跳过前 N 条用于续跑）
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
START = int(sys.argv[2]) if len(sys.argv) > 2 else 0

print("加载模型...")
features = np.load(os.path.join(BASE, "face_features_insightface.npz"))
known_encodings = features['encodings']
norm_known = known_encodings / np.linalg.norm(known_encodings, axis=1, keepdims=True)
app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
ocr = RapidOCR()

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

def text_matches(ocr_texts, expected):
    """返回 (是否匹配, 最高匹配度)"""
    if not ocr_texts: return False, 0
    exp = expected.replace(" ", "").replace("·", "")
    best = 0
    for t in ocr_texts:
        tt = t.replace(" ", "").replace("·", "")
        r = lcs_ratio(exp, tt)
        if r > best: best = r
        if exp in tt or (tt in exp and len(tt) >= 2):
            return True, 1.0
    return best >= MATCH_THRESHOLD, best

def ocr_subtitle(frame_bgr):
    crop = frame_bgr[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
    result, _ = ocr(np.array(crop))
    if not result:
        return []
    return [r[1] for r in result if len(r) > 1 and isinstance(r[1], str) and r[1].strip()]

def face_verify(frame_bgr):
    """返回 (是否通过, best_sim, best_ratio, 人脸数)"""
    faces = app.get(frame_bgr)
    if not faces:
        return False, 0.0, 0.0, 0
    h, w = frame_bgr.shape[:2]
    frame_area = h * w
    best_sim = 0.0
    best_ratio = 0.0
    for face in faces:
        emb = face.embedding
        norm_emb = emb / np.linalg.norm(emb)
        sim = float(np.dot(norm_known, norm_emb).max())
        bbox = face.bbox
        fw, fh = bbox[2]-bbox[0], bbox[3]-bbox[1]
        ratio = (fw * fh) / frame_area
        if sim > best_sim: best_sim = sim
        if ratio > best_ratio: best_ratio = ratio
        if sim >= FACE_SIM_THRESHOLD and ratio >= FACE_MIN_RATIO:
            return True, best_sim, best_ratio, len(faces)
    return False, best_sim, best_ratio, len(faces)

def save_frame(frame, video_title, ts, offset):
    h, w = frame.shape[:2]
    scale = min(W / w, H / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = cv2.copyMakeBorder(resized, (H - nh)//2, H - nh - (H - nh)//2,
                                (W - nw)//2, W - nw - (W - nw)//2,
                                cv2.BORDER_CONSTANT, value=(0, 0, 0))
    ep = re.search(r"\[P(\d+)\]", video_title).group(1)
    tag = f"{offset:+d}s" if offset else ""
    out_name = f"P{ep}_{ts}{tag}.jpg"
    cv2.imwrite(os.path.join(FRAMES_DIR, out_name), canvas, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return out_name

def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    # 收集所有记录（按集排序，保持确定性）
    all_entries = []
    for fname in sorted(os.listdir(SUBTITLE_DIR)):
        if not (fname.endswith(".json") and PATTERN.match(fname)):
            continue
        video_title = fname[:-5]
        with open(os.path.join(SUBTITLE_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        for e in data:
            ts = e.get("timestamp", "")
            sec = parse_ts(ts)
            if sec is None: continue
            all_entries.append((video_title, ts, sec, e.get("text", "").strip(), e.get("similarity", 0.0)))
    print(f"总记录: {len(all_entries)}")

    # 只抽 sim>=0.5 的记录（爱染诚疑似在场）
    all_entries = [e for e in all_entries if e[4] >= 0.5]
    print(f"sim>=0.5 记录: {len(all_entries)}")
    if LIMIT > 0:
        all_entries = all_entries[START:START+LIMIT]
    print(f"本次处理: {len(all_entries)} 条 (从 {START} 开始)")

    # 按视频分组，避免重复打开 VideoCapture
    from collections import defaultdict
    by_video = defaultdict(list)
    for v, ts, sec, text, sim in all_entries:
        by_video[v].append((ts, sec, text, sim))

    stats = {"ok": 0, "no_subtitle": 0, "no_face": 0, "both_fail": 0, "ghost": 0, "video_missing": 0}
    missing = []
    t0 = time.time()

    for video_title, entries in by_video.items():
        video_path = os.path.join(VIDEO_DIR, video_title + ".mp4")
        if not os.path.exists(video_path):
            stats["video_missing"] += len(entries)
            for ts, sec, text, sim in entries:
                missing.append({"file": video_title, "ts": ts, "text": text, "reason": "video_missing"})
            continue
        cap = cv2.VideoCapture(video_path)
        for ts, sec, text, sim in entries:
            chosen = None
            match_ratio = 0
            # F-1 窗口
            for offset in OFFSETS:
                t = sec + offset
                if t < 0: continue
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ret, frame = cap.read()
                if not ret: continue
                ocr_texts = ocr_subtitle(frame)
                matched, mr = text_matches(ocr_texts, text)
                if not matched: continue
                ok, best_sim, best_ratio, nfaces = face_verify(frame)
                if ok:
                    chosen = (frame, offset, best_sim, best_ratio)
                    match_ratio = mr
                    break
            if chosen is None:
                # 幽灵记录：标记原因
                stats["ghost"] += 1
                # 区分原因：字幕未匹配 vs 人脸未通过
                reason = "no_subtitle"
                for offset in OFFSETS:
                    t = sec + offset
                    if t < 0: continue
                    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                    ret, frame = cap.read()
                    if not ret: continue
                    ocr_texts = ocr_subtitle(frame)
                    matched, mr = text_matches(ocr_texts, text)
                    if matched:
                        reason = "no_face"
                        break
                missing.append({"file": video_title, "ts": ts, "text": text, "reason": reason, "sim": sim})
                if reason == "no_subtitle": stats["no_subtitle"] += 1
                else: stats["no_face"] += 1
                continue
            frame, offset, best_sim, best_ratio = chosen
            save_frame(frame, video_title, ts, offset)
            stats["ok"] += 1
        cap.release()

    # 保存幽灵记录
    with open(MISSING_FILE, "w", encoding="utf-8") as f:
        json.dump({"total": len(missing), "records": missing}, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    total = sum(stats.values())
    print(f"\n=== 抽帧统计 ===")
    print(f"总处理: {total} 条")
    print(f"成功: {stats['ok']} ({stats['ok']/total*100:.1f}%)")
    print(f"幽灵: {stats['ghost']} ({stats['ghost']/total*100:.1f}%)")
    print(f"  - 字幕未匹配: {stats['no_subtitle']}")
    print(f"  - 人脸未通过: {stats['no_face']}")
    print(f"视频缺失: {stats['video_missing']}")
    print(f"耗时: {elapsed:.0f}s ({elapsed/total:.2f}s/条)")
    print(f"幽灵记录: {MISSING_FILE}")

if __name__ == "__main__":
    main()
