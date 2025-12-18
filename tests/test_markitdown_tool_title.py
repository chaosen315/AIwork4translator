import os
import tempfile
import pytest
from modules.markitdown_tool import markitdown_tool

def test_markitdown_tool_adds_title_when_missing():
    """
    测试当输入文件没有标题时，markitdown_tool 是否会使用文件名作为标题。
    这是针对"极端情况"的测试：纯文本，无任何 Markdown 格式。
    """
    content = "This is a paragraph.\nIt has no title.\nJust plain text."
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 使用不含空格的文件名，方便断言
        base_name = "test_no_title"
        input_filename = f"{base_name}.txt"
        input_path = os.path.join(temp_dir, input_filename)
        
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 调用被测试函数
        # 注意：markitdown_tool 会在输入文件同目录下生成新文件
        try:
            output_path = markitdown_tool(input_path)
        except Exception as e:
            pytest.fail(f"markitdown_tool execution failed: {e}")
            
        assert output_path != "", "Should return a valid file path"
        assert os.path.exists(output_path), "Output file should exist"
        
        with open(output_path, "r", encoding="utf-8") as f:
            output_content = f.read()
            
        # 验证是否添加了标题
        expected_title_line = f"# {base_name}"
        
        print(f"Output content:\n{output_content}")
        
        # 检查文件是否以标题开头
        assert output_content.strip().startswith(expected_title_line), \
            f"Content should start with title '{expected_title_line}'"
            
        # 检查原始内容是否还在（注意 markitdown 可能把换行替换为空格）
        # 原文: "This is a paragraph.\nIt has no title.\nJust plain text."
        # 处理后: "This is a paragraph. It has no title. Just plain text." (大约)
        assert "This is a paragraph." in output_content

def test_markitdown_tool_converts_bold_to_title():
    """
    测试 markitdown_tool 是否能将 **Title** 格式转换为 # Title，
    并且在这种情况下不应该再添加文件名作为标题。
    """
    content = "**My Bold Title**\n\nSome content here."
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_name = "test_bold_title"
        input_filename = f"{base_name}.txt"
        input_path = os.path.join(temp_dir, input_filename)
        
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        output_path = markitdown_tool(input_path)
        
        with open(output_path, "r", encoding="utf-8") as f:
            output_content = f.read()
            
        print(f"Output content:\n{output_content}")
        
        # 验证 **My Bold Title** 被转换为 # My Bold Title
        assert output_content.strip().startswith("# My Bold Title")
        
        # 验证没有重复添加基于文件名的标题
        assert f"# {base_name}" not in output_content

def test_markitdown_tool_respects_existing_hash_title():
    """
    测试当输入文件已经有 # Title 时，不应做多余更改。
    """
    content = "# Existing Header\n\nContent."
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_name = "test_hash_title"
        input_filename = f"{base_name}.txt"
        input_path = os.path.join(temp_dir, input_filename)
        
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        output_path = markitdown_tool(input_path)
        
        with open(output_path, "r", encoding="utf-8") as f:
            output_content = f.read()
            
        assert output_content.strip().startswith("# Existing Header")
        assert f"# {base_name}" not in output_content
