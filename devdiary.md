# 开发日记：程序翻译工具项目

## 概述
本开发日记记录了程序翻译工具项目的关键修改和开发进展，包括命令行版本(src)和WebUI版本(webui_project)的同步更新。

## 阅读指南
- 时间线按日期排序，记录阶段性变更与原因。
- 当前项目结构概览已更新为根目录统一结构，便于新读者快速定位。
- 修复与优化汇总于独立章节，避免与时间线相互干扰。
- 验证与结果、关键变更摘要与最后更新时间位于文档末尾，便于串联回顾。

## 开发时间线记录

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
  - `test_prompts/test_terms.csv`（术语词典示例）

### 2025/12/06 - 段落重试、术语合并开关与专有名匹配优化
- **文件修改**：
  - `main.py`
  - `modules/csv_process_tool.py`
  - `tests/test_matching_terms_aho.py`
- **主要更新**：
  - 段落级 API 重试：在 `main.py:130-169` 引入循环重试当前段落，捕获异常并累计 `consecutive_api_failures`，当达到 `MAX_RETRIES` 后触发 API 配置测试并退出；成功调用后重置失败计数。
  - 术语合并开关与并集匹配：在 `main.py:113-116` 新增是否合并新术语的交互开关；在 `main.py:137-145` 使用 CSV 术语与运行中收集的新术语的并集 `union_terms_dict` 进行段落匹配；结束时按选择进行合并保存或将“新术语”单独保存（`main.py:198-203`）。
  - 专有名匹配优化：在 `modules/csv_process_tool.py:98-113` 优化 `preprocess_text`，对全大写或首字母大写的词不进行单数化与形态归一，仅做小写标准化，从而解决如 `HOPKINS` ↔ `Hopkins` 在后续段落的匹配问题。
  - 测试用例补充：在 `tests/test_matching_terms_aho.py` 增加针对专有名的大小写匹配、标点边界与重复键折叠的测试用例，覆盖 `Hopkins/HOPKINS` 的常见场景。
- **验证与结果**：
  - 新增测试已就绪，运行命令：`python -m pytest -q`。
  - 若本地缺少相关依赖（如 `ahocorasick` 或 NLTK 资源）导致测试失败，可将环境变量 `CSV_MATCH_ENGINE` 设置为 `regex` 进行验证，或按需安装依赖。
  - `test_prompts/test_prompts.py`（早期测试脚本）
  - `test_prompts/simulator.py`（仿真测试程序，直接调用 `modules` 工具链）
- **主要更新**：
  1. 提示词输出格式规范化：在 `SYSTEM_PROMPT` 与 `BASE_PROMPT` 中明确规定译文必须分为上下两段，第一段为正文，第二段为“译注”列表；两段之间以单个换行分隔；“译注”需以列表形式给出新术语的翻译理由与可能典故（参考 `data/.env:7-10`）。
  2. 强化术语处理：正文严格使用词典中的译名；对词典未覆盖的新术语，正文保留英文并在“译注”中说明译名依据与来源。
  3. 仿真测试工具：新增 `simulator.py`，复刻真实 CLI 流程，直接使用 `LLMService.create_prompt` 与 `LLMService.call_ai_model_api` 调用模型，结合 `csv_process_tool.find_matching_terms` 进行术语匹配，并依据 `global_config.max_chunk_size` 进行段落切分与逐段测试；内置格式合规分析，检测“译注：”分隔与列表格式是否满足要求。
- **使用说明**：
  - 运行仿真：`python test_prompts\simulator.py --provider kimi`
  - 结果输出：`test_prompts/simulation_results/simulation_<provider>_<timestamp>.json|.txt`
- **验证要点**：
  - 检查译文是否包含“正文”与“译注”两段，且“译注”开头包含“译注：”标识并以列表呈现。
  - 统计格式合规率、段落成功率与tokens消耗，辅助提示词迭代。
- 关键调用参考：`modules/api_tool.py:LLMService.create_prompt` 与 `LLMService.call_ai_model_api`；术语匹配参考：`modules/csv_process_tool.py:find_matching_terms`。

