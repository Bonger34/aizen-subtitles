# 将 25 集罗布奥特曼字幕 JSON 转为纯前端搜索用的 gzip subtitle_db
# 格式与原项目 VV/Web 一致：每条记录 {f: 文件名, t: 时间戳, s: 人脸相似度, x: 文本}
# 数据源：subtitle_clean/（已清洗噪声）
import os, json, gzip, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
SUBTITLE_DIR = os.path.join(BASE, "subtitle_clean")  # 使用清洗后数据
WEB_DIR = os.path.join(BASE, "web")
OUTPUT = os.path.join(WEB_DIR, "subtitle_db")

# 只匹配 [P01]~[P25]，排除旧项目《这就是中国》的 [P00x]/[Pxxx] 三位数文件
PATTERN = re.compile(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]')


def load_js_object(path):
    """读取形如 `window.XXX = {...};` 的 JS 声明，返回 dict（文件不存在返回空）。"""
    if not os.path.exists(path):
        return {}
    content = open(path, encoding='utf-8').read()
    m = re.search(r'=\s*(\{.*?\})\s*;', content, re.S)
    return json.loads(m.group(1)) if m else {}


def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    # 爱染诚标记：帧名 -> 1（画面含爱染诚）；映射：f|t -> 帧名
    AISOME = load_js_object(os.path.join(WEB_DIR, 'aisome_frames.js'))
    FMAP = load_js_object(os.path.join(WEB_DIR, 'frames_map.js'))
    print(f'加载: 爱染诚帧标记 {len(AISOME)} 个，帧映射 {len(FMAP)} 条')
    records = []
    files = sorted(f for f in os.listdir(SUBTITLE_DIR)
                   if f.endswith(".json") and PATTERN.match(f))
    if not files:
        print("未找到罗布字幕 json（[P01]~[P25]），请检查 subtitle/ 目录")
        sys.exit(1)

    for fname in files:
        filepath = os.path.join(SUBTITLE_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        video_title = fname[:-5]  # 去掉 .json 后缀
        n = 0
        for entry in data:
            text = entry.get("text", "").strip()
            if not text:
                continue
            ts = entry.get("timestamp", "")
            # 该条字幕对应帧若「画面含爱染诚」→ d=1（爱染诚相关台词）
            frame = FMAP.get(f"{video_title}|{ts}")
            d = 1 if (frame and frame in AISOME) else 0
            records.append({
                "f": video_title,
                "t": ts,
                "s": entry.get("similarity", 0.0),
                "x": text,
                "d": d
            })
            n += 1
        print(f"  {fname}: {n} 条")

    # gzip 压缩写入（与原项目 subtitle_db 同格式）
    raw = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    compressed = gzip.compress(raw.encode("utf-8"))
    with open(OUTPUT, "wb") as f:
        f.write(compressed)

    # 输出明文 JS 版（file:// 直开兼容：script 标签注入，不受 CORS 限制）
    js_output = os.path.join(WEB_DIR, "subtitle_db.js")
    js_content = "window.SUBTITLE_DB = " + raw + ";"
    with open(js_output, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"\n总记录数: {len(records)}")
    print(f"原始大小: {len(raw.encode('utf-8'))/1024:.1f} KB")
    print(f"gzip 大小: {len(compressed)/1024:.1f} KB")
    print(f"JS 版大小: {len(js_content.encode('utf-8'))/1024:.1f} KB")
    print(f"输出: {OUTPUT}")
    print(f"输出: {js_output}")

if __name__ == "__main__":
    main()
