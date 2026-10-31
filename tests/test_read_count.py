from modules.count_tool import count_structured_paragraphs
from modules.read_tool import read_structured_paragraphs

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


def test_count_matches_special_structure_segmentation(tmp_path):
    md = tmp_path / "special.md"
    md.write_text(
        "# Title\n\n"
        "| Name | Value |\n"
        "| --- | --- |\n"
        "| alpha | one |\n"
        "| beta | two |\n\n"
        "```python\n"
        "print('hello')\n"
        "print('world')\n"
        "```\n",
        encoding="utf-8",
    )

    chunks = list(
        read_structured_paragraphs(
            str(md),
            max_chunk_size=45,
            preserve_structure=True,
        )
    )
    count = count_structured_paragraphs(
        str(md),
        max_chunk_size=45,
        preserve_structure=True,
    )

    assert count == len(chunks)
