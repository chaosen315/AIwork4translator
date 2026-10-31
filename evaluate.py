from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from modules.lightweight_evaluator import (
    NoEvaluationSamplesError,
    evaluate_samples,
    format_report_summary,
    load_config_from_json,
    prepare_evaluation_samples,
    write_evaluation_report,
)

load_dotenv(dotenv_path="data/.env")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="轻量自动评估器：对比两组翻译配置的质量代理与稳定性指标。")
    parser.add_argument("--input-dir", default="input_files", help="评测样本目录，默认 input_files")
    parser.add_argument("--provider", default="kimi", help="默认 Provider，未在配置文件中指定时生效")
    parser.add_argument("--baseline-config-file", help="基线配置 JSON 文件路径")
    parser.add_argument("--experiment-config-file", help="实验配置 JSON 文件路径")
    parser.add_argument("--baseline-name", default="baseline", help="未提供配置文件时的基线配置名")
    parser.add_argument("--experiment-name", default="experiment", help="未提供配置文件时的实验配置名")
    parser.add_argument("--repeat", type=int, default=2, help="每组配置重复测同一样本的次数，默认 2")
    parser.add_argument("--sample-limit", type=int, help="最多采样多少个文件")
    parser.add_argument("--segment-limit", type=int, help="每个样本最多评测多少段")
    parser.add_argument(
        "--bootstrap-from-seed",
        action="store_true",
        help="当 input_files 为空时，显式允许从 seed-dir 或默认 test_prompts 建立最小基线集",
    )
    parser.add_argument(
        "--seed-dir",
        help="与 --bootstrap-from-seed 配合使用的种子目录，默认 test_prompts",
    )
    parser.add_argument(
        "--safe-degrade",
        choices=["off", "auto", "on"],
        default="auto",
        help="API/网络不可用时是否退回受控降级结果，默认 auto",
    )
    parser.add_argument(
        "--output",
        default="comparison_results.csv",
        help="对比 CSV 输出路径，默认 comparison_results.csv",
    )
    parser.add_argument(
        "--details-json",
        default="comparison_results.json",
        help="详细 JSON 输出路径，默认 comparison_results.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        discovery = prepare_evaluation_samples(
            args.input_dir,
            sample_limit=args.sample_limit,
            bootstrap_from_test_prompts=args.bootstrap_from_seed,
            seed_dir=args.seed_dir,
        )
    except NoEvaluationSamplesError as exc:
        print(f"未执行评测：{exc}")
        return 2
    if discovery.bootstrap_message:
        print(discovery.bootstrap_message)
    samples = discovery.samples

    baseline_config = load_config_from_json(
        args.baseline_config_file,
        default_name=args.baseline_name,
        provider=args.provider,
        safe_degrade_mode=args.safe_degrade,
    )
    experiment_config = load_config_from_json(
        args.experiment_config_file,
        default_name=args.experiment_name,
        provider=args.provider,
        safe_degrade_mode=args.safe_degrade,
    )

    report = evaluate_samples(
        samples=samples,
        configs=[baseline_config, experiment_config],
        repeat_count=args.repeat,
        segment_limit=args.segment_limit,
    )
    write_evaluation_report(
        report=report,
        comparison_csv_path=args.output,
        details_json_path=args.details_json,
    )

    print(format_report_summary(report))
    print(f"对比结果已保存到 {args.output}")
    print(f"详细结果已保存到 {args.details_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
