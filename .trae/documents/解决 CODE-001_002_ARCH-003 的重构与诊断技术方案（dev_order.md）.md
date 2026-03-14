# 解决 CODE-001/002/ARCH-003 的重构与诊断技术方案

## 背景与目标
- 背景：当前同步循环与异步 Worker 在术语匹配、提示词构造、API 调用与 JSON 修复、写入逻辑上存在重复；CLI 主流程 `main()` 体积膨胀；异步模式发生不可恢复异常后缺少统一的 API 诊断。
- 目标：
  - CODE-001：抽象统一的翻译核心，供同步/异步/WebUI 共同调用，行为一致。
  - CODE-002：瘦身 `main()`，提取配置获取与同步循环函数，提升可维护性。
  - ARCH-003：为异步模式添加非阻塞 API 诊断与全局错误记录，便于定位故障与自动恢复。

## 适配边界与约束
- 语言与环境：Python，默认使用 `.venv`；依赖管理通过 `uv`。
- LLM 调用：默认 `BASE_URL=https://api.moonshot.cn/v1`、`MODEL=kimi-k2-turbo-preview`，建议参数 `max_tokens=2048`、`temperature=0.7`、`top_p=0.95`；确保密钥安全存储在 `data/.env`。
- 输出策略：保留结构化与非结构化两种写入路径，兼容 `write_to_markdown` 与 `write_to_markdown_through_json`。

## 设计总览
- 新核心：`TranslationCore` 抽象统一“段落翻译一步”的业务流程，屏蔽同步/异步调用差异。
- 同步循环/异步 Worker 对齐：同步 for-loop 与异步 `worker()` 均改为委托 `TranslationCore`，写入由调用方选择策略（平铺或经 JSON 保序）。
- CLI 解耦：`main()` 提取为 `get_user_config()` 与 `run_sync_translation_loop()`，并对现有 `run_translation_loop` 进行轻度重构以调用核心。
- 异步诊断：在并发任务失败到达上限时触发非阻塞 API 自检与全局错误状态记录。

## 核心组件设计
- 新增文件：`modules/translation_core.py`
- 接口定义：
  - `class TranslationCore`
    - 依赖注入：`LLMService`、`WritePolicy`、`RepairPolicy`、`TerminologyPolicy`。
    - 方法：
      - `execute_translation_step(segment, terms_dict, aggregated_new_terms, tracker_state=None) -> TranslationResult`
        - 输入：`segment`（含原文、结构位置信息）、`terms_dict`、`aggregated_new_terms` 引用、可选 `tracker_state`（并发有序写入需要）。
        - 处理：术语匹配 → Prompt 构造 → 结构化 API 调用 → JSON 修复（按策略）→ 术语一致性复写 → notes/译文拼接。
        - 输出：`TranslationResult(content, notes, tokens, new_terms_delta, header_path)`；不直接写盘。
  - 数据结构：
    - `class TranslationResult`
      - 字段：`content: str`, `notes: str`, `tokens: int`, `new_terms_delta: dict`, `header_path: list[str]`
    - `enum WritePolicy`：`PLAIN_MD`, `ORDERED_JSON`
    - `enum RepairPolicy`：`RETRY_MAX_5`, `RETRY_MAX_3`, `NONE`
    - `enum TerminologyPolicy`：`MERGE_ON_CONFLICT`, `KEEP_ORIGINAL`
- 关键调用点对齐：
  - CLI 同步：在 for-loop 调用 `TranslationCore.execute_translation_step(...)`，随后由 `WritePolicy` 决定使用 `modules/write_out_tool.py:80` 或 `modules/write_out_tool.py:6` 写盘。
  - CLI 并发：在 `main.py:127` 的 `run_translation_loop` 内 `worker()` 将现有 `process_segment_task` 精简为调用核心并写盘；保留 `asyncio.Lock` 仅用于写盘序列化。
  - WebUI：`app.py:140` 的 `process_files` 改为逐段委托核心；`process_files_with_progress` 维持外层进度包装。

## 代码改动点
- 新增：`modules/translation_core.py`
- 修改：
  - `main.py:15` 的 `process_segment_task`：改为薄封装，核心处理迁移到 `TranslationCore`。
  - `main.py:127` 的 `run_translation_loop`：`worker()` 内统一调用核心；写盘路径通过策略选择。
  - `main.py:174` 的 `main()`：提取为 `get_user_config()` 与 `run_sync_translation_loop()`；`main()` 仅负责总调度与异常保护。
  - `app.py:140` `process_files` 与 `app.py:467` `process_files_with_progress`：改为调用 `TranslationCore`。
  - `modules/api_tool.py:231` `LLMService`：确保提供 `create_prompt`、`call_ai_model_api`、`repair_json`、`rewrite_with_glossary`；复用现有 API，必要时增加轻量异步适配（通过 `asyncio.to_thread`）。

