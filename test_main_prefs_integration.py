import os
import json
import csv
import importlib
import pytest


class FakeLLMService:
    calls = []
    def __init__(self, provider="kimi"):
        self.provider = provider
        self.providers = {"kimi": None}
        FakeLLMService.calls.append(provider)
    def create_prompt(self, paragraph, terms):
        return "prompt"
    def call_ai_model_api(self, prompt):
        return {"translation": "ok", "new_terms": [], "notes": ""}, 1
    def test_api(self):
        return {"success": True}


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)


def test_main_prefs_roundtrip(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    md = tmp_path / "doc.md"
    md.write_text("hello", encoding="utf-8")
    csvp = tmp_path / "terms.csv"
    write_csv(csvp, [["term","definition"],["outlaw","法外之徒"]])

    monkeypatch.setattr("modules.api_tool.LLMService", FakeLLMService)
    monkeypatch.setattr("modules.config.global_config", type("CFG", (), {"preserve_structure": False, "max_chunk_size": 1024})())
    monkeypatch.setattr("modules.read_tool.read_structured_paragraphs", lambda *a, **k: ["p"]) 
    monkeypatch.setattr("modules.count_tool.count_structured_paragraphs", lambda *a, **k: 1)
    monkeypatch.setattr("modules.count_tool.count_md_words", lambda *a, **k: 1)
    def _write_to_markdown(path, payload, mode='flat'):
        if mode == 'structured':
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(payload[0]))
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(payload[0]))
    monkeypatch.setattr("modules.write_out_tool.write_to_markdown", _write_to_markdown)
    monkeypatch.setattr("modules.csv_process_tool.find_matching_terms", lambda p, t: {})

    inputs = iter(["kimi", str(md), "y", str(csvp), "y", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    import main as mainmod
    importlib.reload(mainmod)
    mainmod.main()

    prefs_path = tmp_path / "data" / ".prefs.json"
    assert prefs_path.exists()
    prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
    assert prefs["last_provider"] == "kimi"
    assert prefs["last_input_md_file"] == str(md)
    assert prefs["last_csv_path"] == str(csvp)

    inputs2 = iter(["", "", "y", "", "y", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs2))
    importlib.reload(mainmod)
    mainmod.main()

    prefs2 = json.loads(prefs_path.read_text(encoding="utf-8"))
    assert prefs2["last_provider"] == "kimi"
    assert prefs2["last_input_md_file"] == str(md)
    assert prefs2["last_csv_path"] == str(csvp)
    assert FakeLLMService.calls[-1] == "kimi"
