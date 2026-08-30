# 生成 web/frames_map.js：filename|timestamp → 帧图文件名 映射
# 扫描 web/frames/ 下的正式帧（Pxx_时间戳[±偏移].jpg），与 subtitle_clean 记录建立映射
import os, re, json

BASE = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BASE, "web", "frames")
OUTPUT = os.path.join(BASE, "web", "frames_map.js")
SUBTITLE_DIR = os.path.join(BASE, "subtitle_clean")

# 帧文件名格式: P01_5m41s.jpg / P03_13m25s+1s.jpg / P08_0m18s-1s.jpg
FRAME_PATTERN = re.compile(r'^P(\d{1,2})_(\d+)m(\d+)s([+-]\d+s)?\.jpg$')

def main():
    # 1. 收集所有正式帧（排除 diag/raw 等）
    frames = {}
    if os.path.isdir(FRAMES_DIR):
        for fname in sorted(os.listdir(FRAMES_DIR)):
            if not fname.endswith(".jpg"): continue
            m = FRAME_PATTERN.match(fname)
            if not m: continue  # 排除 diag_*.jpg 等非正式帧
            ep, min_, sec, offset = m.groups()
            ep = int(ep)
            ts = f"{int(min_)}m{int(sec):02d}s"  # 秒数保留两位（0m00s 而非 0m0s）
            frames[(ep, ts)] = fname
    print(f"正式帧总数: {len(frames)}")

    # 2. 建立 subtitle_clean 记录 → 帧图映射（支持 ts±1s 回退：帧名=实际匹配帧时刻时仍可映射）
    def ts_sec(st):
        m = re.match(r'(\d+)m(\d+)s', st)
        return int(m.group(1)) * 60 + int(m.group(2)) if m else None

    def ts_str(sec):
        return f"{sec // 60}m{sec % 60:02d}s"

    mapping = {}
    matched = 0
    for fname in sorted(os.listdir(SUBTITLE_DIR)):
        if not fname.endswith(".json"): continue
        ep_m = re.match(r'\[P(\d+)\]', fname)
        if not ep_m: continue
        ep = int(ep_m.group(1))
        video_title = fname[:-5]
        with open(os.path.join(SUBTITLE_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            ts = entry.get("timestamp", "")
            key = f"{video_title}|{ts}"
            sec = ts_sec(ts)
            frame = None
            if sec is not None:
                # 精确优先；窗口版帧名=选中帧时刻（字幕持续期间 t>=ts 居多），
                # 密集扫描补丁帧达 ts+3s，回退扩到 ±3s
                for off in (0, 1, -1, 2, -2, 3, -3):
                    f = frames.get((ep, ts_str(sec + off)))
                    if f:
                        frame = f
                        break
            if frame:
                mapping[key] = frame
                matched += 1
    print(f"映射记录数: {matched}")

    # 3. 输出 JS
    js = "window.FRAMES_MAP = " + json.dumps(mapping, ensure_ascii=False, separators=(",", ":")) + ";"
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"输出: {OUTPUT} ({len(js.encode('utf-8'))/1024:.0f} KB)")

if __name__ == "__main__":
    main()
