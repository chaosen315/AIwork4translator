import os


def _extract_untranslated(original_path, paragraph_text, output_dir, base_name):
    keyword = paragraph_text[:20]
    with open(original_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    idx = original_content.find(keyword)
    if idx == -1:
        return None
    untranslated_part = original_content[idx:]
    out_path = os.path.join(output_dir, f"{base_name}_rest.md")
    with open(out_path, 'w', encoding='utf-8') as uf:
        uf.write(untranslated_part)
    return out_path


def test_untranslated_rest_success(tmp_path):
    md = tmp_path / "sample.md"
    content = (
        "# Title\n\n"
        "Intro paragraph line.\n\n"
        "Second paragraph begins here and continues with more text...\n\n"
        "Third paragraph."
    )
    md.write_text(content, encoding="utf-8")
    paragraph = "Second paragraph begins here and continues"
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "sample")
    assert out_path is not None
    assert os.path.exists(out_path)
    data = (tmp_path / "sample_rest.md").read_text(encoding="utf-8")
    assert data.startswith("Second paragraph begins here")
    assert data.endswith("Third paragraph.")


def test_untranslated_rest_not_found(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("Alpha\n\nBeta\n\nGamma", encoding="utf-8")
    paragraph = "Delta paragraph starts"
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "doc")
    assert out_path is None
    assert not (tmp_path / "doc_rest.md").exists()


def test_untranslated_rest_with_setext_headers(tmp_path):
    md = tmp_path / "md.md"
    content = (
        "Title Setext\n"
        "====================\n\n"
        "Intro paragraph.\n\n"
        "Body starts here with unique token ABCDEFGHIJ12345 and continues...\n\n"
        "Tail."
    )
    md.write_text(content, encoding="utf-8")
    paragraph = "Body starts here with unique token ABCDEFGHIJ12345"
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "md")
    assert out_path is not None
    data = (tmp_path / "md_rest.md").read_text(encoding="utf-8")
    assert data.startswith("Body starts here with unique token ABCDEFGHIJ12345")
    assert data.endswith("Tail.")


def test_untranslated_rest_keyword_occurs_multiple_times_returns_first(tmp_path):
    md = tmp_path / "multi.md"
    repeated = "repeat phrase appears twice"
    content = (
        f"Header\n\n{repeated} in the intro.\n\n"
        f"Middle text with other content.\n\n{repeated} and then more tail."
    )
    md.write_text(content, encoding="utf-8")
    paragraph = repeated + " and then"
    # keyword will be first 20 chars of repeated, which occurs twice; current logic finds first occurrence
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "multi")
    assert out_path is not None
    data = (tmp_path / "multi_rest.md").read_text(encoding="utf-8")
    assert data.startswith(repeated)  # starts at the first occurrence
    assert data.endswith("more tail.")


def test_untranslated_rest_with_chinese_unicode_and_crlf(tmp_path):
    md = tmp_path / "cn.md"
    content = (
        "# 标题\r\n\r\n"
        "这是第一段落，包含中文字符。\r\n\r\n"
        "第二段落从这里开始，并且含有关键短语：关键短语内容示例XYZ。\r\n\r\n"
        "最后一段。\r\n"
    )
    md.write_bytes(content.encode("utf-8"))
    paragraph = "第二段落从这里开始，并且含有关键短语：关键短语内容示例XYZ"
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "cn")
    assert out_path is not None
    data = (tmp_path / "cn_rest.md").read_text(encoding="utf-8")
    assert data.startswith("第二段落从这里开始")
    assert "最后一段。" in data


def test_untranslated_rest_paragraph_shorter_than_20_chars(tmp_path):
    md = tmp_path / "short.md"
    content = "A\n\nshort para here.\n\nend"
    md.write_text(content, encoding="utf-8")
    paragraph = "short para here."
    out_path = _extract_untranslated(str(md), paragraph, str(tmp_path), "short")
    assert out_path is not None
    data = (tmp_path / "short_rest.md").read_text(encoding="utf-8")
    assert data.startswith("short para here.")
