# -*- coding: utf-8 -*-
"""dump_vl_raw.py — VL 原始输出诊断

对给定帧的字幕带做 VL 识别，dump 原始 parsing_res_list（content/score/box/行），
判断读错原因：引擎 / 预处理 / blocks 拼接逻辑。
用法: python dump_vl_raw.py <img路径>
"""
import json
import os
import sys

import cv2

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
sys.path.insert(0, BASE)
import vl_recheck_new


def main():
    img = sys.argv[1]
    # 从视频取 1080p 原帧（若参数是已有全帧图则直接读）
    if img.endswith('.mp4'):
        cap = cv2.VideoCapture(img)
        cap.set(cv2.CAP_PROP_POS_MSEC, 432000)
        ret, frame = cap.read()
        print('取帧 432.0s:', frame.shape if ret else None)
    else:
        img = sys.argv[1]
        frame = cv2.imread(img)
        print('读图:', frame.shape if frame is not None else None)
    if frame is None:
        return
    pipe = vl_recheck_new.get_vl_pipeline()
    crop = frame[895:985, 100:1820]
    # 原始 predict：不套 vl_ocr_frame 的过滤，拿完整结果
    results = list(pipe.predict(
        crop,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=False,
        prompt_label="ocr",
        use_chart_recognition=False,
        use_seal_recognition=False,
        max_new_tokens=256,
        min_pixels=28 * 28 * 130,
        max_pixels=28 * 28 * 512,
    ))
    out = []
    for res in results:
        blocks = res.get("parsing_res_list", []) if isinstance(res, dict) else []
        for b in blocks:
            c = b.get("content", "") if isinstance(b, dict) else getattr(b, "content", "")
            s = b.get("score", None) if isinstance(b, dict) else getattr(b, "score", None)
            box = b.get("block_bbox", None) if isinstance(b, dict) else getattr(b, "block_bbox", None)
            out.append({"content": c, "score": s, "box": box})
    with open(os.path.join(BASE, 'review', 'vl_raw_dump.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print('VL raw blocks:')
    for b in out:
        print(f"  score={b['score']} box={b['box']} content={b['content']!r}")
    yield_ = None
    # 同时试更大分辨率参数
    results2 = list(pipe.predict(
        crop,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=False,
        prompt_label="ocr",
        use_chart_recognition=False,
        use_seal_recognition=False,
        max_new_tokens=256,
        min_pixels=28 * 28 * 200,
        max_pixels=28 * 28 * 1024,
    ))
    out2 = []
    for res in results2:
        blocks = res.get("parsing_res_list", []) if isinstance(res, dict) else []
        for b in blocks:
            c = b.get("content", "") if isinstance(b, dict) else getattr(b, "content", "")
            out2.append(c)
    print('VL larger pixels:', out2)


if __name__ == '__main__':
    main()
