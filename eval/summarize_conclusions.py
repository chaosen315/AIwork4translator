"""Summarise eval/results/summary.json into the issue #44 conclusion numbers.

Usage:
    python eval/summarize_conclusions.py [--summary eval/results/summary.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(value):
    if value is None:
        return "n/a"
    return "%.1f%%" % (100 * value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default=str(Path(__file__).resolve().parent / "results" / "summary.json"))
    args = parser.parse_args()
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    groups = summary.get("groups", {})
    a, b, c = groups.get("A", {}), groups.get("B", {}), groups.get("C", {})

    print("provider:", summary.get("provider"), "model:", summary.get("model"))
    print("rag: embeddings=%s top_k=%s build_tokens=%s" % (
        summary.get("embedding_model"), summary.get("rag_top_k"), summary.get("rag_index_build_tokens")))
    print()
    print("term hit:        A=%s  B=%s  C=%s" % (pct(a.get("term_hit_rate")), pct(b.get("term_hit_rate")), pct(c.get("term_hit_rate"))))
    print("occurrence hit:  A=%s  B=%s  C=%s" % (pct(a.get("occurrence_hit_rate")), pct(b.get("occurrence_hit_rate")), pct(c.get("occurrence_hit_rate"))))
    print("prompt tokens:   A=%s  B=%s  C=%s" % (a.get("prompt_tokens_est"), b.get("prompt_tokens_est"), c.get("prompt_tokens_est")))
    print("embedding tok:   A=%s  B=%s  C=%s" % (a.get("embedding_tokens"), b.get("embedding_tokens"), c.get("embedding_tokens")))
    print()

    docs = summary.get("docs", {})
    totals = {"B": [], "C": []}
    for doc, block in docs.items():
        a_block = block.get("A") or {}
        base = a_block.get("prompt_tokens_est")
        if base is None:
            continue
        row = [doc]
        for group in ("B", "C"):
            g = block.get(group) or {}
            extra = (g.get("prompt_tokens_est") or 0) - base + (g.get("embedding_tokens") or 0)
            totals[group].append(extra)
            row.append("%s: prompt+%s emb=%s total=+%s" % (
                group,
                round((g.get("prompt_tokens_est") or 0) - base, 0),
                g.get("embedding_tokens"),
                round(extra, 0),
            ))
        print("%-14s %s | %s" % (row[0], row[1], row[2]))

    if totals["B"] and totals["C"]:
        mean_b = sum(totals["B"]) / len(totals["B"])
        mean_c = sum(totals["C"]) / len(totals["C"])
        print()
        print("mean total extra: B=+%.0f  C=+%.0f" % (mean_b, mean_c))
        print("C/B total extra: %.1f%%  -> C saves %.1f%% vs RAG baseline" % (100 * mean_c / mean_b, 100 * (1 - mean_c / mean_b)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
