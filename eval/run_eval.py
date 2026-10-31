"""Issue #44 evaluation runner: A (no glossary) / B (vector RAG) / C (segmented AC).

Scale note
----------
Real usage has 1k-3k glossary entries and 2k-10k+ word documents, so injecting the
full glossary is impossible. Group B therefore implements the realistic RAG
baseline: the glossary is embedded once, and for every segment a query embedding
is issued and the top-k entries are injected. Group C injects only the terms that
match the segment via Aho-Corasick.

Cost accounting
---------------
* prompt input tokens: tiktoken estimate over system prompt + prompt (per segment)
* embedding tokens: provider usage for B's query embeddings (index build is
  reported separately, because it amortises across queries in production)
* provider tokens: usage.total_tokens returned by the chat model

Example:
    python eval/run_eval.py --provider silicon --model deepseek-ai/DeepSeek-V3 --rag-top-k 8
    python eval/run_eval.py --stub
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=str(REPO_ROOT / "data" / ".env"))

from modules.api_tool import LLMService  # noqa: E402
from modules.csv_process_tool import find_matching_terms, serialize_terms_for_prompt  # noqa: E402
from modules.read_tool import read_structured_paragraphs  # noqa: E402
from modules.translation_core import TranslationCore, TerminologyPolicy  # noqa: E402

DOCS = ["technical_doc", "rulebook", "novel"]
GROUPS = ["A", "B", "C"]


def load_glossary(doc: str) -> dict[str, dict[str, str]]:
    path = EVAL_DIR / "glossaries" / (doc + ".csv")
    terms: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            term = (row.get("term") or "").strip()
            translation = (row.get("translation") or "").strip()
            if not term or not translation:
                continue
            terms[term] = {"translation": translation, "reason": (row.get("reason") or "").strip()}
    return terms


def load_annotations(doc: str) -> dict:
    return json.loads((EVAL_DIR / "annotations" / (doc + ".json")).read_text(encoding="utf-8"))


def load_segments(doc: str, segment_size: int) -> list[tuple[str, dict]]:
    path = EVAL_DIR / "documents" / (doc + ".md")
    segments = []
    for item in read_structured_paragraphs(str(path), max_chunk_size=segment_size, preserve_structure=True):
        content, meta = item if isinstance(item, tuple) else (item, {})
        if str(content).strip():
            segments.append((str(content), meta or {}))
    return segments


def count_tokens(text: str, encoding) -> int | None:
    return len(encoding.encode(text or "")) if encoding is not None else None


class RagIndex:
    """Embedding-based retriever over the glossary (vector RAG baseline)."""

    def __init__(self, glossary: dict[str, dict[str, str]], model: str, client=None, cache_path: Path | None = None, rebuild: bool = False):
        self.terms = list(glossary.keys())
        self.glossary = glossary
        self.model = model
        self.client = client
        self.cache_path = cache_path
        self.build_tokens = 0
        self.vectors = []
        self.backend = "embeddings"
        if self._load_cache() and not rebuild:
            self.backend = "cache"
            return
        self._build(48)
        self._save_cache()

    def _load_cache(self) -> bool:
        if not self.cache_path or not self.cache_path.exists():
            return False
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if payload.get("model") != self.model or len(payload.get("terms", [])) != len(self.terms):
            return False
        if payload.get("terms") != self.terms:
            return False
        self.vectors = payload.get("vectors", [])
        return bool(self.vectors)

    def _save_cache(self) -> None:
        if not self.cache_path or not self.vectors:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps({"model": self.model, "terms": self.terms, "vectors": self.vectors}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _doc_text(self, term: str) -> str:
        return term + " -> " + self.glossary[term]["translation"]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        self.build_tokens += int(getattr(response.usage, "total_tokens", 0) or 0)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def _build(self, batch_size: int) -> None:
        if self.client is None:
            self.backend = "unavailable"
            return
        try:
            for start in range(0, len(self.terms), batch_size):
                batch = self.terms[start:start + batch_size]
                self.vectors.extend(self._embed([self._doc_text(term) for term in batch]))
        except Exception as exc:  # pragma: no cover - provider dependent
            self.backend = "failed:" + type(exc).__name__
            self.vectors = []

    def query(self, text: str, top_k: int) -> tuple[list[str], int]:
        """Return (selected terms, query embedding tokens)."""
        if not self.vectors:
            # Deterministic lexical fallback so the pipeline still runs offline.
            words = set(re.findall_words(text))
            scored = []
            for term in self.terms:
                overlap = len(words.intersection(re.findall_words(term)))
                if overlap:
                    scored.append((overlap, term))
            scored.sort(reverse=True)
            return [term for _, term in scored[:top_k]], 0
        response = self.client.embeddings.create(model=self.model, input=[text])
        query_tokens = int(getattr(response.usage, "total_tokens", 0) or 0)
        query_vec = response.data[0].embedding
        norm_q = math.sqrt(sum(value * value for value in query_vec)) or 1.0
        scored = []
        for index, vector in enumerate(self.vectors):
            norm_v = math.sqrt(sum(value * value for value in vector)) or 1.0
            dot = sum(a * b for a, b in zip(query_vec, vector))
            scored.append((dot / (norm_q * norm_v), index))
        scored.sort(reverse=True)
        return [self.terms[index] for _, index in scored[:top_k]], query_tokens


def findall_words(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", (text or "").lower())


def build_prompt_with_terms(service: LLMService, content: str, terms: dict[str, dict[str, str]]) -> str:
    stable_terms = serialize_terms_for_prompt(terms)
    base_prompt = os.getenv("BASE_PROMPT") or ""
    return "术语表：\n" + stable_terms + "\n原文段落：\n" + content + base_prompt


def build_prompt_a(service: LLMService, content: str) -> str:
    return service.create_prompt(content, {})


def build_prompt_c(service: LLMService, content: str, glossary: dict[str, dict[str, str]]) -> str:
    matched = find_matching_terms(content, glossary)
    return service.create_prompt(content, matched)


async def translate_segment(
    group: str,
    content: str,
    meta: dict,
    glossary: dict,
    service: LLMService,
    core: TranslationCore,
    stub: bool,
    rag: RagIndex | None,
    top_k: int,
):
    if stub:
        return {"translation": "STUB " + content, "provider_tokens": 0, "embedding_tokens": 0,
                "prompt": content, "error": None, "rag_terms": 0}

    if group == "A":
        prompt = build_prompt_a(service, content)
        data, tokens = service.call_ai_model_api(prompt)
        return {"translation": data.get("translation", ""), "provider_tokens": tokens,
                "embedding_tokens": 0, "prompt": prompt, "error": None, "rag_terms": 0}

    if group == "B":
        if rag is None:
            return {"translation": "", "provider_tokens": 0, "embedding_tokens": 0,
                    "prompt": content, "error": "rag-unavailable", "rag_terms": 0}
        selected, query_tokens = rag.query(content, top_k)
        subset = {term: glossary[term] for term in selected}
        prompt = build_prompt_with_terms(service, content, subset)
        data, tokens = service.call_ai_model_api(prompt)
        return {"translation": data.get("translation", ""), "provider_tokens": tokens,
                "embedding_tokens": query_tokens, "prompt": prompt, "error": None, "rag_terms": len(subset)}

    prompt = build_prompt_c(service, content, glossary)
    result = None
    last_error = None
    for attempt in range(2):
        try:
            result = await core.execute_translation_step(
                {"content": content, "meta_data": meta, "paragraph_number": None},
                glossary,
                {},
                terminology_policy=TerminologyPolicy.MERGE_ON_CONFLICT,
            )
            break
        except Exception as exc:
            last_error = str(exc)
            await asyncio.sleep(3 + attempt * 3)
    if result is None:
        return {"translation": "", "provider_tokens": 0, "embedding_tokens": 0,
                "prompt": prompt, "error": last_error, "rag_terms": 0}
    return {"translation": result.content, "provider_tokens": result.tokens, "embedding_tokens": 0,
            "prompt": prompt, "error": None if result.success else (result.error or "partial"), "rag_terms": 0}


def evaluate_translation(translation: str, annotations: dict) -> dict:
    terms = annotations["terms"]
    term_hits = 0
    occurrence_hits = 0
    for item in terms:
        expected = item["translation"]
        appearances = translation.count(expected) if expected else 0
        if appearances > 0:
            term_hits += 1
        occurrence_hits += min(appearances, int(item["occurrences"]))
    total = int(annotations.get("total_occurrences") or 0)
    return {
        "term_hits": term_hits,
        "term_total": len(terms),
        "term_hit_rate": round(term_hits / len(terms), 4) if terms else 0.0,
        "occurrence_hits": occurrence_hits,
        "occurrence_total": total,
        "occurrence_hit_rate": round(occurrence_hits / total, 4) if total else 0.0,
    }


async def run_one(doc, group, repeat, args, service, core, encoding, glossary, annotations, segments, rag) -> dict:
    started = time.time()
    translations = []
    prompt_tokens = 0
    provider_tokens = 0
    embedding_tokens = 0
    rag_terms = 0
    errors = []
    for index, (content, meta) in enumerate(segments):
        outcome = await translate_segment(group, content, meta, glossary, service, core, args.stub, rag, args.rag_top_k)
        estimated = count_tokens((os.getenv("SYSTEM_PROMPT") or "") + outcome["prompt"], encoding)
        prompt_tokens += estimated or 0
        provider_tokens += int(outcome.get("provider_tokens") or 0)
        embedding_tokens += int(outcome.get("embedding_tokens") or 0)
        rag_terms += int(outcome.get("rag_terms") or 0)
        if outcome.get("error"):
            errors.append({"segment": index, "error": outcome["error"]})
        translations.append(outcome["translation"] or "")
        if not args.stub:
            await asyncio.sleep(args.sleep)

    translation = "\n\n".join(translations)
    metrics = evaluate_translation(translation, annotations)
    record = {
        "type": "run",
        "doc": doc,
        "group": group,
        "repeat": repeat,
        "provider": args.provider,
        "model": args.model,
        "embedding_model": args.embedding_model if group == "B" else None,
        "rag_top_k": args.rag_top_k if group == "B" else None,
        "rag_backend": rag.backend if (rag is not None and group == "B") else None,
        "stub": bool(args.stub),
        "segments": len(segments),
        "prompt_tokens_est": prompt_tokens,
        "embedding_tokens": embedding_tokens,
        "rag_injected_entries": rag_terms,
        "provider_tokens": provider_tokens,
        "duration_seconds": round(time.time() - started, 2),
        "errors": errors,
        **metrics,
    }
    return {"record": record, "translation": translation}


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def write_results(all_runs: list[dict], out_dir: Path, args, rag_build_tokens: dict[str, int]) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = [run["record"] for run in all_runs]
    (out_dir / "runs.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n", encoding="utf-8"
    )

    docs = sorted({item["doc"] for item in records})
    groups = [g for g in GROUPS if any(item["group"] == g for item in records)]
    summary = {
        "provider": args.provider,
        "model": args.model,
        "embedding_model": args.embedding_model,
        "rag_top_k": args.rag_top_k,
        "stub": bool(args.stub),
        "docs": {},
        "groups": {},
        "rag_index_build_tokens": rag_build_tokens,
    }

    for doc in docs:
        summary["docs"][doc] = {}
        base_prompt = None
        for group in groups:
            runs = [item for item in records if item["doc"] == doc and item["group"] == group]
            if not runs:
                continue
            block = {
                "runs": len(runs),
                "term_hit_rate": mean([item["term_hit_rate"] for item in runs]),
                "occurrence_hit_rate": mean([item["occurrence_hit_rate"] for item in runs]),
                "prompt_tokens_est": mean([item["prompt_tokens_est"] for item in runs]),
                "embedding_tokens": mean([item["embedding_tokens"] for item in runs]),
                "rag_injected_entries": mean([item["rag_injected_entries"] for item in runs]),
                "provider_tokens": mean([item["provider_tokens"] for item in runs]),
                "duration_seconds": mean([item["duration_seconds"] for item in runs]),
                "errors": sum(len(item["errors"]) for item in runs),
            }
            if group == "A":
                base_prompt = block["prompt_tokens_est"]
            block["extra_prompt_tokens"] = round(block["prompt_tokens_est"] - base_prompt, 0) if base_prompt is not None else None
            block["total_extra_tokens"] = (
                round(block["extra_prompt_tokens"] + block["embedding_tokens"], 0)
                if block["extra_prompt_tokens"] is not None
                else None
            )
            summary["docs"][doc][group] = block

    for group in groups:
        runs = [item for item in records if item["group"] == group]
        summary["groups"][group] = {
            "runs": len(runs),
            "term_hit_rate": mean([item["term_hit_rate"] for item in runs]),
            "occurrence_hit_rate": mean([item["occurrence_hit_rate"] for item in runs]),
            "prompt_tokens_est": mean([item["prompt_tokens_est"] for item in runs]),
            "embedding_tokens": mean([item["embedding_tokens"] for item in runs]),
            "provider_tokens": mean([item["provider_tokens"] for item in runs]),
            "duration_seconds": mean([item["duration_seconds"] for item in runs]),
            "errors": sum(len(item["errors"]) for item in runs),
        }

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "results.md").write_text(render_markdown(summary, args), encoding="utf-8")
    return summary


def render_markdown(summary: dict, args) -> str:
    lines = ["# Issue #44 evaluation results", ""]
    lines.append("- provider: " + str(args.provider) + " / model: " + str(args.model))
    lines.append("- RAG baseline: embeddings " + str(args.embedding_model) + ", top-k=" + str(args.rag_top_k))
    lines.append("- repeats per document: " + str(args.repeat) + "; segment size: " + str(args.segment_size))
    lines.append("- stub run: " + ("YES (numbers are meaningless)" if args.stub else "no"))
    lines.append("")
    lines.append("## Per document")
    lines.append("")
    lines.append("| doc | group | term hit | occurrence hit | prompt tokens (est) | embedding tokens | total extra vs A | provider tokens | seconds | errors |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for doc, groups in summary["docs"].items():
        for group, block in groups.items():
            lines.append(
                "| %s | %s | %.1f%% | %.1f%% | %s | %s | %s | %s | %s | %s |"
                % (
                    doc, group,
                    100 * (block.get("term_hit_rate") or 0),
                    100 * (block.get("occurrence_hit_rate") or 0),
                    block.get("prompt_tokens_est"),
                    block.get("embedding_tokens"),
                    block.get("total_extra_tokens"),
                    block.get("provider_tokens"),
                    block.get("duration_seconds"),
                    block.get("errors"),
                )
            )
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append("| group | term hit | occurrence hit | prompt tokens (est) | embedding tokens | provider tokens | seconds | errors |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for group, block in summary["groups"].items():
        lines.append(
            "| %s | %.1f%% | %.1f%% | %s | %s | %s | %s | %s |"
            % (
                group,
                100 * (block.get("term_hit_rate") or 0),
                100 * (block.get("occurrence_hit_rate") or 0),
                block.get("prompt_tokens_est"),
                block.get("embedding_tokens"),
                block.get("provider_tokens"),
                block.get("duration_seconds"),
                block.get("errors"),
            )
        )
    build_tokens = summary.get("rag_index_build_tokens") or {}
    if build_tokens:
        lines.append("")
        lines.append("RAG index build tokens (one-time, reported separately): " + json.dumps(build_tokens, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Issue #44 terminology evaluation (A / B=vector RAG / C)")
    parser.add_argument("--docs", default=",".join(DOCS))
    parser.add_argument("--groups", default=",".join(GROUPS))
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--provider", default=os.getenv("EVAL_PROVIDER", "silicon"))
    parser.add_argument("--model", default=os.getenv("EVAL_MODEL", "deepseek-ai/DeepSeek-V3"))
    parser.add_argument("--embedding-model", default=os.getenv("EVAL_EMBEDDING_MODEL", "BAAI/bge-m3"))
    parser.add_argument("--rag-top-k", type=int, default=8)
    parser.add_argument("--rebuild-embeddings", action="store_true")
    parser.add_argument("--segment-size", type=int, default=1200)
    parser.add_argument("--max-segments", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--out-dir", default=str(EVAL_DIR / "results"))
    parser.add_argument("--stub", action="store_true")
    return parser.parse_args(argv)


async def main_async(argv=None) -> int:
    args = parse_args(argv)
    docs = [item.strip() for item in args.docs.split(",") if item.strip()]
    groups = [item.strip().upper() for item in args.groups.split(",") if item.strip()]

    os.environ.setdefault("Requests_Per_Minute", "60")
    os.environ.setdefault("Currency_Limit", "5")
    if args.provider == "silicon":
        os.environ["SILICON_JSON_MODEL"] = args.model

    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as exc:  # pragma: no cover
        print("[warn] tiktoken unavailable (%s)" % exc)
        encoding = None

    service = LLMService(provider=args.provider)
    core = TranslationCore(service)

    embedding_client = None
    if "B" in groups and not args.stub:
        from openai import OpenAI

        embedding_client = OpenAI(
            api_key=os.getenv("SILICON_API_KEY"),
            base_url=os.getenv("SILICON_JSON_URL") or "https://api.siliconflow.cn/v1",
        )

    out_dir = Path(args.out_dir)
    all_runs = []
    build_tokens = {}
    for doc in docs:
        glossary = load_glossary(doc)
        annotations = load_annotations(doc)
        segments = load_segments(doc, args.segment_size)
        if args.max_segments:
            segments = segments[: args.max_segments]
        print("[%s] %d segments, glossary=%d, anchors=%d" % (doc, len(segments), len(glossary), len(annotations["terms"])))
        rag = None
        if "B" in groups:
            cache_path = out_dir / ".cache" / ("embeddings_" + doc + "_" + args.embedding_model.replace("/", "_") + ".json")
            rag = (
                RagIndex(glossary, args.embedding_model, embedding_client, cache_path=cache_path, rebuild=args.rebuild_embeddings)
                if not args.stub
                else None
            )
            build_tokens[doc] = getattr(rag, "build_tokens", 0) if rag else 0
            print("  rag backend=%s build_tokens=%s" % (getattr(rag, "backend", "stub"), build_tokens[doc]))
        for group in groups:
            for repeat in range(1, args.repeat + 1):
                run = await run_one(doc, group, repeat, args, service, core, encoding, glossary, annotations, segments, rag)
                all_runs.append(run)
                record = run["record"]
                print(
                    "  %s rep%d term_hit=%.3f occ_hit=%.3f prompt_tokens=%s emb=%s total_extra=%s %.1fs err=%d"
                    % (
                        group, repeat,
                        record["term_hit_rate"], record["occurrence_hit_rate"],
                        record["prompt_tokens_est"], record["embedding_tokens"],
                        record["prompt_tokens_est"] + record["embedding_tokens"],
                        record["duration_seconds"], len(record["errors"]),
                    )
                )
        del rag

    summary = write_results(all_runs, out_dir, args, build_tokens)
    print("results written to", out_dir)
    print(json.dumps(summary["groups"], ensure_ascii=False, indent=1))
    return 0


def main(argv=None) -> int:
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    raise SystemExit(main())
