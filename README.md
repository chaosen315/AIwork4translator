# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **精准的术语控制，专业的文档翻译。**

AIwork4translator 是一个专为技术文档设计的翻译工具。通过**Aho-Corasick 自动机**与**正则过滤**技术，它能在翻译过程中精准识别并保护专有名词，确保术语的一致性。支持 Markdown、PDF、Word 等多种格式，提供 CLI 和 WebUI 两种交互方式。

[English](./README_en.md) | [更新日志](./CHANGELOG.md)

---

## ✨ 核心特性

- **🎯 专有名词保护**：基于 AC 自动机的高效术语匹配，支持复数归一化与冠词智能处理。
- **📚 动态术语管理**：翻译过程中实时采集新术语，支持交互式合并与导出。
- **⚡ 高并发架构**：采用 Queue + Worker Pool 模式，大文件翻译性能提升约 6 倍。
- **🛡️ 健壮的异常恢复**：支持断点续传、API 自动修复、Ctrl+C 安全中断保护。
- **🖥️ 双模交互**：
  - **CLI**：偏好记忆、极简操作。
  - **WebUI**：双栏实时预览、所见即所得。
- **📄 多格式支持**：原生支持 Markdown，集成 [MarkItDown](https://github.com/microsoft/markitdown) 支持 PDF/Word/Excel 等格式转换。

---

## 🚀 快速开始

本项目使用 `uv` 进行依赖管理，确保环境纯净且高效。

### 1. 环境准备

```bash
# 同步项目依赖（自动创建 .venv）
uv sync

# 激活环境（Windows）
.venv\Scripts\activate
```

### 2. 配置 API

在 `data/.env` 文件中配置您的 LLM 服务（默认支持 OpenAI 格式）：

```ini
# data/.env
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BASE_URL=https://api.moonshot.cn/v1
MODEL=kimi-k2-turbo-preview
```

### 3. 运行程序

**命令行模式 (CLI)**
```bash
uv run main.py
# 跟随引导选择文件与术语表即可
```

**网页界面 (WebUI)**
```bash
uv run app.py
# 浏览器访问 http://localhost:8008
```

---

## 📖 使用指南

### 命令行版本 (CLI)

CLI 版本专注于效率，适合批量处理和大文件翻译。

1.  **启动**：运行 `uv run main.py`。
2.  **偏好记忆**：程序会自动记住上次使用的 API 平台和文件路径，下次启动直接回车即可。
3.  **术语表**：
    *   **无词表**：输入 `n`，程序可生成空白词表（*功能调整中*）。
    *   **有词表**：输入 `y` 并提供 CSV 路径。翻译结束后，可选择是否将新发现的术语合并回原表。
4.  **非 MD 文件**：程序会自动调用 MarkItDown 转换为 Markdown，转换后需用户确认继续。

### WebUI 版本

WebUI 提供直观的双栏编辑器，适合需要实时校对的场景。

1.  **启动**：运行 `uv run app.py`。
2.  **流程**：
    *   **上传**：在首页选择 `.md` 文件和可选的 `.csv` 词表。
    *   **预览**：进入双栏编辑器，左侧原文，右侧译文。
    *   **翻译**：点击“开始翻译”，右侧实时流式更新。
    *   **编辑与保存**：支持直接编辑译文，系统自动保存（Ctrl+S 手动保存）。

### 术语表格式 (Glossary)

请使用标准的 CSV 格式，包含两列：**原文** 和 **译文**。

| 原文 (Source) | 译文 (Target) |
| :--- | :--- |
| Server | 服务器 |
| Client | 客户端 |

**注意**：
*   文件编码必须为 **UTF-8**。
*   原文列不能有重复值。
*   无空行。

---

## ⚙️ 进阶配置

### 环境变量详解 (`data/.env`)

| 变量名 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `API_KEY` | LLM API 密钥 | (必填) |
| `BASE_URL` | API 基础地址 | `https://api.moonshot.cn/v1` |
| `MODEL` | 模型名称 | `kimi-k2-turbo-preview` |
| `Currency_Limit` | 并发请求限制 | `5` |
| `OLLAMA_BASE_URL` | 本地 Ollama 地址 | (可选) |
| `OLLAMA_MODEL` | 本地 Ollama 模型 | (可选) |

### 本地模型支持 (Ollama)

支持接入 Ollama 运行本地模型（如 Llama 3, Qwen 等）：

1.  确保 Ollama 服务已启动。
2.  修改 `.env`：
    ```ini
    OLLAMA_BASE_URL=http://localhost:11434/v1
    OLLAMA_MODEL=llama3
    ```

### 翻译模式

- **结构化模式**：针对原生 Markdown，识别 H1-H6 标题结构，按章节智能切分（推荐）。
- **非结构化模式**：针对转换后的文档（如 PDF 转 MD），不依赖标题结构，按段落流式处理。

---

## 🏗️ 项目结构

```
project_root/
├── data/               # 配置文件与环境变量
├── modules/            # 核心业务模块 (翻译引擎, 术语管理, IO工具)
├── services/           # 全局服务 (诊断, 状态管理)
├── templates/          # WebUI 模板
├── static/             # WebUI 静态资源
├── main.py             # CLI 入口
└── app.py              # WebUI 入口
```

## 📬 联系方式

如有问题或建议，欢迎提交 Issue 或联系：chasen0315@gmail.com

---

<p align="center">Made with ❤️ for documentation.</p>