### 2025/12/04 - 名词表XLSX转换与验证优化
- 文件修改：`modules/csv_process_tool.py`、`app.py`、`main.py`
- 主要更新：
  - `validate_csv_file` 支持 `.xlsx` 自动转换为 `.csv`，返回 `(is_valid, updated_path)`，并在转换后继续进行两列非空校验（`modules/csv_process_tool.py:21`、`modules/csv_process_tool.py:75`）。
  - `get_valid_path` 适配新返回值，直接返回转换后的有效路径（`modules/csv_process_tool.py:7-19`）。
  - Web 端 `/validate-file` 接口接入新签名并在转换后更新 `file_path`（`app.py:110-119`）。
  - CLI 端通过 `get_valid_path("请输入名词表CSV文件路径: ", validate_csv_file)` 获取转换后的路径，无需额外改动（`main.py:78-82`）。
- 依赖与实现：
  - 使用 `pandas` 进行 XLSX 读取与 CSV 写出，项目依赖已包含（`requirements.txt:56`）。
  - 转换产物命名为 `<原名>_converted.csv`，编码 `utf-8-sig`，列名规范化为 `term, definition`。
- 验证与结果：
  - 运行 `python -m pytest -k xlsx -q`，结果：`2 passed, 35 deselected`，耗时约 16.27s（Terminal#607-610）。
- 注意事项：
  - CSV 校验严格要求两列且非空；若 XLSX 列数不满足要求则拒绝并不产生转换文件。
  - Web 端验证返回的路径为转换后的 CSV 绝对路径，后续处理统一以该路径为准。

### 2025/12/04 - CLI偏好持久化与交互预填充
- 文件修改：`main.py`、`modules/csv_process_tool.py`
- 主要更新：
  - 在 CLI 中新增偏好持久化，记录上次使用的 API 平台与文件路径，写入 `data/.prefs.json`（`main.py:182-192`）。
  - 启动时读取偏好作为默认值，输入提示以 `[...]` 形式预填充，支持直接回车沿用（`main.py:17-24`、`main.py:26-45`、`main.py:105`）。
  - 路径输入函数支持默认值与重试，兼容引号剥离与转换后路径返回（`modules/csv_process_tool.py:7-19`）。
- 测试与验证：
  - 单元测试：`tests/test_get_valid_path.py`（默认值、引号剥离、重试逻辑），`tests/test_validate_csv_file.py`（有效 CSV、不合规列、空单元格）。
  - 集成测试：`tests/test_main_prefs_integration.py` 验证首次运行写入偏好、二次运行沿用默认值，替换 `LLMService` 与 I/O 链路确保可控。
  - 结果：在 `.venv` 下运行 `python -m pytest -q` 全部通过；单测与集测独立运行均通过。
- 使用说明：
  - 偏好文件位于 `data/.prefs.json`（隐藏文件名，资源管理器需启用隐藏文件显示或使用 `Get-ChildItem data -Force`）。
  - 若流程在转换确认阶段选择 `n` 或异常提前退出，则偏好不会写入；需要完成一次正文翻译流程以生成偏好文件。

### 2025/12/08 - Dashboard优化与项目审查
- **文件修改**：
  - `main.py`
  - `modules/terminology_tool.py`
  - `tests/test_dashboard_columns.py` (新增)
  - `reviews/program-review-2025-12-08T220000.md` (新增)
- **主要更新**：
  1. **Dashboard 监控粒度深化**：
     - 在 `main.py` 的 dashboard CSV 输出中新增了4个关键性能指标列：
       - `Term_Matching_Time_s`：术语匹配耗时（使用 `perf_counter` 独立计时）。
       - `Total_API_Time_s`：API 交互总耗时（包含请求与重试）。
       - `Pure_API_Time_s`：纯模型推理耗时（累加多次请求）。
       - `JSON_Repair_Time_s`：JSON 格式修复耗时。
       - `Retry_Count`：该段落触发的重试次数。
     - 目的：精确定位任务时长高企的根因（是本地匹配慢、API响应慢还是重试过多）。
  2. **Bug 修复**：
     - 修复 `modules/terminology_tool.py` 中的 `dict_to_df` 函数，当输入列表为空时，正确返回包含 `term`, `translation`, `reason` 列的空 DataFrame，解决了测试中的 KeyError 问题。
  3. **测试覆盖**：
     - 新增 `tests/test_dashboard_columns.py`，模拟 CLI 流程验证 Dashboard CSV 的表头结构与数据写入正确性。
  4. **代码审查与重构规划**：
     - 完成了全面的代码审查（`reviews/program-review-2025-12-08T220000.md`），识别出 `main.py` 的单体架构问题，并提出了基于 `TranslationSession` 类的重构方案。

