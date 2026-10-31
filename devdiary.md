# 开发日记：程序翻译工具项目

## 概述
本开发日记记录了程序翻译工具项目的关键修改和开发进展，包括命令行版本(src)和WebUI版本(webui_project)的同步更新。

## 阅读指南
- 时间线按日期排序，记录阶段性变更与原因。
- 当前项目结构概览已更新为根目录统一结构，便于新读者快速定位。
- 修复与优化汇总于独立章节，避免与时间线相互干扰。
- 验证与结果、关键变更摘要与最后更新时间位于文档末尾，便于串联回顾。

## 开发时间线记录


### 2026/06/14 - LLM Provider 缓存协议调研完成
- **新增文件**：
  - `.trae/documents/plan_llm_provider_cache_research.md`：调研计划
  - `.trae/documents/LLM Provider 缓存协议调研报告_VER_A.md`：调研交付物（含 9 个 Provider 全景分析表 + 关键代码原型草案）
- **覆盖范围**：业务已接入 7 个 Provider（Kimi / OpenAI / DeepSeek / SiliconFlow / Gemini / Doubao / Ollama）+ 高价值候选 2 个（Anthropic Claude、OpenAI gpt-5 / o-series）
- **状态**：调研执行完成，待内部技术评审。**未修改任何源码与测试**。

### 2025/11/9 21:24:08 - MarkItDown工具优化（命令行版本）
- **文件修改**：src/modules/markitdown_tool.py
- **主要更新**：
  - 使用`enable_plugins=False`参数初始化MarkItDown，避免不必要的插件加载和依赖问题
  - 安装了MarkItDown的PDF转换可选依赖`pip install markitdown[pdf]`，确保PDF文件能正确转换

### 2025/11/9 21:39:28 - MarkItDown工具优化（WebUI版本）
- **文件修改**：webui_project/modules/markitdown_tool.py
- **主要更新**：
  - 同步使用`enable_plugins=False`参数初始化MarkItDown，避免不必要的插件和依赖
  - 目的：保持与命令行版本一致的初始化方式，提高稳定性

### 2025/11/9 21:41:59 - 环境配置和依赖更新
- **相关文件**：
  - webui_project/modules/api_tool.py
  - webui_project/data/.env
  - requirements.txt
- **主要更新**：
  - 环境变量配置更新：添加SILLION_API_KEY和Ollama本地模型配置（OLLAMA_API_KEY、OLLAMA_BASE_URL、OLLAMA_MODEL）
  - 统一了各provider的返回值格式，确保命令行和WebUI版本行为一致
  - 更新requirements.txt，包含最新安装的MarkItDown PDF转换依赖
  - 安装了WebUI项目缺少的`python-multipart`依赖

### 2025/11/10 - 命令行版本交互体验改进
- **文件修改**：src/main.py
- **主要更新**：
  1. **文件转换后暂停执行**：当非Markdown格式文件转换为Markdown后，程序会暂停并等待用户确认
  2. **文件信息展示**：显示转换后文件的完整路径、大小、字数和段落数量
  3. **用户确认机制**：提供y/n选项，用户可选择继续翻译或退出程序
  4. **进度展示**：在翻译过程中实时显示当前翻译进度（当前段落数/总段落数）
  5. **错误处理优化**：API调用失败时提供更详细的错误信息和解决建议
  6. **文件路径优化**：将文件路径单独显示在一行，确保在Windows终端中可以通过Ctrl+点击直接打开文件
  7. **操作提示增强**：提供更清晰的操作指引和状态信息

### 2025/11/10 - API测试逻辑优化
- **文件修改**：
  - src/modules/api_tool.py
  - src/main.py
- **主要更新**：
  1. **移除内部重试机制**：在api_tool.py中移除了call_ai_model_api和basic_rag_ai_model_api方法的内部重试逻辑
  2. **实现连续失败计数**：在main.py中添加了连续API调用失败计数机制
  3. **自动测试触发**：当连续3次API调用失败后，自动执行API配置测试并退出程序
  4. **错误信息优化**：保留最后一次API调用的错误信息，在退出时一并显示
  5. **重置机制**：成功的API调用会重置失败计数，确保系统能够从临时错误中恢复
  6. **简化错误处理逻辑**：移除了段落内的重试机制，改为连续3次翻译失败就中止程序并触发API测试，简化了代码结构和执行流程
  7. **修复测试结果输出**：添加了对API测试结果（test_results）的打印，提供更详细的诊断信息

