# 项目审查报告：program_translator（2025-12-04）

## 项目概述
- 项目目标：面向专业文档翻译，利用术语表与正则/NER手段保障术语一致性与准确性，提供命令行与WebUI两种使用方式。
- 关键能力：
  - 结构化/非结构化的Markdown分段与写入
  - 术语表校验与术语匹配
  - LLM提供者抽象，支持 Kimi、OpenAI、Deepseek、Gemini、Doubao、Sillion
  - 非MD文件到MD的转换（MarkItDown）
  - WebUI（FastAPI + Jinja 模板 + 前端脚本）与 CLI 对齐
- 参考文档：`README.md:43-81, 161-216, 265-283`。

## 审查范围与方法
- 文档与配置：`README.md`、`pyproject.toml:12-93, 101-103`、`requirements.txt:1-78`、`data/.env.example:1-45`。
- 核心代码：`app.py`（WebUI入口与端点）、`templates/index.html`、`templates/editor.html`、`static/script.js`、`static/editor.js`、`modules/*`（读取/计数/术语CSV/写出/LLMService）。
- 测试与样例：`tests/test_webui_app.py:6-26`。
- 评估维度：代码质量、架构设计、性能与资源、安全与错误处理、可维护性、测试与运维；重点聚焦从 html+css+js 向本地 SPA 架构的演进路径。

## 初步印象
- 技术栈：Python 3.11+；后端 FastAPI（`app.py:47-58`），模板引擎 Jinja2（`app.py:53-55`），静态资源挂载（`app.py:50-51`）。
- WebUI 路由：模板页 `/` 与 `/editor`（`app.py:62-66, 290-316`），其余为纯 REST 接口（上传验证、启动翻译、轮询进度、保存、下载、文件读取）。
- 前端形态：以 CDN + 原生脚本为主（`templates/*.html`、`static/*.js`），存在一定页面间耦合（模板注入 `window.templateParams`，`templates/editor.html:54-62`）。
- 迁移可行性：后端已基本具备 SPA 需要的 REST 契约；仅需将模板页演进为单页容器与前端路由，逐步剥离 Jinja 注入即可。

## 代码质量
- 命名与结构：整体清晰；WebUI 端的脚本较为“页面脚本化”，全局变量与内嵌逻辑集中在单文件（`static/editor.js:1-13`, `static/script.js:1-20`）。
- 脚本可维护性：缺少模块化边界（API 封装、状态管理、视图组件化）；轮询、缓存、文件验证等逻辑分散在多个脚本。
- 模板注入：`editor.html` 通过 Jinja 注入 `window.templateParams`（`templates/editor.html:54-62`），形成后端模板与前端状态的耦合点，不利于前后端解耦与本地 SPA。
- 后端日志：统一使用 `log_action/log_error` 包装（`app.py:27-43`），便于追踪；建议将异常信息标准化为错误码对象，方便前端统一处理。

## 架构设计
- 现状分层：
  - 界面层：模板 `index.html`/`editor.html` + 原生 JS。
  - 后端：FastAPI 路由与 REST API（文件上传验证、准备编辑器、开始翻译、进度、保存、下载、打开、加载内容、API 测试）。
  - 业务层：读取/分段、术语匹配、LLMService、写出。
- SPA 目标架构（建议）：
  - 单页容器：一个 `index.html` 承载应用根节点（去除 Jinja 注入）。
  - 路由层：前端路由驱动 `/#/home`、`/#/editor` 等视图切换；使用原生 ESM + 简单 Router（不强依赖框架）。
  - 服务层：封装 REST 调用（`/validate-file`, `/prepare-editor`, `/start-translation`, `/translation-progress`, `/save-content`, `/download`, `/open-file`, `/load-content`, `/get-latest-cache`, `/test-api`）。
  - 视图层：`Home`（上传与验证、供应商选择、跳转编辑器）与 `Editor`（双栏编辑器、轮询与保存）。
  - 状态层：轻量全局状态（最近缓存、任务ID、文件路径、供应商），通过模块导出共享。
  - 后端适配：`/` 返回静态 SPA 容器；增加 SPA Fallback（未匹配路由均返回 `index.html`）；保留现有 REST 接口不变。

