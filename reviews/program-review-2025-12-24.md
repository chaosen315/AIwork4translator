# 项目审查报告（2025-12-24）

## 项目信息
- 项目名称：`program-translator`
- 技术栈：`Python 3.11+`、`asyncio`、`pydantic`、`OpenAI SDK`、`pandas`、`pytest`
- 依赖管理：`uv`（默认 `.venv`）、测试通过 `python -m pytest`
- 默认LLM：`Kimi`（`https://api.moonshot.cn/v1`、`kimi-k2-turbo-preview`）
- 审查依据：`devdiary.md` 2025/12/01–2025/12/18 更新、`README.md`、核心模块代码与测试

## 审查范围
- 并发与调度：`main.py:192-348`
- 翻译核心：`modules/translation_core.py:41-287`
- API 封装与结构化输出：`modules/api_tool.py:183-274`
- 段落读取与合并：`modules/read_tool.py:8-167`, `modules/read_tool.py:270-339`, `modules/read_tool.py:395-486`
- 结构化写出：`modules/write_out_tool.py:6-83`, `modules/write_out_tool.py:108-122`
- 词表与匹配：`modules/csv_process_tool.py`（按日记说明抽查）

## 评估标准
- 代码质量：可读性、模块边界、异常与降级处理、类型与数据契约一致性
- 架构设计：分层清晰、扩展性、并发正确性、数据流控制
- 性能与稳定性：并发调度、RPM限流、重试与修复成本、I/O开销
- 安全性：密钥与配置管理、日志敏感信息、外部调用防御
- 可维护性：注释与文档、测试覆盖、配置一致性、默认值与约束

## 关键发现（分级与编号）
- CRITICAL-001 并发写出与顺序保证
  - 发现：并发模式通过中间 JSON 与 `tracker_state['next_id']` 保序写出（`main.py:269-279`、`modules/write_out_tool.py:49-83`）。整体设计健壮，但在熔断恢复后“未翻译段落定位”仅在 JSON 模式有兜底（`main.py:293-347`）。
  - 建议：为非 JSON 模式增加轻量进度标记（如本地队列索引镜像），统一 rest.md 兜底行为。

- CRITICAL-002 结构化输出解析与降级策略一致性
  - 发现：移除了模型返回的 `notes` 字段，统一在解析时生成（`modules/api_tool.py:183-224`）；`TranslationCore` 提供双层降级（部分有效返回与无效 JSON 提取，`modules/translation_core.py:214-276`）。
  - 建议：在 `.env` 明确“模型不返回 notes，由客户端生成”的契约，并在集成测试覆盖空术语时 `notes==""` 的路径。

- MAJOR-003 句中跨页合并算法边界
  - 发现：跨页断句判定 `_is_sentence_midpage_break` 使用强否决+计分（`modules/read_tool.py:270-339`），能有效提升英文论文连续性；但对以大写开头的延续（如专有名或引号）可能误判为新句。
  - 建议：增加“引号开头”“括号开头”“冒号后续”等弱阳性信号，并将 `isupper()` 判定改为“首字符非断句标志且上一尾部非句末标点”。

- MAJOR-004 图片跳过与位置保持
  - 发现：合并逻辑可跳过图片并在文本块之后回填（`modules/read_tool.py:413-467`），测试覆盖完备（见 `devdiary.md` 2025/12/18）。
  - 建议：将回填策略抽象为策略枚举（如“紧随”“保持相对位置”“聚合到章节结尾”）以适配不同出版格式需求。

- MAJOR-005 RPM 线程安全与异步交互
  - 发现：`LLMService` 通过锁与时间戳队列实现 RPM 限流（`modules/api_tool.py:326-346`），在 `asyncio.to_thread` 场景下可工作，但会阻塞线程池。
  - 建议：在并发场景提供异步版限流（基于 `asyncio.Semaphore` + 时间窗），统一 Worker 等待策略以减少空转。

- MINOR-006 结构化写出状态持有方式
  - 发现：写出端通过文件句柄属性 `_header_stack` 维护标题栈（`modules/write_out_tool.py:108-122`）。因多次打开文件句柄，栈在每次写入时重建，当前逻辑以目标栈为准写入，行为正确但不直观。
  - 建议：将标题栈持有搬到调用方（如 `tracker_state` 或写出上下文对象），提升可读性与测试可控性。

- MINOR-007 生成器物化的内存开销
  - 发现：并发预处理会一次性物化所有原子段落（`modules/read_tool.py:368-374`），对超大文档可能增加内存压力。
  - 建议：引入分批处理与滚动窗口（例如每 N 段合并与写回 JSON），降低峰值内存。

- INFO-008 配置与环境一致性
  - 发现：默认 Kimi Provider 配置与用户偏好一致；`pyproject.toml` 依赖齐全（`pyproject.toml:12-96`）。
  - 建议：在 `README.md` 明确 `.env` 的关键项（KIMI_API_KEY 等）与备用 Provider 行为差异。

## 优秀实践
- 并发架构由 `Semaphore+as_completed` 迭代为 `Queue+Worker Pool`，保证取用与写出顺序（`README.md:12-18`、`main.py:288-291`）。
- API 结构化解析与 JSON 修复统一到服务层，降级路径清晰（`modules/api_tool.py:269-291`、`modules/translation_core.py:214-276`）。
- 读取与合并逻辑将图片段落作为一等公民处理，避免对非文本内容的误操作（`modules/read_tool.py:40-73`）。
- 结构化写出支持“续写段落”，避免重复标题（`modules/write_out_tool.py:73-77`）。

## 测试与验证
- 单元与集成测试覆盖主要链路：并发流程、短段落合并、结构化写出、CSV 校验、偏好持久化等（详见 `devdiary.md` 2025/12/04、12/11、12/17、12/18）。
- 建议补充：
  - 跨页断句更多边界用例（引号、括号、冒号后延续）。
  - Provider 输出差异下的解析一致性测试（特别是 Silicon/Gemini 模式）。
  - 超长文档场景的内存与性能回归（原子段落物化与批量写出）。

## 重构建议（优先级与工作量）
- 高优先级
  - 引入异步限流器（工作量：中）。
  - 非 JSON 模式下的未翻译部分保存兜底（工作量：中）。
  - 跨页断句算法信号体系扩展与参数化（工作量：中）。
- 中优先级
  - 写出标题栈持有改为上下文对象；统一策略枚举抽象图片回填方式（工作量：中）。
  - 中间 JSON 分批写入与滚动窗口（工作量：中）。
- 低优先级
  - `.env` 与 README 的契约补充（工作量：低）。

## 结论
- 架构演进方向正确；并发、结构化解析与降级策略协同良好。
- 段落读取与合并逻辑显著提升英文技术文档处理质量，图片与标题栈处理符合预期。
- 建议围绕异步限流、断句边界与非 JSON 兜底进一步增强稳健性，以支撑更大规模与更多 Provider 的场景。
