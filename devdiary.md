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

## 最后更新时间
2025/11/29

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