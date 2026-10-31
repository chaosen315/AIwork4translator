import json

from modules.read_tool import (
    read_and_process_structured_paragraphs_to_json,
    read_structured_paragraphs,
)


def _read_structured_chunks(md_path, max_chunk_size):
    return list(
        read_structured_paragraphs(
            str(md_path),
            max_chunk_size=max_chunk_size,
            preserve_structure=True,
        )
    )


def test_markdown_table_keeps_header_and_splits_by_rows(tmp_path):
    md = tmp_path / "table.md"
    md.write_text(
        "# Title\n\n"
        "| Name | Value |\n"
        "| --- | --- |\n"
        "| alpha | one |\n"
        "| beta | two |\n"
        "| gamma | three |\n",
        encoding="utf-8",
    )

    chunks = _read_structured_chunks(md, max_chunk_size=55)
    table_chunks = [
        (content, meta)
        for content, meta in chunks
        if meta.get("structure_kind") == "markdown_table"
    ]

    assert len(table_chunks) >= 2
    for content, meta in table_chunks:
        assert content.startswith("| Name | Value |")
        assert "| --- | --- |" in content
        assert meta["is_protected_block"] is True

    joined_table = "\n".join(content for content, _ in table_chunks)
    assert "| alpha | one |" in joined_table
    assert "| beta | two |" in joined_table
    assert "| gamma | three |" in joined_table


def test_code_fence_isolated_and_wrapped_when_split(tmp_path):
    md = tmp_path / "code.md"
    md.write_text(
        "# Title\n\n"
        "Intro paragraph.\n\n"
        "```python\n"
        "print('line 1')\n"
        "print('line 2')\n"
        "print('line 3')\n"
        "```\n\n"
        "Tail paragraph.\n",
        encoding="utf-8",
    )

    chunks = _read_structured_chunks(md, max_chunk_size=38)
    fence_chunks = [
        (content, meta)
        for content, meta in chunks
        if meta.get("structure_kind") == "code_fence"
    ]
    text_chunks = [
        content
        for content, meta in chunks
        if not meta.get("is_protected_block") and not meta.get("is_image")
    ]

    assert len(fence_chunks) >= 2
    for content, meta in fence_chunks:
        assert content.startswith("```python")
        assert content.rstrip().endswith("```")
        assert meta["is_protected_block"] is True

    assert any("Intro paragraph." in content for content in text_chunks)
    assert any("Tail paragraph." in content for content in text_chunks)


def test_html_block_repeats_outer_wrapper_when_split(tmp_path):
    md = tmp_path / "html.md"
    md.write_text(
        "# Title\n\n"
        "<details>\n"
        "<summary>More</summary>\n"
        "<p>First line.</p>\n"
        "<p>Second line.</p>\n"
        "<p>Third line.</p>\n"
        "</details>\n",
        encoding="utf-8",
    )

    chunks = _read_structured_chunks(md, max_chunk_size=70)
    html_chunks = [
        (content, meta)
        for content, meta in chunks
        if meta.get("structure_kind") == "html_block"
    ]

    assert len(html_chunks) >= 2
    for content, meta in html_chunks:
        assert content.startswith("<details>")
        assert content.rstrip().endswith("</details>")
        assert meta["is_protected_block"] is True


def test_paired_block_repeats_fence_when_split(tmp_path):
    md = tmp_path / "paired.md"
    md.write_text(
        "# Title\n\n"
        "::: warning\n"
        "first warning line\n"
        "second warning line\n"
        "third warning line\n"
        ":::\n",
        encoding="utf-8",
    )

    chunks = _read_structured_chunks(md, max_chunk_size=40)
    paired_chunks = [
        (content, meta)
        for content, meta in chunks
        if meta.get("structure_kind") == "paired_block"
    ]

    assert len(paired_chunks) >= 2
    for content, meta in paired_chunks:
        assert content.startswith("::: warning")
        assert content.rstrip().endswith(":::")
        assert meta["is_protected_block"] is True


def test_post_process_does_not_merge_across_protected_blocks(tmp_path):
    md = tmp_path / "protected_merge.md"
    md.write_text(
        "Before short.\n\n"
        "```python\n"
        "print('keep me isolated')\n"
        "```\n\n"
        "After short.\n",
        encoding="utf-8",
    )

    json_path = read_and_process_structured_paragraphs_to_json(
        str(md),
        max_chunk_size=120,
        min_chunk_size=100,
        preserve_structure=True,
    )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    paragraphs = data["text_info"]
    assert len(paragraphs) == 3
    assert paragraphs[0]["content"].strip() == "Before short."
    assert paragraphs[1]["meta_data"]["is_protected_block"] is True
    assert paragraphs[1]["meta_data"]["structure_kind"] == "code_fence"
    assert paragraphs[2]["content"].strip() == "After short."
