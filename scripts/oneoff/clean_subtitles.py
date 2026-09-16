# 清洗字幕库：过滤日文假名、无中文、过短无意义记录、繁体字（职员表）
# 输出到 subtitle_clean/，供后续 subtitle_db.js 与抽帧使用
import os, json, re, sys

try:
    from opencc import OpenCC
    _cc = OpenCC('t2s')  # 繁→简
except ImportError:
    _cc = None
    print("警告: OpenCC 未安装，繁体检测规则跳过")

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(BASE, "subtitle")
DST = os.path.join(BASE, "subtitle_clean")
PATTERN = re.compile(r'^\[P(0[1-9]|1[0-9]|2[0-5])\]')

# 日文假名范围（含片假名长音符 ー）
HIRAGANA = re.compile(r'[\u3040-\u309f]')
KATAKANA = re.compile(r'[\u30a0-\u30ff]')
CJK = re.compile(r'[\u4e00-\u9fff]')
# 尾部纯 ASCII 乱码（如 "你们来找我有什么事egreo" 的 "egreo"）
TAIL_ASCII = re.compile(r'[a-zA-Z0-9_\-]{2,}\s*$')
# 文本中任意位置的 ASCII 字母片段（含单个字母，如 "N哥哥" 的 "N"、"做什么DREN" 的 "DREN"）
# 只删字母不删数字，避免误伤 "15年之久"、"第12集" 等有效数字
MID_ASCII = re.compile(r'[a-zA-Z]{1,}')
# 白名单：有效台词中的合法英文缩写/词（剥离时保护，不被当作乱码删除）
# 经扫描确认：仅 PDF/GPS/NASA 是有效台词（OK/TV/AI 只出现在乱码串中，不保护）
WHITELIST = ["PDF", "GPS", "NASA"]
# VL 日期幻觉残留（PaddleOCR-VL 对 OP 歌词/模糊帧的幻觉输出，无假名无 ASCII，
# 常规规则过滤不掉）：年份+赛事/日期 模式，如 "2023年夏季国际高山滑雪锦标赛"、"2023年1月1日星期一"
DATE_HALLUCINATION = re.compile(r'(20\d{2}年|星期一|星期二|星期三|星期四|星期五|星期六|星期日)')
# 占位符（用不会被 MID_ASCII 匹配的字符序列，还原时替换回来）
_PLACEHOLDER_PREFIX = "\uE000"  # 私用区字符，避免与真实文本冲突

def clean_text(text: str) -> str:
    """清洗文本：剥离 ASCII 字母乱码（水印/装饰残片），但保留白名单英文词，返回清洗后的文本"""
    t = text.strip()
    # 1. 保护白名单词（替换为占位符）
    placeholders = {}
    for i, w in enumerate(WHITELIST):
        if w in t.upper() or w in t:
            # 大小写不敏感匹配，用原词替换
            t = re.sub(w, f"{_PLACEHOLDER_PREFIX}{i}", t, flags=re.IGNORECASE)
            placeholders[i] = w
    # 2. 去掉任意位置的 ASCII 字母（OCR 误识别的水印/装饰残片，含单个字母）
    t = MID_ASCII.sub('', t)
    # 3. 还原白名单词
    for i, w in placeholders.items():
        t = t.replace(f"{_PLACEHOLDER_PREFIX}{i}", w)
    # 4. 压缩因剥离产生的多余空白/标点
    t = re.sub(r'[，。！？、\s]+$', '', t)
    t = re.sub(r'^\s+', '', t)
    return t.strip()

def is_noise(text: str) -> bool:
    """判定是否为噪声记录（True=应过滤）"""
    t = clean_text(text)  # 先剥离尾部乱码
    if not t:
        return True
    # 规则1: 含日文假名（≥1）→ 过滤（歌词/日文原句；有效中文台词不会出现假名）
    hiragana = len(HIRAGANA.findall(t))
    katakana = len(KATAKANA.findall(t))
    if hiragana + katakana >= 1:
        return True
    # 规则2: 无中文字符 → 过滤（纯 ASCII 乱码/英文/数字）
    cjk = len(CJK.findall(t))
    if cjk == 0:
        return True
    # 规则3: 中文占比过低（<40% 且含大量非中文字符）→ 过滤
    total = len(t)
    if cjk / total < 0.4:
        return True
    # 规则4: 繁体字检测 → 过滤（简中字幕不应含繁体，职员表多为繁体/日文汉字）
    if _cc is not None:
        converted = _cc.convert(t)
        if converted != t:
            return True
    # 规则5: VL 日期幻觉残留 → 过滤（如 "2023年1月1日星期一"、"2023年夏季国际高山滑雪锦标赛"）
    if DATE_HALLUCINATION.search(t):
        return True
    return False

def main():
    os.makedirs(DST, exist_ok=True)
    total_before = 0
    total_after = 0
    total_filtered = 0
    files_processed = 0

    for fname in sorted(os.listdir(SRC)):
        if not (fname.endswith(".json") and PATTERN.match(fname)):
            continue
        files_processed += 1
        with open(os.path.join(SRC, fname), encoding="utf-8") as f:
            data = json.load(f)
        total_before += len(data)

        kept = []
        filtered = []
        for entry in data:
            text = entry.get("text", "").strip()
            if is_noise(text):
                filtered.append(entry)
            else:
                # 保存剥离尾部乱码后的文本
                entry = dict(entry)
                entry["text"] = clean_text(text)
                kept.append(entry)

        total_after += len(kept)
        total_filtered += len(filtered)
        with open(os.path.join(DST, fname), "w", encoding="utf-8") as f:
            json.dump(kept, f, ensure_ascii=False, indent=2)
        print(f"  {fname}: {len(data)} → {len(kept)} (滤 {len(filtered)})")

    print(f"\n=== 清洗统计 ===")
    print(f"处理文件: {files_processed}")
    print(f"清洗前: {total_before} 条")
    print(f"清洗后: {total_after} 条")
    print(f"过滤: {total_filtered} 条 ({total_filtered/total_before*100:.1f}%)")
    print(f"输出: {DST}")

if __name__ == "__main__":
    main()
