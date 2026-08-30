import os
from PIL import Image
# 添加 ANTIALIAS 兼容性处理
Image.ANTIALIAS = Image.Resampling.LANCZOS

import numpy as np
import ddddocr
import io
import json
import re
from collections import defaultdict
from params import SUBTITLE_AREA, REQUIRED_RESOLUTION

class SubtitleExtractor:
    def __init__(self):
        # 只初始化 OCR
        self.ocr = ddddocr.DdddOcr()

        # 设置字幕区域裁剪范围（来自 params.py，可针对《罗布奥特曼》字幕位置调整）
        self.crop_box = SUBTITLE_AREA
        
        # 正则表达式模式
        self.pattern = r'\[([^]]+)\]([^_]+)_(\d+m\d+s)_sim_(\d+\.\d+)'
        
        # 存储字幕的字典
        self.subtitles_dict = defaultdict(list)

    def parse_timestamp(self, timestamp):
        """将时间戳 (如 "2m28s") 转换为总秒数"""
        match = re.match(r'(\d+)m(\d+)s', timestamp)
        if match:
            minutes, seconds = map(int, match.groups())
            return minutes * 60 + seconds
        return 0

    def process_image(self, img_path):
        """处理单个图像并提取文字"""
        img = Image.open(img_path)
        
        if img.size != REQUIRED_RESOLUTION:
            return None
            
        # 裁剪图像
        cropped_img = img.crop(self.crop_box)
        
        # 图像预处理
        img_array = np.array(cropped_img)
        mask = np.all(img_array > 245, axis=2)
        img_array[mask] = [255, 255, 255]
        img_array[~mask] = [0, 0, 0]
        
        # 转换为PIL图像
        processed_img = Image.fromarray(img_array)
        
        # 准备OCR
        buffer = io.BytesIO()
        processed_img.convert('RGB').save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        
        # OCR识别
        text = self.ocr.classification(image_bytes)
        return text.strip() if text else None

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

            episode_num, title, timestamp, similarity = match.groups()
            video_title = f"{episode_num}{title}"
            print(f"处理文件: {filename}")
            
            img_path = os.path.join(input_folder, filename)
            text = self.process_image(img_path)
            
            if not text:
                continue

            print(f"识别到文本: {text}")
            
            # 检查重复
            subtitles = self.subtitles_dict[video_title]
            if subtitles and subtitles[-1]["text"] == text:
                continue
            
            # 添加字幕
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