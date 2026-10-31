# Issue #44 术语翻译评测（A / B=向量 RAG / C）

本目录是 [issue #44](https://github.com/chaosen315/AIwork4translator/issues/44) 要求的可复现评测集与脚本：用同一批文档、同一模型、同一套基础提示词，对比「无词表」「向量 RAG 检索注入」「分段 AC 命中注入」三种方式的术语命中率、token 开销与耗时。

## 规模设定（对齐真实使用）

真实场景里词表 1k–3k 条、正文 2k–1w+ 字，**整表注入不可行**。因此本评测集按同一量级构造：

- 每份文档的词表 **≈1,200 条**（约 40 个锚点术语 + 1,160 条干扰项，干扰项不应出现在正文中）；
- 每份文档 **≈2,100 词**，锚点术语在文中出现 134–165 次；
- 评测分母只统计**锚点术语**（正文里应出现的术语）。

这使 B 组必须走「检索后注入」，而不是把整表塞进 prompt。

## 三组定义

| 组 | 名称 | 做法 |
|---|---|---|
| A | 基线 | 不注入任何词表 |
| B | 向量 RAG | 词表全部条目用 embedding 建索引（一次）；**每个分段**用 embedding 检索 top-k（默认 8）后注入 |
| C | 本项目 | Aho-Corasick 在分段内精确匹配，只注入命中术语 |

三组共用：同一 provider/model、同一 system prompt、同一 `BASE_PROMPT`、同一分段、同一结构化输出约束。

## 指标

1. **术语命中率（term 级）**：译文中出现标准译名的术语数 / 锚点术语总数。
2. **术语命中率（occurrence 级）**：Σ min(译名出现次数, 标注应出现次数) / Σ 标注应出现次数。
3. **token 开销**（两条线分开记）：
   - **prompt 输入 token**：tiktoken `cl100k_base` 对「system prompt + 首次请求 prompt」估算；
   - **embedding token**：B 组每段的查询 embedding 实际 usage；词表索引的建库 token 单独列出（生产中会摊销到大量查询上）。
   - B 的总开销 = prompt 增量 + embedding 查询 token；C 只有 prompt 增量。
4. **耗时**：每份文档每组每次运行的墙钟时间。

判定规则：中文译名按子串计数；锚点术语的复数/变体由生成器控制为单数形式。

## 目录与复现

```
eval/
├── generate_dataset.py     # 生成文档/词表/标注（确定性，seed=42）
├── documents/              # 3 份 ~2,100 词的合成文档（CC0）
├── glossaries/             # 3 份 ~1,200 条词表
├── annotations/            # 锚点术语与应出现次数
├── build_annotations.py    # 校验标注（重数并核对）
├── run_eval.py             # A/B/C 执行器（含向量 RAG）
├── summarize_conclusions.py
└── results/                # runs.jsonl / summary.json / results.md / conclusions.md
```

```bash
uv sync
uv run python eval/generate_dataset.py        # 重新生成数据（可选，仓库内已带）
uv run python eval/build_annotations.py       # 校验标注
uv run python eval/run_eval.py --provider silicon --model deepseek-ai/DeepSeek-V3 --rag-top-k 8 --repeat 2
```

需要 `data/.env` 中的 `SILICON_API_KEY`（chat 与 embedding 共用 SiliconFlow 端点）。embedding 会缓存在 `eval/results/.cache/`（已 gitignore），重跑不会重复建库；`--rebuild-embeddings` 强制重建。

Windows 提醒：若 `NO_PROXY` 含 `[::1]`，httpx 构造客户端会报 `Invalid port`，先 `$env:NO_PROXY=""`。

## 产物

- `results/runs.jsonl`：每份文档 × 每组 × 每次的明细（命中率、prompt/embedding token、耗时、错误）。
- `results/summary.json`：按文档与按组聚合，含 RAG 建库 token。
- `results/results.md`：结果表。
- `results/conclusions.md`：结论与对外表述修订建议。

## 成本曲线（token vs 术语密度）

`eval/sweep_cost.py` 用「不含对话调用」的方式扫描术语密度：对每个密度构造若干 ~180 词的分段，分别计算 A/B/C 的 prompt token（tiktoken），B 的每条查询 embedding token 由 Provider usage 给出；结果写 `results/cost_sweep.csv`。`eval/plot_cost_curve.py` 画出 `results/cost_curve.png/svg`。

- **横轴**：每段命中的术语数（Aho-Corasick 命中）；副轴是等效术语密度（每 1,000 源词出现次数）。
- **纵轴**：每段额外输入 token（相对无词表基线），把 system prompt 等固定成本消掉。
- **两条主线**：向量 RAG（top-8，prompt 注入 + 每段一次 embedding 查询）与 本项目 C（只注入命中术语）；RAG 的 prompt 部分单独用虚线表示，阴影是检索开销。

为什么选密度而不是文档长度：两组的成本都随文档长度线性增长，长度不是区分变量；真正决定 C 成本的是「每段命中多少术语」，而 RAG 的成本几乎与命中数无关（top-k 与每段检索固定）。

```bash
uv run python eval/sweep_cost.py
uv run python eval/plot_cost_curve.py
```

已知口径：嵌入建库 token（约 1.4–1.6 万/份）未计入曲线，按查询摊销；密度 >12 的采样点段长略增，RAG 线末端随之上翘。

## 已知限制

- 文档为**合成数据**：句式模板化，术语密度高于真实文档（对 C 组的 token 开销偏保守），不代表真实译文质量。
- 术语命中用子串判定，未做人工逐句误译评分。
- 单模型、2 次重复；换模型或换 `rag-top-k` 需重跑。
- embedding 与 chat 使用同一家 Provider（SiliconFlow），跨 Provider 只看相对量。
