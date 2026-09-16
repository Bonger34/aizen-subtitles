# -*- coding: utf-8 -*-
"""compare_ocr.py — 字幕识别预处理对比实验

对 P03 7m10-7m20s 中 4 个时刻的字幕带，测试预处理组合：
  orig / up2x(双三次放大) / bin2(反色二值化) / bin2x(放大+二值化)
跑 rapidocr 与 VL 两引擎，打印识别文本矩阵，寻找能读出
「到了我这一代后扩大了规模」的配置。
用法: python compare_ocr.py
"""
import os
import sys

import cv2
import numpy as np

BASE = r'D:\Bonger\Desktop\2026-08-21-18-21-50\VV_Rob'
VIDEO = os.path.join(BASE, 'Videos', '[P03]3 欢迎来到爱染科技.mp4')
SUBTITLE_AREA = (100, 895, 1820, 985)
TARGET = '到了我这一代后扩大了规模'
MOMENTS = (431000, 432000, 433000, 434000, 436000)


def prep(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # 白字黑边：反相后 OTSU
    inv = 255 - gray
    _, bin2 = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bin2


def main():
    os.makedirs(os.path.join(BASE, 'review', 'ocr_variants'), exist_ok=True)
    sys.path.insert(0, BASE)
    import vl_recheck_new
    cap = cv2.VideoCapture(VIDEO)
    rows = []
    for ms in MOMENTS:
        cap.set(cv2.CAP_PROP_POS_MSEC, ms)
        ret, frame = cap.read()
        if frame is None:
            continue
        crop = frame[SUBTITLE_AREA[1]:SUBTITLE_AREA[3], SUBTITLE_AREA[0]:SUBTITLE_AREA[2]]
        b = prep(crop)
        up = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        bu = cv2.resize(b, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        variants = {'orig': crop, 'up2x': up, 'bin': cv2.cvtColor(b, cv2.COLOR_GRAY2BGR),
                    'bin2x': cv2.cvtColor(bu, cv2.COLOR_GRAY2BGR)}
        for name, v in variants.items():
            fp = os.path.join(BASE, 'review', 'ocr_variants', f'{ms//1000}_{name}.jpg')
            cv2.imwrite(fp, v)
            t_vl = ''
            try:
                pv = list(vl_recheck_new.get_vl_pipeline().predict(
                    v, use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_layout_detection=False, prompt_label='ocr',
                    use_chart_recognition=False, use_seal_recognition=False,
                    max_new_tokens=64, min_pixels=28 * 28 * 130, max_pixels=28 * 28 * 512))
                for rr in pv:
                    blocks = rr.get('parsing_res_list', []) if isinstance(rr, dict) else []
                    t_vl = ''.join((b2.get('content', '') if isinstance(b2, dict)
                                    else getattr(b2, 'content', '')) for b2 in blocks)
            except Exception as e:
                t_vl = f'ERR:{str(e)[:30]}'
            mark_v = '★' if TARGET in t_vl else ''
            rows.append(f'{ms/1000:7.1f}s {name:6} VL:{t_vl[:30]!r}{mark_v}')
            print(rows[-1], flush=True)
        print('---', flush=True)
    print('\n目标文本:', TARGET)
    with open(os.path.join(BASE, 'review', 'ocr_compare_vl.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(rows) + '\n目标: ' + TARGET + '\n')
    print('保存 review/ocr_compare_vl.txt')


if __name__ == '__main__':
    main()
