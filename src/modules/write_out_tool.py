from typing import Union,Tuple
import re

# @title 模块5：写入并累加更新markdown文件

def write_to_markdown(
    output_file_path: str,
    content: Union[str, Tuple[str, dict]],
    mode: str = "auto"
) -> None:
    """
    结构化写入Markdown文件（兼容模式）

    参数：
    :param output_file_path: 输出文件路径
    :param content: 输入内容，支持两种格式：
       - str: 纯文本段落（兼容模式）
       - tuple: (段落文本, 元数据字典)（结构化模式）
    :param mode: 写入模式
       - 'auto': 自动检测输入类型（默认）
       - 'flat': 强制扁平化写入
       - 'structured': 强制结构化写入

    元数据字典结构：
    {
        'current_level': int,         # 当前标题层级（0=无标题）
        'header_path': List[str],     # 标题路径（如 ["# Main", "## Section1"]）
        'is_continuation': bool       # 是否为续分段
    }
    """
    # 解析输入内容
    paragraph_text, metadata = _parse_content(content, mode)

    # 过滤掉思考链内容
    paragraph_text = _filter_think_content(paragraph_text)

    # 创建文件写入上下文
    with open(output_file_path, 'a', encoding='utf-8') as file:
        # 结构化写入逻辑
        if metadata and mode != 'flat':
            _write_structured_section(file, paragraph_text, metadata)
        else:
            # 兼容模式写入
            file.write(f"\n{paragraph_text}\n# end")

def _filter_think_content(text: str) -> str:
    """过滤掉思考链内容"""
    # 移除<think>...</think>标签及其内容
    filtered_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 移除可能的空行
    filtered_text = re.sub(r'\n{3,}', '\n\n', filtered_text)
    return filtered_text.strip()

def _parse_content(content, mode) -> Tuple[str, dict]:
    """统一解析输入内容"""
    # 强制扁平化模式
    if mode == 'flat':
        if isinstance(content, tuple):
            return content[0], None
        return content, None

    # 结构化模式检测
    if mode == 'structured' and not isinstance(content, tuple):
        raise ValueError("结构化模式需要传入元组格式内容")

    # 自动检测
    if isinstance(content, tuple):
        return content[0], content[1]
    return content, None

def _write_structured_section(file, text: str, meta: dict):
    # 使用内存维护标题栈，避免重复读取文件
    if not hasattr(file, '_header_stack'):
        file._header_stack = []
    current_headers = file._header_stack
    target_headers = meta['header_path']

    # 找到第一个不同的标题位置
    min_len = min(len(current_headers), len(target_headers))
    i = 0
    while i < min_len and current_headers[i] == target_headers[i]:
        i += 1

    # 截断当前栈到i的位置
    file._header_stack = list(current_headers[:i])

    # 添加剩余的标题
    for header in target_headers[i:]:
        file.write(f"\n\n{header}\n\n")  # 修正换行符
        file._header_stack.append(header)

    # 写入内容
    file.write(f"{text}\n\n")
