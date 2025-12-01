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
    compact_markdown = re.sub(r'(?<!\n)\n(?!\n)', ' ', result.text_content)
    compact_markdown = re.sub(r'^[^0-9\n]\s*$', '', compact_markdown, flags=re.MULTILINE)
    compact_markdown = re.sub(r'\n{3,}', '\n\n', compact_markdown).strip()
    input_dir = os.path.dirname(file_path)
    input_filename = os.path.basename(file_path)
    base_name, extension = os.path.splitext(input_filename)
    input_base_filename = f"{base_name}_md_form_for_input"
    input_md_file = os.path.join(input_dir, f"{input_base_filename}.md")
    counter = 1
    while os.path.exists(input_md_file):
        input_md_file = os.path.join(input_dir, f"{input_base_filename}_{counter}.md")
        counter += 1
    with open(input_md_file, 'w', encoding='utf-8') as f:
        f.write(compact_markdown)
    clean_file(input_md_file)
    return input_md_file
