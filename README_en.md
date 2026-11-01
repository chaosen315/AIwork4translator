# AIwork4translator

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **Precise terminology control, professional document translation.**

AIwork4translator is an AI translation tool for professional documents — technical docs, long-form narratives, novels, and rulebooks. It identifies and protects proper nouns during translation through **glossary-driven matching + Aho-Corasick automaton + regex**, keeping terminology consistent. Markdown is supported natively; PDF/Word/Excel/HTML inputs are converted via MarkItDown. Both CLI and WebUI workflows are available, and results can be exported to DOCX/PDF/EPUB/XLSX.

[简体中文](./README.md) | [Changelog](./CHANGELOG.md)

---

## Latest Update (2026/06/14)

- **Paragraph-level retry and failure list**: a failed paragraph is requeued up to `PARAGRAPH_MAX_RETRIES` (falling back to `MAX_RETRIES`); once the limit is reached it is recorded in `failed_segments`, the final Markdown starts with a `> [!WARNING]` summary, and `_intermediate.json` records `translation_status=partial` plus completion counters.
- **Multi-layer bad-JSON recovery**: parsing now falls back through "strict parse → strip code fences → extract balanced JSON → JSON repair → conservative field recovery", keeping the translated body whenever possible.
- **Targeted fallback**: high-risk content (tables, HTML blocks, code fences, container blocks, nested lists) and provider-specific failure patterns switch to a more conservative prompt.
- **Robust segmentation**: tables, code fences, HTML blocks, `:::` containers and images are kept as protected blocks; oversized ones are split along structure boundaries with wrapper lines repeated.
- **Lightweight evaluator**: `evaluate.py` compares two configurations, supports `--safe-degrade off|auto|on` and explicit `--bootstrap-from-seed`, and reports quality proxy, structure preservation, terminology consistency, repeat similarity and `prefix_hash` reuse.
- **WebUI fix**: the WebUI translation path no longer fails with `NameError` caused by a missing `import json`; failed paragraphs now also produce the WARNING summary;
- **Terminology evaluation (issue #44)**: a reproducible A/B/C evaluation over three self-authored documents is available; term hit rate goes from 68.5% to 99.6% — see "Terminology Evaluation (Reproducible)" below and [eval/](./eval/).

Blueprint + append-only log, async providers and multi-format export from 2026/03/14 are documented in [CHANGELOG.md](./CHANGELOG.md).

## Key Features

- **🎯 Proper-noun protection**: Aho-Corasick based glossary matching with plural normalization and smart article handling.
- **📚 Dynamic terminology management**: new terms are collected in real time during translation and can be merged interactively or exported separately.
- **⚡ High-concurrency architecture**: Queue + Worker Pool, roughly 6x faster than the serial workflow on large files.
- **🛡️ Robust failure recovery**: automatic JSON repair, resume-from-checkpoint, safe Ctrl+C interruption, and interactive failure recovery.
- **🖥️ Dual interfaces**: CLI (preference memory, minimal interaction) + WebUI (two-column live preview, WYSIWYG editing).
- **📄 Multi-format input**: native Markdown, plus PDF/Word/Excel/HTML via [MarkItDown](https://github.com/microsoft/markitdown).
- **📦 Multi-format export**: one-click DOCX/PDF/EPUB/XLSX export from `_intermediate.json`.
- **🔌 Multiple providers**: Kimi / OpenAI / DeepSeek / SiliconFlow / Gemini / Doubao (current implementations).

## Terminology Evaluation (Reproducible)

Three self-authored documents (technical doc / rulebook / novel; about 1,200 glossary entries and 2,150 words each) are translated with three glossary strategies: no injection, vector RAG (bge-m3 top-8, per-segment retrieval), and this project (per-segment Aho-Corasick matches). Each document runs twice per group; all 18 runs completed without API errors.

| Strategy | Term hit rate | Occurrence hit rate | Extra input tokens |
|---|---|---|---|
| No glossary | 68.5% | 43.9% | 0 |
| Vector RAG top-8 | 79.7% | 54.1% | +4,257 (prompt +1,258 / retrieval +3,000) |
| **This project** | **99.6%** | **95.3%** | **+1,410** |

- Term hit rate improves by **+31.1 pp (about +45% relative)** over the no-glossary baseline and is **19.9 pp higher than vector RAG**.
- Extra tokens are about **33% of the RAG baseline** (67% less) with no retrieval calls; the lower the term density, the larger the saving — with zero matches this project adds nothing, while RAG still pays a retrieval call per segment.
- The dataset, scripts and raw results live in [eval/](./eval/); the cost curve is [eval/results/cost_curve.png](./eval/results/cost_curve.png).

> Method: substring-based term matching; synthetic documents; single model (DeepSeek-V3 via SiliconFlow). Details and limitations: [eval/README.md](./eval/README.md).

## Quick Start

### 1. Prerequisites

This project uses `uv` for dependency and environment management:

```bash
uv sync --frozen   # install dependencies from uv.lock (creates .venv automatically)
```

On Windows, activate the environment with `.venv\Scripts\activate`; `uv run` also works without manual activation.

### 2. Configure the API

```bash
cp data/.env.example data/.env
```

Fill in at least the key of the provider you plan to use. Keep `SYSTEM_PROMPT` / `BASE_PROMPT` from the example as-is (the translation workflow and the JSON output contract depend on them):

```ini
KIMI_API_KEY=sk-xxxxxxxxxxxxxxxx
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=kimi-k2-turbo-preview
```

The default provider is `kimi`.

### 3. Run

```bash
uv run main.py    # CLI
uv run app.py     # WebUI: open http://localhost:8008 in a browser
```

### 4. Run Tests

```bash
uv run python -m pytest -q
```

Current baseline: **94 passed, 5 skipped** (provider tests are skipped automatically when the corresponding API key is missing).

## Usage

### CLI

1. Run `uv run main.py`.
2. Choose a provider (the last choice is remembered; press Enter to reuse it).
3. Enter the input file path (remembered across runs; non-Markdown files are converted via MarkItDown first and require confirmation).
4. Handle the glossary:
   - Enter `n`: generate a blank glossary (with sample entries); after translation you can choose whether to merge newly found terms.
   - Enter `y`: provide a CSV/XLSX glossary and choose whether to merge new terms back into it (if not, they are saved as a separate CSV).
5. Choose whether to enable concurrency.
6. After translation, save the output and glossary, then optionally export to DOCX/PDF/EPUB/XLSX. `counting_table.csv` records input/output lengths, tokens, and elapsed time.

Interruption and recovery:

- `Ctrl+C` saves the accumulated glossary and the untranslated remainder (`_rest.md`);
- concurrency mode can resume from `_translation_log.jsonl`;
- after `MAX_RETRIES` consecutive failures, an interactive recovery prompt appears (retry or save and exit).

### WebUI

1. Run `uv run app.py` and open http://localhost:8008.
2. Upload a `.md` file (or a convertible format) and an optional glossary.
3. In the two-column editor (source left, translation right), click "Start Translation" for live streaming updates.
4. Online editing, Ctrl+S manual save, autosave, and translation download are supported.

Main endpoints: `/validate-file`, `/start-translation`, `/translation-progress`, `/save-content`, `/download`, `/open-file`.

### Glossary Format

Standard CSV (UTF-8, BOM allowed) with two columns: source and target. Source terms must be unique, with no empty rows. `.xlsx` is also accepted (converted to CSV automatically). An optional third column `reason` records the naming rationale.

| Source | Target | Reason (optional) |
| :--- | :--- | :--- |
| Server | 服务器 | common term |
| Outlaw | 法外之徒 | in-universe proper noun |

### Export & Preview

The CLI can export directly after translation. To inspect the structure of an exported file (headings / TOC / first-page text):

```bash
uv run python scripts/preview_export_outputs.py "<base path without extension>"
```

Example:

```bash
uv run python scripts/preview_export_outputs.py "input_files/《赤红传说》112-127"
```

## Advanced Configuration

### Environment Variables (`data/.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `KIMI_API_KEY` / `KIMI_BASE_URL` / `KIMI_MODEL` | Kimi configuration | base_url `https://api.moonshot.cn/v1`, model `kimi-k2-turbo-preview` |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `GPT_MODEL` | OpenAI configuration | `https://api.openai.com/v1` / `gpt-realtime` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | DeepSeek configuration | — / `deepseek-chat` |
| `SILICON_API_KEY` / `SILICON_JSON_URL` / `SILICON_JSON_MODEL` | SiliconFlow configuration | — / — |
| `GEMINI_API_KEY` / `GEMINI_BASE_URL` / `GEMINI_MODEL` | Gemini configuration | — / `gemini-2.5-flash` |
| `DOUBAO_API_KEY` / `DOUBAO_BASE_URL` / `DOUBAO_MODEL` | Doubao configuration | — / `doubao-seed-1-6-251015` |
| `SYSTEM_PROMPT` | System prompt (two-step translation workflow + JSON output contract) | required, see `.env.example` |
| `BASE_PROMPT` | Additional user prompt (terminology / JSON constraints) | required, see `.env.example` |
| `Requests_Per_Minute` | Requests per minute limit (0 or negative = unlimited) | `10` |
| `Currency_Limit` | Max concurrent workers (effective value is min(this, RPM)) | `6` |
| `MAX_RETRIES` | Consecutive-failure circuit-breaker threshold | `3` |
| `PRESERVE_STRUCTURE` | Whether to enable structured mode | `true` |
| `MAX_CHUNK_SIZE` | Maximum length of a single segment | `4000` |
| `STRUCTURED_OUTPUT` | Whether to parse model output as structured JSON | `true` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Legacy reserved keys: Ollama support is **not implemented** in the current version | — |

### Provider Notes

Implemented providers (see `modules/api_tool.py`): `kimi`, `gpt`, `deepseek`, `silicon`, `gemini`, `doubao`. Gemini and Doubao rely on each vendor's structured-output SDK and are relatively new / not yet fully validated. Ollama integration is not implemented at this time.

### Translation Modes

- **Structured mode**: detects H1–H6 headings and splits by section — recommended for native Markdown;
- **Flat mode**: ignores headings and streams paragraph by paragraph — suitable for converted documents (PDF/Word, etc.).

## Project Structure

```text
project_root/
├── data/                    # configuration (.env.example tracked; .env ignored)
├── modules/                 # business modules
│   ├── api_tool.py          # LLMService: provider adapters, prompts, structured parsing/JSON repair, glossary rewrite
│   ├── translation_core.py  # unified translation core: term matching → prompt → retry/repair → consistency → result
│   ├── read_tool.py         # structured segmentation, mid-page sentence merging, image skipping
│   ├── write_out_tool.py    # blueprint JSON + append-only log → final Markdown
│   ├── log_manager.py       # JSONL incremental log (resume / preview)
│   ├── csv_process_tool.py  # Aho-Corasick term matching, CSV/XLSX validation
│   ├── terminology_tool.py  # glossary load / merge / save
│   ├── export_tool.py       # DOCX/PDF/EPUB/XLSX export
│   ├── markitdown_tool.py   # non-Markdown → Markdown conversion
│   ├── count_tool.py        # paragraph / word count
│   └── config.py            # global configuration (env)
├── services/diagnostics.py  # async API diagnostics and global error state
├── templates/ static/       # WebUI (FastAPI + Jinja + vanilla JS)
├── scripts/                 # install / export preview / check scripts
├── tests/                   # pytest (126 passed / 6 skipped; live-API cases skipped by default)
├── eval/                    # issue #44 evaluation set and scripts (A/B/C, cost curve, raw results)
├── reviews/                 # historical AI review reports (2025-11 to 2025-12)
├── main.py                  # CLI entry point
├── app.py                   # WebUI entry point
├── baseline.py              # no-glossary baseline script (for evaluation; paths are examples and need editing)
├── pyproject.toml           # dependencies and script entry points (uv.lock / requirements.txt kept in sync)
└── devdiary.md / CHANGELOG.md
```

## Testing

```bash
uv run python -m pytest -q    # current: 94 passed, 5 skipped
```

- Tests that require per-provider API keys are skipped automatically when the key is missing;
- Coverage: translation core (retry / JSON repair / glossary rewrite / fallback), concurrency flow, structured reading and mid-page merging, incremental-log writing, glossary matching, export, CLI preferences, etc.;
- No CI yet: GitHub Actions will be added to run pytest on pull requests.

## Roadmap

### Next Iteration (Scheduled)

- **Evaluation extensions** ([issue #44](https://github.com/chaosen315/AIwork4translator/issues/44)): the A/B/C evaluation and cost curve are now available in [eval/](./eval/); next steps are longer/lower-density documents, RAG top-k sensitivity (k=3/5/12) and human-judged mistranslation scoring.

### Later

- Stability: async RPM rate limiter, fallback for untranslated content in non-JSON mode, broader mid-page break signals, strategy-based image re-insertion, write-context refactor, batched processing for very large documents;
- Engineering: GitHub Actions + pytest CI; cleanup of tracked `__pycache__` / `egg-info` / local internal docs;
- Documentation: the public numbers are now based on the reproducible evaluation in [eval/](./eval/).

## Known Limitations

- Terminology depends on a supplied glossary — **no automatic term recognition** (the NER capability was removed on 2025-12-27);
- The "+35% recognition / 99% token savings" figures came from early small-sample experiments; they are now replaced by the reproducible numbers in [eval/](./eval/) (see "Terminology Evaluation" above);
- Ollama integration is not implemented;
- Export layout is based on Markdown structure, so complex layouts (tables, formulas, image positions) are limited; Chinese fonts for PDF depend on the runtime environment;
- Memory usage and rate limiting for very large files still need improvement; the WebUI recommends files ≤10MB;
- Designed for single-user local use; no multi-user authentication or cloud deployment.

## Contact & License

- Questions and suggestions: feel free to open an Issue;
- Email: chasen0315@gmail.com;
- License: [MIT](./LICENSE)