### 2025/11/11 - read_tool.py日志埋点系统增强
- **文件修改**：webui_project/modules/read_tool.py
- **主要更新**：
  - 添加完整的日志记录系统，用于跟踪并捕获"list index out of range"异常
  - 在文件开头导入并配置logging模块，设置适当的日志级别和格式
  - 在read_structured_paragraphs和_format_output函数中添加详细的日志埋点
  - 增强异常处理机制，为标题栈访问(header_stack[-1])添加专门的异常处理
  - 记录详细的上下文信息，包括标题栈长度/内容、当前处理层级和行信息
  - 提供清晰的错误堆栈信息，帮助快速定位和修复问题

### 2025/11/11 - WebUI样式优化
- **文件修改**：webui_project/static/style.css
- **主要更新**：
  - 修复input-group组件的圆角样式问题
  - 调整form-control和btn的圆角设置，使组件样式更加统一和协调
  - 将btn的过大圆角(50px)改为与input-group一致的样式，提升UI美观度

### 2025/11/11 - WebUI脚本重定向处理逻辑优化
- **文件修改**：webui_project/static/script.js
- **主要更新**：
  - 为fetch('/process')调用添加redirect: 'manual'配置，确保能够正确处理服务器返回的303重定向响应
  - 实现手动重定向处理逻辑：检查响应的redirected属性并执行window.location.href跳转
  - 增强错误处理：添加请求成功但无重定向时的处理逻辑，显示适当的错误信息
  - 优化用户体验：确保只有"使用双栏编辑器"按钮会触发页面跳转，验证文件按钮只执行验证而不跳转
  - 修复了页面无法正确跳转到editor页面的问题

### 2025/11/11 - WebUI双栏编辑器页面开发
- **文件修改**：
  - webui_project/templates/editor.html
  - webui_project/static/editor.js
  - webui_project/app.py（相关路由）
- **主要功能实现**：
  - **双栏布局设计**：实现左右分栏的Markdown编辑器，左侧显示原文（只读模式），右侧显示译文
  - **编辑器可调整宽度**：添加可拖动的分隔线，用户可以自由调整左右栏宽度
  - **实时翻译进度**：显示翻译状态、当前段落/总段落数和进度条
  - **自动滚动功能**：翻译过程中自动滚动到最新内容，用户手动滚动后暂停自动滚动
  - **自动保存机制**：翻译完成后每20秒自动保存译文内容
  - **快捷键支持**：添加Ctrl+S快捷键保存功能
  - **文件操作**：支持打开原始文件和翻译结果文件
  - **异步翻译处理**：使用轮询机制实时获取翻译进度和更新译文内容
  - **完整用户界面**：包含状态指示器、翻译按钮、完成提示和下载功能

### 2025/11/11 - WebUI参数缓存功能实现
- **文件修改**：
  - webui_project/app.py
- **主要功能实现**：
  - **参数缓存系统**：实现`parameter_cache`全局列表存储翻译参数，避免重复传递文件路径
  - **缓存管理函数**：开发`add_to_cache`和`get_from_cache`函数，支持参数的添加和检索
  - **缓存大小限制**：设置MAX_CACHE_SIZE=10，防止内存占用过大
  - **文件路径处理**：自动处理相对路径，确保存储完整的文件路径
  - **缓存键机制**：使用索引作为缓存键，简化参数传递过程
  - **编辑器路由集成**：修改editor页面路由，支持通过cache_key加载预配置的翻译参数

### 2025/11/11 - WebUI界面按钮优化
- **文件修改**：
  - webui_project/templates/index.html
