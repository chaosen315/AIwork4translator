# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Precise AI translation method with noun comparison list.

中文 | [English](./README_en.md)

## 目录

- [简介](#简介)
- [功能特性](#功能特性)
- [程序结构](#程序结构)
- [原理](#原理)
- [效果演示](#效果演示)
- [支持环境](#支持环境)
- [使用教程](#使用教程)
  - [命令行版本](#命令行版本)
  - [WebUI版本](#webui版本)
- [名词表格式](#名词表格式)
- [进阶使用](#进阶使用)
- [联系方式](#联系方式)

## 简介

AIwork4translator 是一个专业的文档翻译工具，通过专有名词识别和正则过滤方法，确保大模型翻译时准确使用专业术语。它能够智能处理各种格式的技术文档，保留原文格式和专有名词，提供高质量的翻译结果。

## 功能特性

- **专有名词识别与保护**：使用正则表达式和术语表确保专业术语在翻译过程中保持不变
- **多格式支持**：支持`.txt`和`.md`格式文件的翻译，通过MarkItDown工具还可以支持PDF、PowerPoint、Word、Excel、HTML等更多格式
- **多种翻译引擎**：支持多种API翻译引擎，包括OpenAI、Kimi、DeepSeek、Ollama等
- **命令行与WebUI双模式**：提供命令行和Web界面两种使用方式，满足不同场景需求
- **双栏Markdown编辑器**：WebUI中提供左右分栏的原文/译文实时展示功能
- **实时翻译进度展示**：翻译过程中实时显示当前处理的段落数/总段落数
- **轮询机制**：采用高效的轮询机制，实时获取并更新翻译进度和内容
- **自动保存功能**：翻译完成后自动检测并保存用户修改
- **交互式确认**：非Markdown文件转换后提供用户确认环节，确保转换质量
- **空白名词表生成**：可自动识别原文中的实体名词并生成空白名词表（命令行版本）
- **结构化/非结构化翻译模式**：支持基于Markdown标题结构的智能分段处理

## 程序结构

```python
project_root/
├── data/
│   └── .env
├── models/
│   └── dbmdz/bert-large-cased-finetuned-conll03-english-for-ner/
│       ├── config.json
│       ├── gitattributes
│       ├── model.safetensors
│       ├── special_tokens_map.json
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       └── vocab.txt
├── modules/                # 统一的业务模块
│   ├── __init__.py
│   ├── api_tool.py         # LLMService 与各供应商适配（返回content,tokens）
│   ├── config.py           # GlobalConfig（env优先），不含会话缓存
│   ├── count_tool.py
│   ├── csv_process_tool.py
│   ├── markitdown_tool.py
│   ├── ner_list_tool.py    # 稳健模型查找，优先根 models/
│   ├── read_tool.py
│   └── write_out_tool.py   # 默认不写 “# end”
├── templates/
│   ├── index.html
│   └── editor.html
├── static/
│   ├── style.css
│   ├── script.js
│   └── editor.js
├── uploads/                # WebUI 上传与输出目录（由后端挂载）
├── app.py                  # WebUI 根入口（提供 main()）
├── main.py                 # CLI 根入口（交互式）
├── baseline.py             # CLI 基线示例（不含RAG缓存）
├── ner_list_check.py       # NER 生成名词表工具
└── pyproject.toml          # 脚本入口：CLI/WebUI
```

## 原理

本项目的核心是在翻译前后对专有名词进行智能识别与约束。我们通过正则与词表匹配在段落中捕捉术语，并在提示词中显式要求模型遵循这些译名，从而提升术语一致性与可审阅性。与传统 RAG 方案相比，初步测试显示：额外 token 开销可减少约 99%，术语命中数量提升约 35%，整体译文质量因术语准确度提升而更稳定。

同时，任何词表都不可能覆盖文本中的所有新术语。为此，系统会在翻译结果中自动汇总并标注未覆盖的新名词，便于编辑审核与补充词表。

推荐的使用方式：输入 Markdown 原文与 CSV 词表，输出为 Markdown 译文。对于非 Markdown 文件，该程序会自动识别并使用 MarkItDown 转换后再翻译。感谢 [MarkItDown](https://github.com/microsoft/markitdown) 的贡献；目前 PDF（非 OCR）表现良好，OCR PDF 仍待进一步验证。

也可以使用通过 [MinerU](https://mineru.ai/) 解析获得的 Markdown 文件作为输入，程序对此的适配良好。

## 效果演示

![image1](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444430551-b22bfb0e-d7a9-40f7-8f69-b02b524b5b08.jpg)

## 支持环境

```python
Python:3.10-3.13
```

## 使用教程

### 命令行版本

#### 基本使用步骤

1. 使用 `uv` 进行依赖管理：在项目根目录执行 `uv sync`（默认创建并使用 `.venv`）
2. 激活虚拟环境（Windows：`\.venv\Scripts\activate`）
3. 修改 `data\.env` 中的环境变量，配置 API KEY 等
4. 运行根入口 `uv run main.py`，按提示选择供应商与文件路径
5. 新增/卸载依赖：`uv add <package>` / `uv remove <package>`
6. 运行 `python -m pytest` 执行测试（用例已绑定根入口与资源）。

### 使用注意事项（重要）

- 配置与密钥：在 `data/.env` 配置 API KEY，切勿提交到仓库；连续 API 失败≥3次时，运行 CLI 的 API 测试并检查网络/代理。默认 Kimi：`BASE_URL=https://api.moonshot.cn/v1`、`MODEL=kimi-k2-turbo-preview`。
- 词表质量与性能：CSV 必须两列、UTF-8、无空行、原文列唯一。大规模词表会增加匹配耗时，建议先收敛核心术语；多词术语匹配更稳定，后续将优化预编译正则与缓存。
- 输入与结构：优先提供原生 Markdown；非 Markdown 会自动转换，转换后请人工校对再继续。结构化模式依赖标题层级，建议合理使用 `#`/`##` 标题。
- 段落与大文件：超长段落会被智能拆分；极大文件处理时间较长，WebUI 建议≤10MB；CLI 进度以“当前/总段落”显示，请耐心等待。
- 翻译一致性：为提高术语一致性，建议降低 `temperature`；提示词已显式注入术语对照以提升稳定性。
- 本地模型：如使用 Ollama，请在 `.env` 设置 `OLLAMA_BASE_URL` 与 `OLLAMA_MODEL`，首次使用需确认服务已启动。
- 日志与输出：CLI 打印“共耗时：x时x分x秒”；统计表 `counting_table.csv` 记录原始秒数与 tokens；WebUI 终端输出带时间戳。

#### 文件转换确认功能

当处理非Markdown格式文件时，程序会先将其转换为Markdown格式。转换完成后，程序会暂停并显示以下信息：
- 生成的Markdown文件路径
- 文件大小和段落数量
- 提示用户输入`y`继续翻译，或输入`n`退出程序

示例提示信息：
```
文件转换完成，路径为【d:\BaiduSyncdisk\桌游\program_translator\data\test_file_output.md】，字数为【1500】，段落数量为【20】，是否继续翻译？如果选择n将结束程序。(y/n)
```

#### 实时进度显示

翻译过程中，系统会实时显示当前翻译进度：
```
正在翻译段落【当前段落数】/【总段落数】
```

#### 名词表处理

1. 如果没有csv格式的名词表，输入`n`进入空白名词表生成流程
   - 注意：需要先下载[BERT模型](https://huggingface.co/chaosen/bert-large-cased-finetuned-conll03-english-for-ner)到指定文件夹
   - 空白名词表生成结束后程序将自动关闭

2. 如果已有csv格式的名词表，输入`y`进入名词表文件上传流程
   - 输入csv格式的名词表文件路径
   - 等待程序完成翻译并保存为md文档

#### 注意事项

- 确保在`\data`文件夹中修改环境变量，将`API_KEY`更换为你自己的
- 开发过程中主要使用kimi进行测试，其他翻译引擎的API访问代码未充分测试
- 对于本地Ollama模型，需要修改`\data\.env`中的`OLLAMA_BASE_URL`与`OLLAMA_MODEL`配置

### WebUI版本

#### 基本使用步骤

1. 修改根 `data\.env` 中的环境变量，配置 API KEY 等
2. 运行根入口 `uv run app.py` 或脚本 `program-translator-webui`
3. 打开终端返回的链接，或直接在浏览器中输入 `http://localhost:8008/`
4. 首页上传 `.md` 与 `.csv` 验证后，点击“使用双栏编辑器”，在编辑器页面点击“开始翻译”。
5. 验证端点：`/validate-file`、`/start-translation`、`/translation-progress`、`/save-content`、`/download`、`/open-file`。
5. 在界面中依次点击“选择文件”与“验证文件/词典”，等待成功提示
6. 选择所使用的API供应平台与模型
7. 点击“开始处理文本”按钮，系统会开始处理文本并跳转到双栏编辑器页面
8. 在双栏编辑器页面，点击“开始翻译”按钮启动翻译过程
9. 翻译过程中，可以在右侧编辑器实时查看翻译进度和结果
10. 翻译完成后，可以直接在右侧编辑器编辑内容
11. 系统会自动保存内容，也可以使用`Ctrl+S`快捷键手动保存

#### 双栏编辑器功能

- **左侧编辑器**：显示原文内容，默认为只读模式
- **右侧编辑器**：实时显示翻译结果，支持编辑
- **进度显示**：在翻译过程中显示当前处理的段落数/总段落数
- **自动保存**：翻译结束后，每隔约20秒自动检查并保存内容变更
- **宽度调节**：可通过拖拽两个编辑器中间的分隔线调整宽度

#### 轮询机制

- 系统采用0.5秒间隔的轮询机制，实时从后端获取翻译进度和新内容
- 轮询过程中，只更新新增的翻译内容，避免整个文档重新加载
- 翻译完成后，轮询自动停止

#### 技术实现细节

WebUI 使用 `FastAPI` 框架开发，主要文件位于根目录：

**核心文件：**
- `app.py`: Web 应用主入口，包含路由定义与 API 实现
- `templates/index.html`: 主页面模板
- `templates/editor.html`: 双栏编辑器页面模板
- `static/style.css`: 样式文件
- `static/script.js`: 前端交互逻辑
- `static/editor.js`: 编辑器与轮询逻辑

**主要API端点：**
- `/`: 首页，展示上传表单
- `/validate-file`: 文件验证与格式转换接口
- `/process`: 处理参数并跳转到编辑器页面
- `/editor`: 双栏编辑器页面
- `/start-translation`: 启动翻译任务接口
- `/translation-progress`: 查询翻译进度和内容接口
- `/save-content`: 保存编辑器内容接口
- `/download`: 下载结果文件接口
- `/open-file`: 打开文件接口
- `/load-content`: 加载文件内容接口
- `/test-api`: LLM API连接测试接口

![image2](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/444591524-9efb2f04-2aa1-4fe7-ad3d-b206f227f3d1.png)

界面截图

![image3](https://github.com/chaosen315/AIwork4translator/blob/1.0.0-release/images/180406E35AFC69EE34ACE24CAAB3E460.png)

下载页面：在右键菜单中选择“另存为”即可。

#### 注意事项

- 文件大小不应超过10MB
- 过大的文件可能导致处理时间较长，请耐心等待
- 对于格式复杂的文件，可能需要先手动转换为Markdown格式，以获得更好的翻译效果

## 名词表格式

| 原文 | 译文 |
| --- | --- |
| …… | …… |
| …… | …… |

在提供名词表后，程序设置了严格的审核步骤以确保名词表可以被正确使用。你可以提前确保以下几个标准以减少在这个步骤中需要花费的时间：

```python
1. 确保文件无空行与空值。
2. 确保原文列无重复值。
3. 确保可以用“UTF-8”解码。
```

## 进阶使用

### 翻译模式说明

- **非结构化翻译模式**：适用于由Markitdown工具转换的非MD文件
  - 不会识别MD文档的标题结构
  - 适用于格式较为简单的文档

- **结构化翻译模式**：适用于原生MD文件
  - 默认识别文件中最多6级的标题结构
  - 智能根据文本结构进行文段切割
  - 默认分行符号为两个换行符号

### 本地模型支持

已支持Ollama本地部署模型的接入。通过修改`\data\.env`中的以下配置来调用本地模型：
- `OLLAMA_BASE_URL`: Ollama服务的URL
- `OLLAMA_MODEL`: 要使用的模型名称

### 快速开始（uv）

```bash
# 同步项目依赖（默认 .venv）
uv sync

# 安装或卸载依赖
uv add <package>
uv remove <package>

# 运行 CLI
uv run main.py

# 运行 WebUI
uv run app.py

# 运行测试
python -m pytest
```

### 环境与默认配置
- `.env` 位于根 `data/.env`；默认 LLM 配置：
  - `KIMI_BASE_URL=https://api.moonshot.cn/v1`
  - `KIMI_MODEL=kimi-k2-turbo-preview`
  - 建议参数：`max_tokens=2048`、`temperature=0.7`、`top_p=0.95`。
  - 请务必安全保存 API KEY，不要提交到仓库。

### 迁移说明（2025/11/29）
- 已合并 `src/` 与 `webui_project/` 到根结构；删除旧目录以减少路径混淆。
- 统一模块到根 `modules/`，移除 RAG 缓存；WebUI 与 CLI 对齐返回值与写出策略（平铺默认不写 `# end`）。
- 脚本入口更新为根：`program-translator-cli = "main:main"`、`program-translator-webui = "app:main"`。

## 开发计划

- 1.2.0 版本：基础功能完成，包括 CLI、WebUI、模型支持等。
- 未来版本：
  - 计划通过MinerU增强对Markdown文件的解析性能。
  - 计划实现传统CAP软件的交互模式，例如表格形式的翻译界面，原文与译文逐句对应，用户可以方便地进行编辑和修改。
  - 计划添加对术语表实时更新的功能，在文档中识别到陌生术语后会自动添加到术语表中，用户可以在翻译过程中实时查看和更新术语表。
  - 计划增强空白术语表的生成效果，除了实体类型外，还提供术语的翻译建议，帮助用户更准确地翻译文档。

## 联系方式

对于该程序有更多想法或遇到部署问题可以发信至chasen0315@gmail.com。最迟24小时内（截止2025/12/29）会进行回复。
