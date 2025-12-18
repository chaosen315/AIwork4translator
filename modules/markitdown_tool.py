from markitdown import MarkItDown
import re
import os

def clean_file(file_path, chunk_size=1024):
    temp_file_path = file_path + '.tmp'
    try:
        with open(file_path, 'rb') as f, open(temp_file_path, 'wb') as temp_f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                try:
                    decoded_chunk = chunk.decode('utf-8')
                except UnicodeDecodeError as e:
                    decoded_chunk = chunk[:e.start].decode('utf-8') + chunk[e.end:].decode('utf-8')
                temp_f.write(decoded_chunk.encode('utf-8'))
        os.replace(temp_file_path, file_path)
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def markitdown_tool(file_path):
    md = MarkItDown(enable_plugins=False)
    try:
        result = md.convert(file_path)
    except Exception as e:
        print(f"Marktidown解析文件时出错：{e}")
        return ""
    input_dir = os.path.dirname(file_path)
    input_filename = os.path.basename(file_path)
    base_name, extension = os.path.splitext(input_filename)
    # 处理孤立换行符：将段落中的单个换行符替换为空格，保持段落连续性
    # 正则解释：(?<!\n)\n(?!\n) - 匹配前后都不是换行符的单个换行符
    compact_markdown = re.sub(r'(?<!\n)\n(?!\n)', ' ', result.text_content)
    
    # 清理无效行：删除只包含非数字字符和空白字符的无效行
    # 正则解释：^[^0-9\n]\s*$ - 匹配行首到行尾，不包含数字和换行符的任意字符+空白
    compact_markdown = re.sub(r'^[^0-9\n]\s*$', '', compact_markdown, flags=re.MULTILINE)
    
    # 规范化换行符：将3个或更多连续换行符压缩为2个换行符，保持段落间距整洁
    # 正则解释：\n{3,} - 匹配3个或更多连续换行符
    compact_markdown = re.sub(r'\n{3,}', '\n\n', compact_markdown).strip()
    # 转换标题格式：将Markdown加粗格式的标题转换为一级标题格式
    # 正则解释：^\*\*(.+?)\*\*$ - 匹配整行的**标题**格式，捕获标题内容
    # 替换为：# 加上捕获的标题内容，实现格式转换
    compact_markdown = re.sub(r'^\*\*(.+?)\*\*$', r'# \1', compact_markdown, flags=re.MULTILINE)    

    # 检查文档是否已有标题：如果第一行不是以#开头，添加基于文件名的标题
    # 这确保转换后的Markdown文档具有明确的标题结构
    if not compact_markdown.startswith('#'):
        # 使用原始文件名（不含扩展名）作为标题，并添加一级标题标记
        compact_markdown = f"# {base_name}\n\n{compact_markdown}"
    input_base_filename = f"{base_name}_md_for_input"
    input_md_file = os.path.join(input_dir, f"{input_base_filename}.md")
    counter = 1
    while os.path.exists(input_md_file):
        input_md_file = os.path.join(input_dir, f"{input_base_filename}_{counter}.md")
        counter += 1
    with open(input_md_file, 'w', encoding='utf-8') as f:
        f.write(compact_markdown)
    clean_file(input_md_file)
    return input_md_file
