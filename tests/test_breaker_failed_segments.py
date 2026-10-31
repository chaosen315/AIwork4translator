import asyncio
import json

from modules.translation_core import TranslationResult
from services.diagnostics import global_diagnostics

import main as mainmod


class _FailingCore:
    def __init__(self):
        self.llm_service = self

    async def execute_translation_step(self, segment, terms, aggregated, **kwargs):
        return TranslationResult(
            content="",
            notes="",
            tokens=0,
            repair_tokens=0,
            new_terms_delta=[],
            matched_terms_delta=[],
            header_path=[],
            success=False,
            error="boom",
        )

    def test_api(self):
        return {"success": True}


def _write_blueprint(path, paragraph_count=5):
    data = {
        "text_info": [
            {
                "paragraph_number": index + 1,
                "content": f"paragraph {index + 1}",
                "meta_data": {"header_path": ["# Title"]},
                "translation": "",
                "notes": "",
                "new_terms": [],
                "status": "pending",
            }
            for index in range(paragraph_count)
        ]
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_breaker_moves_unprocessed_paragraphs_into_failed_segments(tmp_path, monkeypatch):
    """熔断后队列里未处理的段落必须进入失败清单，成品标记 partial。"""
    global_diagnostics.set_global_error_state(False, "")

    monkeypatch.setenv("MAX_RETRIES", "1")
    monkeypatch.setenv("PARAGRAPH_MAX_RETRIES", "1")
    monkeypatch.setenv("Currency_Limit", "1")
    monkeypatch.setenv("Requests_Per_Minute", "1")

    blueprint = tmp_path / "doc_intermediate.json"
    _write_blueprint(blueprint, 5)
    output_md = tmp_path / "doc_output.md"

    paragraphs = [
        {
            "paragraph_number": index + 1,
            "content": f"paragraph {index + 1}",
            "meta_data": {"header_path": ["# Title"]},
            "status": "pending",
        }
        for index in range(5)
    ]

    asyncio.run(
        mainmod.run_translation_loop(
            paragraphs,
            _FailingCore(),
            {},
            [],
            str(output_md),
            True,
            json_path=str(blueprint),
        )
    )

    data = json.loads(blueprint.read_text(encoding="utf-8"))
    assert data["translation_status"] == "partial"
    assert len(data["failed_segments"]) == 5
    assert "部分完成" in output_md.read_text(encoding="utf-8")

    global_diagnostics.set_global_error_state(False, "")