- **主要更新**：
  - **按钮功能优化**：优化验证文件相关按钮，增强用户交互体验
  - **界面语言调整**：将验证名词表文件的按钮文本从"验证文件"改为"验证词典"，更准确反映功能
  - **颜色主题统一**：统一按钮样式和颜色主题，提升界面一致性
  - **用户引导增强**：优化步骤指示和按钮位置，引导用户按照正确流程操作
  - **API测试按钮优化**：将API测试按钮移至选择API平台下拉框旁，方便用户快速测试连接状态

### 2025/11/16

## 功能修复与优化

### 1. 修复markitdown在Windows 11系统上的兼容性问题
- **问题描述**：在Windows 11系统上，由于onnxruntime版本不兼容，导致markitdown工具无法正常运行
- **解决方案**：更新了依赖管理，确保onnxruntime版本与Windows 11系统兼容
- **修改文件**：requirements.txt，更新了onnxruntime及相关依赖的版本约束

### 2. 修复段落计数导致内存溢出的bug
- **问题描述**：原代码中通过将生成器转换为列表（`list(read_structured_paragraphs())`）来计算段落总数，对于大型文件会导致内存溢出
- **解决方案**：
  - 实现了专门的`count_structured_paragraphs`函数，与`read_structured_paragraphs`保持完全一致的分段逻辑
  - 修改主程序流程，先使用计数函数获取总数，再直接使用生成器处理段落，避免一次性加载所有内容到内存
- **修改文件**：
  - src/modules/count_tool.py：添加count_structured_paragraphs函数
  - src/main.py：优化段落计数和处理逻辑




### 2025/11/16 - WebUI功能修复与优化

#### 1. 缓存加载参数的脚本问题修复
- **问题描述**：编辑器页面无法正确从缓存加载md_path等参数，导致无法显示原文内容
- **解决方案**：
  - 在editor.js中重构了loadOriginalContent函数，实现从模板上下文全局变量、URL参数、缓存（通过/get-latest-cache端点）三级获取md_path参数的逻辑
  - 在editor.html中添加了window.templateParams全局变量，用于前端访问后端传递的md_path、csv_path和llm_provider参数
  - 在app.py中添加了/get-latest-cache端点实现，用于前端获取最新缓存的参数
- **修改文件**：
  - webui_project/static/editor.js
  - webui_project/templates/editor.html
  - webui_project/app.py

#### 2. 移除自动跳转功能，优化页面跳转逻辑
- **问题描述**：文件验证成功后会自动跳转到编辑器页面，影响用户体验和操作流程
- **解决方案**：
  - 修改script.js文件，移除了自动跳转配置和相关逻辑
  - 确保只有用户点击"使用双栏编辑器"按钮时才会执行页面跳转
  - 保留了文件验证成功后的缓存保存功能
- **修改文件**：
  - webui_project/static/script.js

### 2025/11/29 - 目录合并与统一（三阶段）
- 阶段一（盘点与规划）：
  - 生成项目快照与入口/环境位置清单，梳理 `src/modules` 与 `webui_project/modules` 差异（返回值、RAG缓存、写出标记、NER模型路径查找）。
  - 输出迁移指导：目标根结构、路径映射、脚本更新计划、验证清单。
- 阶段二（统一与适配）：
  - 合并统一 `modules/`（根）：
    - `api_tool.py` 统一返回 `(content, total_tokens)`；默认 Kimi 使用 `https://api.moonshot.cn/v1` 与 `kimi-k2-turbo-preview`；移除 RAG 缓存相关逻辑。
    - `write_out_tool.py` 平铺模式默认不写 `# end`；结构化保持标题栈。
    - `ner_list_tool.py` 采用稳健模型查找逻辑，优先根 `models/dbmdz/...`。
    - 其余工具对齐：`read/count/csv_process/markitdown/config`（移除会话缓存，仅 `GlobalConfig`）。
  - WebUI 适配统一返回值，修复段落元组解包与进度条异常。
  - 移除 baseline 的 RAG 缓存调用，改为统一 `call_ai_model_api`；计数写入 `counting_table.csv`。
