from modules.write_out_tool import write_to_markdown


def test_write_structured_appends_content_when_header_matches_atx(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# Title\n\nExisting.\n", encoding="utf-8")
    
    # 模拟 write_to_markdown_through_json 的行为
    # 如果是续写，meta_data 应为 None
    # 但这里我们要测试的是 _write_structured_section 的去重逻辑
    # 实际上，新的逻辑已经移除了 write_to_markdown 中的去重
    # 所以如果传入 metadata，它就会写入标题
    # 因此，这个测试用例的预期行为需要改变：
    # 如果我们传入了 metadata，它应该写入标题（即使之前有）
    # 除非 _write_structured_section 内部有状态管理（它是有的，通过 file._header_stack）
    # 但 file._header_stack 是临时的，每次 open 都重置
    # 所以 write_to_markdown 现在是"无状态"写入，它只负责把传入的 metadata 写进去
    # "状态"和"去重"的责任转移到了调用者（通过 is_continuation -> None）
    
    # 因此，这个测试现在应该验证：如果传入 metadata，它会写入标题
    
    metadata = {
        "current_level": 2,
        "header_path": ["# Title", "# 标题"],
        "is_continuation": False,
    }
    
    # 注意：write_to_markdown 不再读取文件检查重复标题
    # 所以它会直接写入标题
    write_to_markdown(str(md), ("New para", metadata), mode="structured")
    
    content = md.read_text(encoding="utf-8")
    # 旧逻辑会去重，新逻辑不会去重（除非是 is_continuation）
    # 但等等，_write_structured_section 内部有逻辑：
    # i = 0
    # while i < min_len and current_headers[i] == target_headers[i]:
    #     i += 1
    # 但 file._header_stack 是空的（新打开的文件句柄）
    # 所以它会把所有标题都写一遍
    
    assert content.count("# Title") == 2 # 原有一个，新写入一个
    assert "# 标题" in content
    assert "New para" in content


def test_write_structured_skips_headers_when_is_continuation(tmp_path):
    # 这是新的测试场景：模拟续写逻辑
    md = tmp_path / "doc_cont.md"
    md.write_text("# Title\n\nExisting.\n", encoding="utf-8")
    
    # 模拟 write_to_markdown_through_json 的预处理
    # 如果 is_continuation 为 True，调用者应该传 None
    # 但作为单元测试，我们直接测试 write_to_markdown 对 None 的处理
    
    metadata = None # 模拟 is_continuation=True 后的处理结果
    
    write_to_markdown(str(md), ("New continuation", metadata), mode="structured")
    
    content = md.read_text(encoding="utf-8")
    # 应该没有新增标题
    assert content.count("# Title") == 1
    assert "New continuation" in content


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
