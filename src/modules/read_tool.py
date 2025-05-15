from typing import Generator, Tuple, Union
import re

def read_markdown_file(file_path: str) -> str:
    """
    读取markdown文件内容
    :param file_path: markdown文件路径
    :return: 文件内容字符串
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def read_structured_paragraphs(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> Generator[Union[str, Tuple[str, dict]], None, None]:
    """
    智能分段读取Markdown文档（兼容模式）

    参数：
    :param file_path: Markdown文件路径
    :param max_chunk_size: 最大段落字符数（默认1500）
    :param preserve_structure: 是否保留结构信息（默认True）

    生成：
    :yield:
      - 当preserve_structure=False时：段落文本 (str)
      - 当preserve_structure=True时：(段落文本, 元数据字典)
        元数据包含：
        - 'current_level': 当前标题层级（0=无标题）
        - 'header_path': 标题路径（如 ["# Main", "## Section1"]）
        - 'is_continuation': 是否为续分段（True/False）
    """
    current_chunk = []
    chunk_length = 0
    if preserve_structure == True:
        # 状态跟踪变量
        current_level = 0
        header_stack = []
        chunk_length = 0
        continuation_flag = False
        print(file_path)
        # 编译正则表达式（支持ATX标题和Setext风格标题）
        atx_header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(\s+#+)?$')
        setext_header_pattern = re.compile(r'^={3,}$|^-{3,}$')

        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.rstrip('\n')
                raw_line = line  # 保留原始行用于结构分析

                # 预处理：删除前后空格但保留空行识别
                stripped_line = line.strip()

                # 标题检测逻辑 -------------------------------------------------
                header_match = atx_header_pattern.match(line)
                setext_match = None

                # Setext风格标题检测（需要前一行内容）
                if line_num > 1 and not stripped_line:
                    prev_line = current_chunk[-1] if current_chunk else ""
                    if setext_header_pattern.match(raw_line):
                        setext_match = (
                            '=' in raw_line and len(raw_line) >=3 or
                            '-' in raw_line and len(raw_line) >=3
                        )
                        if setext_match:
                            header_level = 1 if '=' in raw_line else 2
                            header_text = prev_line.strip()

                            # 重构为ATX格式标准化
                            line = f"{'#' * header_level} {header_text}"
                            current_chunk.pop()  # 移除原文本行

                # 标题处理逻辑
                if header_match or setext_match:
                    # 标准化后的标题处理
                    if header_match:
                        header_level = len(header_match.group(1))
                        header_text = header_match.group(2).strip()
                    else:
                        header_level = 1 if '=' in raw_line else 2
                        header_text = current_chunk.pop().strip()

                    # 触发分段的逻辑条件
                    should_yield = False
                    if current_chunk:
                        # 条件1：新标题层级 <= 当前层级
                        if header_level <= current_level:
                            should_yield = True
                        # 条件2：当前段落接近长度限制
                        elif chunk_length + len(line) > max_chunk_size * 0.8:
                            should_yield = True

                    if should_yield:
                        # 生成当前段落（带元数据或纯文本）
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        # 重置状态（保留标题栈）
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False

                    # 更新标题栈
                    current_level = header_level
                    while len(header_stack) >= current_level:
                        header_stack.pop()
                    header_stack.append(f"{'#' * header_level} {header_text}")

                    # 添加标题到新段落
                    current_chunk.append(line)
                    chunk_length += len(line) + 1  # +1 for newline
                    continuation_flag = False
                    continue

                # 非标题内容处理 ---------------------------------------------
                if not stripped_line:  # 空行处理
                    if current_chunk and not current_chunk[-1].endswith('\n\n'):
                        current_chunk.append('')
                        chunk_length += 1
                    continue

                # 长度控制逻辑
                line_length = len(line) + 1  # 包含换行符
                if chunk_length + line_length > max_chunk_size:
                    # 智能寻找分割点（优先在句子结束处分割）
                    split_pos = _find_split_position(line, max_chunk_size - chunk_length)

                    if split_pos > 0:
                        # 分割当前行
                        current_chunk.append(line[:split_pos])
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        # 新段落以续写标识开始
                        current_chunk = [
                            f"<!-- Continued from {header_stack[-1]} -->",
                            line[split_pos:]
                        ]
                    else:
                        # 整行无法放入当前段落
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        current_chunk = [line]

                    chunk_length = len(line[split_pos:] if split_pos > 0 else line)
                    continuation_flag = True
                else:
                    current_chunk.append(line)
                    chunk_length += line_length

            # 处理最后剩余的段落
            if current_chunk:
                yield _format_output(
                    current_chunk,
                    current_level,
                    header_stack.copy(),
                    continuation_flag,
                    preserve_structure
                )
    else:
        #preserve_structure 为False，意味着只需要进行文段分割，并返回文本即可。
        # 非结构化模式：简单段落分割
        pending_chunks = []  # 用于累积短段落
        pending_length = 0

        def process_pending_chunks():
            """处理累积的短段落"""
            nonlocal pending_chunks, pending_length
            if pending_chunks:
                combined_text = '\n'.join(pending_chunks)
                pending_chunks = []
                pending_length = 0
                return combined_text
            return None
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.rstrip('\n')
                stripped_line = line.strip()
                
                # 空行处理
                if not stripped_line:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        current_chunk = []
                        chunk_length = 0
                        
                        # 如果当前段落小于最小长度，加入待处理队列
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            
                            # 如果累积长度超过最大长度，输出累积内容
                            if pending_length >= max_chunk_size:
                                yield process_pending_chunks()
                        else:
                            # 如果有待处理的短段落，先输出
                            if pending_chunks:
                                yield process_pending_chunks()
                            # 输出当前段落
                            yield chunk_text
                    continue
                
                # 长度控制逻辑
                line_length = len(line) + 1
                if chunk_length + line_length > max_chunk_size:
                    # 尝试智能分割
                    split_pos = _find_split_position(line, max_chunk_size - chunk_length)
                    
                    if split_pos > 0:
                        # 分割当前行
                        current_chunk.append(line[:split_pos])
                        chunk_text = '\n'.join(current_chunk)
                        
                        # 处理分割后的第一部分
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                yield process_pending_chunks()
                        else:
                            if pending_chunks:
                                yield process_pending_chunks()
                            yield chunk_text
                        
                        # 开始新的段落
                        current_chunk = [line[split_pos:]]
                        chunk_length = len(line[split_pos:])
                    else:
                        # 如果当前段落非空
                        if current_chunk:
                            chunk_text = '\n'.join(current_chunk)
                            if len(chunk_text) < min_chunk_size:
                                pending_chunks.append(chunk_text)
                                pending_length += len(chunk_text)
                                if pending_length >= max_chunk_size:
                                    yield process_pending_chunks()
                            else:
                                if pending_chunks:
                                    yield process_pending_chunks()
                                yield chunk_text
                        
                        # 将整行作为新段落
                        current_chunk = [line]
                        chunk_length = line_length
                else:
                    current_chunk.append(line)
                    chunk_length += line_length
            
            # 处理最后剩余的内容
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                if len(chunk_text) < min_chunk_size:
                    pending_chunks.append(chunk_text)
                    pending_length += len(chunk_text)
                else:
                    if pending_chunks:
                        yield process_pending_chunks()
                    yield chunk_text
            
            # 输出最后累积的短段落
            if pending_chunks:
                yield process_pending_chunks()



def _format_output(chunk, level, headers, is_continuation, return_metadata):
    """统一格式化输出段落"""
    formatted_text = '\n'.join(chunk)
    if not return_metadata:
        return formatted_text
    return (
        formatted_text,
        {
            'current_level': level,
            'header_path': headers.copy(),
            'is_continuation': is_continuation
        }
    )

def _find_split_position(line, remaining_space):
    """智能查找最佳分割位置"""
    if remaining_space >= len(line):
        return -1  # 无需分割

    # 优先在句子结束符处分割
    for pos in range(remaining_space, max(0, remaining_space-100), -1):
        if pos < len(line) and line[pos] in ('.', '。', '!', '！', '?', '？'):
            return pos + 1

    # 次优选择：在逗号或分号处分割
    for pos in range(remaining_space, max(0, remaining_space-50), -1):
        if pos < len(line) and line[pos] in (',', '，', ';', '；'):
            return pos + 1

    # 最后选择：在空格处分割
    for pos in range(remaining_space, max(0, remaining_space-20), -1):
        if pos < len(line) and line[pos].isspace():
            return pos + 1

    return remaining_space  # 强制分割