### 2025/12/08 - API修复与中断保护机制增强
- **文件修改**：
  - `main.py`
  - `modules/terminology_tool.py`
  - `tests/test_save_glossary_df.py` (新增)
  - `tests/test_untranslated_rest.py` (新增)
  - `tests/test_save_terms_result.py` (新增)
- **主要更新**：
  1. **API 内容修复优化**：
     - 在 `main.py` 中增强了对 `Invalid JSON format` 错误的显式处理，当检测到 JSON 格式错误时抛出异常触发段落级重试，防止程序因解析失败而崩溃。
  2. **翻译流程中断保护**：
     - **KeyboardInterrupt 捕获**：在 `main.py` 中捕获 `Ctrl+C` 中断信号，确保在用户手动终止程序时，能够保存当前已累积的新术语表和剩余未翻译的原文。
     - **API 连续失败交互**：当 API 连续失败次数达到上限时，暂停程序并提供交互选项。用户可选择重置失败计数继续重试，或保存进度后退出。
     - **未翻译部分保存**：通过匹配当前段落的前20个字符，在原文件中定位翻译进度，将剩余未翻译内容保存为 `_rest.md` 文件。
  3. **术语表保存逻辑优化**：
     - **无状态封装**：将 `main.py` 中重复的术语保存逻辑封装为 `modules/terminology_tool.py` 中的 `save_terms_result` 函数，统一了“合并保存”与“单独保存”的处理流程。
     - **文件名修复**：修复 `save_glossary_df` 函数在保存时丢失原文件名的 bug，输出格式规范为 `原文件名_时间戳.csv`。
  4. **测试覆盖增强**：
- 新增针对术语保存文件名、封装函数逻辑及未翻译部分定位算法的单元测试，覆盖 Setext 标题、重复关键词、中文 Unicode 字符等复杂场景。

### 2025/12/11 - 并发架构迭代与队列监控、RPM管理修复
- 文件修改：
  - `main.py:109-145`（并发翻译循环重构、队列监控日志、并发数读取配置）
  - `modules/read_tool.py`（新增 `read_and_process_structured_paragraphs_to_json`，一次性切分与短段落合并）
  - `modules/write_out_tool.py:80-96`（结构化写出 `header_path` 健壮性检查，避免 `IndexError`）
  - `modules/api_tool.py`（RPM 限流线程安全修复）
  - `tests/test_concurrency_flow.py`（新增并发流程与短段合并测试）
  - `data/.env`（新增并发控制项 `Currency_Limit`）
- 主要更新：
  1. 并发架构由 `Semaphore + as_completed` 调整为 `asyncio.Queue + Worker Pool`，确保任务按段落顺序被取用，避免出现后段率先开始的问题。
  2. 在并发模式中引入中间 JSON（`*_intermediate.json`），包含 `paragraph_number/meta_data/content/...`，翻译完成后按 `tracker_state['next_id']` 顺序落盘，保证写入有序且无冲突。
  3. `Currency_Limit` 驱动并发工作池大小，默认 5，支持在 `.env` 中统一调控。
  4. 队列监控与调试日志：为每个 Worker 添加启动/取任务/完成/队列为空退出日志；在段落任务开始时输出 `[段落{p_id}] 开始翻译...`，提升可观测性。
  5. RPM 管理修复：为 `LLMService` 增加互斥锁与安全计数，修复并发场景下每分钟请求数限制不生效的问题，同时不影响“流式竞赛”模式。
  6. 写出健壮性：`write_out_tool.py` 在结构化模式下对 `meta_data.header_path` 做类型与长度校验，避免并发下偶发 `IndexError`。
