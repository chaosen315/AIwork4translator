from markitdown import MarkItDown
import re
import os

def clean_file(file_path, chunk_size=1024):
    """
    遍历文件并删除 UTF-8 无法解码的异常字符
    :param file_path: 文件路径
    :param chunk_size: 每次读取的块大小（字节）
    """
    temp_file_path = file_path + '.tmp'  # 创建一个临时文件用于存储清洗后的内容
    try:
        with open(file_path, 'rb') as f, open(temp_file_path, 'wb') as temp_f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                try:
                    # 尝试解码为 UTF-8
                    decoded_chunk = chunk.decode('utf-8')
                except UnicodeDecodeError as e:
                    # 如果解码失败，跳过错误的字节
                    decoded_chunk = chunk[:e.start].decode('utf-8') + chunk[e.end:].decode('utf-8')
                # 将清洗后的内容写入临时文件
                temp_f.write(decoded_chunk.encode('utf-8'))
        
        # 用临时文件替换原文件
        os.replace(temp_file_path, file_path)
        # print(f"文件已清洗并保存为 UTF-8 编码: {file_path}")
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)  # 删除临时文件



def markitdown_tool(file_path):
    md = MarkItDown(docintel_endpoint="<document_intelligence_endpoint>")
    try:
        result = md.convert(file_path)
    except Exception as e:
        print(f"Marktidown解析文件时出错：{e}")
        return ""
    # (1) 合并换行符为空格（但保留段落分隔）
    compact_markdown = re.sub(r'(?<!\n)\n(?!\n)', ' ', result.text_content)

    # (2) 移除单字符行（如 "5"）
    compact_markdown = re.sub(r'^[^0-9\n]\s*$', '', compact_markdown, flags=re.MULTILINE)  

    # (3) 清理多余空行
    compact_markdown = re.sub(r'\n{3,}', '\n\n', compact_markdown).strip()  
    input_dir = os.path.dirname(file_path)
    input_filename = os.path.basename(file_path)
    base_name, extension = os.path.splitext(input_filename)
    input_base_filename = f"{base_name}_md_form_for_input"
    input_md_file = os.path.join(input_dir, f"{input_base_filename}.md")
    # 如果输出文件已存在，添加编号后缀
    counter = 1
    while os.path.exists(input_md_file):
        input_md_file = os.path.join(input_dir, f"{input_base_filename}_{counter}.md")
        counter += 1
    with open(input_md_file, 'w', encoding='utf-8') as f:
      f.write(compact_markdown)
    clean_file(input_md_file)
    return input_md_file

if __name__ == "__main__":
    return_file_path = markitdown_tool("input_files\RTG-CPR-DLC-AchievementsandLootBoxes.pdf")

    print(return_file_path)
    print(type(return_file_path))