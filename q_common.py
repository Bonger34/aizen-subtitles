# -*- coding: utf-8 -*-
"""q_common.py — 文本质量提升共用的字幕行切分与 OCR 引擎构造。

字幕布局事实(实测):
  * 字幕行 y 位置不固定: 约 900~1010 之间浮动(受画面构图影响);
  * 片尾/片头段同一画面里还有演职员表(日文, 左右两列, 横跨全宽)与日文歌词;
  * 固定窄带 (100,895,1820,985) 会切掉靠下的字幕行(407 帧实测伸出下缘)。
因此改为: 在 y∈[LOW, HIGH] 内按白像素行剖面切出文字行带, 再逐段 OCR, 交给上层挑选。
"""
import os
import re
import sys

_NV_DLL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_nv_dlls')
_ORT124 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_ort124')
if os.path.isdir(_NV_DLL):
    os.add_dll_directory(_NV_DLL)
    os.environ['PATH'] = _NV_DLL + os.pathsep + os.environ.get('PATH', '')
if os.path.isdir(_ORT124):
    sys.path.insert(0, _ORT124)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# 扫描区(1080p 坐标): 上限 840 以上一般只有画面, 下限 1075 覆盖到片尾滚动字
SCAN_TOP, SCAN_BOT = 840, 1075
X0, X1 = 40, 1880          # 左右留边
WHITE_MIN = 200            # 近白阈值(比出帧 JPEG 的 245 宽, 适配压缩噪声)
ROW_TH_RATIO = 0.12        # 行带判定: 该行白像素数 > 峰值 * 该比例
ROW_GAP = 4                # 行间断: 空 >ROW_GAP 行视为不同文字行
PAD_Y = 6                  # 每段上下留白
KANA = tuple(range(0x3041, 0x30FF + 1)) + (0x30FC,)
CJK_ALNUM = re.compile(r'[\u4e00-\u9fff0-9A-Za-z]')
_CC = None


def to_simp(s):
    """繁转简 —— PP-OCR 的 CH 模型偶尔输出繁体(如 愛染诚), 比对与落盘都按简体口径。"""
    global _CC
    if not s:
        return s
    try:
        if _CC is None:
            from opencc import OpenCC
            _CC = OpenCC('t2s')
        return _CC.convert(s)
    except Exception:
        return s


def norm(s):
    """只保留汉字/数字/拉丁字母 —— 比对时忽略空格与标点。"""
    return ''.join(CJK_ALNUM.findall(s or ''))


def sim(a, b):
    """字符级相似度 = 1 - 编辑距离/min(长度); 全库脚本统一口径。"""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return 1.0 - prev[n] / min(m, n)


def kana_ratio(s):
    """假名占比 —— 片头/片尾日文歌词与演职员表的强信号。"""
    if not s:
        return 0.0
    return sum(1 for ch in s if ord(ch) in KANA) / len(s)


def is_subseq(a, b):
    """a 是否为 b 的子序列 —— 判定"旧文本只是少读了几个字"(方向可靠, 只增不删)。"""
    it = iter(b)
    return all(c in it for c in a)


def diff_rel(old, new):
    """比较旧文本与新读数, 返回 same/add/del/diff。add=新读数只是旧文本插入了字符。"""
    a, b = norm(old), norm(new)
    if not b:
        return ''
    if sim(a, b) >= 0.95:
        return 'same'
    if len(b) > len(a) and is_subseq(a, b):
        return 'add'
    if len(b) < len(a) and is_subseq(b, a):
        return 'del'
    return 'diff'


def gray_white(img, thr=WHITE_MIN):
    """近白掩膜(BGR -> bool)。"""
    if img.ndim == 2:
        return img > thr
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    return np.minimum(np.minimum(b, g), r) > thr


