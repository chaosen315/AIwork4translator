from __future__ import annotations

import csv
import json
import os
import re
import shutil
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

from modules.api_tool import LLMService
from modules.csv_process_tool import find_matching_terms, load_terms_dict, validate_csv_file
from modules.read_tool import read_structured_paragraphs

SUPPORTED_SAMPLE_SUFFIXES = {".md", ".markdown", ".txt"}
IGNORED_SAMPLE_MARKERS = (
    "_output",
    "_translated",
    "_intermediate",
)
DEFAULT_BASELINE_SEED_SAMPLE = "baseline_seed_test_samples.md"
DEFAULT_BASELINE_SEED_GLOSSARY = "baseline_seed_test_samples.csv"
VALID_SAFE_DEGRADE_MODES = {"off", "auto", "on"}


class NoEvaluationSamplesError(RuntimeError):
    """Raised when no usable evaluation samples can be discovered."""


@dataclass(frozen=True)
class EvaluationSample:
    path: str
    glossary_path: Optional[str] = None

    @property
    def sample_name(self) -> str:
        return Path(self.path).name


@dataclass(frozen=True)
class EvaluationConfig:
    name: str
    provider: str = "kimi"
    env_overrides: Optional[Dict[str, str]] = None
    preserve_structure: bool = False
    safe_degrade_mode: str = "auto"


@dataclass
class EvaluationRunResult:
    sample_path: str
    sample_name: str
    config_name: str
    repeat_index: int
    translation: str
    duration_seconds: float
    total_tokens: int
    source_word_count: int
    translated_word_count: int
    terminology_consistency: Optional[float]
    terminology_hits: int
    terminology_total: int
    structure_preservation: float
    quality_proxy: float
    error: Optional[str] = None
    degraded: bool = False
    degraded_reason: Optional[str] = None
    prefix_hashes: List[str] = field(default_factory=list)
    prefix_hash_unique_count: int = 0


@dataclass(frozen=True)
class SampleDiscoveryResult:
    samples: List[EvaluationSample]
    bootstrap_message: Optional[str] = None


@dataclass
class EvaluationReport:
    sample_count: int
    repeat_count: int
    comparison_rows: List[Dict[str, Any]]
    config_summaries: Dict[str, Dict[str, Any]]
    overall_summary: Dict[str, Any]
    raw_runs: List[EvaluationRunResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "repeat_count": self.repeat_count,
            "comparison_rows": self.comparison_rows,
            "config_summaries": self.config_summaries,
            "overall_summary": self.overall_summary,
            "raw_runs": [asdict(item) for item in self.raw_runs],
        }


RunSampleFunc = Callable[[EvaluationSample, EvaluationConfig, int, Optional[int]], EvaluationRunResult]


def discover_evaluation_samples(
    input_dir: str,
    sample_limit: Optional[int] = None,
    bootstrap_from_test_prompts: bool = False,
    seed_dir: Optional[str] = None,
) -> List[EvaluationSample]:
    return prepare_evaluation_samples(
        input_dir=input_dir,
        sample_limit=sample_limit,
        bootstrap_from_test_prompts=bootstrap_from_test_prompts,
        seed_dir=seed_dir,
    ).samples


def prepare_evaluation_samples(
    input_dir: str,
    sample_limit: Optional[int] = None,
    bootstrap_from_test_prompts: bool = False,
    seed_dir: Optional[str] = None,
) -> SampleDiscoveryResult:
    root = Path(input_dir)
    if not root.exists() or not root.is_dir():
        raise NoEvaluationSamplesError(f"评测输入目录不存在或不可用：{input_dir}")

    samples = _collect_evaluation_samples(root)
    bootstrap_message = None
    if not samples and bootstrap_from_test_prompts:
        bootstrap_message = _bootstrap_minimal_baseline_set(root, seed_dir=seed_dir)
        samples = _collect_evaluation_samples(root)

    if sample_limit is not None:
        samples = samples[: max(sample_limit, 0)]

    if not samples:
        if bootstrap_from_test_prompts:
            raise NoEvaluationSamplesError(
                f"`{input_dir}` 中没有可用评测样本，且无法从 `test_prompts/` 建立最小基线集。"
            )
        raise NoEvaluationSamplesError(
            f"`{input_dir}` 中没有可用评测样本；如需自动建立最小基线集，请显式启用 bootstrap 并提供 `--seed-dir`（或使用默认 `test_prompts/`）。"
        )
    return SampleDiscoveryResult(samples=samples, bootstrap_message=bootstrap_message)