- 阶段三（入口/资源上移与脚本更新）：
  - 根入口：新增 `main.py`、`baseline.py`、`ner_list_check.py`、`app.py`；复制 `templates/`、`static/`、`uploads/` 到根；更新 `pyproject.toml` 脚本为 `main:main`、`app:main`。
  - 修复 WebUI 模板签名（`TemplateResponse(request, name)`），统一资源挂载；根 `app.py` 内联路由逻辑，不再依赖 `webui_project` 包。
  - 测试同步：新增/更新 `tests/test_webui_app.py`、`tests/test_read_count.py` 绑定根入口与分段策略。
  - 清理旧目录：删除 `src/` 与 `webui_project/`，避免路径残留。

#### 验证与结果
- 依赖：执行 `uv sync` 成功，使用 `.venv` 环境。
- 测试：`python -m pytest` 全部通过（4 passed）；修复 `TemplateResponse` 警告；移除 `load_dotenv("data\.env")` 的反斜杠语法警告（改为原始字符串）。
- WebUI：统一根资源与路由；前端进度条与内容轮询恢复正常；文件验证与编辑器流程可用。
- CLI：`main.py` 支持非 Markdown 转换确认与 CSV 校验；`baseline.py` 统一 API 调用与计数；`ner_list_check.py` NER 生成词表。

#### 变更摘要（关键文件）
- 根入口与资源：`app.py`、`main.py`、`baseline.py`、`ner_list_check.py`、`templates/*`、`static/*`、`uploads/`
- 模块统一：`modules/api_tool.py`、`modules/config.py`、`modules/write_out_tool.py`、`modules/ner_list_tool.py`、`modules/read_tool.py`、`modules/count_tool.py`、`modules/csv_process_tool.py`、`modules/markitdown_tool.py`
- 脚本：`pyproject.toml` 更新脚本入口；`data/README.md` 更新根结构与使用说明。

### 2025/12/04 - 提示词双段式输出与仿真测试工具
- **文件修改**：`data/.env`（提示词优化）
- **新增文件**：
  - `test_prompts/test_samples.md`（多类型英文样例，用于提示词验证）

### 2026/03/14 - 写入性能重构：Blueprint + 增量日志
- **背景**：在并发翻译长文档（如 >100段）时，原有的“每翻译一段就重写整个Markdown文件”的逻辑导致了严重的IO性能瓶颈，写入耗时呈指数级增长（O(N²)），甚至阻塞了翻译线程。
- **核心变更**：
  - **引入 `TranslationLogManager`**：位于 `modules/write_out_tool.py`，负责管理增量日志（.jsonl）。
  - **Blueprint 模式**：翻译开始时生成一个包含所有段落占位符的 `_intermediate.json`（蓝图），翻译过程中只追加 `{"p_id": 1, "translation": "..."}` 格式的日志。
  - **延迟合并**：新增 `finalize_translation_output` 函数，仅在所有任务完成后，读取蓝图和日志，一次性合并生成最终的 Markdown 文件。
  - **WebUI 优化**：`app.py` 中的 `/translation-progress` 接口适配了新模式，直接通过 `TranslationLogManager` 获取预览内容，不再读取物理 Markdown 文件。
- **效果**：
  - 写入时间从随段落数增加而暴涨，变为恒定的 O(1) 追加操作。
  - 最终合并操作为 O(N)，整体效率提升显著。
  - WebUI 预览流畅度不再受文件大小影响。
- **文件修改**：
  - `modules/write_out_tool.py`: 新增日志管理与合并逻辑。
  - `app.py`: 适配日志读取预览。
  - `main.py`: 适配日志写入流程。
  - `tests/`: 新增 `test_log_manager.py` 和 `test_finalize_flow.py` 验证新流程。

### 2026/03/14 - Ctrl+C 中断修复：LLM Provider 全量异步迁移
- **背景**：并发翻译过程中使用 Ctrl+C 终止任务时，部分 Provider 由于同步网络请求阻塞，导致中断响应不及时。
- **核心变更**：
  - 统一在 `LLMProvider` 增加 `generate_completion_async` 异步接口，供上层在 asyncio 场景下直接 `await`。
  - OpenAI 兼容 Provider（Kimi / GPT / Deepseek / Silicon / Doubao）补齐 `AsyncOpenAI` 客户端与对应的异步调用实现，并保持与同步调用参数一致。
  - Gemini Provider 使用 `google.genai.Client.aio.models.generate_content` 提供原生异步实现。
