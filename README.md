# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **精准的术语控制，专业的文档翻译。**

AIwork4translator 是一个面向专业文档的 AI 翻译工具，适合技术文档、长篇叙事、小说与规则书。它通过**词表驱动 + Aho-Corasick 自动机 + 正则匹配**在翻译过程中识别并保护专有名词，保证术语一致性；原生支持 Markdown，并通过 MarkItDown 接入 PDF/Word/Excel/HTML 等格式；提供 CLI 与 WebUI 两种交互方式；可导出 DOCX/PDF/EPUB/XLSX。

[English](./README_en.md) | [更新日志](./CHANGELOG.md)

---

## 最新更新（2026/06/14）

- **段落级重试与失败清单**：单段失败按 `PARAGRAPH_MAX_RETRIES`（未设置时回退 `MAX_RETRIES`）重新入队；超限后写入 `failed_segments`，最终 Markdown 顶部输出 `> [!WARNING]` 摘要，`_intermediate.json` 回写 `translation_status=partial` 与完成段计数；
- **坏 JSON 多层恢复**：解析链路改为「标准解析 → 去代码围栏 → 平衡 JSON 抽取 → JSON 修复 → 保守字段恢复」，优先保住译文正文；
- **定向 fallback**：按内容风险（表格 / HTML / 代码围栏 / 容器块 / 嵌套列表）与 Provider 失败特征切换更保守的 Prompt；
- **稳健分段**：表格、代码围栏、HTML 块、`:::` 容器与图片按受保护块整体成块，超长时按结构拆分并重复包裹行；
- **轻量评测器**：`evaluate.py` 支持两组配置对比、`--safe-degrade off|auto|on`、`--bootstrap-from-seed` 显式建立最小基线集，报告含质量代理、结构保持、术语一致性、重复相似度与 `prefix_hash` 复用指标；
- **WebUI 修复**：修复 WebUI 翻译链路缺少 `import json` 导致的 `NameError`，失败段现在也会写入 WARNING 摘要；
- **术语评测（issue #44）**：3 份自造文档 × A/B/C 三组的可复现评测已落地，术语命中率 68.5% → 99.6%，详见下文「术语一致性评测」与 [eval/](./eval/)。

2026/03/14 的蓝图 + 增量日志、异步 Provider 与多格式导出见 [CHANGELOG.md](./CHANGELOG.md)。

## 核心特性