def evaluate_samples(
    samples: List[EvaluationSample],
    configs: List[EvaluationConfig],
    repeat_count: int = 2,
    segment_limit: Optional[int] = None,
    run_sample: Optional[RunSampleFunc] = None,
) -> EvaluationReport:
    if len(configs) < 2:
        raise ValueError("至少需要两组配置进行对比。")
    if repeat_count < 1:
        raise ValueError("repeat_count 必须大于等于 1。")

    runner = run_sample or run_sample_with_llm
    raw_runs: List[EvaluationRunResult] = []
    grouped: Dict[str, Dict[str, List[EvaluationRunResult]]] = {}

    for sample in samples:
        sample_groups = grouped.setdefault(sample.path, {})
        for config in configs:
            config_runs = sample_groups.setdefault(config.name, [])
            for repeat_index in range(1, repeat_count + 1):
                result = runner(sample, config, repeat_index, segment_limit)
                raw_runs.append(result)
                config_runs.append(result)

    comparison_rows = build_comparison_rows(samples, configs, grouped)
    config_summaries = build_config_summaries(configs, raw_runs)
    overall_summary = build_overall_summary(configs, comparison_rows, config_summaries)

    return EvaluationReport(
        sample_count=len(samples),
        repeat_count=repeat_count,
        comparison_rows=comparison_rows,
        config_summaries=config_summaries,
        overall_summary=overall_summary,
        raw_runs=raw_runs,
    )


def write_evaluation_report(
    report: EvaluationReport,
    comparison_csv_path: str,
    details_json_path: Optional[str] = None,
) -> None:
    comparison_path = Path(comparison_csv_path)
    comparison_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sample_name",
        "sample_path",
        "baseline_config",
        "experiment_config",
        "baseline_quality_proxy",
        "experiment_quality_proxy",
        "quality_proxy_delta",
        "baseline_structure_preservation",
        "experiment_structure_preservation",
        "structure_preservation_delta",
        "baseline_terminology_consistency",
        "experiment_terminology_consistency",
        "terminology_consistency_delta",
        "baseline_repeat_similarity",
        "experiment_repeat_similarity",
        "repeat_similarity_delta",
        "baseline_prefix_hash_count",
        "experiment_prefix_hash_count",
        "baseline_unique_prefix_hash_count",
        "experiment_unique_prefix_hash_count",
        "baseline_prefix_hash_reuse_ratio",
        "experiment_prefix_hash_reuse_ratio",
        "prefix_hash_reuse_ratio_delta",
        "shared_prefix_hash_count",
        "prefix_hash_jaccard_similarity",
        "baseline_prefix_hashes",
        "experiment_prefix_hashes",
        "baseline_avg_tokens",
        "experiment_avg_tokens",
        "baseline_avg_duration_seconds",
        "experiment_avg_duration_seconds",
        "baseline_error_runs",
        "experiment_error_runs",
        "baseline_degraded_runs",
        "experiment_degraded_runs",
    ]
    with comparison_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.comparison_rows:
            writer.writerow({name: row.get(name) for name in fieldnames})

    if details_json_path:
        details_path = Path(details_json_path)
        details_path.parent.mkdir(parents=True, exist_ok=True)
        details_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def format_report_summary(report: EvaluationReport) -> str:
    baseline_name = report.overall_summary.get("baseline_config", "")
    experiment_name = report.overall_summary.get("experiment_config", "")
    lines = [
        f"评测样本数：{report.sample_count}",
        f"每组重复次数：{report.repeat_count}",
        f"基线配置：{baseline_name}",
        f"实验配置：{experiment_name}",
        f"安全降级运行次数：{report.overall_summary.get('total_degraded_runs', 0)}",
        f"质量代理均值变化：{_format_float(report.overall_summary.get('avg_quality_proxy_delta'))}",
        f"结构保持均值变化：{_format_float(report.overall_summary.get('avg_structure_preservation_delta'))}",
        f"术语一致性均值变化：{_format_float(report.overall_summary.get('avg_terminology_consistency_delta'))}",
        f"重复相似度均值变化：{_format_float(report.overall_summary.get('avg_repeat_similarity_delta'))}",
        f"Prefix Hash 复用率均值变化：{_format_float(report.overall_summary.get('avg_prefix_hash_reuse_ratio_delta'))}",
        f"Prefix Hash 重叠度均值：{_format_float(report.overall_summary.get('avg_prefix_hash_jaccard_similarity'))}",
    ]
    return "\n".join(lines)


