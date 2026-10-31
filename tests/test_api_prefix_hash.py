import json
import logging

from modules.api_tool import LLMService


class FakeProvider:
    def generate_completion(self, prompt: str, system_prompt: str):
        payload = {"translation": "译文", "new_terms": []}
        return json.dumps(payload, ensure_ascii=False), 12


def test_prefix_hash_stays_stable_for_equivalent_glossary(monkeypatch):
    monkeypatch.setenv("STRUCTURED_OUTPUT", "True")
    monkeypatch.setenv("KIMI_API_KEY", "test_key")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("BASE_PROMPT", "\n请输出 JSON")

    service = LLMService(provider="kimi")
    terms_a = {
        "Night  City": {"translation": " 夜之城 ", "reason": "赛博，朋克"},
        "Night City": {"translation": "夜之城", "reason": "赛博, 朋克"},
        "the Outlaw": {"translation": "法外之徒", "reason": "常见：阵营名"},
    }
    terms_b = {
        "the Outlaw": {"translation": "法外之徒", "reason": "常见: 阵营名"},
        "Night City": {"translation": "夜之城", "reason": "赛博, 朋克"},
    }

    prompt_a = service.build_prompt_parts("Paragraph A", terms_a)
    prompt_b = service.build_prompt_parts("Paragraph B", terms_b)

    assert prompt_a["metadata"]["prefix_hash"] == prompt_b["metadata"]["prefix_hash"]
    assert prompt_a["prompt_prefix"] == prompt_b["prompt_prefix"]
    assert prompt_a["paragraph_body"] != prompt_b["paragraph_body"]


def test_prefix_hash_changes_when_stable_prefix_changes(monkeypatch):
    monkeypatch.setenv("STRUCTURED_OUTPUT", "True")
    monkeypatch.setenv("KIMI_API_KEY", "test_key")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("BASE_PROMPT", "\n请输出 JSON")

    service = LLMService(provider="kimi")
    baseline = service.build_prompt_parts("Paragraph", {"Night City": "夜之城"})

    monkeypatch.setenv("BASE_PROMPT", "\n请严格输出 JSON")
    changed_service = LLMService(provider="kimi")
    changed = changed_service.build_prompt_parts("Paragraph", {"Night City": "夜之城"})

    assert baseline["metadata"]["prefix_hash"] != changed["metadata"]["prefix_hash"]


def test_call_ai_model_api_logs_prefix_hash(monkeypatch, caplog):
    monkeypatch.setenv("STRUCTURED_OUTPUT", "True")
    monkeypatch.setenv("KIMI_API_KEY", "test_key")
    monkeypatch.setenv("SYSTEM_PROMPT", "system prompt")
    monkeypatch.setenv("BASE_PROMPT", "\n请输出 JSON")

    service = LLMService(provider="kimi")
    service.Linkedprovider = FakeProvider()
    prompt = service.create_prompt("Hello", {"Night City": "夜之城"})

    with caplog.at_level(logging.INFO):
        result, tokens = service.call_ai_model_api(prompt)

    assert result["translation"] == "译文"
    assert tokens == 12
    assert service.last_prefix_hash
    joined = "\n".join(caplog.messages)
    assert "provider=kimi" in joined
    assert f"prefix_hash={service.last_prefix_hash}" in joined
    assert "structured=True" in joined
