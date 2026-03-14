import json
import os
import pytest
from modules.write_out_tool import finalize_translation_output, TranslationLogManager

@pytest.fixture
def blueprint_file(tmp_path):
    data = {
        "text_info": [
            {
                "paragraph_number": 1, 
                "content": "Original 1", 
                "translation": "", 
                "status": "pending",
                "meta_data": {"header_path": ["# Header 1"]}
            },
            {
                "paragraph_number": 2, 
                "content": "Original 2", 
                "translation": "", 
                "status": "pending",
                "meta_data": {"header_path": ["# Header 1", "## Subheader"]}
            }
        ]
    }
    path = tmp_path / "test_finalize_intermediate.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return str(path)

def test_finalize_flow(blueprint_file, tmp_path):
    md_path = tmp_path / "final_output.md"
    
    # 1. Create logs
    manager = TranslationLogManager(blueprint_file)
    manager.append_log(1, {
        "translation": "Translated 1", 
        "notes": "Note 1",
        "new_terms": [],
        "matched_terms": []
    })
    manager.append_log(2, {
        "translation": "Translated 2", 
        "notes": "",
        "new_terms": [],
        "matched_terms": []
    })
    
    # 2. Call finalize
    finalize_translation_output(blueprint_file, str(md_path), mode="structured")
    
    # 3. Verify MD
    assert os.path.exists(md_path)
    content = md_path.read_text(encoding="utf-8")
    
    # Check headers and content
    assert "# Header 1" in content
    assert "Translated 1" in content
    assert "Note 1" in content
    assert "## Subheader" in content
    assert "Translated 2" in content
    
    # 4. Verify JSON update
    with open(blueprint_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    p1 = data['text_info'][0]
    assert p1['status'] == 'completed'
    assert p1['translation'] == "Translated 1"
    assert p1['notes'] == "Note 1"
    
    p2 = data['text_info'][1]
    assert p2['status'] == 'completed'
    assert p2['translation'] == "Translated 2"

def test_finalize_clears_md_before_writing(blueprint_file, tmp_path):
    md_path = tmp_path / "existing.md"
    md_path.write_text("Old junk content", encoding="utf-8")
    
    manager = TranslationLogManager(blueprint_file)
    manager.append_log(1, {"translation": "New 1"})
    
    finalize_translation_output(blueprint_file, str(md_path), mode="structured")
    
    content = md_path.read_text(encoding="utf-8")
    assert "Old junk content" not in content
    assert "New 1" in content
