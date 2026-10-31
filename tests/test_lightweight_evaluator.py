from pathlib import Path

from evaluate import main as evaluate_main
from modules.lightweight_evaluator import (
    EvaluationConfig,
    EvaluationSample,
    EvaluationRunResult,
    NoEvaluationSamplesError,
    compute_quality_proxy,
    compute_structure_preservation,
    compute_terminology_consistency,
    count_text_words,
    discover_evaluation_samples,
    evaluate_samples,
    prepare_evaluation_samples,
    run_sample_with_llm,
    write_evaluation_report,
)


def test_discover_evaluation_samples_pairs_glossary_and_ignores_outputs(tmp_path):
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()
    (input_dir / "sample.md").write_text("# Title\n\nNight City", encoding="utf-8")
    (input_dir / "sample.csv").write_text(
        "term,translation\nNight City,夜之城\n",
        encoding="utf-8",
    )
    (input_dir / "sample_output.md").write_text("ignored", encoding="utf-8")
    (input_dir / "sample_intermediate.md").write_text("ignored", encoding="utf-8")

    samples = discover_evaluation_samples(str(input_dir))

    assert len(samples) == 1
    assert Path(samples[0].path).name == "sample.md"
    assert samples[0].glossary_path is not None
    assert Path(samples[0].glossary_path).name == "sample.csv"


def test_prepare_evaluation_samples_bootstraps_minimal_baseline_set_when_input_dir_is_empty(tmp_path):
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()
    seed_dir = tmp_path / "test_prompts"
    seed_dir.mkdir()
    (seed_dir / "test_samples.md").write_text("# Seed\n\nNight City", encoding="utf-8")
    (seed_dir / "test_terms.csv").write_text(
        "term,translation\nNight City,夜之城\n",
        encoding="utf-8",
    )

    discovery = prepare_evaluation_samples(
        str(input_dir),
        bootstrap_from_test_prompts=True,
        seed_dir=str(seed_dir),
    )

    assert len(discovery.samples) == 1
    assert discovery.bootstrap_message is not None
    assert "最小基线集" in discovery.bootstrap_message
    assert (input_dir / "baseline_seed_test_samples.md").exists()
    assert (input_dir / "baseline_seed_test_samples.csv").exists()


def test_prepare_evaluation_samples_exits_safely_by_default_when_input_dir_is_empty(tmp_path):
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()

    try:
        prepare_evaluation_samples(str(input_dir))
    except NoEvaluationSamplesError as exc:
        assert "显式启用 bootstrap" in str(exc)
    else:
        raise AssertionError("empty input_dir should not auto-bootstrap by default")


def test_run_sample_with_llm_uses_safe_degrade_result_on_api_error(monkeypatch, tmp_path):
    sample_path = tmp_path / "story.md"
    sample_path.write_text("# Title\n\nNight City arrives.\n", encoding="utf-8")
    glossary_path = tmp_path / "story.csv"
    glossary_path.write_text("term,translation\nNight City,夜之城\n", encoding="utf-8")

    class FailingLLMService:
        def __init__(self, provider: str = "kimi"):
            self.provider = provider

        def create_prompt(self, paragraph, terms_dict):
            return "prompt"

        def call_ai_model_api(self, prompt):
            raise RuntimeError("network down")

    monkeypatch.setattr("modules.lightweight_evaluator.LLMService", FailingLLMService)

    result = run_sample_with_llm(
        EvaluationSample(path=str(sample_path), glossary_path=str(glossary_path)),
        EvaluationConfig(name="baseline", provider="kimi", safe_degrade_mode="auto"),
        repeat_index=1,
    )

    assert result.degraded is True
    assert result.degraded_reason == "llm_call_failed"
    assert result.error == "network down"
    assert "夜之城" in result.translation