- 测试与验证：
  - `tests/test_concurrency_flow.py` 验证并发循环在 mock API 下的总 tokens 统计、写出调用次数与术语累积；覆盖短段落合并的期望输出（3 段）。
  - 引入 `pytest-asyncio` 以支持异步测试；在 `.venv` 环境中运行 `python -m pytest` 通过。
- 设计动因与效果：
  - 解决用户反馈的“段落 52 完成而段落 17 才开始”的调度异常；新架构保证任务取用顺序与写出顺序一致，终端可通过队列日志直观看到并发健康状态。
  - 保持“流式竞赛”优势，同时确保 RPM/写出顺序与结构化标题处理的稳定性。


### 2025/12/11 - 核心架构重构与代码审查问题解决
- **文件修改**：
  - `main.py`（拆分超长函数，统一核心逻辑）
  - `modules/translation_core.py`（新增，封装翻译核心逻辑）
  - `services/diagnostics.py`（新增，异步诊断管理）
  - `app.py`（适配新的TranslationCore）
  - `.data/document/dev_order.md`（更新开发计划）
- **主要更新**：
  1. **解决CODE-001（核心逻辑重复）**：
     - 抽象`TranslationCore.execute_translation_step()`统一CLI同步循环与并发Worker的翻译逻辑
     - 通过依赖注入`LLMService`实现可测试性，使用`asyncio.to_thread`避免阻塞事件循环
     - 封装术语匹配、Prompt构造、API调用/重试、JSON修复、术语复写等完整流程
  2. **解决CODE-002（main()函数过长）**：
     - 将`main()`拆分为`get_user_config()`、`run_sync_translation_loop()`、`finalize_process()`等专注函数
     - 使用`@dataclass`提升配置可读性，职责分离明确
  3. **解决ARCH-003（缺少异步API诊断）**：
     - 新增`safediagnostics`模块，实现单例`DiagnosticsManager`管理全局错误状态
     - 在并发模式下添加非阻塞诊断流程，避免Worker失败时重复诊断
  4. **解决ARCH-004（aggregated_new_terms类型不一致）**：
     - 统一并发路径中的术语聚合形态：使用`aggregated_new_terms_dict`进行核心匹配，通过写锁同步更新
     - 删除main.py:228-266中的无效占位代码，确保类型一致性
  5. **代码质量提升**：
     - 新增`tests/test_translation_core.py`（4个单元测试）验证核心模块功能
     - 修复多个过时测试用例，确保测试套件与代码变更同步
     - 保留NER空白术语表生成代码作为未来开发基础
- **验证结果**：
  - 所有新增测试通过，无回归问题
  - 并发流程测试与核心模块测试均正常
  - CLI与WebUI统一使用TranslationCore，消除逻辑分裂

## 最后更新时间
2025/12/12

## 项目结构概览（合并后）

- 根入口
  - `main.py`（CLI 交互式主程序）
  - `baseline.py`（统一 API 调用的基线示例）
  - `ner_list_check.py`（NER 词表生成工具）
  - `app.py`（WebUI 主入口，提供 `main()`）
- 统一模块 `modules/`
  - `api_tool.py`（LLMService 与供应商适配，返回 `content,tokens`，无 RAG 缓存）
  - `config.py`（`GlobalConfig`，环境优先）
  - `read_tool.py`、`count_tool.py`（结构化分段与计数，逻辑一致）
  - `csv_process_tool.py`（CSV 校验与术语匹配）
  - `markitdown_tool.py`（非 Markdown 转换）
  - `write_out_tool.py`（结构化/平铺写出，默认不写 `# end`）
  - `ner_list_tool.py`（稳健模型路径查找，优先根 `models/dbmdz/...`）
- 资源与数据
  - `templates/`（`index.html`、`editor.html`）
  - `static/`（`style.css`、`script.js`、`editor.js`）
  - `uploads/`（上传与输出目录）
  - `data/.env`（统一环境配置）
  - `models/dbmdz/bert-large-cased-finetuned-conll03-english-for-ner/`（NER 模型）
