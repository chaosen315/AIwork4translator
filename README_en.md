# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Precise technical-document translation powered by glossary-aware prompts and robust Markdown segmentation. This project provides both CLI and WebUI with a unified module layer.

## Table of Contents
- Overview
- Key Features
- Project Structure (Unified Root)
- Installation
- Quick Start (uv)
- Usage
  - CLI
  - WebUI
- Environment & Defaults
- Testing
- FAQ
- Changelog & Migration Notes
 - Roadmap
 - Contact

## Overview
AIwork4translator focuses on translating technical documents while preserving terminology accuracy. It detects and protects domain-specific terms and provides an editor workflow to review translations efficiently.

### Principles
- Glossary-first prompts: regex and glossary matching identify domain terms per segment; prompts instruct the model to use exact translations consistently.
- Compared to typical RAG uploads for small glossaries, early tests show ~99% less extra token overhead and ~35% more term hits. Overall quality improves due to stable terminology.
- Since no glossary can be complete, newly detected terms are automatically highlighted/summarized in the output to aid review and glossary updates.

## Key Features
- Terminology detection & protection via glossary matching and regex-based scanning
- Multi-format input support: native `.md/.txt`, and conversion for PDF/Word/Excel/HTML via MarkItDown
- Multiple LLM providers: Kimi, OpenAI (GPT), DeepSeek, and optional local models via Ollama
- CLI and WebUI modes with the same core logic
- Two-column Markdown editor (original vs translation) with live progress
- Real-time progress polling and safe autosave after completion
- Interactive confirmation for non-Markdown conversion
- Optional empty glossary generation via NER (CLI)
- Structured vs flat translation modes based on Markdown headers

## Project Structure (Unified Root)
```
project_root/
├── data/
│   ├── .env
│   └── README_en.md
├── models/
│   └── dbmdz/bert-large-cased-finetuned-conll03-english-for-ner/
├── modules/
│   ├── api_tool.py          # LLMService, returns (content, tokens), no RAG cache
│   ├── config.py            # GlobalConfig (env-first)
│   ├── read_tool.py         # Structured Markdown segmentation
│   ├── count_tool.py        # Paragraph counting (mirrors segmentation logic)
│   ├── csv_process_tool.py  # CSV validation & term matching
│   ├── markitdown_tool.py   # Non-Markdown → Markdown conversion
│   ├── write_out_tool.py    # Structured/flat writing (no "# end" by default)
│   └── ner_list_tool.py     # Robust model path detection (prefers root models/)
├── templates/
│   ├── index.html
│   └── editor.html
├── static/
│   ├── style.css
│   ├── script.js
│   └── editor.js
├── uploads/
├── app.py                   # WebUI entry (provides main())
├── main.py                  # CLI entry (interactive)
├── baseline.py              # Baseline CLI (unified API call, no RAG cache)
├── ner_list_check.py        # NER-based glossary generator
└── pyproject.toml           # Scripts: CLI/WebUI
```

## Installation
- Requirements: Python 3.11+
- Dependency manager: `uv`
- Virtual environment: `.venv` (default)

```
uv sync
```

## Quick Start (uv)
```
# Sync project dependencies (creates .venv)
uv sync

# Install / remove dependencies
uv add <package>
uv remove <package>

# Run CLI (recommended)
uv run main.py
# Or
python main.py

# Run WebUI
python app.py
# Or script entry
program-translator-webui

# Run tests
python -m pytest
```

## Important Notes for Translation

- Configuration & secrets: Set API keys in `data/.env` and never commit secrets. On ≥3 consecutive API failures, run the CLI API test and check your network/proxy. Kimi defaults: `BASE_URL=https://api.moonshot.cn/v1`, `MODEL=kimi-k2-turbo-preview`.
- Glossary quality & performance: CSV must have 2 columns, UTF-8 encoding, no empty rows, and unique source terms. Very large glossaries increase matching time—start with core terms. Multi-word terms are more stable; precompiled regex and caching are planned.
- Input & structure: Prefer native Markdown. Non-Markdown files are auto-converted; please review the converted file before continuing. Structured mode relies on heading levels—use `#`/`##` reasonably.
- Paragraphs & large files: Very long paragraphs are split intelligently. Large files take longer; WebUI recommends ≤10MB. CLI shows progress as `[current/total]`.
- Consistency: Lower `temperature` improves term consistency. The prompt explicitly injects term mappings to stabilize outputs.
- Local models: For Ollama, set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env`. Ensure the service is running before use.
- Logging & outputs: CLI prints `Total time: xh xm xs` (Chinese format enabled). `counting_table.csv` records raw seconds and tokens. WebUI logs include timestamps.

## Usage
### CLI
- Run `uv run main.py` (or `python main.py`)
- Select the provider (kimi/gpt/deepseek/ollama)
- Enter the input file path
  - If the file is not Markdown, it will be converted via MarkItDown and you will be prompted to continue (y/n)
- If you don’t have a glossary, choose `n` to generate an empty glossary via NER, then exit and fill the translation column
- If you have a glossary, provide the CSV path and proceed with translation
- Progress prints: `Translating segment [current]/[total]`

### WebUI
- Run `uv run app.py`
- Open `http://localhost:8008/`
- On the home page:
  - Upload original file (`.md` or convertible format) and validate
  - Upload glossary CSV and validate
  - Choose provider, click “Use Two-Column Editor”, then in the editor page click “Start Translation”
- Endpoints tested: `/validate-file`, `/start-translation`, `/translation-progress`, `/save-content`, `/download`, `/open-file`
- After completion, autosave checks every ~20 seconds

## Environment & Defaults
- Environment file: `data/.env`
- Default provider config for Kimi:
  - `KIMI_BASE_URL=https://api.moonshot.cn/v1`
  - `model=kimi-k2-turbo-preview`
- Suggested parameters: `max_tokens=2048`, `temperature=0.7`, `top_p=0.95`
- Keep API keys secure and do not commit to the repository

## Testing
- Run all tests: `python -m pytest`
- Tests are aligned to the unified root structure

## FAQ
- The editor shows progress as segments are processed; content updates incrementally
- Non-Markdown files are converted and require a user confirmation before translation
- Default writing mode does not append `# end` in flat mode (to match CLI/WebUI behavior)

## Changelog & Migration Notes
- 2025-11-29: Unified root structure (merged CLI/WebUI), removed RAG cache, aligned modules, updated script entries, cleaned legacy directories

## Roadmap
- v1.2.0: Core features completed (CLI, WebUI, provider support, unified modules).
- Future versions:
  - Enhance Markdown parsing performance with MinerU.
  - Add a CAT-like interactive table view (source/target aligned per sentence) for efficient editing.
  - Support real-time glossary updates: auto-adding unfamiliar terms during translation and allowing quick edits.
  - Improve empty glossary generation: include type plus translation suggestions for faster review.

## Contact
Email: chasen0315@gmail.com (reply within 24 hours by 2025-12-29)
