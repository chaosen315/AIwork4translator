## 目标与结果

* 消除 `src/` 与 `webui_project/` 两个文件夹

* 在根目录统一放置 CLI 与 WebUI 入口文件、静态资源与上传目录

* 将两套 `modules/` 合并为一套公共模块，并同时兼容 CLI 与 WebUI 的用法

* 保持 `.venv`、`uv` 管理与 `data/.env` 的配置不变，功能稳定可运行

## 新目录结构（重构后）

* 根目录：`main.py`、`baseline.py`、`ner_list_check.py`、`app.py`

* 公共模块：`modules/`（合并后的模块代码，含 `__init__.py`）

* 前端目录：`templates/`、`static/`、`uploads/`

* 其余保持：`data/`、`models/`、`services/`、`tests/`、`pyproject.toml`、`uv.lock` 等

## 准备事项

* 在根目录创建备份分支或临时拷贝，确保可回滚

* 激活 `.venv` 并确认 `python -V` ≥ 3.11；保留 `uv` 管理依赖

* 记录当前 `data/README.md` 的程序结构图，便于更新

## 步骤一：合并 modules（核心）

* 对比并统一以下文件（以 `src/modules` 为基准，合并 `webui_project/modules` 的差异）：

  * `__init__.py`、`api_tool.py`、`config.py`、`count_tool.py`、`csv_process_tool.py`、`markitdown_tool.py`、`ner_list_tool.py`、`read_tool.py`、`write_out_tool.py`

* 推荐策略：

  * 以 `src/modules` 为主干，保留更健壮的实现（例如 `ner_list_tool.py` 的模型目录查找逻辑；`api_tool.py` 的 tokens 统计与 Kimi 默认模型）。

  * 补充 WebUI 所需的行为差异（例如写入 `# end` 的标记若前端确有依赖，则在 `write_out_tool.py` 中通过参数开关控制；否则移除以统一行为）。

  * 统一 `LLMService.call_ai_model_api` 返回类型为 `(content, total_tokens)`；在 WebUI 侧仅使用 `content`，忽略 `tokens`。

  * 确保 `KimiProvider` 默认使用：`base_url=https://api.moonshot.cn/v1`、`model=kimi-k2-turbo-preview`，其余 API key 与 URL 从 `data/.env` 读取。

* 将合并后的模块文件置于根目录 `modules/`，并保留 `__init__.py`。

## 步骤二：迁移 CLI 入口到根目录

* 将 `src/baseline.py`、`src/main.py`、`src/ner_list_check.py` 移动到根目录

* 校正（或确认）以下点：

  * `load_dotenv(dotenv_path="data/.env")` 保持有效

  * 所有 `from modules...` 的导入能在根目录解析到新的 `modules/`

  * 文件路径使用相对根目录的路径（例如输出与输入文件的路径生成逻辑不依赖 `src/`）

## 步骤三：迁移 WebUI 到根目录

* 将 `webui_project/app.py` 移动到根目录为 `app.py`

* 将 `webui_project/templates/`、`webui_project/static/`、`webui_project/uploads/` 整体移动至根目录并保持同名

* 校正（或确认）以下点：

  * `app.mount("/static", StaticFiles(directory="static"), name="static")` 与 `templates`、`uploads` 挂载目录均为根目录相对路径

  * `UPLOAD_DIR = Path("uploads")` 能在根目录正常创建与使用

  * 仅从公共 `modules/` 导入

  * 若 `call_ai_model_api` 返回 `(content, tokens)`，在 `app.py` 中解包并忽略 `tokens`

## 步骤四：更新入口与依赖

* 更新 `pyproject.toml` 的脚本入口：

  * `program-translator-cli = "main:main"`

  * `program-translator-webui = "app:main"`（若当前 `app.py` 没有 `main()`，新增一个启动 uvicorn 的 `main()`）

* 保持依赖管理使用 `uv`，无需改动版本；如需新增依赖，用 `uv add`；若需移除，用 `uv remove`

## 步骤五：清理旧目录

* 确认根目录运行正常后，删除 `src/` 与 `webui_project/`（包括其 `modules/` 与 `.idea/` 等与该布局绑定的残留）

* 若存在 `src/program_translator.egg-info/` 等打包残留，可一并清理

## 步骤六：功能验证

* CLI 验证：

  * `python main.py` 按交互流程处理一个小型 `md` 文件，确认输出、名词表与 API 流程正常

  * `python baseline.py` 走 RAG 分支，确认缓存与计数表输出正常

  * `python ner_list_check.py` 触发 NER 生成空白名词表

* WebUI 验证：

  * `uv run python app.py` 或 `uv run uvicorn app:app --host localhost --port 8008`

  * 访问 `http://localhost:8008/`，上传 `md` 与 `csv`，完成一次翻译；轮询进度接口与下载接口确认可用

* 测试用例：

  * 在根目录运行 `python -m pytest`，如有不匹配的旧路径测试，更新为新结构后再运行

## 注意事项与风险

* `api_tool.py` 的两套实现存在差异（模型名、返回值是否包含 tokens）。统一为返回 `(content, tokens)` 更通用；WebUI 侧忽略 tokens 即可。

* `write_out_tool.py` 的结尾标记（`# end`）若前端使用，请通过参数或模式控制；尽量保持 CLI 与 WebUI 行为一致。

* `ner_list_tool.py` 建议采用 `src/modules` 的版本以提升模型目录定位的鲁棒性。

* 更新 `data/README.md` 的程序结构图与使用说明，反映新的单根目录结构与入口命令。

* 所有密钥保留在 `data/.env`，避免在代码与日志中输出敏感信息。

## 交付标准

* 根目录可直接运行 CLI 与 WebUI，两套功能均通过一次完整实测

* `modules/` 在根目录统一且无重复代码，导入路径稳定

* `pyproject.toml` 的脚本入口更新后可安装为命令行脚本（可选）

* `data/README.md` 已更新为最新结构图与说明

