from modules.write_out_tool import write_to_markdown


def test_write_structured_appends_content_when_header_matches_atx(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# Title\n\nExisting.\n", encoding="utf-8")
    metadata = {
        "current_level": 2,
        "header_path": ["# Title", "# 标题"],
        "is_continuation": False,
    }
    write_to_markdown(str(md), ("New para", metadata), mode="structured")
    content = md.read_text(encoding="utf-8")
    assert content.count("# Title") == 1
    assert "New para" in content


def test_write_structured_writes_headers_when_header_differs_setext(tmp_path):
    md = tmp_path / "doc2.md"
    md.write_text("Section\n---\n\nOld.\n", encoding="utf-8")
    metadata = {
        "current_level": 1,
        "header_path": ["# Title"],
        "is_continuation": False,
    }
    write_to_markdown(str(md), ("New para", metadata), mode="structured")
    content = md.read_text(encoding="utf-8")
    assert "Section\n---" in content
    assert content.count("# Title") == 1
    assert "New para" in content