- **效果**：
  - 上层可通过取消 asyncio 任务更快打断正在进行的请求，Ctrl+C 响应更及时。
  - 各 Provider 的返回值格式保持一致：`(content, total_tokens)`。
- **文件修改**：
  - `modules/api_tool.py`: 为各 Provider 增加异步 client 与异步生成方法。

### 2026/03/14 - 多格式导出与结构预览：基于 `_intermediate.json`
- **背景**：翻译完成后需要直接生成可分发的文档（Word/PDF/EPUB/Excel），并能快速检查导出结果的结构是否正确（标题层级/目录/正文）。
- **核心变更**：
  - 以 `_intermediate.json` 为单一数据源实现导出，避免对 Markdown 进行二次解析导致结构丢失。
  - 导出模块统一按 Markdown 标题语法（`#`-`######`）识别并重建结构：
    - DOCX：标题写入为 Heading，正文按段落写入；Notes 以灰色斜体追加。
    - EPUB：按一级标题拆分章节并生成目录（TOC），正文段落换行保留为 `<br/>`。
    - PDF：改用 ReportLab 直出（避免 CJK 字体在 xhtml2pdf 中不稳定），嵌入系统中文字体后中文可正常显示与文本抽取。
  - 新增结构预览脚本：输出 DOCX 标题、EPUB 目录，以及 PDF 第 1 页文本抽取，便于快速人工验收。
- **文件修改/新增**：
  - `modules/export_tool.py`
  - `scripts/preview_export_outputs.py`
- **验证与结果**：
  - 测试：`uv run pytest -q tests/test_export.py` 通过。
  - 实测：对 `input_files/《赤红传说》112-127_intermediate.json` 导出 `docx/pdf/epub`，预览脚本可正确展示 DOCX 标题、EPUB 目录，且 PDF 中文文本抽取正常。

### 2026/06/14 - 翻译稳健性增强、真实复跑验证与文档对齐
- **背景**：真实长文档翻译中暴露出两个关键问题：一是单段失败后并发任务仍继续推进，但失败段可能被静默丢失；二是表格、HTML 块、代码围栏等高风险结构容易触发坏 JSON 或结构化输出不稳定。为显著提高成功率、可恢复性与可排查性，本次围绕段落级重试、稳健分段、保守解析与文档对齐进行集中更新。
- **核心变更**：
  - **段落级重试与失败清单补全**：
    - 在 `main.py` 的并发翻译循环中补上“失败段重新入队 + 次数上限”机制。
    - 达到 `PARAGRAPH_MAX_RETRIES` 后，不再静默跳过，而是写入 `failed_segments`，并在最终输出中标记为部分完成。
    - 最终 Markdown 顶部新增 warning 摘要；`_intermediate.json` 回写 `failed_segments`、`translation_status`、`completed_paragraphs`、`total_paragraphs`。
  - **坏 JSON 多层恢复与保守解析**：
    - 在 `modules/api_tool.py` 中增强结构化解析，新增代码块解包、平衡 JSON 提取与更稳健的解析入口。
    - 在 `modules/translation_core.py` 中增加坏 JSON 保守恢复逻辑，无法完整修复时优先提取 `translation/notes`，放弃不可靠的 `new_terms` 回写。
  - **高风险内容定向 fallback**：
    - 在 `modules/translation_core.py` 中加入对 Markdown 表格、HTML 块、代码围栏、容器块、嵌套列表等高风险内容的识别。
    - 针对 `kimi`、`gemini`、`doubao` 等 Provider 的结构化失败特征，启用更保守的 fallback Prompt，优先保证正文与结构边界。
  - **稳健分段与结构保护**：
    - 在 `modules/read_tool.py` 中强化对表格、HTML 块、代码围栏、容器块、图片节点的边界识别。
    - 通过“原子分段 + 受控合并”减少半截结构段进入翻译链路，提高复杂文档的整体成功率。
  - **输出与恢复链路统一**：
    - 在 `modules/write_out_tool.py` 中统一最终汇总流程，将失败摘要写入 Markdown，并把失败状态同步回蓝图 JSON。
    - 延续 Blueprint + 增量日志模式，确保恢复、预览与最终落盘逻辑保持一致。
