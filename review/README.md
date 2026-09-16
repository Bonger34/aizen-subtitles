# review/ —— 复核工作目录

这个目录有两重身份，动它之前先分清：

1. **校验链的工作目录** —— `duration_check.py` 往这里写 `duration_check.txt`，
   `stat_coverage.py` 写 `coverage_final.json`，`q_rescan.py` / `q_timeline.py` /
   `q_align_tl.py` 在这里读写中间结果。
2. **判定源文件的存放处** —— 下面这 8 个 JSON 是那 195 条修正的可复现依据，**不要删**。

## 已入库 · 8 个判定源文件

| 文件 | 谁在读 |
|---|---|
| `q_manual_verdicts.json` | `q_audit.py`（校验链第 8 步）等 9 个脚本 |
| `q_apply_result.json` | `q_audit.py`（校验链第 8 步）等 4 个脚本 |
| `q_revert_result.json` | `q_audit.py`（校验链第 8 步）等 3 个脚本 |
| `q_reframe_tg.json` | `q_reframe.py`（帧图重抽的默认 `--src`） |
| `q_locate2_verdicts.json` | `q_locate2_apply.py` |
| `q_apply2_result.json` | `q_apply2.py`、`q_review9_apply.py` |
| `q_suspect_class.json` | `q_sheet8.py` |
| `q_targets.json` | `q_diag3.py`、`q_fillalign.py`、`q_locate2.py` 等 7 个脚本 |

前四个一旦删掉，校验链的收尾两步会直接报错 —— `q_audit.py` 读不到输入，
`q_reframe.py` 找不到待重抽清单。用 `scripts/pipeline/q_audit.py` 自检：

```
修正 195 · 落盘 193 · 回退 2 · 异常 0
```

## 已入库 · 11 篇报告

| 报告 | 内容 |
|---|---|
| `文本质量提升报告.md` | 总纲，含各轮的最终状态与目录 |
| `漏句复查报告.md` · `漏句收敛报告.md` · `漏句第四轮与范围说明.md` · `残留2条与漏句发现.md` | 漏句检测与收敛过程 |
| `带外字幕重扫报告.md` · `带外垃圾条目清单.md` | 剔除带外内容（版权卡 / OP·ED / 预告等） |
| `时间戳修复报告.md` | 时间戳漂移的定位与修正 |
| `共用配图修复报告.md` | 多条台词共用同一张帧图的纠正 |
| `孤儿帧102问答.md` | 无条目引用的帧图定性 |
| `全系列密集扫描报告.md` | 高采样率密扫的结论 |

## 未入库

`.gitignore` 在这里只放行 `*.md` 和上表那 8 个 JSON，其余全是本地产物：

- `*.png` 截图与对照图（`live_*.png`、`compare_*.png`、`master_*.png` …）；
- `*.txt` / 中间 `*.json`（`band_position.txt`、`orphan_*.txt`、`q_sheet*_apply.json` …）。

它们是跑校验时**重新生成**的，不是证据本身 —— 换台机器 clone 后不存在属正常。
报告里出现的老路径按需重跑对应脚本即可。

> 10507 个中间文件 / 1150 MB 已在 2026-09 打包移出仓库，
> 见上一级的 `_VV_Rob_review_archive_2026-08-21.zip`。