def build_comparison_rows(
    samples: Iterable[EvaluationSample],
    configs: List[EvaluationConfig],
    grouped_runs: Dict[str, Dict[str, List[EvaluationRunResult]]],
) -> List[Dict[str, Any]]:
    baseline_config = configs[0]
    experiment_config = configs[1]
    rows: List[Dict[str, Any]] = []

    for sample in samples:
        sample_runs = grouped_runs.get(sample.path, {})
        baseline_summary = summarize_config_runs(sample_runs.get(baseline_config.name, []))
        experiment_summary = summarize_config_runs(sample_runs.get(experiment_config.name, []))
        baseline_prefix_hashes = baseline_summary["prefix_hashes"]
        experiment_prefix_hashes = experiment_summary["prefix_hashes"]
        shared_prefix_hash_count = len(
            set(baseline_prefix_hashes).intersection(experiment_summary["prefix_hashes"])
        )
        rows.append(
            {
                "sample_name": sample.sample_name,
                "sample_path": sample.path,
                "baseline_config": baseline_config.name,
                "experiment_config": experiment_config.name,
                "baseline_quality_proxy": baseline_summary["quality_proxy"],
                "experiment_quality_proxy": experiment_summary["quality_proxy"],
                "quality_proxy_delta": _safe_delta(
                    experiment_summary["quality_proxy"],
                    baseline_summary["quality_proxy"],
                ),
                "baseline_structure_preservation": baseline_summary["structure_preservation"],
                "experiment_structure_preservation": experiment_summary["structure_preservation"],
                "structure_preservation_delta": _safe_delta(
                    experiment_summary["structure_preservation"],
                    baseline_summary["structure_preservation"],
                ),
                "baseline_terminology_consistency": baseline_summary["terminology_consistency"],
                "experiment_terminology_consistency": experiment_summary["terminology_consistency"],
                "terminology_consistency_delta": _safe_delta(
                    experiment_summary["terminology_consistency"],
                    baseline_summary["terminology_consistency"],
                ),
                "baseline_repeat_similarity": baseline_summary["repeat_similarity"],
                "experiment_repeat_similarity": experiment_summary["repeat_similarity"],
                "repeat_similarity_delta": _safe_delta(
                    experiment_summary["repeat_similarity"],
                    baseline_summary["repeat_similarity"],
                ),
                "baseline_prefix_hash_count": baseline_summary["prefix_hash_count"],
                "experiment_prefix_hash_count": experiment_summary["prefix_hash_count"],
                "baseline_unique_prefix_hash_count": baseline_summary["unique_prefix_hash_count"],
                "experiment_unique_prefix_hash_count": experiment_summary["unique_prefix_hash_count"],
                "baseline_prefix_hash_reuse_ratio": baseline_summary["prefix_hash_reuse_ratio"],
                "experiment_prefix_hash_reuse_ratio": experiment_summary["prefix_hash_reuse_ratio"],
                "prefix_hash_reuse_ratio_delta": _safe_delta(
                    experiment_summary["prefix_hash_reuse_ratio"],
                    baseline_summary["prefix_hash_reuse_ratio"],
                ),
                "shared_prefix_hash_count": shared_prefix_hash_count,
                "prefix_hash_jaccard_similarity": _jaccard_similarity(
                    baseline_prefix_hashes,
                    experiment_prefix_hashes,
                ),
                "baseline_prefix_hashes": "|".join(baseline_prefix_hashes),
                "experiment_prefix_hashes": "|".join(experiment_prefix_hashes),
                "baseline_avg_tokens": baseline_summary["avg_tokens"],
                "experiment_avg_tokens": experiment_summary["avg_tokens"],
                "baseline_avg_duration_seconds": baseline_summary["avg_duration_seconds"],
                "experiment_avg_duration_seconds": experiment_summary["avg_duration_seconds"],
                "baseline_error_runs": baseline_summary["error_runs"],
                "experiment_error_runs": experiment_summary["error_runs"],
                "baseline_degraded_runs": baseline_summary["degraded_runs"],
                "experiment_degraded_runs": experiment_summary["degraded_runs"],
            }
        )
    return rows