- **真实复跑验证**：
  - 基于真实保留的 `_intermediate.json` 与真实输入文件进行复跑验证，重点检查高风险段落与坏 JSON 场景。
  - 验证结果表明：单段失败后不再被静默吞掉；高风险段会进入更保守路径；最终产物可以明确区分 `completed` 与 `partial`。
  - 对真实失败现场的复盘进一步确认：当前版本比旧版本更适合长文档与复杂结构混合内容的稳定翻译。
- **审查与文档对齐**：
  - 对本轮代码更新与 `README.md` 的表述冲突进行了专项审查，重点检查 API 配置、失败恢复、`_intermediate.json` 用途与高风险结构说明。
  - 更新 `README.md`，补充 Provider 专用环境变量说明，修正旧的统一 `API_KEY/BASE_URL/MODEL` 叙述。
  - 新增“失败恢复与排查”“`_intermediate.json` 的作用与注意事项”“高风险结构与保守解析”等说明，确保文档与当前实现一致。
- **相关文件**：
  - `main.py`
  - `modules/translation_core.py`
  - `modules/api_tool.py`
  - `modules/read_tool.py`
  - `modules/write_out_tool.py`
  - `README.md`
  - `.trae/specs/improve-translation-resilience/spec.md`
  - `.trae/specs/improve-translation-resilience/tasks.md`
  - `.trae/specs/improve-translation-resilience/checklist.md`

### 2026/06/14 - Task4/Task5：轻量评测闭环补齐与最小基线集
- **背景**：上一版轻量评测在 `input_files/` 为空时会默认自动 bootstrap，和“默认安全退出、仅在用户显式授权时改写输入目录”的要求不一致；同时需要补上一份基于 `seed-dir` 的真实基线/实验对比报告，作为 Task 清单可勾选的交付物。
- **核心变更**：
  - 在 `modules/lightweight_evaluator.py` 调整最小基线集发现逻辑：`prepare_evaluation_samples()` / `discover_evaluation_samples()` 默认不再自动 bootstrap，空目录时改为安全退出并提示显式启用方式。
  - 为 `EvaluationConfig` 与评测结果增加 `safe_degrade_mode`、`degraded`、`degraded_reason` 字段；`safe_degrade=on` 时直接走本地受控降级，不发真实 API 请求，`auto` 时则在真实调用失败后回退。
  - 扩展 `evaluate.py` CLI 参数，新增显式开关 `--bootstrap-from-seed`，并要求与 `--seed-dir`（或默认 `test_prompts`）配合使用；未显式启用时不再偷偷建立最小基线集。
  - 新增可直接运行的 `test_prompts/evaluate_baseline.json` 与 `test_prompts/evaluate_experiment.json`，作为默认基线/实验配置样例。
  - 更新 `README.md` 与 `.trae/specs/improve-translation-resilience/*`，把评测器的默认安全退出、显式 bootstrap、报告产物与测试状态同步到文档和任务清单。
- **验证与结果**：
  - 自动化测试：`python -m pytest tests/test_lightweight_evaluator.py tests/test_api_prefix_hash.py -q` 通过（`10 passed`），新增覆盖“空目录默认安全退出”和“显式 bootstrap 后生成报告”。
  - CLI 闭环验证：执行 `evaluate.main()` 并传入 `--input-dir output_files/seed_eval_input --bootstrap-from-seed --seed-dir test_prompts --baseline-config-file test_prompts/evaluate_baseline.json --experiment-config-file test_prompts/evaluate_experiment.json --safe-degrade on --output comparison_results.csv --details-json comparison_results.json`，确认空目录会先由 `seed-dir` 建立 `baseline_seed_test_samples.md/.csv`，随后成功落盘基线/实验对比报告。
  - 报告摘要：`comparison_results.csv/json` 当前记录 1 个 seed 样本、2 次降级运行；基线与实验的质量代理、结构保持、术语一致性 delta 均为 `0.0`，实验平均耗时略低（`1.4632s` vs `1.8814s`）。
