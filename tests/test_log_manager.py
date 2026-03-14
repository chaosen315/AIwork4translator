import json
import os
import pytest
from modules.log_manager import TranslationLogManager

@pytest.fixture
def blueprint_file(tmp_path):
    data = {
        "text_info": [
            {"paragraph_number": 1, "content": "p1"},
            {"paragraph_number": 2, "content": "p2"},
            {"paragraph_number": 3, "content": "p3"}
        ]
    }
    path = tmp_path / "test_intermediate.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return str(path)

def test_log_path_generation(blueprint_file):
    manager = TranslationLogManager(blueprint_file)
    expected = blueprint_file.replace("_intermediate.json", "_translation_log.jsonl")
    assert manager.log_path == expected

def test_append_and_replay(blueprint_file):
    manager = TranslationLogManager(blueprint_file)
    
    # Append
    manager.append_log(1, {"translation": "t1"})
    manager.append_log(3, {"translation": "t3"})
    
    # Replay
    updates = manager.replay_logs()
    assert len(updates) == 2
    assert updates[1]["translation"] == "t1"
    assert updates[3]["translation"] == "t3"
    assert 2 not in updates

def test_get_preview_content(blueprint_file):
    manager = TranslationLogManager(blueprint_file)
    
    # Initial preview (empty)
    with open(blueprint_file, 'r') as f:
        blueprint_data = json.load(f)
    
    preview = manager.get_preview_content(blueprint_data)
    assert preview == "" # No translations yet
    
    # Add logs
    manager.append_log(1, {"translation": "Translated 1", "notes": ""})
    manager.append_log(2, {"translation": "Translated 2", "notes": "Note 2"})
    
    # Preview again
    preview = manager.get_preview_content(blueprint_data)
    assert "Translated 1" in preview
    assert "Translated 2" in preview
    assert "Note 2" in preview
    # Verify order and formatting (simple join for now)
    assert preview.startswith("Translated 1")
    assert "Translated 2\n\n---\n\nNote 2" in preview
