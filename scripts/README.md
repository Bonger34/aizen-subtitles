# scripts/ —— 构建与校验脚本

这里只有**参与「从视频到站点」构建与校验**的脚本，全部可移植（实测：0 处写死绝对路径）。

| 目录 | 数量 | 内容 |
|---|---:|---|
| `pipeline/` | 23 个 `.py` + 1 个 `.js` | 验证链用到的入口 + 它们 import 的共享库（依赖闭包） |

用法见仓库根目录的 `复刻运行手册.md`。**本索引是手工维护的** —— 增删 `pipeline/` 下的文件时
请一并更新这里的表格。

### 脚本的位置约定

脚本里指向仓库根的锚点统一是**上三级**：

```python
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

`q_common.py` 是唯一的例外：它按**上四级**去找 `_nv_dlls/` 与 `_ort124/`（CUDA 12 的 DLL 与
onnxruntime 1.24.4，见 `字幕核对方法论.md` §7.1）。这两个目录在**仓库之外**、
随机器而建，**clone 后不存在**；脚本用 `os.path.isdir()` 守卫，缺了就跳过 —— 只是 GPU 加速
失效（回退 CPU，单帧从 0.6s 掉到 5~15s），不影响正确性。

> 2026-09 之前这里还有 285 个一次性脚本（`oneoff/`）。那批是字幕清洗过程的研究留档，
> 只能读不能跑（212 个写死了本机绝对路径），已删除；它们写下的判据与参数提炼在
> 仓库根目录的 `字幕核对方法论.md`，需要原始实现时用
> `git show <提交>:scripts/oneoff/<脚本名>.py` 取回。

## pipeline/ —— 复刻必需

站点构建链 + 六项校验 + 手册 §11/§12 的复核流程工具。


### `q_` —— 文本**质**量系列：交互式取证与逐条核对（7 个）

| 文件 | 说明 |
|---|---|
| `q_align_tl.py` | q_align.py — 把全片字幕时间线(q_timeline_<EP>.json)与库条目对齐, 判定每条文本该不该改。 |
| `q_audit.py` | 从 subtitle 反查全部文本修正是否已落盘, 生成统一审计文件。 |
| `q_common.py` | 文本质量提升共用的字幕行切分与 OCR 引擎构造。 |
| `q_reframe.py` | 重新抽取"帧图与文本对不上"的条目的画面帧。 |
| `q_rescan.py` | 全库文本质量提升: 原帧重扫(自适应行切分 + 双路识别 + 多帧投票)。 |
| `q_subband.py` | 1080p 原帧字幕行定位 + 干净裁切(解决"白衬衫吃掉字幕行"的问题)。 |
| `q_timeline.py` | 全片字幕时间线重扫(文本质量提升的主数据源)。 |

### `verify_` —— 验证（2 个）

| 文件 | 说明 |
|---|---|
| `verify_consistency.py` | 最终一致性校验 |
| `verify_search.js` | 用 node 模拟前端搜索, 验证数据可用性与帧文件存在 |

### `make_` —— 产物生成（3 个）

| 文件 | 说明 |
|---|---|
| `make_frames_full.py` | 全量抽帧：960×540、JPEG q80、等比缩放居中 → `docs/frames/` |
| `make_frames_map.py` | 生成 `docs/frames_map.js`：`filename\|timestamp` → 帧图文件名 映射（含 ±3s 回退窗口） |
| `make_subtitle_db.py` | 把 `subtitle/` 的 25 集 JSON 转成纯前端搜索用的 gzip `docs/subtitle_db` + 明文 `docs/subtitle_db.js` |

### `_` —— 临时/一次性（1 个）

| 文件 | 说明 |
|---|---|
| `_make_snapshot.py` | 把 docs/ 的单页应用打包成"双击即看"的单文件快照。**已不再维护快照产物**（回退统一走 git，见手册 §14），脚本留作备用 |

### 管线本体与共享库（11 个）

| 文件 | 说明 |
|---|---|
| `main.py` | **管线入口**。遍历 `Videos/` 每集：抽帧 + 人脸相似度 → 字幕 OCR → 写 `subtitle_raw/`；已存在同名字幕 JSON 的集会被跳过（断点续跑）；每集跑完把 `output_frames/` 轮转成 `output_frames_old_<时间>` |
| `params.py` | 全部路径与适配参数：`SUBTITLE_AREA` / `REQUIRED_RESOLUTION` / `SUBTITLE_OUTPUT` / GPU 开关 |
| `FaceRec_insightface.py` | 人脸识别器：按 insightface embedding 算余弦相似度，把相似度编码进帧文件名（跨阶段数据总线） |
| `CutSubtitle_rapidocr.py` | **`main.py` 真正调用的字幕提取器**（RapidOCR / ONNX）。白字 `>245` 二值化后 OCR `SUBTITLE_AREA` |
| `CutSubtitle_paddleocr.py` | 同一接口的 PaddleOCR 版实现（本站未使用，保留作对照） |
| `CutSubtitle.py` | 最早的一版实现（上游遗留 + ANTIALIAS 兼容性处理），本站未使用 |
| `generate_features_insightface.py` | 把 `target/` 里的爱染诚正脸批量提特征，写 `face_features_insightface.npz`（手册第 3 步） |
| `rebuild_map.py` | 以字幕库为唯一真源重建 `frames_map.js`（不含 `clean_map.py` 里的一次性 P02 修改） |
| `dup_check.py` | 校验：找出库内同集同时间戳的重复条目 |
| `duration_check.py` | 校验：库条目时间戳是否超出视频实际长度（超出即为错误时间戳），结果写 `review/duration_check.txt` |
| `stat_coverage.py` | 校验：最终覆盖率统计 + 无帧图台词清单，结果写 `review/coverage_final.json` |
