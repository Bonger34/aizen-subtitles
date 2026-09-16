# review/ —— 复核工作目录

这个目录有两重身份，动它之前先分清：

1. **校验链的工作目录** —— `duration_check.py` 往这里写 `duration_check.txt`，
   `stat_coverage.py` 写 `coverage_final.json`，`q_rescan.py` / `q_timeline.py` /
   `q_align_tl.py` / `q_reframe.py` 在这里读写中间结果。
2. **判定源文件的存放处** —— 下面这 8 个 JSON 是那 195 条修正的可复现依据，**不要删**。

## 两份报告

| 报告 | 内容 |
|---|---|
| `复核总报告.md` | **唯一入口**。合并了原先 10 篇分轮报告（漏句 / 带外 / 时间戳 / 配图 / 孤儿帧 / 帧图 / 文本质量）。最终状态、各专项实测数据、证据清单都在里面 |
| `带外垃圾条目清单.md` | **待人工决定**的 3 条: 画面不是台词、库里却存了文本。不是报告，是待办 |

分轮原文见 git 历史（`5fa4e02` 及更早）：`git show 5fa4e02:review/文本质量提升报告.md`。

## 已入库 · 8 个判定源文件

「谁在读」一列是**当前仓库里实际读它**的脚本；空表示读者已随一次性脚本删除，这些文件现在
只是**证据留档**。

| 文件 | 谁在读（当前） | 大小 |
|---|---|---:|
| `q_manual_verdicts.json` | `q_audit.py`（校验链第 8 步） | 23 KB |
| `q_apply_result.json` | `q_audit.py` | 14 KB |
| `q_revert_result.json` | `q_audit.py` | 567 B |
| `q_reframe_tg.json` | `q_reframe.py`（帧图重抽的默认 `--src`） | 220 KB |
| `q_locate2_verdicts.json` | —（读者 `q_locate2_apply.py` 已删） | 8.5 KB |
| `q_apply2_result.json` | —（读者 `q_apply2.py` / `q_review9_apply.py` 已删） | 31 KB |
| `q_suspect_class.json` | —（读者 `q_sheet8.py` 已删） | 23 KB |
| `q_targets.json` | —（读者 `q_diag3.py` / `q_fillalign.py` / `q_locate2.py` 已删） | 65 KB |

**前四个一旦删掉，校验链的收尾两步会直接报错** —— `q_audit.py` 读不到输入，
`q_reframe.py` 找不到待重抽清单。用 `scripts/pipeline/q_audit.py` 自检：

```
修正总数 195 | 已落盘 193 | 已回退 2 | 异常 0
```

> ⚠️ 这个 195 **只覆盖到第 4 轮**。后两批字幕带对照表另有 39 条修正确已落盘，
> 但它们的应用记录 `q_review9_apply.json` / `q_sheet10_apply.json` / `q_sheet11_apply.json`
> **从未提交 git、也不在归档 zip 里，已永久丢失**。详见 `复核总报告.md` 第 6 节。

## 未入库

`.gitignore` 在这里只放行 `*.md` 和上表那 8 个 JSON，其余全是本地产物：

- `*.png` 截图与对照图（`live_*.png`、`compare_*.png`、`master_*.png` …）；
- `*.txt` / 中间 `*.json`（`band_position.txt`、`orphan_*.txt`、`q_sheet*_apply.json`、
  `q_fixes_final.json`、`coverage_final.json` …）。

它们是跑校验时**重新生成**的，不是证据本身 —— 换台机器 clone 后不存在属正常。
报告里出现的老路径按需重跑对应脚本即可。

> 10507 个中间文件 / 1150 MB 已在 2026-09 打包移出仓库，
> 见上一级的 `_VV_Rob_review_archive_2026-08-21.zip`（1106.9 MB）。
> **这份归档里没有那 3 个 `*_apply.json`** —— 不要再去找。
