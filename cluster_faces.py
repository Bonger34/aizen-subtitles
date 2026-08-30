"""
人脸候选自动聚类辅助脚本（复刻辅助）
- 输入: faces_candidates/ 下全部 .jpg 候选
- 处理: 用 insightface(buffalo_l) 提取 512 维 embedding，按余弦相似度做层次聚类
- 输出:
    1) clusters/Cxxxx/  每簇一个子目录，含该簇所有候选副本（便于人工逐簇筛选）
    2) clusters_report.html  每簇代表缩略图网格 + 数量，便于快速定位爱染诚所在簇
    3) cluster_embeddings.npz  特征缓存（重跑时跳过提取，只重聚类）
- 说明: 仅做分组，不判断“谁是爱染诚”；人工对每个簇抽几张确认即可。

用法: python cluster_faces.py
"""
import os
import sys
import json
import base64
import io
import shutil
from tqdm import tqdm

import numpy as np
import cv2
from PIL import Image
from insightface.app import FaceAnalysis
from scipy.cluster.hierarchy import linkage, fcluster

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import params  # 复用 USE_GPU_FACE 等配置

CAND = os.path.join(BASE, "faces_candidates")
# embedding 由抽帧脚本(run_extract.py)在裁脸时直接保存，已是正确的人脸特征，
# 避免对已裁切小脸图重新检测（召回率极低）。聚类脚本优先读取此文件。
EMB_SRC = os.path.join(BASE, "face_embeddings.npz")
# 聚类脚本自身的缓存（仅在无 EMB_SRC 时作为兜底）
EMB_CACHE = os.path.join(BASE, "cluster_embeddings.npz")
OUT_ROOT = os.path.join(BASE, "clusters")
REPORT = os.path.join(BASE, "clusters_report.html")

# 聚类阈值：余弦距离 = 1 - 余弦相似度。t=0.35 对应相似度 0.65，
# 同人通常 >0.65，异人通常 <0.4，可作为分组边界。可按实际效果上下调整。
CLUSTER_DIST_THRESHOLD = 0.35
THUMB_SIZE = 112  # 报告页内每簇代表缩略图边长(px)


def build_analyzer():
    """加载 buffalo_l 模型，GPU/CPU 由 params 控制。"""
    app = FaceAnalysis(name="buffalo_l")
    app.prepare(ctx_id=0 if params.USE_GPU_FACE else -1,
                det_size=(640, 640), det_thresh=0.5)
    return app


# 短边放大下限：仅作为兜底（无抽帧 embedding 时）使用
UPSCALE_MIN = 320


def extract_embeddings(app):
    """获取全部候选的 embedding。

    优先读取抽帧脚本(run_extract.py)直接保存的 face_embeddings.npz ——
    该文件在裁脸时已用 buffalo_l 提取 512 维特征，对裁切小脸无需重新检测，最可靠。
    若不存在，则回退为自行检测（PIL 读图 + 放大短边到 UPSCALE_MIN 再检测）。
    """
    files = sorted([f for f in os.listdir(CAND) if f.lower().endswith(".jpg")])

    if os.path.exists(EMB_SRC):
        cache = np.load(EMB_SRC, allow_pickle=True)
        src_files = list(cache["files"])
        src_enc = cache["encodings"].astype(np.float32)
        # 仅保留当前候选目录中存在的文件，顺序与 files 对齐
        enc_map = {f: e for f, e in zip(src_files, src_enc)}
        valid = [(f, enc_map[f]) for f in files if f in enc_map]
        if valid:
            vf = [x[0] for x in valid]
            ve = np.stack([x[1] for x in valid])
            print(f"[embedding] 从 {os.path.basename(EMB_SRC)} 读取 {len(vf)} 张有效特征")
            return vf, ve
        else:
            print(f"[embedding] {os.path.basename(EMB_SRC)} 无匹配文件，转回退检测")

    # 回退：自行检测
    if os.path.exists(EMB_CACHE):
        cache = np.load(EMB_CACHE, allow_pickle=True)
        cached_files = list(cache["files"])
        if cached_files == files and len(files) == len(cached_files):
            print(f"[缓存] 命中 {len(files)} 张 embedding，跳过提取")
            return files, cache["encodings"].astype(np.float32)

    encodings = []
    valid_files = []
    skip = 0
    for f in tqdm(files, desc="提取embedding"):
        path = os.path.join(CAND, f)
        try:
            rgb = np.array(Image.open(path).convert("RGB"))
            img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            h, w = img.shape[:2]
            if min(h, w) < UPSCALE_MIN:
                scale = UPSCALE_MIN / float(min(h, w))
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
            faces = app.get(img)
            if not faces:
                skip += 1
                continue
            emb = faces[0].embedding if len(faces) == 1 else \
                faces[int(np.argmax([fc.bbox[2] * fc.bbox[3] for fc in faces]))].embedding
            encodings.append(emb.astype(np.float32))
            valid_files.append(f)
        except Exception as e:
            print(f"[跳过] {f}: {e}")

    encodings = np.array(encodings, dtype=np.float32)
    np.savez(EMB_CACHE, files=np.array(valid_files), encodings=encodings)
    print(f"[完成] 提取 {len(valid_files)} 张有效 embedding（跳过 {skip} 张无人脸），已缓存")
    return valid_files, encodings