- **已知限制**：
  - `safe_degrade=on` 产出的译文是本地保守替代结果，主要用于验证评测流程、对比维度和文件产物是否正常，不代表真实翻译质量。
  - 当前环境下 Provider 返回 `invalid temperature: only 1 is allowed for this model`，因此本次报告走了受控降级链路；若需要真正比较提示词工程改动对质量代理指标的影响，仍应在修正 Provider 参数后使用 `safe_degrade=auto` 或 `off` 复测。
- **相关文件**：
  - `modules/lightweight_evaluator.py`
  - `evaluate.py`
  - `tests/test_lightweight_evaluator.py`
  - `tests/test_api_prefix_hash.py`
  - `test_prompts/evaluate_baseline.json`
  - `test_prompts/evaluate_experiment.json`
  - `comparison_results.csv`
  - `comparison_results.json`
  - `output_files/seed_eval_input/`
  - `README.md`

### 2026/06/14 - add-prefix-context-caching 收尾：轻量评测报告补齐 prefix_hash 代理信号
- **背景**：`modules/api_tool.py` 已经具备稳定前缀 `prefix_hash`，但轻量评测器只比较质量代理与稳定性指标，缺少对“前缀是否复用、实验提示词是否改变前缀族”的留痕，导致 `add-prefix-context-caching` 的任务清单仍无法闭环勾选。
- **核心变更**：
  - 在 `modules/lightweight_evaluator.py` 为 `EvaluationRunResult` 增加 `prefix_hashes`、`prefix_hash_unique_count`，评测时无论真实调用成功、异常降级还是 `safe_degrade=on` 的受控降级，都会先构造 prompt 并采集前缀 hash。
  - 扩展 `comparison_results.csv/json` 的样本对比行、配置汇总与总体摘要，新增 `prefix_hash_count`、`unique_prefix_hash_count`、`prefix_hash_reuse_ratio`、`shared_prefix_hash_count`、`prefix_hash_jaccard_similarity` 等字段。
  - 更新 `tests/test_lightweight_evaluator.py`，为基线/实验伪造不同的 hash 分布，覆盖复用率变化、前缀集合重叠度以及新产物字段写盘。
  - 更新 `README.md` 与 `.trae/specs/add-prefix-context-caching/tasks.md`、`checklist.md`，同步声明轻量评测已具备 prefix hash 代理信号与可复盘结论。
- **验证与结果**：
  - 自动化测试：`python -m pytest tests/test_lightweight_evaluator.py tests/test_api_prefix_hash.py -q` 通过（`10 passed`）。
  - CLI 复跑：执行 `python evaluate.py --input-dir output_files/seed_eval_input --bootstrap-from-seed --seed-dir test_prompts --baseline-config-file test_prompts/evaluate_baseline.json --experiment-config-file test_prompts/evaluate_experiment.json --safe-degrade on --output comparison_results.csv --details-json comparison_results.json` 成功生成新报告。
  - 报告摘要：当前 seed 样本下，基线与实验各记录 `2` 次 prefix hash 命中、各有 `1` 个唯一 hash，复用率均为 `0.5`；两组配置的前缀 hash 完全不同，`shared_prefix_hash_count=0`、`prefix_hash_jaccard_similarity=0.0`，说明实验配置确实改变了稳定前缀族，但未带来质量代理与稳定性指标退化。
- **结论**：
  - 现有前缀缓存化改动已具备最小可复盘评测闭环：既能追踪质量代理，也能追踪 `prefix_hash` 这一缓存命中代理信号。
  - 基于当前报告，可继续推进后续提示词工程优化，但应保持“质量代理不下降、结构/术语稳定不回退、prefix_hash 复用率与重叠度变化可解释”作为后续门槛。
- **相关文件**：
  - `modules/lightweight_evaluator.py`
  - `tests/test_lightweight_evaluator.py`
  - `comparison_results.csv`
  - `comparison_results.json`
  - `.trae/specs/add-prefix-context-caching/tasks.md`
  - `.trae/specs/add-prefix-context-caching/checklist.md`
  - `README.md`
