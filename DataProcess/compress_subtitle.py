# ⚠️ 已废弃, 不要用它建本站的库 —— 用 scripts/pipeline/make_subtitle_db.py
#
# 这是一个会静默产出"看起来正常但更差"的库的陷阱, 两处硬伤:
#   1. 它读 subtitle/, 本站的权威库是 subtitle_clean/  (少 986 条)
#   2. 它产出的记录没有 d 字段, 而 docs/db_search.js:130 读 item.d 判"画面含爱染诚"
#      -> 539 条爱染诚标记会全部归零, 前端"仅列爱染诚档案"开关点下去返回空
#
# 上游 VV 用它是没问题的(上游没有 d 字段的需求); 本站已由 make_subtitle_db.py 取代。
# 保留此文件仅为尊重上游、便于对照。
import json
import os
import gzip
import base64
from pathlib import Path

def optimize_subtitle_database():
    subtitle_dir = Path("subtitle")
    output_file = Path("subtitle_db.gz")
    
    if not subtitle_dir.exists():
        return
    output_file.parent.mkdir(exist_ok=True)
    all_subtitles = []
    
    for json_file in subtitle_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            filename = json_file.name
            episode_match = filename.split("]")[0].replace("[P", "")
            episode_num = int(episode_match) if episode_match.isdigit() else 0
 
            for item in data:
                all_subtitles.append({
                    "e": episode_num,               
                    "f": filename,                 
                    "t": item.get("timestamp", ""),  
                    "s": item.get("similarity", 0),  
                    "x": item.get("text", "")
                })
            
        except Exception as e:
            print(e)
    
    json_data = json.dumps(all_subtitles, ensure_ascii=False)
    compressed_data = gzip.compress(json_data.encode('utf-8'), compresslevel=9)
    
    with open(output_file, "wb") as f:
        f.write(compressed_data)

if __name__ == "__main__":
    optimize_subtitle_database() 