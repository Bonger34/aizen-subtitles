"""
稳健抽帧驱动（复刻辅助） v2
- 逐视频处理，逐帧容错，实时写日志
- 断点续跑：已完成视频记录在 extract_progress.txt，重启时跳过
- 路径全部基于脚本所在目录，避免 cwd 问题
用法: python run_extract.py
"""
import sys, os, time, traceback
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from insightface.app import FaceAnalysis
from PIL import Image
import cv2
import numpy as np
import params

CAND = os.path.join(BASE, "faces_candidates")
PROGRESS = os.path.join(BASE, "extract_progress.txt")
LOG = os.path.join(BASE, "extract_faces_run.log")
# 抽帧同时保存每张候选脸的 512 维 embedding，供后续聚类脚本直接复用，
# 避免对已裁切的小脸图重新检测（小脸重检召回率极低）。
EMB_NPZ = os.path.join(BASE, "face_embeddings.npz")
# 进程内累积 embedding，进程结束或退出前落盘
_emb_files = []
_emb_vecs = []

if not os.path.isabs(params.VIDEOS_FOLDER):
    params.VIDEOS_FOLDER = os.path.join(BASE, params.VIDEOS_FOLDER)

SAMPLE_INTERVAL = 5
MAX_FACES = 1


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, flush=True)


def load_done():
    done = set()
    if os.path.exists(PROGRESS):
        with open(PROGRESS, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    done.add(line)
    return done


def mark_done(vf):
    with open(PROGRESS, "a", encoding="utf-8") as f:
        f.write(vf + "\n")


def build_analyzer():
    app = FaceAnalysis(name="buffalo_l")
    app.prepare(ctx_id=0 if params.USE_GPU_FACE else -1, det_size=(640, 640), det_thresh=0.5)
    return app


def process_video(vf, app):
    cap = cv2.VideoCapture(vf)
    if not cap.isOpened():
        log(f"[跳过] 无法打开: {vf}")
        return 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(fps * SAMPLE_INTERVAL)))
    name = os.path.splitext(os.path.basename(vf))[0]
    written = 0
    idx = 0
    bad = 0
    while True:
        try:
            ret, frame = cap.read()
        except Exception as e:
            bad += 1
            if bad <= 5:
                log(f"[读帧异常] {name} f{idx}: {repr(e)}")
            # 读帧失败：尝试重开一次，若仍失败则中止本视频（交给上层跳过）
            try:
                cap.release()
                cap = cv2.VideoCapture(vf)
                if not cap.isOpened():
                    break
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                continue
            except Exception:
                break
        if not ret:
            break
        if idx % step == 0:
            try:
                if frame.shape[0] > 2000 or frame.shape[1] > 2000:
                    s = min(2000 / frame.shape[0], 2000 / frame.shape[1])
                    frame = cv2.resize(frame, (0, 0), fx=s, fy=s)
                faces = app.get(frame)
                if faces:
                    faces.sort(key=lambda f: f.bbox[2] * f.bbox[3], reverse=True)
                    for rank, face in enumerate(faces[:MAX_FACES]):
                        x1, y1, x2, y2 = [int(v) for v in face.bbox]
                        h, w = frame.shape[:2]
                        mx1, my1 = max(0, x1 - 10), max(0, y1 - 10)
                        mx2, my2 = min(w, x2 + 10), min(h, y2 + 10)
                        crop = frame[my1:my2, mx1:mx2]
                        if crop.size == 0:
                            continue
                        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                        out = os.path.join(CAND, f"{name}_f{idx:06d}_r{rank}.jpg")
                        # 写文件带重试（外部进程短暂锁定时重试 3 次）
                        for attempt in range(3):
                            try:
                                Image.fromarray(crop_rgb).save(out)
                                break
                            except Exception as e:
                                if attempt == 2:
                                    raise
                                time.sleep(1.0)
                        # 同步保存该脸的 512 维 embedding（直接复用已检测的 face 对象）
                        try:
                            emb = face.embedding.astype(np.float32)
                            _emb_files.append(os.path.basename(out))
                            _emb_vecs.append(emb)
                        except Exception:
                            pass
                        written += 1
            except Exception as e:
                bad += 1
                if bad <= 3:
                    log(f"[帧异常] {name} f{idx}: {repr(e)}")
        idx += 1
    cap.release()
    log(f"[完成] {name}: 抽帧约 {idx // step} 张, 写入候选 {written} 张, 异常帧 {bad}")
    return written


def save_embeddings():
    """将累积的 embedding 落盘到 EMB_NPZ（断点续跑时合并旧数据）。

    直接 np.savez 覆盖写（open 'wb'），不经 tmp+replace——
    np.savez 会自动追加 .npz 后缀，若 tmp 路径带 .tmp 会生成 .tmp.npz，
    导致 replace 源文件不存在。同时避免 os.remove 触发安全删除钩子。
    """
    global _emb_files, _emb_vecs
    files = list(_emb_files)
    vecs = list(_emb_vecs)
    # 合并已存在（之前视频）的 embedding，避免续跑时覆盖
    if os.path.exists(EMB_NPZ):
        try:
            old = np.load(EMB_NPZ, allow_pickle=True)
            old_files = list(old["files"])
            old_vecs = list(old["encodings"])
            have = set(files)
            for f, v in zip(old_files, old_vecs):
                if f not in have:
                    files.append(f)
                    vecs.append(v)
        except Exception:
            pass
    if vecs:
        np.savez(EMB_NPZ, files=np.array(files), encodings=np.array(vecs, dtype=np.float32))
    _emb_files, _emb_vecs = [], []


def main():
    os.makedirs(CAND, exist_ok=True)
    done = load_done()
    app = build_analyzer()
    log(f"=== 抽帧开始 {time.strftime('%H:%M:%S')} (已完成 {len(done)} 个) ===")
    vids = []
    for root, _d, files in os.walk(params.VIDEOS_FOLDER):
        for f in sorted(files):
            if f.lower().endswith(('.mp4', '.mkv', '.flv', '.avi', '.mov', '.ts')):
                vids.append(os.path.join(root, f))
    vids.sort()
    total = 0
    for vf in vids:
        if vf in done:
            log(f"[续跑跳过] {os.path.basename(vf)}")
            continue
        # 视频级重试：偶发外部锁（杀毒/索引）导致读取中断时，整体重试最多 3 次
        ok = False
        for attempt in range(1, 4):
            try:
                total += process_video(vf, app)
                ok = True
                break
            except Exception as e:
                log(f"[视频异常] {os.path.basename(vf)} (第{attempt}次): {repr(e)}")
                traceback.print_exc()
                time.sleep(2 * attempt)
        if not ok:
            log(f"[视频失败] {os.path.basename(vf)}: 重试3次仍失败，跳过")
            continue
        mark_done(vf)  # 整集处理完才标记，避免半截
        save_embeddings()  # 每集结束即落盘，避免进程崩溃丢全部 embedding
    log(f"=== 全部完成 本次写入 {total} 张, 累计已完成 {len(load_done())}/{len(vids)} ===")


if __name__ == "__main__":
    main()
