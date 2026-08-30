import os
from PIL import Image
Image.ANTIALIAS = Image.Resampling.LANCZOS

import numpy as np
import json
import re
from collections import defaultdict
from rapidocr_onnxruntime import RapidOCR
import traceback
from params import SUBTITLE_AREA, REQUIRED_RESOLUTION

class SubtitleExtractor:
    """基于 RapidOCR（PaddleOCR 模型 ONNX 移植）的中文字幕提取，接口与 CutSubtitle_paddleocr 一致。"""

    def __init__(self):
        self.ocr = RapidOCR()
        self.subtitle_area = SUBTITLE_AREA
        # 匹配 "标题_0m12s_sim_0.550" 形式
        self.pattern = r'([^_]+)_(\d+m\d+s)_sim_(\d+\.\d+)'
        self.subtitles_dict = defaultdict(list)

    def clean_text(self, text):
        """清理文本末尾的标点符号和多余空格"""
        if not text:
            return text
        return re.sub(r'[\u3000-\u303F\uFF00-\uFFEF\u2000-\u206F.,!?;:\s]+$', '', text.strip())

    def parse_timestamp(self, timestamp):
        match = re.match(r'(\d+)m(\d+)s', timestamp)
        if match:
            minutes, seconds = map(int, match.groups())
            return minutes * 60 + seconds
        return 0

    def process_image(self, img_path):
        try:
            img = Image.open(img_path)
            if img.size != REQUIRED_RESOLUTION:
                return None
            subtitle_img = img.crop(self.subtitle_area)
            img_array = np.array(subtitle_img)

            # 白字二值化(上游 VV 机制, fork 时曾丢失):
            # 字幕为白字黑描边 → 白色像素(>245)保留, 其余(彩色画面文字/招牌/片尾职员表)黑掉
            mask = np.all(img_array > 245, axis=2)
            img_array[mask] = [255, 255, 255]
            img_array[~mask] = [0, 0, 0]

            result, _ = self.ocr(img_array)

            img.close()
            subtitle_img.close()
            del img, subtitle_img, img_array

            if result:
                # result 结构: [[box, text, score], ...]（text 是字符串）
                texts = [r[1] for r in result if len(r) > 1 and isinstance(r[1], str) and r[1].strip()]
                joined = ''.join(texts).strip()
                joined = self.clean_text(joined)
                return joined if joined else None
            return None
        except Exception as e:
            print(f"Error processing image {img_path}:")
            traceback.print_exc()
            return None

    def process_frames(self, input_folder, output_folder):
        """处理文件夹中的所有帧并生成字幕"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for filename in sorted(os.listdir(input_folder)):
            if not filename.endswith(('.jpg', '.png')):
                continue
            match = re.match(self.pattern, filename)
            if not match:
                continue

            title, timestamp, similarity = match.groups()
            video_title = title
            print(f"处理文件: {filename}")

            img_path = os.path.join(input_folder, filename)
            text = self.process_image(img_path)

            if not text:
                continue

            print(f"识别到文本: {text}")

            subtitles = self.subtitles_dict[video_title]
            if subtitles and subtitles[-1]["text"] == text:
                continue

            self.subtitles_dict[video_title].append({
                "timestamp": timestamp,
                "similarity": float(similarity),
                "text": text
            })

        # 保存字幕文件
        for video_title, subtitles in self.subtitles_dict.items():
            sorted_subtitles = sorted(subtitles, key=lambda x: self.parse_timestamp(x["timestamp"]))
            output_json = os.path.join(output_folder, f"{video_title}.json")
            try:
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(sorted_subtitles, f, ensure_ascii=False, indent=4)
                print(f"成功保存 {video_title} 的字幕")
            except Exception as e:
                print(f"保存文件时出错: {str(e)}")

        print("\n处理完成")