## 性能考量
- 轮询机制：当前采用固定间隔轮询（前端），后端提供增量读取（`app.py:479-521`，读取文件并计算进度）。在 SPA 模式下可复用现有端点；如未来升级，可考虑 SSE/WebSocket 替代高频轮询以降低负载。
- 分段与写出：后端按段处理与写出文件（`app.py:178-253`），已具备流式特征；SPA 不需要改动此核心路径。
- 术语匹配：性能优化方向与 CLI/WebUI 共通，建议预编译术语正则并缓存（参考历史建议）。

## 安全性
- 输入与上传：`/validate-file` 对 CSV 做严格验证，对非 MD 的转换路径做异常保护（`app.py:69-138`）；前端 `accept` 限制文件类型（`templates/index.html:23,31`）。建议后端再做 MIME/扩展名双重校验，并限制上传大小。
- 环境变量：集中在 `data/.env`（示例见 `data/.env.example:13-45`），未发现密钥打印；保持密钥不进入日志。
- XSS/渲染：前端编辑器使用 SimpleMDE（CDN），注意在显示译文与原文时统一走纯文本路径（当前通过 `value()` 设置），避免不可信 HTML 注入。

## 错误处理
- 后端统一 `JSONResponse` 输出（`app.py:124-138, 380-386, 401-405, 572-578` 等）；建议引入标准错误码字段，前端据此映射用户提示。
- 任务失败自检：后端在连续失败时触发 `test_api`（`app.py:237-246, 608-627`），前端应接入并可视化诊断结果（Home 视图提供“测试API连接”按钮，`templates/index.html:46-47`）。

## 测试覆盖
- 基础用例存在：路由与基础端点可用性（`tests/test_webui_app.py:6-26`）。
- 建议补充：`translation-progress` 合同测试（状态推进与内容增量）、文件转换失败路径、`prepare-editor`/`process` 参数缓存语义测试。

## 发现清单（聚焦 SPA 迁移）
- [CRITICAL-SPA-001] 模板注入与页面耦合阻碍前后端分离
  - 位置：`templates/editor.html:54-62`
  - 影响：`window.templateParams` 绑定服务端渲染上下文，迁移 SPA 时需剥离。
  - 建议：移除模板注入，统一通过 REST 获取最新缓存与参数；前端状态模块集中管理。

- [MAJOR-SPA-002] 采用 303 跳转至模板页的流程不利于 SPA 路由
  - 位置：`app.py:365-378`
  - 影响：`/process` 端点以 303 跳转至 `/editor` 模板；SPA 更适合前端自行导航。
  - 建议：前端调用 `/prepare-editor` 获得 `cache_key` 后在客户端路由跳转（`/#/editor?cache_key=...`），后端保留 `/process` 以兼容旧流程。

- [MAJOR-SPA-003] 前端脚本未模块化，难以复用与测试
  - 位置：`static/script.js:1-31`, `static/editor.js:1-13`
  - 影响：全局变量与交叉依赖不利于单页应用的视图与服务抽象。
  - 建议：拆分 `api.js`（封装 fetch 调用）、`router.js`（路由）、`views/Home.js`、`views/Editor.js`、`store.js`（状态），以原生 ESM 组织。

- [MINOR-SPA-004] 参数缓存键语义与索引不够直观
  - 位置：`app.py:263-279`
  - 影响：始终返回字符串 `"0"`，但读取最新缓存采用栈头；对外语义不清晰。
  - 建议：返回真实索引或使用 UUID；前端路由统一以键检索。

