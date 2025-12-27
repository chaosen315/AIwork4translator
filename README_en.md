# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

Precise technical-document translation powered by glossary-aware prompts and robust Markdown segmentation. This project provides both CLI and WebUI with a unified module layer.

## Latest Update (2025/12/24)

### 🔍 Mid-Page Sentence Continuation Detection (English Papers)
Added sentence-continuation detection optimized for English academic papers:
- **Mid-page break heuristic**: Uses hard veto + scoring to avoid false merges (e.g., sentence-ending punctuation, abbreviation endings)
- **Skip image blocks**: Merge logic can skip image segments to avoid treating non-text as merge candidates
- **Preserve ordering**: Skipped image blocks are kept in the correct relative position to maintain document structure

### ⚡ Major Concurrency Performance Breakthrough
We have implemented a brand-new concurrent translation architecture, bringing significant performance improvements:
- **Queue + Worker Pool Mode**: Adopts `asyncio.Queue` + worker pool architecture, supporting 6 concurrent worker threads
- **Performance Improvement**: 81 pages of content reduced from the original 3 hours to within 30 minutes, **performance improved by approximately 6x**
- **Order Guarantee**: Through paragraph number sorting and write lock mechanism, ensures translation results are output in original order
- **Smart Scheduling**: Supports flexible adjustment of concurrency through `Currency_Limit` environment variable (default 5, maximum does not exceed RPM, i.e., requests per minute limit)

### 🛡️ Exception Protection and Interruption Recovery
- **Interactive Failure Recovery**: When the number of consecutive API failures reaches the limit, the program no longer exits directly, but pauses and offers options: users can choose to "reset failure count and continue retrying" or "save current progress and exit".
- **Manual Interruption Protection**: Captures `Ctrl+C` interrupt signals to ensure that the accumulated glossary and remaining untranslated original text can be safely saved when the user manually stops the program.
- **Resume Support**: The program automatically locates and saves the untranslated part as a `_rest.md` file, facilitating subsequent translation continuation.
- **API Content Auto-Repair**: Implemented automatic detection and paragraph-level retry mechanisms for JSON format errors returned by the API, preventing program crashes caused by single parsing failures.

### 🏗️ Core Architecture Refactoring
- **Unified Translation Core**: Added `TranslationCore` module, unifying CLI and WebUI translation logic, eliminating code duplication
- **Asynchronous Diagnostics**: Introduced non-blocking API diagnostics and global error state management, improving system stability
- **Type Safety**: Unified terminology aggregation forms, resolving type inconsistency issues in concurrent environments

### 🚀 Interaction Experience and Terminology Management
- **CLI Preference Memory**: Automatically loads the last used API platform, file path, and other configurations at startup; simply press Enter to reuse them.
- **Terminology Union Matching**: Real-time collection of "new terms" during translation, forming a union with the CSV glossary for matching to maximize term hit rate.
- **Controllable Merge Switch**: At the end of translation or upon interruption, users can interactively choose whether to merge newly collected terms into the original glossary; if not merged, they are automatically exported as an independent CSV file (`original_filename_timestamp.csv`).
- **Proper Noun Matching Optimization**: More robust case normalization for all-uppercase/capitalized proper nouns (e.g., HOPKINS/Hopkins).

> Plan Change: Due to the current suboptimal performance of the "Blank Glossary Generation" function, it has been decided to temporarily remove it. It may be refactored or discontinued in the future depending on the situation.

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
- **Glossary-first prompts**: Aho-Corasick automaton and regex matching identify domain terms per segment; prompts instruct the model to use exact translations consistently.
- **High Efficiency**: Compared to typical RAG uploads for small glossaries, early tests show ~99% less extra token overhead and ~35% more term hits. Overall quality improves due to stable terminology.
- **Adaptive**: Supports plural normalization (e.g., "outlaws" -> "outlaw") and smart article handling ("the Outlaw" matches "an outlaw").
- **Continuous Improvement**: Since no glossary can be complete, newly detected terms are automatically highlighted/summarized in the output to aid review and glossary updates.

## Key Features
- **Terminology detection & protection**: Efficient Aho-Corasick matching with plural/article normalization.
- **Multi-format input support**: Native `.md/.txt`, and conversion for PDF/Word/Excel/HTML via MarkItDown.
- **Multiple LLM providers**: Kimi, OpenAI (GPT), DeepSeek, and optional local models via Ollama.
- **CLI and WebUI modes**: Unified core logic with interactive CLI and feature-rich WebUI.
- **CLI Preference Memory**: Automatically remembers last used provider and file paths for faster startup.
- **Two-column Markdown editor**: WebUI split-view (original vs translation) with live progress.
- **Real-time progress**: Live polling and safe autosave after completion.
- **Interruption Protection & Recovery**: Supports Ctrl+C safe interruption, automatically saving progress and untranslated content.
- **Interactive Failure Recovery**: Provides pause and retry options upon consecutive API failures to prevent accidental task termination.
- **Interactive confirmation**: For non-Markdown conversion steps.
- **Optional empty glossary generation**: Via NER (CLI) (Note: planned temporary deprecation; see Roadmap).
- **Structured translation**: Smart segmentation based on Markdown headers.
- **Dynamic terminology management (refactor core)**: Real-time union of new terms with the CSV glossary for matching; end-of-run merge switch; paragraph-level retries for stability.