## 异步模式诊断（ARCH-003）
- 触发点：在 `run_translation_loop.worker()` 内，当段级重试超限或捕获不可恢复异常时。
- 动作：
  - 非阻塞执行：`asyncio.create_task(safe_api_diagnostics(llm_service))`
  - `safe_api_diagnostics`：调用 `modules/api_tool.py:300` `LLMService.test_api()`；将结果写入日志文件（如 `uploads/diagnostics_YYYYMMDD_HHMMSS.json`）并在进程内设置全局错误标志（`services/diagnostics.py` 提供 `set_global_error_state()`）。
  - 反馈：CLI 打印简短提示；WebUI 端点 `/test-api` 复用同一实现以便前端展示。
- 降级与恢复：在全局错误标志为真时，后续任务减少并发度或进入暂停等待人工干预（保留现有交互式故障恢复窗口）。

## CLI 主流程瘦身（CODE-002）
- 新增：`def get_user_config() -> UserConfig`（处理 `.env`、偏好载入、交互、文件转换确认）。
- 新增：`def run_sync_translation_loop(config, llm_service, terms_dict) -> None`（仅负责：切分、逐段调用核心、写盘、统计与收尾）。
- `main()`：仅进行总调度、异常保护与是否并发的分支选择；偏好保存与术语合并的收尾逻辑提取到独立函数 `finalize_terms_merge(...)`。

## WebUI 对齐（CODE-001）
- `app.py:140` `process_files` 使用 `TranslationCore`，使 CLI 与 WebUI 段级行为一致（术语复写、JSON 修复次数、notes 拼接）。
- 保留现有线程转移模型；如后续引入段级并发，直接复用核心，不改变路由层接口。

## 测试方案与验收标准
- 单元测试（pytest）：
  - 新增：`tests/test_translation_core.py`
    - 覆盖：术语匹配一致性、Prompt 构造、API 返回解析与 JSON 修复策略、术语复写行为、结果对象字段完整性。
  - 现有并发测试：`tests/test_concurrency_flow.py` 对齐核心调用，确保“调用次数/写入次数/新术语聚合/tokens”统计不回退。
  - WebUI 行为一致性：对比 CLI 同步与 WebUI 在同一输入上生成的 Markdown 结构一致（标题保序、notes 拼接一致）。
- 运行：`python -m pytest`
- 验收标准：
  - 同步/异步/WebUI 在同一参数下，`TranslationCore` 输出一致；
  - CLI `main()` 的圈复杂度显著降低；
  - 异步模式在故障时产生诊断日志，并能通过全局状态标志触发降级或暂停；
  - 不引入接口不兼容或明显性能回退（并发下写盘仍保序）。

## 验证与交付
- 本地验证：
  - CLI：`uv run main.py`；并分别运行非并发与并发模式，检查输出与统计表。
  - WebUI：`uv run app.py` 后浏览器访问 `http://localhost:8008/`，通过 `/test-api` 与翻译任务观察一致性与诊断行为。
- 交付物：
  - 新文件：`modules/translation_core.py`、`services/diagnostics.py`、`tests/test_translation_core.py`
  - 调整文件：`main.py`、`app.py`、必要的 `modules/api_tool.py` 轻度适配
  - 文档：`.data/document/dev_order.md`（即本文档）

## 风险与缓解
- 行为差异风险：同步循环与异步 `process_segment_task` 在术语一致性复写上存在细微差异；统一为核心逻辑后，提供开关 `TerminologyPolicy`，默认采用 `MERGE_ON_CONFLICT`，并在 README 标注变更。
- 性能风险：核心抽象引入轻微的函数层次；通过 `asyncio.to_thread` 复用现有同步 API 封装，不强制改写为原生异步以降低重构成本。
- 回滚策略：保留旧流程分支与配置开关一版迭代期可启用；出现不可接受问题时快速回切旧实现。

## 参考代码位置（用于实施）
- CLI：`main.py:174`（`main()`）、`main.py:127`（`run_translation_loop`）、`main.py:15`（`process_segment_task`）
- WebUI：`app.py:140`（`process_files`）、`app.py:467`（`process_files_with_progress`）、`app.py:450`（`run_translation_task`）、`app.py:479`（`/translation-progress`）
- 核心模块：`modules/api_tool.py:231`（`LLMService`）、`modules/api_tool.py:300`（`test_api`）、`modules/write_out_tool.py:6`（`write_to_markdown_through_json`）、`modules/write_out_tool.py:80`（`write_to_markdown`）、`modules/read_tool.py:8`（`read_structured_paragraphs`）、`modules/read_tool.py:197`（`read_and_process_structured_paragraphs_to_json`）、`modules/csv_process_tool.py:116`（`find_matching_terms`）

---

如确认方案，我将创建 `.data/document/dev_order.md` 并按以上内容落盘，同时开始按清单逐步实施与配套测试。