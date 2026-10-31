"""Sweep extra token cost against terminology density for issue #44.

For a range of term densities (annotated term occurrences per 1,000 source words)
this builds synthetic segments and computes, without any chat-model calls:

* A: prompt tokens without glossary
* B: vector-RAG prompt (top-k retrieved entries) + query embedding tokens
* C: AC-matched prompt (only matched terms)

Costs are reported per 1,000 source words, so documents of different lengths are
comparable. Chat calls are not needed: prompt tokens come from tiktoken, embedding
tokens from the provider's embedding usage.

Run:
    python eval/sweep_cost.py
"""

from __future__ import annotations

import csv
import json
import os
import random
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EVAL_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=str(REPO_ROOT / "data" / ".env"))

from modules.api_tool import LLMService  # noqa: E402
from modules.csv_process_tool import find_matching_terms  # noqa: E402

from run_eval import (  # noqa: E402
    RagIndex,
    build_prompt_a,
    build_prompt_c,
    build_prompt_with_terms,
    count_tokens,
    load_annotations,
    load_glossary,
)

DENSITIES = [0, 2, 5, 10, 20, 40, 60, 80, 100, 120]
SEGMENTS_PER_DENSITY = 6
SEGMENT_WORDS = 180
TOP_K = 8
DOC = "technical_doc"
SEED = 7


def load_encoding():
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def filler_sentences(doc_text: str, glossary: dict) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", doc_text) if len(item.split()) >= 6]
    fillers = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term.lower() in lowered for term in glossary):
            continue
        fillers.append(sentence)
    return fillers or ["Operators review the shift report before the next window."]


def build_segment(fillers: list[str], anchors: list[str], matches: int, rng: random.Random) -> str:
    anchor_sentences = []
    for offset in range(matches):
        term = anchors[(offset * 7 + rng.randrange(len(anchors))) % len(anchors)]
        anchor_sentences.append("The " + term + " is reviewed before the next release.")
    anchor_words = sum(len(item.split()) for item in anchor_sentences)
    target = max(SEGMENT_WORDS - anchor_words, 30)

    words = []
    index = 0
    while len(words) < target:
        words.extend(fillers[index % len(fillers)].split())
        index += 1
    parts = [" ".join(words[:target]).strip()] + anchor_sentences
    rng.shuffle(parts)
    return " ".join(parts)


def main() -> int:
    encoding = load_encoding()
    service = LLMService(provider="silicon")
    glossary = load_glossary(DOC)
    annotations = load_annotations(DOC)
    anchors = [item["term"] for item in annotations["terms"]]
    rng = random.Random(SEED)

    doc_text = (EVAL_DIR / "documents" / (DOC + ".md")).read_text(encoding="utf-8")
    fillers = filler_sentences(doc_text, glossary)

    from openai import OpenAI

    embedding_client = OpenAI(
        api_key=os.getenv("SILICON_API_KEY"),
        base_url=os.getenv("SILICON_JSON_URL") or "https://api.siliconflow.cn/v1",
    )
    cache = EVAL_DIR / "results" / ".cache" / "embeddings_sweep_bge-m3.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    rag = RagIndex(glossary, "BAAI/bge-m3", embedding_client, cache_path=cache)

    rows = []
    for density in DENSITIES:
        per_segment = round(density * SEGMENT_WORDS / 1000)
        totals = {"words": 0, "A": 0, "B_prompt": 0, "B_emb": 0, "C": 0, "matches": 0, "rag_terms": 0}
        for _ in range(SEGMENTS_PER_DENSITY):
            segment = build_segment(fillers, anchors, per_segment, rng)
            words = len(segment.split())
            prompt_a = build_prompt_a(service, segment)
            selected, query_tokens = rag.query(segment, TOP_K)
            prompt_b = build_prompt_with_terms(service, segment, {term: glossary[term] for term in selected})
            prompt_c = build_prompt_c(service, segment, glossary)

            sys_prompt = os.getenv("SYSTEM_PROMPT") or ""
            tokens_a = count_tokens(sys_prompt + prompt_a, encoding)
            tokens_b = count_tokens(sys_prompt + prompt_b, encoding)
            tokens_c = count_tokens(sys_prompt + prompt_c, encoding)

            totals["words"] += words
            totals["A"] += tokens_a
            totals["B_prompt"] += tokens_b
            totals["B_emb"] += query_tokens
            totals["C"] += tokens_c
            totals["matches"] += len(find_matching_terms(segment, glossary))
            totals["rag_terms"] += len(selected)

        segments = SEGMENTS_PER_DENSITY
        row = {
            "density_per_1k_words": density,
            "segments": segments,
            "avg_segment_words": round(totals["words"] / segments, 1),
            "matches_per_segment": round(totals["matches"] / segments, 2),
            "A_tokens_per_segment": round(totals["A"] / segments, 1),
            "B_prompt_extra_per_segment": round((totals["B_prompt"] - totals["A"]) / segments, 1),
            "B_embedding_per_segment": round(totals["B_emb"] / segments, 1),
            "B_total_extra_per_segment": round((totals["B_prompt"] - totals["A"] + totals["B_emb"]) / segments, 1),
            "C_prompt_extra_per_segment": round((totals["C"] - totals["A"]) / segments, 1),
            "C_total_extra_per_segment": round((totals["C"] - totals["A"]) / segments, 1),
        }
        rows.append(row)
        print(row)

    out = EVAL_DIR / "results" / "cost_sweep.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("written", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
