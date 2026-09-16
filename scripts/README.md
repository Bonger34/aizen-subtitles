# scripts/ —— 全部脚本

根目录原本堆着 308 个 `.py`，其中只有 23 个真正参与"从视频到站点"的构建与校验。
按这个边界分成两个目录：

| 目录 | 数量 | 判据 |
|---|---:|---|
| `pipeline/` | 23 个 .py + 1 个 .js | 验证链用到的入口 + 它们 import 的共享库（依赖闭包） |
| `oneoff/` | 285 个 .py | 其余。字幕清洗过程的研究留档，不是产品代码 |

**跑站点构建与六项校验只看 `pipeline/`**，用法见仓库根目录的 `复刻运行手册.md`。

### 脚本的位置约定

两个目录都在 `scripts/` 下，所以脚本里指向仓库根的锚点统一是**上三级**：

```python
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

`oneoff/` 里有 41 个脚本要 import `pipeline/` 的共享库（`q_common` / `params` / `q_rescan` …），
它们在被 import 的语句前插了一行 `sys.path` 引导。**移动这些脚本时两处都要跟着改。**

> 另注：`oneoff/` 里约 190 个脚本用的是写死的绝对路径（`B = r'D:\\...\\VV_Rob'`），
> 属于研究留档，没有做可移植化改造；`pipeline/` 里的脚本全部可移植。

## pipeline/ —— 复刻必需

站点构建链 + 六项校验 + 手册 §13/§14 的复核流程工具。


### `q_` —— 文本**质**量系列：交互式取证与逐条核对（7 个）

| 文件 | 说明 |
|---|---|
| `q_align_tl.py` | q_align.py — 把全片字幕时间线(q_timeline_<EP>.json)与库条目对齐, 判定每条文本该不该改。 |
| `q_audit.py` | 从 subtitle_clean 反查全部文本修正是否已落盘, 生成统一审计文件。 |
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
| `make_frames_full.py` | 全量抽帧脚本（F-1 定稿参数 v2） |
| `make_frames_map.py` | 生成 docs/frames_map.js：filename|timestamp → 帧图文件名 映射 |
| `make_subtitle_db.py` | 将 25 集罗布奥特曼字幕 JSON 转为纯前端搜索用的 gzip subtitle_db |

### `_` —— 临时/一次性（1 个）

| 文件 | 说明 |
|---|---|
| `_make_snapshot.py` | 把 docs/ 的单页应用打包成"双击即看"的单文件快照 |

### 其它（11 个）

| 文件 | 说明 |
|---|---|
| `CutSubtitle.py` | 添加 ANTIALIAS 兼容性处理 |
| `CutSubtitle_paddleocr.py` | 添加 ANTIALIAS 兼容性处理 |
| `CutSubtitle_rapidocr.py` |  |
| `FaceRec_insightface.py` |  |
| `dup_check.py` | 找出库内同集同时间戳的重复条目 |
| `duration_check.py` | 一致性检查: 库条目时间戳是否超出视频实际长度(超出即为错误时间戳)。 |
| `generate_features_insightface.py` |  |
| `main.py` |  |
| `params.py` | 路径配置 |
| `rebuild_map.py` | 以字幕库为唯一真源重建 frames_map.js(不含 clean_map.py 里的一次性 P02 修改)。 |
| `stat_coverage.py` | 最终覆盖率统计（无帧图台词清单） |

## oneoff/ —— 一次性脚本

按名字前缀分组。这一批记录了 6783 条台词是怎么一条条核出来的。


### `q_` —— 文本**质**量系列：交互式取证与逐条核对（77 个）

| 文件 | 说明 |
|---|---|
| `q_align.py` | 对账实验: 已存 Web 帧(搜索界面所见) 与 视频各时间点是否同一画面/同一句字幕。 |
| `q_apply.py` | 把 q_align_tl.py 判定为 apply_add 的高置信修正落盘到 subtitle_clean。 |
| `q_apply2.py` | 应用"帧图 × 时间线 双源互证"的文本修正(人工逐条核对后的清单)。 |
| `q_diag.py` | 诊断时间线采样: 打印指定时间区间的采样点(白像素数/签名差异/是否触发OCR)。 |
| `q_diag2.py` | 诊断 unmatched("无任何匹配")条目的成因: 该时间窗里时间线到底发生了什么。 |
| `q_diag3.py` | 诊断逐帧扫描为何仍读不到: 打印目标条目窗口内的白像素/触发/读数情况。 |
| `q_diag4.py` | 诊断"定位到了却读不出": 打印该 1080p 帧的全部文字行段与逐段识别结果。 |
| `q_diag5.py` | 打印 1080p 帧扫描区的逐行白像素剖面 + 扫描 row_th_ratio。 |
| `q_dump.py` | 打印时间线事件/采样点分布, 用于诊断重扫覆盖情况。 |
| `q_edgecheck.py` | 复核"边缘噪声/减字"类修正: 在 t±3s 内逐点读原片, 看画面支持旧文本还是新文本。 |
| `q_fill.py` | 对"时间线无读数"的条目做窗口补扫: 只在这些条目的时间窗内加密采样。 |
| `q_fillalign.py` | 把窗口补扫(q_fill_<EP>.json)的读数与条目对齐并分档。 |
| `q_final.py` | 汇总帧图验证(q_verifyall.json)结果: 分档 + 列出可能的文本修正。 |
| `q_find.py` | 在库中按文本片段查找条目(集/时间戳/文本), 并标出该条目在两种判定中的状态。 |
| `q_frames_audit.py` | 全库"画面 ↔ 文本"一致性审计。 |
| `q_frames_swap.py` | 把 docs/frames_fix/ 里重抽的帧按原文件名覆盖到 docs/frames/。 |
| `q_geom.py` | 纯几何侦察(不 OCR): 统计每帧底部文字行的位置/数量分布。 |
| `q_judge.py` | 重扫结果判定: 哪些条目该替换文本, 哪些被画面证实, 哪些无法同源定位。 |
| `q_list.py` | 按判定类型列出条目(默认 apply_add), 便于逐条人工核对。 |
| `q_listv.py` | 打印帧图验证的严格候选(帧图读数=新文本、≠旧文本), 文字版便于逐条核对。 |
| `q_locate.py` | 文本质量提升主流程: 用已存帧图在视频中反查真实帧, 再对 1080p 原帧重识别。 |
| `q_locate2.py` | 用「字幕带模板匹配」在 1080p 视频里反查帧图的真实帧, 再对原帧重识别。 |
| `q_locate2_apply.py` | 把人工看图后的 q_locate2 判定并入 q_manual_verdicts.json。 |
| `q_locate2_sheet.py` | 把 q_locate2 定位到的**原片帧**做成对照表, 供人工看图判定。 |
| `q_locate2_stat.py` | 汇总 q_locate2 的逐集结果, 分档并挑出"补全型"候选。 |
| `q_locate2_zoom.py` | 把 q_locate2 定位到的原片帧字幕行放大导图, 用于逐字核对。 |
| `q_locate_frame.py` | 在视频中定位"已存帧图"的真实时刻。 |
| `q_online.py` | 单遍在线定位 + 重识别(替代 q_locate 的两遍扫描)。 |
| `q_outscope_delete.py` | 删除可证的"带外条目"(版权卡/日文/演职员表/标题卡乱码)。 |
| `q_partial.py` | 用"帧图读数是旧文本的子集"来部分证实读不出的条目。 |
| `q_partial_fill.py` | 从"部分证实"里筛补全型候选: 旧文本是帧图读数的子序列, 且帧读更长。 |
| `q_pick3.py` | 从 unmatched 里筛"补数字/字母"型候选: 时间线读到的文本比旧文本多出数字或拉丁字母。 |
| `q_pick4.py` | 把人工核对通过的"非互斥收回"候选写入 q_manual_verdicts.json 的 frame_apply。 |
| `q_pick5.py` | 把帧图验证中人工确认的修正写入 q_manual_verdicts.json 的 frame_apply。 |
| `q_probe_band.py` | 探针: 找出能在 1080p 帧里把"字幕行"与"大面积白色衣物"分开的判据。 |
| `q_probe_frames.py` | 把指定条目的帧裁剪带(y820~1080)拼成一张对照图, 供人工核对字幕布局。 |
| `q_prof.py` | 重扫耗时分解: 找出每帧 0.9s 花在哪里(读帧/切段/紧裁/rec)。 |
| `q_prof2.py` | rec 调用开销基准: 单张 vs 批量(rec_batch_num), 决定重扫是否需要攒批。 |
| `q_prof3.py` | 测 rec_batch_num 对批处理吞吐的影响(单张 46ms 是固定启动开销, 攒批也许能摊薄)。 |
| `q_reclaim.py` | 把"被邻条抢走事件"的假 unmatched 收回, 并按非互斥最佳读数重新分档。 |
| `q_reframe_compare.py` | 生成"旧帧图 vs 新帧图"对照表, 用于确认帧图重抽是否修对了。 |
| `q_revert.py` | 回退经原片复核证伪的历史修正。 |
| `q_review9_apply.py` | 处理第 4 轮残留清单里的两类问题(逐条人工看过 586 条上下文后)。 |
| `q_sample_tg.py` | 从全库随机抽样若干条目, 用于估计"库文本 vs 画面"的整体一致率。 |
| `q_scan1.py` | 文本质量侦察: 统计库中可疑条目(短文本/含非中文字符/重复), 输出清单。 |
| `q_scan_ep.py` | 单集原帧重 OCR: 顺序读 1080p 视频, 对每条目取 3 帧, 按文字行分段识别。 |
| `q_scope.py` | 统计未澄清条目的时间分布, 区分"正片台词"与"片头/片尾非台词段"。 |
| `q_seektest.py` | 验证"seek(ts+Δ) + 与已存帧图做内容校验"能否稳定拿到帧图对应的 1080p 原帧。 |
| `q_server_test.py` | 试更强的识别模型(PP-OCRv6 SERVER)能否救回帧图读不出的条目。 |
| `q_sheet.py` | 为待人工核对的条目生成帧图对照表(帧图字幕带 + 旧/新文本 + 序号)。 |
| `q_sheet10.py` | 为"帧图显示的是别的句子"的残留条目生成**字幕带原尺寸**对照表。 |
| `q_sheet10_apply.py` | 应用"字幕带原尺寸对照表"逐条看图后的判定(16 张表 / 156 条)。 |
| `q_sheet11.py` | q_sheet10.py — 为"帧图显示的是别的句子"的残留条目生成**字幕带原尺寸**对照表。 |
| `q_sheet11_apply.py` | 应用第二批"字幕带原尺寸对照表"逐条看图后的判定(14 张表 / 136 条)。 |
| `q_sheet3.py` | 为 q_pick3.py 筛出的"补数字/字母"候选生成帧图对照表。 |
| `q_sheet4.py` | 为"非互斥收回"的 apply_add 型候选(37 条)生成帧图对照表, 供人工核对。 |
| `q_sheet5.py` | 为帧图验证"读不出"的条目生成对照表(帧图 + 旧文本 + 帧图读数), 用于找成因。 |
| `q_sheet6.py` | 为帧图验证的 candidate/weak 档生成对照表(帧图 + 旧文本 + 帧图读数)。 |
| `q_sheet7.py` | 为逐帧扫描(q_fill_resolved.json)的候选生成对照表(帧图 + 旧文本 + 逐帧读数)。 |
| `q_sheet8.py` | 为"帧图重抽失败的疑似正片台词"生成人工对照表。 |
| `q_sheet9.py` | 为"既没有匹配帧、自身时间戳也没被证实"的残留条目生成人工对照表。 |
| `q_sheet_v.py` | 为帧图验证结果生成对照表: 帧图字幕带 + 旧/时间线新/帧图读数。 |
| `q_show.py` | 把指定时间区间的视频帧按固定间隔裁出字幕带并拼图, 用于肉眼核对字幕与白像素。 |
| `q_sigtest.py` | 校准字幕签名: 对比"先缩放后阈值"与"先阈值后缩放"的白像素保留情况。 |
| `q_speed.py` | 测速: 视频 grab 速度 / 裁剪 OCR 单次耗时, 用于估算全量重扫时间。 |
| `q_speed2.py` | 验证"跳过检测、只跑识别(rec)"的可行性与加速比。 |
| `q_stat.py` | 统计 q_align_tl.json 各判定/编辑类型的分布, 并抽样打印。 |
| `q_stat2.py` | 统计 unmatched 条目里"时间线另有读数"的部分, 按相似度分档, 便于人工核对。 |
| `q_suspect.py` | 处理帧图重抽失败的"疑似正片台词"清单(150 条)。 |
| `q_targets.py` | 汇总"仍未澄清"的条目清单, 供逐帧视频扫描使用。 |
| `q_tsread.py` | **按库时间戳直接读原片**: 完全不依赖帧图, 是文本对错的最终判据。 |
| `q_tsread_merge.py` | 把逐集的 q_tsread<tag>_<EP>.json 合并成 q_tsread<tag>.json。 |
| `q_tsread_stat.py` | 汇总"按库时间戳直接读原片"的结果, 给出文本对错的权威分档。 |
| `q_verify.py` | 帧图第三方验证: 用搜索界面实际显示的帧图(960x540)对判定存疑的条目做独立识别。 |
| `q_verifyall.py` | 对"补扫仍未读到"的条目做帧图验证(带续跑与异常保护)。 |
| `q_view.py` | 打印重扫结果的逐条对照(支持 q_rescan / q_web / q_locate / q_online 四种产物)。 |
| `q_webcheck.py` | 用"搜索界面实际显示的帧图(docs/frames, 960x540)"重读字幕。 |

### `dense*` —— 密集扫描：扩窗 + 高采样率找漏句（22 个）

| 文件 | 说明 |
|---|---|
| `dense2_buckets.py` | 把 461 类疑似台词按"与库最近条目的双向分"分档, 分档给出样例与计数。 |
| `dense2_cd_filter.py` | 从 C/D 档(与库低相近)里筛出"像中文台词"的类: 要求含常见中文虚词, 且不是日文歌词式短串。 |
| `dense2_cluster.py` | 对 765 条疑似台词做聚类与近邻分析, 收敛出真正的候选。 |
| `dense2_dialogue_all.py` | 补漏: 对 B 档(与库双向分 0.4~0.6)以及全部 765 条疑似台词, 做"像中文台词"筛选并输出, 逐类人工复核。 |
| `dense2_filter.py` | 密集扫描候选的后处理: 按"只算台词"的口径过滤, 输出真候选清单。 |
| `dense2_filter2.py` | 密集扫描候选后处理(定稿): 先用全库双向模糊匹配排除"其实已收录"的, 再按"只算台词"过滤。 |
| `dense2_improve.py` | 统计: 密集扫描候选里有多少是"库文本是画面文本的真子集且缺的是数字"这类可无损改进项。 |
| `dense2_verdict.py` | 判定"像中文台词"的候选类是真漏句还是同句异读: |
| `dense3_apply.py` | 对"疑似漏句台词"逐条到视频复核, 通过后补入库(条目 + 配图帧)。 |
| `dense3_clean.py` | 最终清理: 手工剔除残留的片尾职员表/歌词/新闻画面文字, 并清理个别杂字前缀。 |
| `dense3_cleanup2.py` | 补做: 删除 8 条残留垃圾条目, 修正 2 处带杂字前缀的文本。 |
| `dense3_cleanup3.py` | 按文本删除残留垃圾条目(不依赖时间戳)。 |
| `dense3_curate.py` | 对复核通过的 750 条做最后策展: 剔除片尾歌词/演职员表/图鉴预告解说/跨集重复, 输出待入库清单。 |
| `dense3_curate2.py` | 二次收紧: 补上图鉴/预告/演职员表关键词 + 批内去重(同集同句 ±6s 只留一条)。 |
| `dense3_filter.py` | 密集扫描(修正版)候选后处理: 全库匹配 -> 按"只算台词"过滤 -> 输出待补清单。 |
| `dense3_finalize.py` | 最终策展: 排除片尾段(>=23m20s, 该段是演职员表/歌词/图鉴)后的待入库台词清单。 |
| `dense4_apply.py` | 最后一轮收敛: 从 369 条复核通过里剔除片尾段与"已有条目的片段", 入库剩余真台词。 |
| `dense4_cleanup.py` | 最后一轮清理: 删除歌词碎片条目, 修正一条被截断的文本。 |
| `dense4_final.py` | 收敛迭代: 对"疑似漏句 + 短文本"逐条到视频复核, 确认库中没有的补入库。 |
| `dense4_last9.py` | 收尾: 对 9 条正片残留台词候选逐条到视频复核, 确认后入库。 |
| `dense5_buckets.py` | 第四轮: 只复核"可能是台词"的候选(先前排除片头片尾歌词/版权卡/职员表/纯数字), 逐条到视频验证后入库。 |
| `dense5_cleanup.py` | 清理第四轮混入的非台词条目, 并修正一处带杂字前缀的文本。 |

### `scan*` —— 全片扫描（11 个）

| 文件 | 说明 |
|---|---|
| `scan3_cand.py` | 阶段1（vv_rob 环境）：rapidocr 粗筛候选帧 |
| `scan3_vl.py` | 阶段2（paddle_env_vv + vl_deps 环境）：VL 精判候选帧 |
| `scan6_probe.py` | 针对指定正常句的扩窗多通道探测 |
| `scan_cont.py` | C方案重做(连续读帧版) |
| `scan_cont_state.py` | 状态驱动采样版(验证短句覆盖) |
| `scan_ext_diff.py` | 三区域字幕检测对比(单遍读完, 只做检测, 不存帧不 OCR): |
| `scan_ext_ocr.py` | 对"仅 LOW 区间"(现有字幕带完全没覆盖、只有带下方有白字)做采样 OCR, 找漏掉的台词。 |
| `scan_full_quality.py` | 全库文本质量复核 v2（PP-OCRv5/v6 server · GPU） |
| `scan_noise.py` | 确定性噪声净化（提升计划 · 阶段 1） |
| `scan_sequence.py` | 密集扫描生成字幕序列（0.2s 步长，v5/v6 GPU） |
| `scan_series_dense.py` | 全系列密集扫描(扩窗 + 0.25s 密采): 找出库里没有的台词。 |

### `extract_` —— 抽帧（12 个）

| 文件 | 说明 |
|---|---|
| `extract_cont_frames.py` | 连续读帧提取候选全帧(960x540 jpg) |
| `extract_dialogue_cands.py` | 从带外(仅LOW)OCR 结果中筛出【台词字幕】候选。 |
| `extract_faces_enhanced.py` | 方案C：人脸优先 + 字幕兜底的全量抽帧 |
| `extract_faces_window.py` | 方案E：字幕持续窗口内的人脸最优帧 |
| `extract_frames_calibrated.py` | 试点：对一集（ts 校准后）重抽帧并验证命中率 |
| `extract_frames_dense.py` | 密集扫描补齐无帧图台词 |
| `extract_frames_scan3.py` | 无帧图台词的逐帧密集扫描（第三级） |
| `extract_frames_scan3_v5.py` | 剩余无帧台词的 VL 精扫（修正版） |
| `extract_frames_scan4.py` | 二值化预处理 + rapidocr 重扫无帧台词 |
| `extract_frames_scan5.py` | 全帧 OCR 通道重扫无帧台词 |
| `extract_frames_scan7.py` | PP-OCRv5/v6 server 引擎重扫无帧台词（19 条） |
| `extract_probe.py` | 顺序读视频, 抽取指定秒的画面存到 review/probe/, 供人工目视比对。 |

### `orphan_` —— 孤儿帧（无库条目引用的帧图）定性（17 个）

| 文件 | 说明 |
|---|---|
| `orphan_102_report.py` | 现有孤儿帧(102 张独有内容)的逐张问答: 画面里有没有台词字幕? 该台词在不在库里? |
| `orphan_ctx.py` | 查看指定集在指定秒附近的库条目, 判断孤儿帧是否是唯一证据。 |
| `orphan_del.py` | 删除"与已映射帧字节完全相同"的重复孤儿帧。 |
| `orphan_dialogue.py` | 重筛: 不看判定结果, 先剔除日文职员表特征, 列出所有含"对话样文本"的孤儿帧及其匹配去向。 |
| `orphan_final.py` | 汇总 102 张"独有内容"孤儿帧的最终定性, 统计各类占比。 |
| `orphan_fullframe.py` | 对"非台词"类孤儿帧做整帧 OCR: 检查是否有【不在字幕带内】的中文字幕(如次回预告卡顶部字幕)。 |
| `orphan_fullframe_query.py` | 在字幕库中检索整帧 OCR 新发现的中文句子, 判断是否已被收录。 |
| `orphan_groups.py` | 孤儿帧分组 × 时间区域 交叉统计, 输出可读报告(A 组正片逐条列出)。 |
| `orphan_hash.py` | 按文件内容哈希统计: 孤儿帧中有多少与已被 map 引用的帧字节完全相同(纯重复)。 |
| `orphan_ocr.py` | 孤儿帧 OCR 复核:确认孤儿帧里的字幕是否已被库覆盖。 |
| `orphan_offset_pix.py` | 孤儿帧 vs 库内同文本条目配图 的像素比对。 |
| `orphan_scan.py` | 孤儿帧体检:统计字幕带白色像素比,并与字幕库对照。 |
| `orphan_suspect.py` | 导出 A 组全部判定, 并筛出 OCR 含中文台词特征的帧供目视核查。 |
| `orphan_uniq_ocr.py` | 对 102 张"独有内容"孤儿帧中尚未 OCR 的 67 张补齐 OCR 并定性。 |
| `orphan_uniq_todo.py` | 对"独有内容"的孤儿帧补齐 OCR(未在 A/B 抽样中出现的), 并给出最终定性。 |
| `orphan_verdict.py` | 对 A 组孤儿帧做全库匹配: |
| `orphan_vs_map_pix.py` | 对"孤儿帧 vs 库条目配图"做像素比对, 判定是否为同一张图(即命名偏移造成的重复)。 |

### `check_` —— 断言式检查（12 个）

| 文件 | 说明 |
|---|---|
| `check_1char.py` | 抽样重 OCR 密集采样帧, 统计被 len<2 过滤掉的单字结果 |
| `check_cand_frames.py` | 直接复核密集扫描保存的候选帧: 这些帧正是候选文本被读出来的画面。 |
| `check_context.py` | 跨数据源核查 P06/P19 争议条目上下文 |
| `check_digit_loss.py` | 核实 3 条"库里掉了数字"的条目: 抓库条目的配图帧并 OCR, 看画面是否有数字。 |
| `check_empty.py` | 分析 OCR 空帧的成因 |
| `check_ext_dialogue.py` | 核查带外候选里"像对白"的几条: 看库中该时段有什么, 以及这些句子是否已存在于全库。 |
| `check_low_hit.py` | 检查已知"带外字幕"的时间点是否落在 仅LOW 区间内(验证扫描的召回)。 |
| `check_missing_lines.py` | 全库检索窗口扫描读到的句子, 判断是真缺还是已收录(可能记在别的时间点)。 |
| `check_offset.py` | 检查已补录条目的时间戳偏移 |
| `check_p06_cands.py` | 检查修好后的 P06 候选: 与全库双向匹配, 分出"库中已有"和"真缺"。 |
| `check_two_line.py` | 验证猜测: 候选文本是不是"两行字幕里库只记了第一行"的第二行。 |
| `check_window_missing.py` | 核实窗口扫描发现"库中缺失"的几句: 打印库中对应时段的条目, 看是否真的缺。 |

### `verify_` —— 验证（3 个）

| 文件 | 说明 |
|---|---|
| `verify_frames_ocr.py` | 对归位帧跑 OCR, 校验帧内容与台词一致 |
| `verify_new_lines.py` | 验证新入库的带外台词: 在 subtitle_db 中能搜到, 且配图帧存在。 |
| `verify_p06_misses.py` | 核实 P06 的几条"真缺台词": 抓画面 OCR + 列出库中同时段条目。 |

### `fix_` —— 文本修复（12 个）

| 文件 | 说明 |
|---|---|
| `fix_ascii_revert.py` | 修正 merge 阶段 ASCII 边段清理的误伤/残留 |
| `fix_digit_loss.py` | 修正 3 条"库文本掉了数字"的条目(配图画面已确认含该数字, 只改文本)。 |
| `fix_dups.py` | 处理库内同秒重复 |
| `fix_noise_entries.py` | 修复 51 条水印/日文残留条目 |
| `fix_offsets.py` | 把偏移过大的补录条目归位到真实秒(±3s 内) |
| `fix_p03_7m12s.py` | 按人工核定修正 P03 7m12s 并登记帧 |
| `fix_residue_apply.py` | 收尾: 修复 9 条残留中的 7 条(改文本 + 抽对应秒的帧), 剩 2 条为纯垃圾条目不处理。 |
| `fix_shared_frames.py` | 修复"共用配图"问题: 给出错条目补抽它自己那句话的画面的帧。 |
| `fix_shared_frames2.py` | 修复"共用配图": 为出错条目补抽它自己那句话的帧。 |
| `fix_shared_frames3.py` | 共用配图修复(定稿版): 给出错条目补抽它自己那句话的帧。 |
| `fix_shared_residue.py` | 对 9 条未解决目标做密集扫描: 0.25s 步长 × ±8s, 双阈值, 两种裁剪(字幕带 / 整下半屏)。 |
| `fix_timestamps.py` | 修正"时间戳超出视频长度"的条目: 按视频实测定位改到真实秒, 并重命名配图帧。 |

### `apply_` —— 修复落地（8 个）

| 文件 | 说明 |
|---|---|
| `apply_context_fixes.py` | 按密集序列修复前后句（每条真句独立入库） |
| `apply_ext_dialogue.py` | 把带外扫出的 6 条台词入库: 2 条替换掉库中的碎片文本, 3 条新增(含抽帧)。 |
| `apply_fill_p01.py` | P01 试点回填 |
| `apply_fill_p01_fix.py` | 删除库 P01 15m24s(好痛)错误条目及其 frames_map 键 |
| `apply_new_lines.py` | 把确认的新台词候选并入字幕库: 顺序读帧抽取配图 -> 追加条目 -> 重建映射与数据库。 |
| `apply_user_fixes.py` | 应用人工复核修正（review/user_fixes.json）到 subtitle_clean/ |
| `apply_user_verdicts.py` | 应用用户核对页标记 |
| `apply_vision_verdicts.py` | 批量应用视觉核定结果 |

### `rollback_` —— 回退（2 个）

| 文件 | 说明 |
|---|---|
| `rollback_ocr_p03.py` | 回滚全库复核误改（P03 水印污染） |
| `rollback_risky_applied.py` | 回滚「完全不同台词」类应用（前后句保护） |

### `residue_` —— 残留分析（6 个）

| 文件 | 说明 |
|---|---|
| `residue_coverage.py` | 廉价判定(不做 OCR): ±120s 窗口内逐帧检测字幕区间, 检查是否都被库中其他条目覆盖。 |
| `residue_dense.py` | 对 5 条"自己那一秒没有字幕"的目标做亚秒级密扫(0.25s × ±1s), 找它们真正的画面。 |
| `residue_own_ocr.py` | 对 9 条未解决目标"自己那一秒"的画面做 OCR, 判断该改文本还是改图。 |
| `residue_widen.py` | 对最后 2 条残留做分档扩窗 + 密集扫描。 |
| `residue_window.py` | 最后 2 条的扩窗密扫(省算力版): 先在 ±120s 窗口内逐帧检测字幕区间, 再只对区间内密采 OCR。 |
| `residue_window2.py` | 最后 2 条的扩窗扫描(定稿): ±120s 内逐帧detect字幕区间 -> 每区间只 OCR 峰值帧。 |

### `probe_` —— 探针（测量用）（6 个）

| 文件 | 说明 |
|---|---|
| `probe_aizen.py` | 诊断爱染诚命中率 |
| `probe_aizen_v2.py` | 提升爱染诚命中率的对照实验 |
| `probe_aizen_v3.py` | 命中率提升实验（P03 精测） |
| `probe_alignment.py` | 对"无文本"删除项做时间对齐探查 |
| `probe_band_measure.py` | 测量指定帧的文字行位置与"字幕带内白像素比", 判断为何字幕带没触发。 |
| `probe_frames.py` | 连续读帧, 输出指定帧区间每 5 帧的字幕带, 供人工核对序列 |

### `make_` —— 产物生成（5 个）

| 文件 | 说明 |
|---|---|
| `make_contact_sheet.py` | 把 cont_cands.json 的候选帧拼成拼图(每图 2 行三列多块), 供人工快速验证 |
| `make_context_review.py` | 12 条前后句核验页 |
| `make_review_html.py` | 生成 OCR 复核可视化核对页 |
| `make_review_pack.py` | 生成人工复核包（按集分类，供人眼快速扫视） |
| `make_sheets_fill.py` | 把 cont_fill_{ep}.json 的新帧图拼成联系表(3列x4行), 供人工抽查 |

### `compare_` —— 对比（4 个）

| 文件 | 说明 |
|---|---|
| `compare_deep.py` | 下探验证: 0.17s 扫描 vs 0.35s 密集扫描 vs 库 |
| `compare_dense.py` | 灵敏度检验对比: 密集扫描 vs 基线扫描 vs 库 |
| `compare_ocr.py` | 字幕识别预处理对比实验 |
| `compare_sub_pos.py` | 对比"库中已有的台词"与"漏掉的台词"在画面中的纵向位置。 |

### `dump_` —— 导出（3 个）

| 文件 | 说明 |
|---|---|
| `dump_p03_7m12s.py` | 导出 P03 7m12s 前后画面帧供人工核定 |
| `dump_p03_context.py` | 导出 P03 7m00-7m30 字幕条目供修订 |
| `dump_vl_raw.py` | VL 原始输出诊断 |

### `clean*` —— 清洗（3 个）

| 文件 | 说明 |
|---|---|
| `clean_dup_entries.py` | 清理全库"同集+同时间戳+同文本"的完全重复条目 |
| `clean_map.py` | 以库为基准重建 frames_map.js |
| `clean_subtitles.py` | 清洗字幕库：过滤日文假名、无中文、过短无意义记录、繁体字（职员表） |

### `locate*` —— 定位帧（4 个）

| 文件 | 说明 |
|---|---|
| `locate_all.py` | 单次顺序读全片, 批量定位参考图的真实时间, 结果写 JSON。 |
| `locate_cand_true.py` | 顺序读帧定位候选真身: P06 170s~215s 每 0.25s OCR, 找出「考虑下时间地点场合啊」的真实位置。 |
| `locate_frame.py` | 顺序读全片, 定位参考图(已存的 960x540 jpg)在视频中的真实出现时间。 |
| `locate_multi.py` | 单次顺序读全片, 同时定位多张参考图在视频中的真实时间(用于刻画时间戳偏移)。 |

### `grab_` —— 补抽帧（3 个）

| 文件 | 说明 |
|---|---|
| `grab_miss2.py` | 抓取 18 条"高度疑似真漏"位置附近的画面并 OCR, 判定是否为真字幕。 |
| `grab_missing_lines.py` | 抓取 3 条疑似漏句的画面 + OCR 复核。 |
| `grab_residue_frames.py` | 把 9 条未解决目标"自己那一秒"的画面抓到 review/probe/ 供目视(seek + 读帧, 内容不验证)。 |

### `_` —— 临时/一次性（8 个）

| 文件 | 说明 |
|---|---|
| `_cdp_measure.py` | 用 Chrome DevTools Protocol 精确测量页面几何(只用标准库) |
| `_compare.py` | 把两个版本的渲染图拼成一张并排对比图(左=当前主线, 右=分支新版) |
| `_contrast.py` | 前端评审: 按 WCAG 2.1 相对亮度公式算正文/次级文本对比度 |
| `_contrast2.py` | 从真实渲染截图里取背景像素, 实算改动后的对比度 |
| `_crop.py` | 裁出截图的一块区域做原尺寸查看(读图工具会缩大图, 所以先裁小) |
| `_nv_dll_fix.py` | nvidia DLL 修复: 绕过 pip, 手动下载 nvidia-*-cu12 wheel 并解压 DLL |
| `_review_probe.py` | 前端评审用: 直接读库核对页面统计口径 |
| `_unzip_whl.py` | 通用: 下载指定 wheel(名称/版本/平台筛选)并解压到目标目录 |

### 其它（67 个）

| 文件 | 说明 |
|---|---|
| `FaceRec.py` |  |
| `add_window_lines.py` | 补入窗口扫描发现的 3 条漏句(已目视 + 全库检索确认)。 |
| `answer_two_entries.py` | 回答"那 2 条到底找没找到": |
| `auto_resume.py` | 自动续跑 main.py：进程被外部回收/异常退出时自动重启，直到 25 集全部完成。 |
| `band_clip.py` | 统计已存帧中"字幕文字行"的纵向位置, 量化当前字幕带 (895~985) 的裁切情况。 |
| `band_position.py` | 测量指定帧中"近白文字像素"的纵向分布, 判断字幕是否落在 SUBTITLE_AREA 之外。 |
| `calibrate_ts.py` | 阶段3：字幕时间戳校准分析（先分析后应用） |
| `classify_ext_cands.py` | 把"仅LOW 区间"OCR 出的候选分类: 版权声明卡 / 片尾歌词 / 噪声 / 疑似台词。 |
| `cluster_faces.py` | 人脸候选自动聚类辅助脚本（复刻辅助） |
| `cont_fill_all.py` | 通用回填: 从 cont_gap.json 提取候选全帧 + 更新库与 frames_map |
| `cont_gap.py` | 库覆盖率差距分析(用 cont_*.json 的 seqs 全量文本) |
| `cont_summary.py` | 汇总 scan_cont 产出的全部候选 |
| `converge_check.py` | 收敛检验: 用扩充后的库重新判定全部扫描候选, 看还剩多少"库中没有的台词"。 |
| `cross_check.py` | 交叉验证 0.17s 与 0.35s 扫描的一致性 |
| `del_noise_entries.py` | 删除 2 条噪声条目(P22 17m53s「口」/ P24 18m11s「敬告」)。 |
| `dup_ref_orphan.py` | 交叉检查: 被两个 key 共用的帧(119 处) 附近是否有孤儿帧可作为其中一个条目的正确配图。 |
| `ext_regions_summary.py` | 输出三区域检测汇总表。 |
| `face_stats_all.py` | 全量统计 docs/frames 帧的主演命中分布（方案C验收） |
| `fill_conflicts.py` | 补录 cont_fill_all 因秒冲突跳过的候选 |
| `fill_dense.py` | 回填密集扫描发现的短句(短句漏句补全) |
| `fill_final.py` | 收尾剩余真候选 |
| `final_context_fix.py` | 同集判定 + P19窗口核对与修复 |
| `final_reconcile.py` | 复核修正最终裁定 |
| `final_residue.py` | 最终残留分析: 从 415 条"疑似漏句"里排除片尾段与跨集重复(歌词碎片), 看正片还剩多少。 |
| `gap_classify.py` | 分类剩余未覆盖项: drop噪声 / 过滤噪声 / 真候选未回填 |
| `gap_view.py` | 查看某集未覆盖清单(自动分歌词/中文), 带候选帧路径输出 |
| `gen_aizen_tags.py` | 标注「画面含爱染诚」的帧 |
| `gen_anchor_aug.py` | 从全 25 集 2s 剖面提取增强锚点 |
| `gen_anchor_aug2.py` | 从已选帧提取增强锚点（快版） |
| `generate_features.py` |  |
| `hybrid_recheck.py` | Hybrid 复核器：v5 server 全量结果 → VL 复核可疑条目 |
| `inspect_dense_cands.py` | 查看密集扫描的候选, 判断哪些是真漏句、哪些是匹配判据造成的误报。 |
| `leak_analysis.py` | 量化剩余漏句风险: 库中短条目、采样密度、单字台词 |
| `list_corner_entries.py` | 列出 P18「情熱行星」对谈段与 P11「图鉴」对谈段的库条目, 标出疑似碎片。 |
| `list_ep_cands.py` | 列出某集策展后的候选, 便于人工核对(默认 P25)。 |
| `low_text_frames.py` | 找出"主文字行带伸出字幕带下缘"的已存帧 —— 这些帧的库文本很可能是被裁切后的碎片。 |
| `map_dup_ref.py` | 检查 frames_map 中多个 key 指向同一帧的情况(可能与孤儿帧互为因果)。 |
| `mapped_tail.py` | 列出指定集指定时间之后的所有库条目及其【已映射配图】, 供批量视频定位验真。 |
| `merge_vl.py` | 将 vl_out/（VL 增量复核输出，基于快照）合并回 subtitle_clean/ |
| `orphans_now.py` | 列出当前孤儿帧(未被 frames_map 引用的文件), 与之前的 102 张对比, 找出新增的。 |
| `overlen_list.py` | 列出时间戳越界的条目及其配图帧名(供视频定位)。 |
| `paddle_rerun.py` | 用 PaddleOCR 官方 PP-OCRv5 server 重跑字幕 OCR |
| `query_entries.py` | 查询指定集指定区间的库条目及其 map 配图, 用于核对'条目配图是否正确'。 |
| `reconcile_context.py` | 20条回滚的二次判定 + P19达令补回 |
| `remove_fallback_frames.py` | 撤销兜底帧（宁缺毋滥） |
| `reocr_probe.py` | 小样本实测: 用"扩大裁剪区"(y 850~1062)重 OCR 已存帧, 与库中现有文本对比, 判断重 OCR 的收益。 |
| `reocr_short.py` | 定向重 OCR: 对库中"文本很短(疑似被裁切的碎片)"的条目, 用加高裁剪区 y 850~1075 重读。 |
| `repair_missing.py` | 修复"库里有条目但配图缺失"的情况: 用同集时间上最近的条目配图补上(优先取靠后的)。 |
| `repro_scan_read.py` | 复现 scan_cont.py 的读取方式(字幕带裁剪 + >245 二值化 + OCR), 看漏句为何没被读到。 |
| `restore_misaligned.py` | 恢复 4 条被时间错位"误删"的真实台词 |
| `retime_dp.py` | 按定位结果用 DP 做最优时间戳分配(最小化总位移), 用于精修。 |
| `retime_from_locate.py` | 按视频定位结果重排某集的时间戳。 |
| `review_buckets.py` | 把未人工复核的两个桶(短文本 198 / 噪声 936)逐条到视频复核, 看是否藏有真台词。 |
| `revise_qc.py` | 复核修正 QC v2：仅回滚「真坏」修正 |
| `run_extract.py` | 稳健抽帧驱动（复刻辅助） v2 |
| `sample_face_check.py` | 抽样检测当前 docs/frames 帧的人脸命中情况（回答"是否人脸最优帧"） |
| `search_lib_frag.py` | 在库中检索候选文本的关键片段, 判断是"真缺"还是"同句变体"。 |
| `shared_frames.py` | 梳理"多条条目共用同一张配图"的情况: 数量、间隔、文本是否相同、错在哪一条。 |
| `shared_frames_cause.py` | 确认成因: 出错的那条条目, 它"自己名字的帧"是否存在? |
| `shared_frames_ocr.py` | 对 119 组共用配图做 OCR 实测: 这张图到底是哪一条的画面? |
| `spotcheck_cands.py` | 抽查"位置附近有条目、但文本全库不存在"的候选: 画面里到底有没有这句台词? |
| `spotcheck_dense3.py` | 抽查"疑似漏句台词": 画面 OCR + 库中同时段条目 + 全库是否真无此句。 |
| `stat_candidates.py` | 一次性统计脚本：各集提升候选分布（互含残句/近重复/超短） |
| `summarize_dense_new.py` | 汇总密集扫描新发现, 过滤噪声, 输出真漏句清单 |
| `tail_dump.py` | 转储每集片尾段(≥21m)库条目, 检查 ED 期间叠加的正片台词是否入册。 |
| `trace_one_cand.py` | 查清一条候选的真身: 在记录位置 ±3s 内每 0.1s OCR, 看该文本到底出现在哪里。 |
| `vl_recheck_new.py` | 阶段2：对确定性规则无法判定的候选（V1近重复/V2互含/V3孤立短句） |
