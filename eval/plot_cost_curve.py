"""Plot the extra-token cost curve: segmented injection (C) vs vector RAG (B).

Run after eval/sweep_cost.py:
    python eval/plot_cost_curve.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.csv_process_tool import find_matching_terms  # noqa: E402
from run_eval import load_glossary, load_segments  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

COLOR_B = "#d95f02"
COLOR_C = "#1b9e77"
COLOR_TXT = "#333333"


def load_sweep() -> list[dict]:
    with (EVAL_DIR / "results" / "cost_sweep.csv").open("r", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append({key: (int(value) if key == "segments" else float(value)) for key, value in row.items()})
        return rows


def measured_point() -> dict:
    summary = json.loads((EVAL_DIR / "results" / "summary.json").read_text(encoding="utf-8"))
    runs = [
        json.loads(line)
        for line in (EVAL_DIR / "results" / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    xs, cs, bs = [], [], []
    for doc in summary["docs"]:
        block = summary["docs"][doc]
        segments = next((item["segments"] for item in runs if item["doc"] == doc), 0)
        if not segments:
            continue
        a_prompt = block["A"]["prompt_tokens_est"]
        cs.append((block["C"]["prompt_tokens_est"] - a_prompt) / segments)
        bs.append((block["B"]["prompt_tokens_est"] - a_prompt + (block["B"].get("embedding_tokens") or 0)) / segments)
        glossary = load_glossary(doc)
        matched = [len(find_matching_terms(text, glossary)) for text, _ in load_segments(doc, 1600)]
        xs.append(sum(matched) / len(matched))
    return {"x": sum(xs) / len(xs), "c": sum(cs) / len(cs), "b": sum(bs) / len(bs)}


def main() -> int:
    rows = load_sweep()
    xs = [row["matches_per_segment"] for row in rows]
    b_prompt = [row["B_prompt_extra_per_segment"] for row in rows]
    b_total = [row["B_total_extra_per_segment"] for row in rows]
    c_total = [row["C_total_extra_per_segment"] for row in rows]
    measured = measured_point()

    fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=160)
    ax.fill_between(xs, b_prompt, b_total, color=COLOR_B, alpha=0.13, label="RAG 每段检索（embedding）开销")
    ax.plot(xs, b_total, color=COLOR_B, lw=2.6, marker="o", ms=4.5, label="向量 RAG（top-8，prompt + 检索）")
    ax.plot(xs, b_prompt, color=COLOR_B, lw=1.4, ls="--", alpha=0.8, label="RAG prompt 注入部分")
    ax.plot(xs, c_total, color=COLOR_C, lw=2.6, marker="s", ms=4.5, label="本项目（AC 命中注入）")

    slope = (c_total[-1] - c_total[0]) / (xs[-1] - xs[0])
    prompt_level = sum(b_prompt) / len(b_prompt)
    cross_prompt = prompt_level / slope if slope else None
    ax.axvline(cross_prompt, color=COLOR_TXT, lw=1, ls=":")
    ax.text(cross_prompt + 0.25, 30, "prompt 交叉 ≈ %.0f 个/段" % cross_prompt, fontsize=9, color=COLOR_TXT)

    ax.scatter([measured["x"]], [measured["c"]], s=95, color=COLOR_C, edgecolor="white", zorder=6)
    ax.scatter([measured["x"]], [measured["b"]], s=95, color=COLOR_B, edgecolor="white", zorder=6)
    ax.annotate(
        "实测：C ≈ %.0f，RAG ≈ %.0f token/段（3 文档 × 3 组 × 2 次）" % (measured["c"], measured["b"]),
        xy=(measured["x"], measured["b"]),
        xytext=(1.2, max(b_total) + 40),
        fontsize=8.5,
        color=COLOR_TXT,
        ha="left",
        arrowprops=dict(arrowstyle="->", color="#777777", lw=0.8, connectionstyle="arc3,rad=-0.15"),
    )

    ax.set_xlabel("每段命中的术语数（Aho-Corasick 命中，段长约 180 词）")
    ax.set_ylabel("每段额外输入 token（相对无词表基线）")
    ax.set_title("额外输入 token 对比：分段命中注入 vs 向量 RAG", fontsize=13, pad=12)
    ax.set_xlim(0, max(xs) + 1)
    ax.set_ylim(0, max(b_total) + 90)
    ax.grid(True, ls=":", alpha=0.35)

    top = ax.secondary_xaxis(
        "top",
        functions=(lambda value: value * 1000 / 180, lambda density: density * 180 / 1000),
    )
    top.set_xlabel("等效术语密度（每 1,000 源词出现次数，按 180 词/段折算）", fontsize=9)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=8.5, frameon=False)
    fig.text(
        0.01,
        0.005,
        "口径：prompt token 用 tiktoken 估算；RAG 每段一次 embedding 查询（约 260–360 token）；"
        "RAG 建库 token（约 1.4–1.6 万/份）未计入，按查询摊销。数据：eval/results/。",
        fontsize=7.2,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))

    out_png = EVAL_DIR / "results" / "cost_curve.png"
    out_svg = EVAL_DIR / "results" / "cost_curve.svg"
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    print("saved", out_png, out_svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
