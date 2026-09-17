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
| 归档台词 | **6699** 条 | `subtitle/`，站点唯一数据源 |
| 爱染诚登场条目 | **534** 条 | 说话时画面含爱染诚 |
| 帧图 | **6696** 张 | 960×540 |
| 帧图覆盖率 | **100.0%** | 6699 条全部有对应帧文件，无占位 |
| 站点体积 | **398 MB** | `docs/`，其中帧图 396.9 MB |

数据的可信度不是靠"看起来对"得来的。仓库里保留了完整的验证链，任何时候都能重跑：

```bash
python scripts/pipeline/rebuild_map.py         # 6699 -> 6699 键, 缺帧 0
python scripts/pipeline/make_subtitle_db.py    # 生成 docs/subtitle_db
python scripts/pipeline/verify_consistency.py  # 缺键 0 / 缺文件 0 / 孤儿键 0
python scripts/pipeline/duration_check.py      # 无条目超出视频长度
python scripts/pipeline/dup_check.py           # 同秒重复组 0
python scripts/pipeline/stat_coverage.py       # 覆盖率 100.0%
node   scripts/pipeline/verify_search.js       # 408 命中 / 缺帧 0
python scripts/pipeline/q_audit.py             # 历史修正 195 处(落盘 170 · 回退 2 · 已删 23), 异常 0
```

## 仓库结构

```
VV_Rob/
├─ README.md                 本文件
├─ 复刻运行手册.md            完整复刻流程（环境 → 取视频 → 人脸 → 字幕 → 站点）
├─ 字幕核对方法论.md          判定口径 / 漏句检测 / 帧图 / 带外剔除 / 去重 / 时间戳 / 参数表
├─ requirements.txt
├─ LICENSE                   GPL-3.0（继承自上游 VV）
│
├─ subtitle/                 【权威库】25 集 / 6699 条台词，站点的唯一数据源
├─ subtitle_raw/             main.py 的输出目录（重跑管线时创建，站点不读它）
├─ docs/                     GitHub Pages 站点本体
│   ├─ index.html  style.css  script.js  db_search.js
│   ├─ subtitle_db           gzip 压缩的字幕库（前端 IndexedDB 缓存）
│   ├─ frames_map.js         条目 → 帧文件名的映射
│   ├─ aizen_frames.js       534 张"含爱染诚"的帧名单（编译期输入）
│   └─ frames/               6696 张帧图
│
├─ scripts/                  构建与校验脚本（全部可移植，无硬编码路径）
│   ├─ README.md             逐个脚本的索引
│   └─ pipeline/             【23 个 .py + 1 个 .js】复刻必需 —— 构建链 + 六项校验
│
├─ review/                   复核报告与判定记录；同时是校验链的工作目录
│   ├─ 复核总报告.md          全过程记录与证据清单（合并了原先 10 篇分轮报告）
│   └─ *.json                 10 个判定源文件
├─ archive/                  历史归档
│   └─ datasets/             早期数据集：各轮清洗快照（5232 / 5797 等）+ 另两次 OCR/VL 跑的结果
│
└─ tools/                     爱染诚人脸候选抽取脚本（手册第 3 步用）

上游 VV 的 api/ · search/ · DataProcess/ · vercel.json 本站一个都不用，因此没有收录
—— 它们是什么、为什么不需要，见手册第 6.2 节；需要对照时去上游仓库取。

本地目录（未入库，clone 后不存在）：
Videos/ 23.85 GB 原片 · target/ 人脸训练图 · clusters/ · faces_candidates/ · output_frames/
```

### 过程留档去哪了

285 个一次性脚本（`scripts/oneoff/`，24912 行）已在 2026-09 删除 —— 它们是**只能读、
不能跑**的研究留档：212 个写死了本机绝对路径，引用的 200 种中间产物也已随 `review/`
的中间产物一起移出仓库。

它们写下的判据、参数与踩坑已提炼进 **[字幕核对方法论.md](字幕核对方法论.md)**
（判定口径 / 字幕定位 / **漏句检测** / 帧图 / 带外与去重 / 时间戳 / 环境 / 流程自身的坑 / 参数表）；
各轮的实测数据、推导过程与证据清单在 **[review/复核总报告.md](review/复核总报告.md)**。
需要看某个结论的原始实现时：

```bash
git log --oneline -- scripts/oneoff/          # 找出删除前的提交
git show <提交>:scripts/oneoff/q_tsread.py    # 取回单个脚本
```

## 复刻 / 二次开发

改字幕区域、换人脸目标、重跑全流程 —— 见 **[复刻运行手册.md](复刻运行手册.md)**。
手册里的路径已与 `scripts/` 结构对齐，可直接照抄执行。

只想改站点外观：直接编辑 `docs/` 下的 `index.html` / `style.css` / `script.js` / `db_search.js`
这 4 个文件即可，无需重新构建数据。（`docs/` 下其余文件是数据产物：`subtitle_db` /
`subtitle_db.js` 由 `make_subtitle_db.py` 生成，`frames_map.js` 由 `rebuild_map.py` 生成，
`frames/` 由 `make_frames_full.py` 生成。）

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
| 数据源 | 站点改用本地 `docs/subtitle_db`，不再请求上游域名（`vvdb.cicada000.work` 已移除） |

站点剩下的对外请求只有两处：跳转原片的 `bilibili.com` 链接，以及 `index.html` 里引的
Google Fonts（Noto Sans SC / IBM Plex Mono）。字体有完整的系统字体兜底链
（`微软雅黑` / `Segoe UI` / `Consolas`），取不到时只是字形变化，不影响功能。
| 已移除 | 上游的 `api/`、`search/`、`DataProcess/`、`vercel.json`、Telegram bot、云端 RAG、口吧水印等本站用不到的能力 |

逐条改动见 `git log` —— 每个提交只做一件事，提交信息写明了改动前后的状态。

**许可**：GPL-3.0（见 [LICENSE](LICENSE)）。沿用上游许可，二次分发请保留同样的自由。

## 声明

本档案转录《罗布奥特曼》全剧字幕，帧图取自原片，**仅供对白检索与学习交流**。
《罗布奥特曼》及相关角色、影像的著作权归圆谷制作株式会社等权利人所有。
