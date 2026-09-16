# 爱染诚 · 台词档案馆

> 《罗布奥特曼》(Ultraman R/B) 全 25 集字幕检索 —— **每句台词对应一帧原片画面**。

**在线站点：<https://bonger34.github.io/aizen-subtitles/>**

---

## 项目简介

把 25 集 1080p 原片的字幕逐句转录成结构化数据，并为每一句配上一张"这句话正在被说出"的帧图，
做成一个纯静态的台词检索站。搜索任意关键词，得到的是台词文本 + 时间戳 + 对应画面。

页面上的两个开关对应两种检索意图：

| 控件 | 作用 |
|------|------|
| 文本匹配度 | 0–100，默认 50。控制模糊匹配的宽松程度 |
| 人脸相似度 | 0–1，默认 0。按帧图上的人脸相似度过滤 |
| 仅列爱染诚档案 | 只保留"说这句话时画面里有爱染诚"的条目 |
| 爱染诚优先 | 不筛选，但把上述条目排到前面 |

## 数据规模（实测，非估计）

| 项 | 数量 | 说明 |
|---|---:|---|
| 集数 | 25 | 全剧 |
| 归档台词 | **6783** 条 | `subtitle_clean/`，站点唯一数据源 |
| 爱染诚登场条目 | **539** 条 | 说话时画面含爱染诚 |
| 帧图 | **6775** 张 | 960×540 |
| 帧图覆盖率 | **100.0%** | 6783 条全部有对应帧文件，无占位 |
| 站点体积 | **398 MB** | `docs/`，其中帧图 396.9 MB |

数据的可信度不是靠"看起来对"得来的。仓库里保留了完整的验证链，任何时候都能重跑：

```bash
python scripts/pipeline/rebuild_map.py         # 6783 -> 6783 键, 缺帧 0
python scripts/pipeline/make_subtitle_db.py    # 生成 docs/subtitle_db
python scripts/pipeline/verify_consistency.py  # 缺键 0 / 缺文件 0 / 孤儿键 0
python scripts/pipeline/duration_check.py      # 无条目超出视频长度
python scripts/pipeline/dup_check.py           # 同秒重复组 0
python scripts/pipeline/stat_coverage.py       # 覆盖率 100.0%
node   scripts/pipeline/verify_search.js       # 408 命中 / 缺帧 0
python scripts/pipeline/q_audit.py             # 历史修正 195 处, 异常 0
```

## 仓库结构

```
VV_Rob/
├─ README.md                 本文件
├─ 复刻运行手册.md            完整复刻流程（环境 → 取视频 → 人脸 → 字幕 → 站点）
├─ 漏句检测方法论.md          漏句检测的采样数学保证与踩坑记录
├─ requirements.txt
├─ LICENSE                   GPL-3.0（继承自上游 VV）
│
├─ subtitle_clean/           【权威库】25 集 / 6783 条台词，站点的唯一数据源
├─ subtitle/                 管线第 5 步的输出目录（站点不读它）
├─ docs/                     GitHub Pages 站点本体
│   ├─ index.html  style.css  script.js  db_search.js
│   ├─ subtitle_db           gzip 压缩的字幕库（前端 IndexedDB 缓存）
│   ├─ frames_map.js         条目 → 帧文件名的映射
│   ├─ aizen_frames.js       539 张"含爱染诚"的帧名单（编译期输入）
│   └─ frames/               6775 张帧图
│
├─ scripts/                  全部 308 个 Python 脚本
│   ├─ README.md             逐个脚本的索引（机器生成，不会漂移）
│   ├─ pipeline/             【23 个 .py + 1 个 .js】复刻必需 —— 构建链 + 六项校验
│   └─ oneoff/               【285 个】一次性脚本，研究过程留档
│
├─ review/                   复核报告与判定记录；同时是校验链的工作目录
├─ archive/                  历史归档
│   └─ datasets/             早期数据集：各轮清洗快照 + 另两次 OCR/VL 跑的结果
│
└─ tools/                     爱染诚人脸候选抽取脚本（手册第 3 步用）

上游 VV 的 api/ · search/ · DataProcess/ · vercel.json 本站一个都不用，因此没有收录
—— 它们是什么、为什么不需要，见手册第 6.2 节；需要对照时去上游仓库取。

本地目录（未入库，clone 后不存在）：
Videos/ 24.4 GB 原片 · target/ 人脸训练图 · clusters/ · faces_candidates/
```

### 关于 `scripts/oneoff/`

那 286 个脚本是字幕清洗过程的研究留档，不是产品代码 —— 它们记录了 6783 条台词
是怎么一条条核出来的（帧图错位修复、白边掩膜解字幕行、漏句扫描、共用配图纠正……）。
按名字前缀可以大致定位：

| 前缀 | 数量 | 用途 |
|---|---:|---|
| `q_` | 77 | 文本**质**量系列：交互式取证与核对 |
| `dense*` | 22 | 密集扫描（扩窗 + 高采样率找漏句） |
| `orphan_` | 17 | 孤儿帧：无库条目引用的帧图定性 |
| `extract_` / `scan*` | 23 | 抽帧与全片扫描 |
| `check_` / `fix_` / `apply_` | 32 | 断言检查 → 修复 → 落地 |
| `_` | 8 | 临时/一次性 |

完整清单见 `scripts/README.md`。

## 复刻 / 二次开发

改字幕区域、换人脸目标、重跑全流程 —— 见 **[复刻运行手册.md](复刻运行手册.md)**。
手册里的路径已与 `scripts/` 结构对齐，可直接照抄执行。

只想改站点外观：直接编辑 `docs/` 下的 5 个文件即可，无需重新构建数据。

## 上游与许可

本项目是 **[Cicada000/VV](https://github.com/Cicada000/VV)**（《这就是中国》张维为语录查询）的
fork。上游提供了一整套"视频 → 人脸识别 → 字幕 OCR → 静态检索站"的管线，
本项目沿用了它的架构、前端检索算法（LCS 匹配 + IndexedDB 缓存）与 GPL-3.0 许可。

相对上游的主要改动：

| 方向 | 内容 |
|------|------|
| 数据 | 全部替换为《罗布奥特曼》—— 25 集字幕、6775 张帧图、爱染诚人脸特征 |
| 管线 | `params.py` 新增 `SUBTITLE_AREA` / `REQUIRED_RESOLUTION`；解出"白边掩膜"字幕行切分法 |
| 前端 | 品牌与文案改为爱染诚档案室；新增爱染诚筛选与优先排序 |
| 数据源 | 站点改用本地 `docs/subtitle_db`，不再请求上游域名 |
| 已移除 | 上游的 `api/`、`search/`、`DataProcess/`、`vercel.json`、Telegram bot、云端 RAG、口吧水印等本站用不到的能力 |

逐条改动见 `git log` —— 每个提交只做一件事，提交信息写明了改动前后的状态。

**许可**：GPL-3.0（见 [LICENSE](LICENSE)）。沿用上游许可，二次分发请保留同样的自由。

## 声明

本档案转录《罗布奥特曼》全剧字幕，帧图取自原片，**仅供对白检索与学习交流**。
《罗布奥特曼》及相关角色、影像的著作权归圆谷制作株式会社等权利人所有。
