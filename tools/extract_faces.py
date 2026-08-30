"""
爱染诚人脸候选抽取工具（复刻新增脚本）
================================================
用途：从 Videos/ 下的《罗布奥特曼》视频中按固定间隔抽帧，仅做人脸检测（不依赖已知特征），
      将每张检测到的人脸裁剪保存为候选图到 faces_candidates/，供人工挑选后放入 target/。

使用流程：
  1. 把下载好的《罗布奥特曼》1080p 视频放到 Videos/ 目录；
  2. 运行本脚本：python tools/extract_faces.py
  3. 打开 faces_candidates/ 目录，挑出爱染诚清晰正脸，复制到 target/ 目录；
  4. 运行 python generate_features_insightface.py 生成 face_features_insightface.npz（覆盖原张维为特征）。

说明：
  - 仅检测 + 裁剪，不调用比对，因此 target/ 为空也能运行；
  - 为避免候选过多，默认每 5 秒抽 1 帧、每帧最多保留 1 张最大人脸；可通过参数调整。
"""

import cv2
import numpy as np
import os
import argparse
from insightface.app import FaceAnalysis
from PIL import Image
from params import VIDEOS_FOLDER, USE_GPU_FACE

# 候选输出目录（相对仓库根目录）
CANDIDATE_DIR = "faces_candidates"
# 抽帧间隔（秒）
SAMPLE_INTERVAL = 5
# 单帧最多保留的人脸数（取面积最大的前 N 张）
MAX_FACES_PER_FRAME = 1


def build_analyzer():
    """加载 insightface 检测模型（与 generate_features_insightface.py 一致）。"""
    app = FaceAnalysis(name="buffalo_l")
    # ctx_id=-1 表示 CPU；det_thresh 与生成特征脚本保持一致
    app.prepare(ctx_id=0 if USE_GPU_FACE else -1, det_size=(640, 640), det_thresh=0.5)
    return app


def extract_candidates_from_video(video_path, app, candidate_dir, sample_interval, max_faces):
    """对单个视频抽帧并裁剪人脸候选，返回写入的文件数。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[跳过] 无法打开视频: {video_path}")
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_step = max(1, int(round(fps * sample_interval)))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    written = 0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_step == 0:
            # 避免超大分辨率拖慢检测
            if frame.shape[0] > 2000 or frame.shape[1] > 2000:
                scale = min(2000 / frame.shape[0], 2000 / frame.shape[1])
                frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

            faces = app.get(frame)
            if faces:
                # 按人脸面积降序，取前 max_faces 张
                faces.sort(key=lambda f: f.bbox[2] * f.bbox[3], reverse=True)
                for rank, face in enumerate(faces[:max_faces]):
                    x1, y1, x2, y2 = [int(v) for v in face.bbox]
                    # 裁剪时留出少量边距，避免切到脸缘
                    h, w = frame.shape[:2]
                    mx1, my1 = max(0, x1 - 10), max(0, y1 - 10)
                    mx2, my2 = min(w, x2 + 10), min(h, y2 + 10)
                    crop = frame[my1:my2, mx1:mx2]
                    if crop.size == 0:
                        continue
                    # 转为 RGB 后保存（与原项目特征生成脚本读取方式一致）
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    out_name = f"{video_name}_f{frame_idx:06d}_r{rank}.jpg"
                    out_path = os.path.join(candidate_dir, out_name)
                    Image.fromarray(crop_rgb).save(out_path)
                    written += 1
        frame_idx += 1

    cap.release()
    print(f"[完成] {video_name}: 抽帧约 {frame_idx // frame_step} 张，写入人脸候选 {written} 张")
    return written


def main():
    parser = argparse.ArgumentParser(description="从视频抽取爱染诚人脸候选")
    parser.add_argument("--videos", default=VIDEOS_FOLDER, help="视频目录（默认 Videos）")
    parser.add_argument("--out", default=CANDIDATE_DIR, help="候选输出目录（默认 faces_candidates）")
    parser.add_argument("--interval", type=int, default=SAMPLE_INTERVAL, help="抽帧间隔（秒）")
    parser.add_argument("--max-faces", type=int, default=MAX_FACES_PER_FRAME, help="每帧最多保留人脸数")
    args = parser.parse_args()

    if not os.path.isdir(args.videos):
        print(f"视频目录不存在: {args.videos}，请先放入《罗布奥特曼》视频")
        return

    os.makedirs(args.out, exist_ok=True)
    app = build_analyzer()

    video_files = [
        os.path.join(args.videos, f)
        for f in sorted(os.listdir(args.videos))
        if f.lower().endswith((".mp4", ".mkv", ".flv", ".avi", ".mov", ".ts"))
    ]
    if not video_files:
        print(f"在 {args.videos} 未找到视频文件")
        return

    total = 0
    for vf in video_files:
        total += extract_candidates_from_video(vf, app, args.out, args.interval, args.max_faces)

    print(f"\n全部完成：共写入 {total} 张人脸候选到 {args.out}/")
    print("下一步：挑选爱染诚清晰正脸复制到 target/，再运行 generate_features_insightface.py")


if __name__ == "__main__":
    main()