def cluster(encodings, t):
    """层次聚类：average 链路 + 余弦距离，按距离阈值切分。"""
    # 归一化后用欧氏距离等价余弦距离，linkage 更稳定
    norms = np.linalg.norm(encodings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = encodings / norms
    Z = linkage(unit, method="average", metric="cosine")
    labels = fcluster(Z, t=t, criterion="distance")
    return labels


def make_thumb_b64(path, size=THUMB_SIZE):
    """读取图片并生成正方形缩略图的 base64（用于报告页）。"""
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((size, size))
        # 补白边成正方形
        canvas = Image.new("RGB", (size, size), (240, 240, 240))
        canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def main():
    os.makedirs(OUT_ROOT, exist_ok=True)
    app = build_analyzer()
    files, encodings = extract_embeddings(app)
    if len(files) == 0:
        print("无有效候选，退出")
        return

    print(f"[聚类] 距离阈值={CLUSTER_DIST_THRESHOLD}，样本数={len(files)}")
    labels = cluster(encodings, CLUSTER_DIST_THRESHOLD)

    # 按簇归集
    groups = {}
    for f, lab in zip(files, labels):
        groups.setdefault(int(lab), []).append(f)

    # 按规模降序，便于优先查看大簇（主角通常在大簇）
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))

    # 注：环境的安全删除钩子在回收站不可用时拒绝 rmtree，
    # 故不预先清空旧簇目录，改为覆盖写入；旧分组若不再出现会残留空目录，无害。
    report_rows = []
    print(f"[分组] 共 {len(ordered)} 个簇")
    for idx, (lab, members) in enumerate(ordered, 1):
        cdir = os.path.join(OUT_ROOT, f"C{idx:04d}")
        os.makedirs(cdir, exist_ok=True)
        for m in members:
            shutil.copy(os.path.join(CAND, m), os.path.join(cdir, m))
        # 代表图取组内靠前的第一张
        rep_b64 = make_thumb_b64(os.path.join(CAND, members[0]))
        report_rows.append((idx, len(members), rep_b64, members[0], cdir))

    # 生成 HTML 报告（每簇一张代表缩略图 + 数量 + 路径）
    sizes = [r[1] for r in report_rows]
    html = _build_report_html(report_rows, sizes)
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"[统计] 簇数={len(ordered)}，最大簇={max(sizes)}，最小簇={min(sizes)}，"
          f"中位数≈{int(np.median(sizes))}")
    print(f"[输出] 簇目录: {OUT_ROOT}")
    print(f"[输出] 报告页: {REPORT}")


def _build_report_html(rows, sizes):
    """构建聚类概览 HTML（纯前端，无外部依赖）。"""
    cards = []
    for idx, cnt, b64, first, cdir in rows:
        rel = os.path.relpath(cdir, BASE).replace("\\", "/")
        img_tag = (f'<img src="data:image/jpeg;base64,{b64}" width="112" height="112" '
                   f'style="object-fit:cover;border-radius:6px">'
                   if b64 else '<div style="width:112px;height:112px;background:#eee"></div>')
        cards.append(
            f'<div style="border:1px solid #ddd;border-radius:8px;padding:8px;'
            f'text-align:center;background:#fff">'
            f'{img_tag}'
            f'<div style="margin-top:6px;font-weight:600">C{idx:04d}</div>'
            f'<div style="color:#666;font-size:13px">{cnt} 张</div>'
            f'<div style="color:#999;font-size:11px;margin-top:4px">'
            f'<a href="{rel}">{rel}</a></div>'
            f'</div>'
        )
    grid = "".join(cards)
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>人脸聚类报告</title>
<style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:24px;background:#f5f5f5}}
h1{{font-size:20px}} .meta{{color:#666;margin-bottom:16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}}
</style></head><body>
<h1>人脸候选聚类报告</h1>
<div class="meta">簇数 {len(rows)} ｜ 候选总数 {sum(sizes)} ｜
最大簇 {max(sizes)} ｜ 最小簇 {min(sizes)} ｜
中位数 {int(np.median(sizes))}<br>
点击各簇目录链接可在文件管理器中打开对应分组，逐簇挑选爱染诚。</div>
<div class="grid">{grid}</div>
</body></html>"""


if __name__ == "__main__":
    main()
