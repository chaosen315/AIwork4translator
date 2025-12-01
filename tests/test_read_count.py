import os
from modules.count_tool import count_structured_paragraphs

def test_count_structured_paragraphs(tmp_path):
    md = tmp_path / "sample.md"
    md.write_text("""
# Title

Paragraph one line.

## Subsection

Another paragraph line.
""".strip(), encoding="utf-8")
    n = count_structured_paragraphs(str(md), max_chunk_size=600, preserve_structure=True)
    assert n >= 1