- **🎯 专有名词保护**：基于 AC 自动机的术语匹配，支持复数归一化与冠词智能处理；
- **📚 动态术语管理**：翻译过程中实时采集新术语，支持交互式合并与独立导出；
- **⚡ 高并发架构**：Queue + Worker Pool，大文件翻译性能相比串行约 6 倍；
- **🛡️ 健壮异常恢复**：JSON 自动修复、断点续传、Ctrl+C 安全中断、交互式故障恢复；
- **🖥️ 双模交互**：CLI（偏好记忆、极简操作）+ WebUI（双栏实时预览、所见即所得）；
- **📄 多格式输入**：原生 Markdown，集成 [MarkItDown](https://github.com/microsoft/markitdown) 支持 PDF/Word/Excel/HTML 等；
- **📦 多格式导出**：翻译完成后基于 `_intermediate.json` 一键导出 DOCX/PDF/EPUB/XLSX；
- **🔌 多 Provider**：Kimi / OpenAI / DeepSeek / SiliconFlow / Gemini / Doubao（当前实现）。

## 术语一致性评测（可复现）

在 3 份自造文档（技术文档 / 规则书 / 小说；每份约 1,200 条词表、约 2,150 词正文）上对比三种方式：不注入词表、向量 RAG（`bge-m3` top-8，按段检索后注入）、本项目（按段 Aho-Corasick 命中注入）。每份文档每组运行 2 次，18 次运行无 API 错误。

| 方式 | 术语命中率 | 出现级命中率 | 额外输入 token |
|---|---|---|---|
| 不注入词表 | 68.5% | 43.9% | 0 |
| 向量 RAG top-8 | 79.7% | 54.1% | +4,257（prompt +1,258 / 检索 +3,000） |
| **本项目** | **99.6%** | **95.3%** | **+1,410** |

- 术语命中率相对无词表基线 **+31.1 个百分点（相对 +45%）**，比向量 RAG 高 **19.9 个百分点**；
- 额外 token 约为 RAG 基线的 **33%**（节省 67%），且不产生检索调用；术语密度越低节省越明显——零命中时本项目无额外开销，RAG 仍有每段检索成本；
- 评测集、脚本与原始结果全部在 [eval/](./eval/)，可一键复现；成本曲线见 [eval/results/cost_curve.png](./eval/results/cost_curve.png)。

> 口径：术语命中为子串判定；文档为合成数据、单模型（DeepSeek-V3 via SiliconFlow）；方法与局限见 [eval/README.md](./eval/README.md)。

## 快速开始

### 1. 环境准备

本项目使用 `uv` 管理依赖与环境：

```bash
uv sync --frozen   # 按 uv.lock 安装依赖（自动创建 .venv）
```

Windows 可执行 `.venv\Scripts\activate` 激活虚拟环境；也可以直接用 `uv run` 运行。

### 2. 配置 API

```bash
cp data/.env.example data/.env
```

在 `data/.env` 中至少填写所选 Provider 的 Key。`SYSTEM_PROMPT` / `BASE_PROMPT` 保持示例内容即可（翻译流程与 JSON 输出契约依赖它们）：

```ini
KIMI_API_KEY=sk-xxxxxxxxxxxxxxxx
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=kimi-k2-turbo-preview
```

默认 Provider 为 `kimi`。

### 3. 运行

```bash
uv run main.py    # CLI
uv run app.py     # WebUI：浏览器打开 http://localhost:8008
```

### 4. 测试

```bash
uv run python -m pytest -q
```

当前基线：**94 passed, 5 skipped**（未配置对应 Provider Key 时相关测试自动跳过）。

## 使用指南

### 命令行（CLI）

1. 运行 `uv run main.py`；
2. 选择 Provider（自动记住上次选择，回车沿用）；
3. 输入原文路径（记住上次；非 Markdown 文件会先经 MarkItDown 转换并等待确认）；
4. 处理术语表：
   - 输入 `n`：生成空白词表（含示例条目），翻译结束后可选择是否合并新术语；
   - 输入 `y`：提供 CSV/XLSX 词表路径，并选择是否将新术语合并回原表（不合并则另存新 CSV）；
5. 选择是否启用并发模式；
6. 翻译完成后保存译文与术语表，并按提示导出 DOCX/PDF/EPUB/XLSX；`counting_table.csv` 会记录输入/输出长度、token 与耗时。

中断与恢复：

- `Ctrl+C` 会保存已累积术语与未翻译原文（`_rest.md`）；
- 并发模式基于 `_translation_log.jsonl` 支持断点续传；
- 连续失败达到 `MAX_RETRIES` 时进入交互式恢复（重试或保存退出）。

### 网页界面（WebUI）

1. 运行 `uv run app.py`，打开 http://localhost:8008；
2. 上传 `.md`（或可转换格式）与可选词表；
3. 进入双栏编辑器：左侧原文、右侧译文，点击「开始翻译」后实时流式更新；
4. 支持在线编辑、Ctrl+S 手动保存、自动保存与下载译文。

主要接口：`/validate-file`、`/start-translation`、`/translation-progress`、`/save-content`、`/download`、`/open-file`。

### 术语表格式

标准 CSV（UTF-8，允许带 BOM），两列：原文、译文；原文列不能重复、不能有空行。也支持 `.xlsx`（自动转换为 CSV）。可选第三列 `reason` 记录取名理由。

| 原文 (Source) | 译文 (Target) | 理由 (可选) |
| :--- | :--- | :--- |
| Server | 服务器 | 通用术语 |
| Outlaw | 法外之徒 | 作品内专名 |

### 导出与预览

翻译完成后 CLI 可直接导出；对已有导出文件可快速预览结构（标题/目录/首页文本）：

```bash
uv run python scripts/preview_export_outputs.py "<导出文件基础路径（不带扩展名）>"
```

示例：

```bash
uv run python scripts/preview_export_outputs.py "input_files/《赤红传说》112-127"
```

## 进阶配置

### 环境变量（`data/.env`）

| 变量名 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `KIMI_API_KEY` / `KIMI_BASE_URL` / `KIMI_MODEL` | Kimi 配置 | base_url 默认 `https://api.moonshot.cn/v1`，model 默认 `kimi-k2-turbo-preview` |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `GPT_MODEL` | OpenAI 配置 | `https://api.openai.com/v1` / `gpt-realtime` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | DeepSeek 配置 | — / `deepseek-chat` |
| `SILICON_API_KEY` / `SILICON_JSON_URL` / `SILICON_JSON_MODEL` | 硅基流动配置 | — / — |
| `GEMINI_API_KEY` / `GEMINI_BASE_URL` / `GEMINI_MODEL` | Gemini 配置 | — / `gemini-2.5-flash` |
| `DOUBAO_API_KEY` / `DOUBAO_BASE_URL` / `DOUBAO_MODEL` | 豆包配置 | — / `doubao-seed-1-6-251015` |
| `SYSTEM_PROMPT` | 系统提示词（两步翻译流程 + JSON 输出契约） | 必填，见 `.env.example` |
| `BASE_PROMPT` | 用户提示补充（术语/JSON 约束） | 必填，见 `.env.example` |
| `Requests_Per_Minute` | 每分钟请求数上限（0 或负值 = 不限流） | `10` |
| `Currency_Limit` | 并发 Worker 上限（实际取 min(该值, RPM)） | `6` |
| `MAX_RETRIES` | 连续失败熔断阈值 | `3` |
| `PRESERVE_STRUCTURE` | 是否启用结构化模式 | `true` |
| `MAX_CHUNK_SIZE` | 单个分段最大长度 | `4000` |
| `STRUCTURED_OUTPUT` | 是否按结构化 JSON 解析模型输出 | `true` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 历史预留项：当前版本**未实现** Ollama 接入 | — |

### Provider 说明

实际实现的 Provider（见 `modules/api_tool.py`）：`kimi`、`gpt`、`deepseek`、`silicon`、`gemini`、`doubao`。其中 Gemini 与 Doubao 使用各家 SDK 的结构化输出，实现较新、尚未充分验证；Ollama 接入当前未实现。

### 翻译模式

- **结构化模式**：识别 H1–H6 标题并按章节切分，适合原生 Markdown（推荐）；
- **非结构化模式**：不依赖标题、按段落流式处理，适合 PDF/Word 等转换后的文档。

## 项目结构

```text
project_root/
├── data/                    # 配置（.env.example 入库；.env 不入库）
├── modules/                 # 业务模块
│   ├── api_tool.py          # LLMService：Provider 适配、prompt、结构化解析/JSON 修复、术语复写
│   ├── translation_core.py  # 统一翻译核心：术语匹配 → prompt → 重试/修复 → 一致性 → 结果封装
│   ├── read_tool.py         # 结构化分段、跨页断句合并、图片跳过
│   ├── write_out_tool.py    # 蓝图 JSON + 增量日志 → 最终 Markdown
│   ├── log_manager.py       # JSONL 增量日志（断点续传 / 预览）
│   ├── csv_process_tool.py  # AC 自动机术语匹配、CSV/XLSX 校验
│   ├── terminology_tool.py  # 词表加载 / 合并 / 保存
│   ├── export_tool.py       # DOCX/PDF/EPUB/XLSX 导出
│   ├── markitdown_tool.py   # 非 Markdown → Markdown 转换
│   ├── count_tool.py        # 段落 / 字数统计
│   └── config.py            # 全局配置（env）
├── services/diagnostics.py  # 异步 API 诊断与全局错误态
├── templates/ static/       # WebUI（FastAPI + Jinja + 原生 JS）
├── scripts/                 # 安装 / 导出预览 / 检查脚本
├── tests/                   # pytest（126 passed / 6 skipped；联网用例默认跳过）
├── eval/                    # issue #44 评测集与脚本（A/B/C、成本曲线、原始结果）
├── reviews/                 # 历史 AI 审查报告（2025-11 ~ 2025-12）
├── main.py                  # CLI 入口
├── app.py                   # WebUI 入口
├── baseline.py              # 无术语注入基线脚本（评测用；路径为示例，需按需修改）
├── pyproject.toml           # 依赖与脚本入口（uv.lock / requirements.txt 同步维护）
└── devdiary.md / CHANGELOG.md
```

## 测试

```bash
uv run python -m pytest -q    # 当前：94 passed, 5 skipped
```

- 需要各 Provider API Key 的测试在缺 Key 时自动 skip；
- 覆盖范围：翻译核心（重试 / JSON 修复 / 术语复写 / 降级）、并发流程、读取与跨页合并、增量日志写出、词表匹配、导出、CLI 偏好等；
- 暂无 CI：后续将加入 GitHub Actions 在 PR 上运行 pytest。

## 路线图

### 下一迭代（已排期）

- **评测扩展**（[issue #44](https://github.com/chaosen315/AIwork4translator/issues/44)）：A/B/C 评测与成本曲线已落地（见 [eval/](./eval/)）；下一步补充更长/更低密度文档、RAG top-k 敏感性（k=3/5/12）与人工误译评分。

### 后续

- 稳定性：异步 RPM 限流器、非 JSON 模式的未翻译部分兜底、跨页断句信号扩展、图片回填策略化、写出上下文重构、大文档分批处理；
- 工程：GitHub Actions + pytest CI；清理 tracked `__pycache__` / `egg-info` / 本地内部文档；
- 文档：对外数字已按 [eval/](./eval/) 评测结果更新。

## 已知限制

- 术语能力依赖给定的词表，**不做自动术语识别**（NER 能力已于 2025-12-27 移除）；
- 「+35% 识别率 / 节省 99% token」为早期小样本结论；现已用 [eval/](./eval/) 的可复现评测替代为具体数字（见上文「术语一致性评测」）；
- 当前未实现 Ollama 接入；
- 导出排版基于 Markdown 结构，复杂版式（表格、公式、图片位置）能力有限；PDF 中文字体依赖运行环境；
- 大文件的内存占用与限流仍需优化，WebUI 建议 ≤10MB；
- 面向本机单用户使用，不含多用户鉴权与云端部署方案。

## 联系与许可

- 问题与建议：欢迎提交 Issue；
- 邮箱：chasen0315@gmail.com；
- License：[MIT](./LICENSE)