## 重构方向与要点（本地 SPA）
- 后端保持 REST 契约稳定：保留现有上传、验证、准备编辑器、启动翻译、进度、保存、下载、打开、加载内容、API 测试等端点。
- 单页容器与静态挂载：
  - 将 `/` 与任意前端路由返回同一个 `index.html`（静态文件），由前端路由驱动视图切换。
  - 后端增加一个 SPA Fallback 路由：未匹配的路径均返回 `index.html`。
- 前端模块划分（建议的文件组织）：
  - `static/app.js`：应用入口，注册路由并挂载根视图。
  - `static/router.js`：解析 `location.hash`，切换视图。
  - `static/api.js`：封装对后端的 REST 调用（如 `validateFile`, `prepareEditor`, `startTranslation`, `getTranslationProgress`, `saveContent`, `download`, `openFile`, `loadContent`, `getLatestCache`, `testApi`）。
  - `static/store.js`：集中管理 `cache_key/md_path/csv_path/llm_provider/task_id` 等状态。
  - `static/views/Home.js`：上传与验证界面逻辑，调用 `api` 与 `store`；导航到 `Editor`。
  - `static/views/Editor.js`：双栏编辑器逻辑，轮询与保存、下载等操作。
- 渐进迁移策略：
  - 第一步：在保持模板页的同时新增 SPA 入口与路由，前端视图先复用现有脚本逻辑；后端增加 Fallback（不影响现有页面）。
  - 第二步：移除 Jinja 注入，统一通过 `get-latest-cache`/`prepare-editor` 获取参数；`/process` 仅用于兼容跳转。
  - 第三步：下线模板页，完全以 SPA 驱动页面；保留所有 REST 接口不变，测试覆盖完整。

## 建议的实施步骤
- 阶段A：后端适配
  - 在 `app.py` 保留现有 REST 端点，新增一个静态 `index.html` 作为单页容器，并添加未匹配路由的 Fallback（返回 `index.html`）。
  - 将 `/editor` 路由逐步下线，转由前端路由控制；继续支持 `/process` 的 303 兼容跳转。
- 阶段B：前端模块化
  - 提取 `static/script.js` 与 `static/editor.js` 逻辑到 `api.js`、`store.js`、`views/Home.js`、`views/Editor.js`，入口 `app.js` 注册路由。
  - 统一参数来源：通过 `getLatestCache` 与 `prepareEditor` 管理 `cache_key`，取消 `window.templateParams` 注入。
- 阶段C：交互与性能
  - 保持轮询方案并完善停止条件与错误提示；后续评估 SSE/WebSocket 以降低轮询成本。
  - 增加前端文件大小预检查与用户提示；后端限制上传大小与 MIME 校验。
- 阶段D：测试与验收
  - 补充端到端契约测试（`translation-progress`、`prepare-editor`、`validate-file` 失败路径）。
  - 基于 `python -m pytest` 运行测试，确保后端改动不破坏现有行为。

## 验收与成功标准
- 前后端分离：`/` 与任意前端路由返回同一容器页；无 Jinja 注入；页面切换由前端路由驱动。
- 契约稳定：所有 REST 端点保持不变；旧流程通过 `/process` 仍可工作。
- 体验一致：双栏编辑器功能与轮询逻辑在 SPA 下完整复用；错误提示清晰。
- 测试通过：`python -m pytest` 通过；新增契约测试覆盖关键路径。

## 参考代码位置
- WebUI应用与端点：`app.py:44-66, 69-138, 178-253, 365-378, 479-521, 608-633`
- 模板与脚本：`templates/index.html:1-64`, `templates/editor.html:1-65`, `static/script.js:1-62`, `static/editor.js:1-23`
- 文档与配置：`README.md:43-81, 161-216, 265-283`, `pyproject.toml:12-93, 101-103`, `requirements.txt:1-78`, `data/.env.example:13-45`
- 测试用例：`tests/test_webui_app.py:6-26`
