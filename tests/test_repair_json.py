import json
import os
import types

import pytest

from modules.api_tool import LLMService


class FakeInvalidProvider:
    def generate_completion(self, prompt: str, system_prompt: str):
        # 返回包含花括号但非合法 JSON 的字符串，以触发 Invalid JSON 逻辑
        return "{translation: '你好', notes: []}", 0


class FakeValidProvider:
    def __init__(self, data):
        self._data = data

    def generate_completion(self, prompt: str, system_prompt: str):
        return json.dumps(self._data, ensure_ascii=False), 0


def _sample_valid_json():
    return {
        "translation": "你好，世界",
        "notes": ["术语1：注释", "术语2：注释"],
        "new_terms": [
            {"term": "Night City", "translation": "夜之城", "reason": "赛博朋克特定名词"}
        ],
    }


def test_repair_json_triggered_when_invalid_json(monkeypatch):
    # 保证结构化解析开启
    monkeypatch.setenv("STRUCTURED_OUTPUT", "True")
    # 避免在构造 KimiProvider 时因缺少 API Key 报错
    monkeypatch.setenv("KIMI_API_KEY", "test_key")

    llm_service = LLMService(provider="kimi")

    # 让首次调用返回非法 JSON，确保触发修复流程
    llm_service.Linkedprovider = FakeInvalidProvider()

    # 监视 repair_json 调用并返回一个固定的修复结果
    called = {"flag": False, "received": None}

    def spy_repair_json(origin_text: str):
        called["flag"] = True
        called["received"] = origin_text
        return {
            "translation": "修复后的译文",
            "notes": "- 术语1：注释\n- 术语2：注释",
            "new_terms": [],
        }

    monkeypatch.setattr(llm_service, "repair_json", spy_repair_json)

    response_obj, _ = llm_service.call_ai_model_api("dummy prompt")
    if response_obj.get("error") == "Invalid JSON format":
        response_obj = llm_service.repair_json(response_obj.get("origin_text", ""))

    assert called["flag"] is True
    assert isinstance(called["received"], str) and "{" in called["received"]
    assert response_obj.get("translation") == "修复后的译文"
    assert "- 术语1：注释" in response_obj.get("notes", "")


def test_repair_json_effective_with_valid_fix(monkeypatch):
    monkeypatch.setenv("STRUCTURED_OUTPUT", "True")
    monkeypatch.setenv("KIMI_API_KEY", "test_key")

    llm_service = LLMService(provider="kimi")

    fixed_json = _sample_valid_json()
    llm_service.Linkedprovider = FakeValidProvider(fixed_json)

    # 输入任意原始非法 JSON 文本，实际由 FakeValidProvider 返回的内容决定解析结果
    result = llm_service.repair_json("{translation: '坏的json'}")

    assert result.get("translation") == fixed_json["translation"]
    notes = result.get("notes", "")
    assert "- 术语1：注释" in notes and "- 术语2：注释" in notes
    newterms = result.get("new_terms", [])
    assert len(newterms) == 1
    assert newterms[0]["term"] == "Night City"
    assert newterms[0]["translation"] == "夜之城"
    assert newterms[0]["reason"] == "赛博朋克特定名词"