def split_lines(img, top=SCAN_TOP, bot=SCAN_BOT, max_density=None, white_min=None,
                row_th_ratio=None):
    """把扫描区按白像素行剖面切成文字行带, 返回 [(y0, y1, fill), ...] (1080p 坐标)。

    fill = 段内白像素总数的相对强度, 用于区分主字幕行与稀疏小字(演职员表)。
    max_density: 若给定, 丢弃"白像素占比高于该值"的段 —— 画面亮部(整片白)会被行剖面
    连成一大段, 混进 OCR 只会产生噪声(实测 Web 帧上有 13.8% 条目因此读不出东西)。
    white_min: 白像素阈值。帧图(960x540)上"明亮天空/彩虹背景"在 200 阈值下整片算白,
    会把字幕行一起吃掉(实测 1052 条里大片 seg=0), 故对帧图用更高的 230。
    row_th_ratio: 行带阈值(相对峰值的比例)。默认 0.12 —— 但 1080p 画面里大面积白色
    (人物白衬衫等)会让大部分行都超过该阈值, 把衬衫与字幕连成一段 235px 高的大块,
    OCR 读不出任何东西; 实测提到 0.6 可只保留白像素密集的字幕行。
    """
    h = img.shape[0]
    sy = 1080.0 / h
    y0, y1 = max(0, int(top / sy)), min(h, int(bot / sy))
    band = img[y0:y1, int(X0 * img.shape[1] / 1920.0):int(X1 * img.shape[1] / 1920.0)]
    mask = gray_white(band, white_min) if white_min else gray_white(band)
    prof = mask.sum(axis=1)
    if prof.max() < 5:
        return []
    ratio = ROW_TH_RATIO if row_th_ratio is None else row_th_ratio
    thr = max(3, int(prof.max() * ratio))
    ys = np.where(prof >= thr)[0]
    runs = []
    for y in ys:
        if runs and y - runs[-1][1] <= ROW_GAP:
            runs[-1][1] = int(y)
        else:
            runs.append([int(y), int(y)])
    out = []
    for a, b in runs:
        fill = int(prof[a:b + 1].sum())
        if max_density is not None:
            area = max(1, (b - a + 1) * band.shape[1])
            if fill / area > max_density:
                continue
        out.append((int(y0 * sy + a * sy), int(y0 * sy + (b + 1) * sy), fill))
    return out


def build_engine(use_cuda=True, model_type=None, rec_shape=(3, 48, 1536), rec_batch_num=1,
                 rec_model_type=None):
    """构造识别引擎。

    rec_model_type 可单独指定: PP-OCRv6 的 server 模型只支持 Det.lang 为特定值,
    实测 Det 用 SERVER 会报 "Unsupported det.lang_type='ch' for PP-OCRv6 server model",
    因此只把 Rec 换成 SERVER(参数量更大, 用于救回帧图上漏读的字)。
    """
    from rapidocr import RapidOCR
    from rapidocr.utils.parse_parameters import ModelType, OCRVersion, LangDet, LangRec
    mt = model_type or ModelType.MEDIUM
    rm = rec_model_type or mt
    return RapidOCR(params={
        'EngineConfig.onnxruntime.use_cuda': use_cuda,
        'Det.model_type': mt, 'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.lang': LangDet.MULTI,
        'Rec.model_type': rm, 'Rec.ocr_version': OCRVersion.PPOCRV6,
        'Rec.lang': LangRec.CH, 'Rec.rec_img_shape': list(rec_shape),
        'Rec.rec_batch_num': rec_batch_num,
    })


def crop_norm(img, r, upscale=2.0):
    """裁剪 + 放大 + 白底黑字归一, 供识别使用。r=(x0,y0,x1,y1) 用 1080p 坐标。"""
    h, w = img.shape[:2]
    sx, sy = w / 1920.0, h / 1080.0
    y0, y1 = max(0, int(r[1] * sy)), min(h, int(r[3] * sy))
    x0, x1 = max(0, int(r[0] * sx)), min(w, int(r[2] * sx))
    c = img[y0:y1, x0:x1]
    if c.size == 0:
        return None
    if upscale != 1.0:
        c = cv2.resize(c, None, fx=upscale / sx, fy=upscale / sy, interpolation=cv2.INTER_CUBIC)
    out = np.full_like(c, 0)
    out[gray_white(c)] = 255
    return out


def ocr_text(ocr, crop):
    if crop is None or crop.size == 0:
        return ''
    try:
        res = ocr(crop)
    except Exception:
        return ''
    return ''.join(res.txts) if getattr(res, 'txts', None) else ''