def build_config_summaries(
    configs: List[EvaluationConfig],
    raw_runs: List[EvaluationRunResult],
) -> Dict[str, Dict[str, Any]]:
    summaries: Dict[str, Dict[str, Any]] = {}
    for config in configs:
        config_runs = [item for item in raw_runs if item.config_name == config.name]
        summaries[config.name] = summarize_config_runs(config_runs)
    return summaries


def build_overall_summary(
    configs: List[EvaluationConfig],
    comparison_rows: List[Dict[str, Any]],
    config_summaries: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    baseline_config = configs[0]
    experiment_config = configs[1]

    return {
        "baseline_config": baseline_config.name,
        "experiment_config": experiment_config.name,
        "avg_quality_proxy_delta": _mean(row["quality_proxy_delta"] for row in comparison_rows),
        "avg_structure_preservation_delta": _mean(
            row["structure_preservation_delta"] for row in comparison_rows
        ),
        "avg_terminology_consistency_delta": _mean(
            row["terminology_consistency_delta"] for row in comparison_rows
        ),
        "avg_repeat_similarity_delta": _mean(
            row["repeat_similarity_delta"] for row in comparison_rows
        ),
        "avg_prefix_hash_reuse_ratio_delta": _mean(
            row["prefix_hash_reuse_ratio_delta"] for row in comparison_rows
        ),
        "avg_prefix_hash_jaccard_similarity": _mean(
            row["prefix_hash_jaccard_similarity"] for row in comparison_rows
        ),
        "total_shared_prefix_hash_count": sum(
            int(row.get("shared_prefix_hash_count", 0) or 0) for row in comparison_rows
        ),
        "total_degraded_runs": sum(
            int(summary.get("degraded_runs", 0) or 0) for summary in config_summaries.values()
        ),
        "config_summaries": {
            baseline_config.name: config_summaries.get(baseline_config.name, {}),
            experiment_config.name: config_summaries.get(experiment_config.name, {}),
        },
    }


def summarize_config_runs(runs: List[EvaluationRunResult]) -> Dict[str, Any]:
    if not runs:
        return {
            "quality_proxy": None,
            "structure_preservation": None,
            "terminology_consistency": None,
            "repeat_similarity": None,
            "prefix_hash_count": 0,
            "unique_prefix_hash_count": 0,
            "prefix_hash_reuse_ratio": None,
            "prefix_hashes": [],
            "avg_tokens": None,
            "avg_duration_seconds": None,
            "error_runs": 0,
            "degraded_runs": 0,
            "unique_outputs": 0,
        }

    translations = [normalize_for_diff(item.translation) for item in runs if item.translation.strip()]
    term_scores = [item.terminology_consistency for item in runs if item.terminology_consistency is not None]
    prefix_hashes = _collect_prefix_hashes(runs)
    unique_prefix_hashes = sorted(set(prefix_hashes))

    return {
        "quality_proxy": _mean(item.quality_proxy for item in runs),
        "structure_preservation": _mean(item.structure_preservation for item in runs),
        "terminology_consistency": _mean(term_scores) if term_scores else None,
        "repeat_similarity": _pairwise_similarity(translations),
        "prefix_hash_count": len(prefix_hashes),
        "unique_prefix_hash_count": len(unique_prefix_hashes),
        "prefix_hash_reuse_ratio": _prefix_hash_reuse_ratio(prefix_hashes),
        "prefix_hashes": unique_prefix_hashes,
        "avg_tokens": _mean(item.total_tokens for item in runs),
        "avg_duration_seconds": _mean(item.duration_seconds for item in runs),
        "error_runs": sum(1 for item in runs if item.error),
        "degraded_runs": sum(1 for item in runs if item.degraded),
        "unique_outputs": len(set(translations)),
    }


def run_sample_with_llm(
    sample: EvaluationSample,
    config: EvaluationConfig,
    repeat_index: int,
    segment_limit: Optional[int] = None,
) -> EvaluationRunResult:
    source_text = Path(sample.path).read_text(encoding="utf-8")
    glossary_terms = load_terms_dict(sample.glossary_path) if sample.glossary_path else {}
    segments = _load_segments(sample.path, config.preserve_structure, segment_limit)
    started_at = time.perf_counter()
    total_tokens = 0
    translated_segments: List[str] = []
    matched_terms: Dict[str, Any] = {}
    safe_degrade_mode = _normalize_safe_degrade_mode(config.safe_degrade_mode)
    prefix_hashes: List[str] = []

    if safe_degrade_mode == "on":
        with temporary_env(config.env_overrides or {}):
            llm_service = LLMService(provider=config.provider)
            for segment in segments:
                segment_text = segment["content"]
                segment_terms = find_matching_terms(segment_text, glossary_terms) if glossary_terms else {}
                matched_terms.update(segment_terms)
                llm_service.create_prompt(segment_text, segment_terms)
                prompt_metadata = getattr(llm_service, "last_prompt_metadata", {}) or {}
                prefix_hash = str(prompt_metadata.get("prefix_hash", "")).strip()
                if prefix_hash:
                    prefix_hashes.append(prefix_hash)
        return _build_run_result(
            sample=sample,
            config=config,
            repeat_index=repeat_index,
            translation=_build_safe_degraded_translation(source_text, glossary_terms),
            duration_seconds=0.0,
            total_tokens=0,
            source_text=source_text,
            matched_terms=glossary_terms,
            error="safe degrade forced by config",
            degraded=True,
            degraded_reason="forced_safe_degrade",
            prefix_hashes=prefix_hashes,
        )

    try:
        with temporary_env(config.env_overrides or {}):
            llm_service = LLMService(provider=config.provider)
            for segment in segments:
                segment_text = segment["content"]
                segment_terms = find_matching_terms(segment_text, glossary_terms) if glossary_terms else {}
                matched_terms.update(segment_terms)
                prompt = llm_service.create_prompt(segment_text, segment_terms)
                prompt_metadata = getattr(llm_service, "last_prompt_metadata", {}) or {}
                prefix_hash = str(prompt_metadata.get("prefix_hash", "")).strip()
                if prefix_hash:
                    prefix_hashes.append(prefix_hash)
                response, usage_tokens = llm_service.call_ai_model_api(prompt)
                translated_segments.append(response.get("translation", "").strip())
                total_tokens += usage_tokens
    except Exception as exc:
        duration = time.perf_counter() - started_at
        degraded = safe_degrade_mode != "off"
        translation = _build_safe_degraded_translation(source_text, glossary_terms) if degraded else ""
        return _build_run_result(
            sample=sample,
            config=config,
            repeat_index=repeat_index,
            translation=translation,
            duration_seconds=duration,
            total_tokens=total_tokens,
            source_text=source_text,
            matched_terms=matched_terms or glossary_terms,
            error=str(exc),
            degraded=degraded,
            degraded_reason="llm_call_failed" if degraded else None,
            prefix_hashes=prefix_hashes,
        )

    duration = time.perf_counter() - started_at
    translation = "\n\n".join(part for part in translated_segments if part).strip()
    return _build_run_result(
        sample=sample,
        config=config,
        repeat_index=repeat_index,
        translation=translation,
        duration_seconds=duration,
        total_tokens=total_tokens,
        source_text=source_text,
        matched_terms=matched_terms,
        error=None,
        degraded=False,
        degraded_reason=None,
        prefix_hashes=prefix_hashes,
    )


def _build_run_result(
    sample: EvaluationSample,
    config: EvaluationConfig,
    repeat_index: int,
    translation: str,
    duration_seconds: float,
    total_tokens: int,
    source_text: str,
    matched_terms: Dict[str, Any],
    error: Optional[str],
    degraded: bool,
    degraded_reason: Optional[str],
    prefix_hashes: Optional[List[str]] = None,
) -> EvaluationRunResult:
    terminology_hits, terminology_total, terminology_consistency = compute_terminology_consistency(
        matched_terms, translation
    )
    structure_preservation = compute_structure_preservation(source_text, translation)
    quality_proxy = compute_quality_proxy(source_text, translation)
    materialized_prefix_hashes = [item for item in (prefix_hashes or []) if str(item).strip()]
    return EvaluationRunResult(
        sample_path=sample.path,
        sample_name=sample.sample_name,
        config_name=config.name,
        repeat_index=repeat_index,
        translation=translation,
        duration_seconds=duration_seconds,
        total_tokens=total_tokens,
        source_word_count=count_text_words(source_text),
        translated_word_count=count_text_words(translation),
        terminology_consistency=terminology_consistency,
        terminology_hits=terminology_hits,
        terminology_total=terminology_total,
        structure_preservation=structure_preservation,
        quality_proxy=quality_proxy,
        error=error,
        degraded=degraded,
        degraded_reason=degraded_reason,
        prefix_hashes=materialized_prefix_hashes,
        prefix_hash_unique_count=len(set(materialized_prefix_hashes)),
    )


def compute_terminology_consistency(
    matched_terms: Dict[str, Any],
    translation: str,
) -> tuple[int, int, Optional[float]]:
    if not matched_terms:
        return 0, 0, None

    normalized_translation = normalize_for_diff(translation)
    total = 0
    hits = 0
    for term_info in matched_terms.values():
        expected_translation = ""
        if isinstance(term_info, dict):
            expected_translation = str(term_info.get("translation", "")).strip()
        else:
            expected_translation = str(term_info).strip()
        if not expected_translation:
            continue
        total += 1
        if normalize_for_diff(expected_translation) in normalized_translation:
            hits += 1

    if total == 0:
        return 0, 0, None
    return hits, total, hits / total


def compute_structure_preservation(source_text: str, translation: str) -> float:
    source_signature = _extract_structure_signature(source_text)
    translation_signature = _extract_structure_signature(translation)
    dimensions = []
    for key, source_value in source_signature.items():
        target_value = translation_signature[key]
        if source_value == 0 and target_value == 0:
            dimensions.append(1.0)
            continue
        denominator = max(source_value, target_value, 1)
        dimensions.append(max(0.0, 1.0 - abs(source_value - target_value) / denominator))
    return _round_metric(_mean(dimensions))


def compute_quality_proxy(source_text: str, translation: str) -> float:
    normalized_source = normalize_for_diff(source_text)
    normalized_translation = normalize_for_diff(translation)
    if not normalized_translation:
        return 0.0

    non_empty_score = 1.0
    source_len = max(len(normalized_source), 1)
    translation_len = len(normalized_translation)
    length_ratio = translation_len / source_len
    length_score = max(0.0, 1.0 - abs(length_ratio - 1.0))
    copy_ratio = SequenceMatcher(None, normalized_source, normalized_translation).ratio()
    copy_score = 1.0 - copy_ratio
    return _round_metric(_mean([non_empty_score, length_score, copy_score]))


def count_text_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def normalize_for_diff(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def load_config_from_json(
    config_path: Optional[str],
    default_name: str,
    provider: str,
    safe_degrade_mode: str = "auto",
) -> EvaluationConfig:
    normalized_safe_degrade_mode = _normalize_safe_degrade_mode(safe_degrade_mode)
    if not config_path:
        return EvaluationConfig(
            name=default_name,
            provider=provider,
            env_overrides={},
            safe_degrade_mode=normalized_safe_degrade_mode,
        )

    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return EvaluationConfig(
        name=payload.get("name", default_name),
        provider=payload.get("provider", provider),
        env_overrides={str(k): str(v) for k, v in payload.get("env_overrides", {}).items()},
        preserve_structure=bool(payload.get("preserve_structure", False)),
        safe_degrade_mode=_normalize_safe_degrade_mode(
            str(payload.get("safe_degrade_mode", normalized_safe_degrade_mode))
        ),
    )


@contextmanager
def temporary_env(overrides: Dict[str, str]) -> Iterator[None]:
    original_values: Dict[str, Optional[str]] = {}
    for key, value in overrides.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, previous in original_values.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _discover_glossary_for_sample(sample_path: Path) -> Optional[str]:
    candidates = [
        sample_path.with_suffix(".csv"),
        sample_path.with_name(f"{sample_path.stem}_terms.csv"),
        sample_path.with_name(f"{sample_path.stem}_glossary.csv"),
        sample_path.with_name(f"{sample_path.stem}_output_terminology.csv"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        is_valid, updated_path = validate_csv_file(str(candidate))
        if is_valid:
            return updated_path
    return None


def _collect_evaluation_samples(root: Path) -> List[EvaluationSample]:
    samples: List[EvaluationSample] = []
    for file_path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue
        if file_path.suffix.lower() not in SUPPORTED_SAMPLE_SUFFIXES:
            continue
        lowered_stem = file_path.stem.lower()
        if any(marker in lowered_stem for marker in IGNORED_SAMPLE_MARKERS):
            continue
        samples.append(
            EvaluationSample(
                path=str(file_path),
                glossary_path=_discover_glossary_for_sample(file_path),
            )
        )
    return samples


def _bootstrap_minimal_baseline_set(input_dir: Path, seed_dir: Optional[str] = None) -> Optional[str]:
    resolved_seed_dir = Path(seed_dir) if seed_dir else Path(__file__).resolve().parent.parent / "test_prompts"
    sample_source = resolved_seed_dir / "test_samples.md"
    glossary_source = resolved_seed_dir / "test_terms.csv"
    if not sample_source.exists():
        return None

    input_dir.mkdir(parents=True, exist_ok=True)
    sample_dest = input_dir / DEFAULT_BASELINE_SEED_SAMPLE
    glossary_dest = input_dir / DEFAULT_BASELINE_SEED_GLOSSARY
    if not sample_dest.exists():
        shutil.copy2(sample_source, sample_dest)
    if glossary_source.exists() and not glossary_dest.exists():
        shutil.copy2(glossary_source, glossary_dest)

    return (
        f"`{input_dir}` 暂无样本，已复用 `{sample_source}` 建立最小基线集：`{sample_dest.name}`"
    )


def _load_segments(
    sample_path: str,
    preserve_structure: bool,
    segment_limit: Optional[int],
) -> List[Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    try:
        raw_segments = read_structured_paragraphs(
            sample_path,
            preserve_structure=preserve_structure,
        )
        for item in raw_segments:
            if isinstance(item, tuple):
                content, meta_data = item
            else:
                content, meta_data = item, {}
            if not str(content).strip():
                continue
            loaded.append({"content": str(content), "meta_data": meta_data or {}})
            if segment_limit is not None and len(loaded) >= segment_limit:
                break
    except Exception:
        raw_text = Path(sample_path).read_text(encoding="utf-8")
        if raw_text.strip():
            loaded = [{"content": raw_text, "meta_data": {}}]

    if not loaded:
        raw_text = Path(sample_path).read_text(encoding="utf-8")
        loaded = [{"content": raw_text, "meta_data": {}}]
    return loaded


def _build_safe_degraded_translation(source_text: str, glossary_terms: Dict[str, Any]) -> str:
    translated = source_text
    for source_term, term_info in sorted(
        glossary_terms.items(),
        key=lambda item: len(str(item[0])),
        reverse=True,
    ):
        expected_translation = ""
        if isinstance(term_info, dict):
            expected_translation = str(term_info.get("translation", "")).strip()
        else:
            expected_translation = str(term_info).strip()
        source_term = str(source_term).strip()
        if not source_term or not expected_translation:
            continue
        translated = re.sub(re.escape(source_term), expected_translation, translated, flags=re.IGNORECASE)
    return translated.strip()


def _extract_structure_signature(text: str) -> Dict[str, int]:
    return {
        "headings": len(re.findall(r"(?m)^#{1,6}\s+", text)),
        "bullet_lists": len(re.findall(r"(?m)^\s*[-*+]\s+", text)),
        "numbered_lists": len(re.findall(r"(?m)^\s*\d+\.\s+", text)),
        "tables": len(re.findall(r"(?m)^\|.+\|\s*$", text)),
        "code_fences": len(re.findall(r"(?m)^```", text)),
        "blockquotes": len(re.findall(r"(?m)^>\s?", text)),
    }


def _pairwise_similarity(texts: List[str]) -> Optional[float]:
    if not texts:
        return None
    if len(texts) == 1:
        return 1.0

    scores: List[float] = []
    for idx, left in enumerate(texts):
        for right in texts[idx + 1 :]:
            scores.append(SequenceMatcher(None, left, right).ratio())
    return _round_metric(_mean(scores))


def _collect_prefix_hashes(runs: List[EvaluationRunResult]) -> List[str]:
    return [
        prefix_hash
        for item in runs
        for prefix_hash in item.prefix_hashes
        if str(prefix_hash).strip()
    ]


def _prefix_hash_reuse_ratio(prefix_hashes: List[str]) -> Optional[float]:
    if not prefix_hashes:
        return None
    unique_count = len(set(prefix_hashes))
    reused_count = len(prefix_hashes) - unique_count
    return _round_metric(reused_count / len(prefix_hashes))


def _jaccard_similarity(left: List[str], right: List[str]) -> Optional[float]:
    left_set = {item for item in left if str(item).strip()}
    right_set = {item for item in right if str(item).strip()}
    if not left_set and not right_set:
        return None
    union = left_set.union(right_set)
    if not union:
        return None
    return _round_metric(len(left_set.intersection(right_set)) / len(union))


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    materialized = [float(value) for value in values if value is not None]
    if not materialized:
        return None
    return _round_metric(sum(materialized) / len(materialized))


def _safe_delta(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None:
        return None
    return _round_metric(current - previous)


def _round_metric(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 4)


def _format_float(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _normalize_safe_degrade_mode(mode: str) -> str:
    normalized = (mode or "auto").strip().lower()
    if normalized not in VALID_SAFE_DEGRADE_MODES:
        raise ValueError(
            f"safe_degrade_mode 仅支持 {sorted(VALID_SAFE_DEGRADE_MODES)}，当前为 `{mode}`"
        )
    return normalized
