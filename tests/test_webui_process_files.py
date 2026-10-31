import asyncio
import json
from types import SimpleNamespace

import app as webapp


class _FakeLLMService:
    def __init__(self, *args, **kwargs):
        self.provider = "kimi"

    def test_api(self):
        return {"success": True}


class _FakeTranslationCore:
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.calls = 0

    async def execute_translation_step(self, segment, terms, aggregated, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            success=True,
            content=f"译:{segment['content']}",
            notes="",
            tokens=1,
            new_terms_delta=[],
            matched_terms_delta=[],
            error=None,
        )


class _FailingTranslationCore:
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def execute_translation_step(self, segment, terms, aggregated, **kwargs):
        raise RuntimeError("boom")


def _prepare_blueprint(tmp_path, monkeypatch, paragraph_count=2):
    md = tmp_path / "doc.md"
    md.write_text("# Title\n\nhello world\n", encoding="utf-8")
    csv_path = tmp_path / "terms.csv"
    csv_path.write_text("term,translation\nhello,你好\n", encoding="utf-8")
    blueprint = tmp_path / "doc_intermediate.json"
    blueprint.write_text(
        json.dumps(
            {
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
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(webapp, "LLMService", _FakeLLMService)
    monkeypatch.setattr(webapp, "TranslationCore", _FakeTranslationCore)
    monkeypatch.setattr(
        webapp,
        "read_and_process_structured_paragraphs_to_json",
        lambda *args, **kwargs: str(blueprint),
    )
    monkeypatch.setattr(webapp, "load_terms_dict", lambda path: {})
    monkeypatch.setattr(webapp, "PS", True)
    return md, csv_path, blueprint


def test_process_files_reads_blueprint_json(tmp_path, monkeypatch):
    """回归：process_files 必须能读取蓝图 JSON。

    2026-10-31 之前 app.py 缺少 `import json`，这里会在 json.load 处抛 NameError，
    导致 WebUI 的每一次翻译任务都落到 error 状态。
    """
    md, csv_path, _ = _prepare_blueprint(tmp_path, monkeypatch)

    result = asyncio.run(webapp.process_files(str(md), str(csv_path), "kimi"))

    assert result["status"] == "success"
    output = tmp_path / "doc_output.md"
    assert output.exists()
    assert "译:paragraph 1" in output.read_text(encoding="utf-8")


def test_process_files_marks_partial_and_writes_warning(tmp_path, monkeypatch):
    """失败段必须进入最终 Markdown 的 WARNING 摘要，并把状态标成 partial。"""
    md, csv_path, _ = _prepare_blueprint(tmp_path, monkeypatch)
    monkeypatch.setattr(webapp, "TranslationCore", _FailingTranslationCore)

    result = asyncio.run(webapp.process_files(str(md), str(csv_path), "kimi"))

    assert result["translation_status"] == "partial"
    assert len(result["failed_segments"]) == 2
    text = (tmp_path / "doc_output.md").read_text(encoding="utf-8")
    assert "部分完成" in text
    assert "未完成段落清单" in text


def test_process_files_breaker_finalizes_before_returning_error(tmp_path, monkeypatch):
    """连续失败达到上限时，必须先 finalize 出「部分完成」产物，再返回 error。"""
    md, csv_path, _ = _prepare_blueprint(tmp_path, monkeypatch, paragraph_count=3)
    monkeypatch.setattr(webapp, "TranslationCore", _FailingTranslationCore)

    result = asyncio.run(webapp.process_files(str(md), str(csv_path), "kimi"))

    assert result["status"] == "error"
    assert result["output_file"].endswith("doc_output.md")
    assert len(result["failed_segments"]) == 3
    text = (tmp_path / "doc_output.md").read_text(encoding="utf-8")
    assert "部分完成" in text
