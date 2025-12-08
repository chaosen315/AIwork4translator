import os
import sys
import csv
import json
import importlib
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class FakeLLMService:
    def __init__(self, provider):
        self.provider = provider
    def create_prompt(self, paragraph, terms):
        return "prompt"
    def call_ai_model_api(self, prompt):
        # Return success on first try
        return {"translation": "译文", "notes": "", "newterminology": []}, 100
    def repair_json(self, text):
        return {"translation": "修复译文", "notes": "", "newterminology": []}
    def test_api(self):
        return {"success": True}

def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)

def test_dashboard_columns(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    md = tmp_path / "doc.md"
    md.write_text("Paragraph 1\n\nParagraph 2", encoding="utf-8")
    csvp = tmp_path / "terms.csv"
    write_csv(csvp, [["term","definition"],["outlaw","法外之徒"]])

    # Mock dependencies
    monkeypatch.setattr("modules.api_tool.LLMService", FakeLLMService)
    monkeypatch.setattr("modules.config.global_config", type("CFG", (), {"preserve_structure": False, "max_chunk_size": 1024})())
    
    # Mock read/count/write tools
    monkeypatch.setattr("modules.read_tool.read_structured_paragraphs", lambda *a, **k: ["Paragraph 1"]) 
    monkeypatch.setattr("modules.count_tool.count_structured_paragraphs", lambda *a, **k: 1)
    monkeypatch.setattr("modules.count_tool.count_md_words", lambda *a, **k: 10)
    
    def _write_to_markdown(path, payload, mode='flat'):
        pass
    monkeypatch.setattr("modules.write_out_tool.write_to_markdown", _write_to_markdown)
    
    # Mock find_matching_terms to simulate delay if needed, or just return empty
    monkeypatch.setattr("modules.csv_process_tool.find_matching_terms", lambda p, t: {})

    # Mock input to run through the CLI flow
    # Inputs: provider, md file, has_glossary(y), glossary path, merge(n)
    inputs = iter(["kimi", str(md), "y", str(csvp), "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    import main as mainmod
    importlib.reload(mainmod)
    
    # Run main
    mainmod.main()

    # Find the dashboard CSV
    # It follows naming: {base_name}_{timestamp}_dashboard.csv
    # base_name of "doc.md" is "doc"
    files = list(tmp_path.glob("doc_*_dashboard.csv"))
    assert len(files) == 1
    dashboard_csv = files[0]

    # Check content
    with open(dashboard_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    # Check Header
    expected_header = [
        'Paragraph_ID', 
        'Term_Matching_Time_s', 
        'Total_API_Time_s', 
        'Pure_API_Time_s', 
        'JSON_Repair_Time_s', 
        'Retry_Count', 
        'Token_Usage', 
        'Timestamp'
    ]
    assert rows[0] == expected_header
    
    # Check Data Row
    # We processed 1 paragraph
    assert len(rows) == 2
    data = rows[1]
    assert data[0] == "1" # Paragraph_ID
    # Time columns should be floats
    assert float(data[1]) >= 0 # Term Matching
    assert float(data[2]) >= 0 # Total API
    assert float(data[3]) >= 0 # Pure API
    assert float(data[4]) >= 0 # Repair Time
    assert int(data[5]) == 0   # Retry Count (should be 0 for success)
    assert int(data[6]) == 100 # Token Usage
    # Timestamp is string