def test_evaluate_main_exits_safely_when_input_dir_is_empty_by_default(tmp_path, capsys):
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()

    exit_code = evaluate_main(["--input-dir", str(input_dir)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "未执行评测" in captured.out
    assert "显式启用 bootstrap" in captured.out


def test_evaluate_main_bootstraps_and_writes_comparison_report(tmp_path, capsys, monkeypatch):
    # 评测器在 safe_degrade=on 下也会构造 LLMService；这里给出占位 Key，
    # 让测试不依赖本机 data/.env（干净 checkout 也必须能跑）。
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()
    seed_dir = tmp_path / "test_prompts"
    seed_dir.mkdir()
    (seed_dir / "test_samples.md").write_text("# Seed\n\nNight City", encoding="utf-8")
    (seed_dir / "test_terms.csv").write_text(
        "term,translation\nNight City,夜之城\n",
        encoding="utf-8",
    )
    baseline_config = tmp_path / "baseline.json"
    baseline_config.write_text(
        '{"name":"baseline","provider":"kimi","safe_degrade_mode":"on"}',
        encoding="utf-8",
    )
    experiment_config = tmp_path / "experiment.json"
    experiment_config.write_text(
        '{"name":"experiment","provider":"kimi","preserve_structure":true,"safe_degrade_mode":"on"}',
        encoding="utf-8",
    )
    csv_path = tmp_path / "comparison.csv"
    json_path = tmp_path / "comparison.json"

    exit_code = evaluate_main(
        [
            "--input-dir",
            str(input_dir),
            "--bootstrap-from-seed",
            "--seed-dir",
            str(seed_dir),
            "--baseline-config-file",
            str(baseline_config),
            "--experiment-config-file",
            str(experiment_config),
            "--safe-degrade",
            "on",
            "--output",
            str(csv_path),
            "--details-json",
            str(json_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "最小基线集" in captured.out
    assert "安全降级运行次数" in captured.out
    assert csv_path.exists()
    assert json_path.exists()
    assert "baseline_config" in csv_path.read_text(encoding="utf-8-sig")
    assert '"total_degraded_runs"' in json_path.read_text(encoding="utf-8")
    assert "baseline_prefix_hash_reuse_ratio" in csv_path.read_text(encoding="utf-8-sig")
    assert '"avg_prefix_hash_jaccard_similarity"' in json_path.read_text(encoding="utf-8")


def test_evaluate_samples_compares_two_configs_and_writes_report(tmp_path):
    input_dir = tmp_path / "input_files"
    input_dir.mkdir()
    sample_path = input_dir / "story.md"
    sample_path.write_text("# Title\n\nNight City arrives.\n", encoding="utf-8")
    glossary_path = input_dir / "story.csv"
    glossary_path.write_text("term,translation\nNight City,夜之城\n", encoding="utf-8")

    samples = discover_evaluation_samples(str(input_dir))
    configs = [
        EvaluationConfig(name="baseline", provider="kimi"),
        EvaluationConfig(name="experiment", provider="kimi"),
    ]

    def fake_runner(sample, config, repeat_index, segment_limit):
        source_text = Path(sample.path).read_text(encoding="utf-8")
        matched_terms = {"Night City": {"translation": "夜之城"}}
        if config.name == "baseline":
            translation = "Night City arrives." if repeat_index == 1 else "Night City is coming."
            tokens = 120
        else:
            translation = "# 标题\n\n夜之城来了。"
            tokens = 90

        term_hits, term_total, term_consistency = compute_terminology_consistency(matched_terms, translation)
        return EvaluationRunResult(
            sample_path=sample.path,
            sample_name=Path(sample.path).name,
            config_name=config.name,
            repeat_index=repeat_index,
            translation=translation,
            duration_seconds=0.2 if config.name == "experiment" else 0.3,
            total_tokens=tokens,
            source_word_count=count_text_words(source_text),
            translated_word_count=count_text_words(translation),
            terminology_consistency=term_consistency,
            terminology_hits=term_hits,
            terminology_total=term_total,
            structure_preservation=compute_structure_preservation(source_text, translation),
            quality_proxy=compute_quality_proxy(source_text, translation),
            error=None,
            prefix_hashes=(
                ["baseline-shared"]
                if config.name == "baseline"
                else [f"experiment-structure-{repeat_index}", f"experiment-json-{repeat_index}"]
            ),
        )

    report = evaluate_samples(
        samples=samples,
        configs=configs,
        repeat_count=2,
        run_sample=fake_runner,
    )

    assert report.sample_count == 1
    assert report.overall_summary["avg_terminology_consistency_delta"] == 1.0
    assert report.overall_summary["avg_repeat_similarity_delta"] > 0
    assert report.overall_summary["avg_prefix_hash_reuse_ratio_delta"] < 0
    assert report.overall_summary["avg_prefix_hash_jaccard_similarity"] == 0.0
    assert report.config_summaries["baseline"]["unique_prefix_hash_count"] == 1
    assert report.comparison_rows[0]["experiment_avg_tokens"] < report.comparison_rows[0]["baseline_avg_tokens"]
    assert report.comparison_rows[0]["baseline_prefix_hash_reuse_ratio"] == 0.5
    assert report.comparison_rows[0]["experiment_prefix_hash_reuse_ratio"] == 0.0
    assert report.comparison_rows[0]["shared_prefix_hash_count"] == 0

    csv_path = tmp_path / "comparison_results.csv"
    json_path = tmp_path / "comparison_results.json"
    write_evaluation_report(report, str(csv_path), str(json_path))

    assert csv_path.exists()
    assert json_path.exists()
    assert "story.md" in csv_path.read_text(encoding="utf-8-sig")
    assert '"avg_repeat_similarity_delta"' in json_path.read_text(encoding="utf-8")
    assert "baseline_prefix_hashes" in csv_path.read_text(encoding="utf-8-sig")
    assert '"prefix_hashes"' in json_path.read_text(encoding="utf-8")