## Project Structure (Unified Root)
```
project_root/
├── data/
│   ├── .env                 # Environment configuration (API keys, model parameters, etc.)
│   └── README_en.md
├── models/
│   └── dbmdz/bert-large-cased-finetuned-conll03-english-for-ner/
├── modules/                 # Unified business modules (core translation logic)
│   ├── api_tool.py          # LLMService, returns (content, tokens), no RAG cache
│   ├── config.py            # GlobalConfig (env-first)
│   ├── read_tool.py         # Structured Markdown segmentation
│   ├── count_tool.py        # Paragraph counting (mirrors segmentation logic)
│   ├── csv_process_tool.py  # Aho-Corasick term matching & CSV validation
│   ├── markitdown_tool.py   # Non-Markdown → Markdown conversion
│   ├── terminology_tool.py  # Glossary management (save, merge, format)
│   ├── translation_core.py  # Translation core engine (encapsulates unified translation workflow)
│   └── write_out_tool.py    # Structured/flat writing (no "# end" by default)
├── services/                # Service layer (async diagnostics, global state management)
│   ├── __init__.py
│   └── diagnostics.py       # Async diagnostics management (singleton pattern)
├── templates/               # WebUI templates
│   ├── index.html           # File upload page
│   └── editor.html          # Two-column editor page
├── static/                  # WebUI static resources
│   ├── style.css            # Global styles
│   ├── script.js            # Homepage interaction logic
│   └── editor.js            # Editor and polling logic
├── uploads/
├── app.py                   # WebUI entry (provides main())
├── main.py                  # CLI entry (interactive, with preference persistence)
├── baseline.py              # Baseline CLI (unified API call, no RAG cache)
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

- **Configuration & secrets**: Set API keys in `data/.env` and never commit secrets. On ≥3 consecutive API failures, run the CLI API test and check your network/proxy. Kimi defaults: `BASE_URL=https://api.moonshot.cn/v1`, `MODEL=kimi-k2-turbo-preview`.
- **Glossary quality & performance**: CSV must have 2 columns, UTF-8 encoding, no empty rows, and unique source terms. Large glossaries are supported efficiently via Aho-Corasick algorithm. Plural forms are automatically handled.
- **CLI Preferences**: The CLI remembers your last choices (provider, file paths) in `data/.prefs.json`. Press Enter to accept the default value shown in `[...]`.
- **Input & structure**: Prefer native Markdown. Non-Markdown files are auto-converted; please review the converted file before continuing. Structured mode relies on heading levels—use `#`/`##` reasonably.
- **Paragraphs & large files**: Very long paragraphs are split intelligently. Large files take longer; WebUI recommends ≤10MB. CLI shows progress as `[current/total]`.
- **Consistency**: Lower `temperature` improves term consistency. The prompt explicitly injects term mappings to stabilize outputs.
- **Local models**: For Ollama, set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env`. Ensure the service is running before use.
- **Logging & outputs**: CLI prints `Total time: xh xm xs` (Chinese format enabled). `counting_table.csv` records raw seconds and tokens. WebUI logs include timestamps.

## Usage
### CLI
- Run `uv run main.py` (or `python main.py`)
- Select the provider (kimi/gpt/deepseek/ollama) - defaults to last used
- Enter the input file path - defaults to last used
  - If the file is not Markdown, it will be converted via MarkItDown and you will be prompted to continue (y/n)
#### Glossary Handling

1. If you don't have a glossary CSV, enter `n`. The program will automatically create a blank glossary file.
   - Filename format: `[Original_Filename]_output_terminology.csv`
   - You can fill in this file after translation (or interruption) for future use.
   - *Note: NER-based automatic generation is temporarily deprecated.*

2. If you have a glossary CSV, enter `y` to provide the file path.
   - Enter the path to your CSV glossary (direct `.xlsx` input is supported; it will be auto-converted).
   - **New Term Merge Option**:
     - After entering the path, you will be asked: "Merge new terms into the glossary? (y/n)".
     - Select `y`: Newly discovered terms will be appended to your original CSV (deduplicated) and saved as a backup.
     - Select `n`: New terms will be saved separately in a new CSV file, leaving the original file untouched.

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
- 2025-12-04: Added CLI preference persistence, Aho-Corasick term matching optimization, and plural/article normalization.
- 2025-11-29: Unified root structure (merged CLI/WebUI), removed RAG cache, aligned modules, updated script entries, cleaned legacy directories

## Roadmap
### High Priority
- **Async rate limiter**: Introduce an async RPM limiter based on `asyncio.Semaphore` + a time window to reduce threadpool blocking under concurrency
- **Fallback for non-JSON mode**: Add lightweight progress markers (e.g., queue index mirror) to unify `rest.md` fallback behavior outside JSON mode
- **Mid-page break algorithm**: Extend the signal set (quotes, parentheses, colon continuations) to improve edge cases like proper nouns / uppercase continuations

### Medium Priority
- **Image reinsertion strategy**: Extract reinsertion as a strategy (e.g., "follow text", "preserve relative position", "collect at section end") for different publishing formats
- **Header stack refactor**: Move header-stack state to a dedicated context (e.g., tracker state / write context) for clarity and testability
- **Batch processing**: Add chunked processing / rolling windows to reduce peak memory usage on very large documents

### Low Priority
- **Config contract docs**: Clarify key `.env` items and provider behavior differences
- **MinerU integration**: Enhance Markdown parsing performance with MinerU
- **CAP-like interaction**: Add a table-style UI (sentence-aligned source/target) for efficient editing

### Completed (2025/12/24)
- ✅ Mid-page sentence continuation detection + image skipping merge
- ✅ Queue-based worker-pool concurrency architecture
- ✅ API auto-repair + two-level JSON degradation strategy
- ✅ CLI preference memory + dynamic glossary management


## Contact
Email: chasen0315@gmail.com (reply within 24 hours by 2025-12-29)
