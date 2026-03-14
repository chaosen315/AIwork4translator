import os
import json
import pytest
from modules.export_tool import export_json_to_xlsx, export_json_to_docx, export_json_to_pdf, export_json_to_epub

@pytest.fixture
def dummy_json_path(tmp_path):
    data = {
        "text_info": [
            {
                "paragraph_number": 1,
                "meta_data": {"header_path": ["# Chapter 1"], "current_level": 1},
                "content": "Hello World",
                "translation": "你好世界",
                "notes": "Test Note"
            },
            {
                "paragraph_number": 2,
                "meta_data": {"header_path": ["# Chapter 1", "## Section 1"], "current_level": 2},
                "content": "This is a test.",
                "translation": "这是一个测试。",
                "notes": ""
            }
        ]
    }
    path = tmp_path / "test_intermediate.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return str(path)

def test_export_xlsx(dummy_json_path, tmp_path):
    output = str(tmp_path / "output.xlsx")
    assert export_json_to_xlsx(dummy_json_path, output)
    assert os.path.exists(output)

def test_export_docx(dummy_json_path, tmp_path):
    output = str(tmp_path / "output.docx")
    assert export_json_to_docx(dummy_json_path, output)
    assert os.path.exists(output)

def test_export_pdf(dummy_json_path, tmp_path):
    output = str(tmp_path / "output.pdf")
    assert export_json_to_pdf(dummy_json_path, output)
    assert os.path.exists(output)

def test_export_epub(dummy_json_path, tmp_path):
    output = str(tmp_path / "output.epub")
    assert export_json_to_epub(dummy_json_path, output)
    assert os.path.exists(output)
