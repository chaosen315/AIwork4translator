import re
from typing import Generator, Tuple, Union

def read_markdown_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def read_structured_paragraphs(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> Generator[Union[str, Tuple[str, dict]], None, None]:
    current_chunk = []
    chunk_length = 0
    
    # Updated pattern to match images in separate blocks if they are standalone
    # Or we can handle it line by line.
    # The requirement is: "将github风格的md语法中```![](url地址)```的图片预览部分单独切块"
    # Note: GitHub style image is usually `![]()` or `[![alt](src)](link)`
    # The user specifically mentioned `![](url地址)`.
    # We should detect lines that are ONLY images (or primarily images) and yield them separately.
    
    image_pattern = re.compile(r'^\s*!\[.*?\]\(.*?\)\s*$')
    
    if preserve_structure == True:
        current_level = 0
        header_stack = []
        chunk_length = 0
        continuation_flag = False
        atx_header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(\s+#+)?$')
        setext_header_pattern = re.compile(r'^={3,}$|^-{3,}$')
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.rstrip('\n')
                raw_line = line
                stripped_line = line.strip()
                
                # Check for Image Line
                if image_pattern.match(line):
                    # If we have current chunk, yield it first
                    if current_chunk:
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False
                    
                    # Yield image as a separate chunk with a special flag/metadata?
                    # The format output returns (text, metadata).
                    # We can mark metadata 'is_image': True or 'type': 'image'
                    # But the current signature of _format_output doesn't support custom keys easily without modification.
                    # However, read_tool yields to main loop.
                    # We can reuse 'meta_data' dict.
                    
                    # Special yield for image
                    # We yield it as is. The translation core should ignore it.
                    yield (
                        line,
                        {
                            'current_level': current_level,
                            'header_path': header_stack.copy(),
                            'is_continuation': False,
                            'is_image': True # New Flag
                        }
                    )
                    continue

                header_match = atx_header_pattern.match(line)
                setext_match = None
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
                            line = f"{'#' * header_level} {header_text}"
                            current_chunk.pop()
                if header_match or setext_match:
                    if header_match:
                        header_level = len(header_match.group(1))
                        header_text = header_match.group(2).strip()
                    else:
                        header_level = 1 if '=' in raw_line else 2
                        header_text = current_chunk.pop().strip()
                    should_yield = False
                    if current_chunk:
                        if header_level <= current_level:
                            should_yield = True
                        elif chunk_length + len(line) > max_chunk_size * 0.8:
                            should_yield = True
                    if should_yield:
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False
                    current_level = header_level
                    while len(header_stack) >= current_level:
                        header_stack.pop()
                    header_stack.append(f"{'#' * header_level} {header_text}")
                    current_chunk.append(line)
                    chunk_length += len(line) + 1
                    continuation_flag = False
                    continue
                if not stripped_line:
                    if current_chunk and not current_chunk[-1].endswith('\n\n'):
                        current_chunk.append('')
                        chunk_length += 1
                    continue
                line_length = len(line) + 1
                if chunk_length + line_length > max_chunk_size:
                    split_pos = _find_split_position(line, max_chunk_size - chunk_length)
                    if split_pos > 0:
                        current_chunk.append(line[:split_pos])
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure
                        )
                        continuation_header = header_stack[-1] if header_stack else "Document Start"
                        current_chunk = [
                            f"<!-- Continued from {continuation_header} -->",
                            line[split_pos:]
                        ]
                    else:
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
            if current_chunk:
                yield _format_output(
                    current_chunk,
                    current_level,
                    header_stack.copy(),
                    continuation_flag,
                    preserve_structure
                )
    else:
        # Non-structured mode (rarely used but good to support)
        # Similar logic for images
        pending_chunks = []
        pending_length = 0
        def process_pending_chunks():
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
                
                # Check for Image Line
                if image_pattern.match(line):
                     # Yield pending text chunks first
                    if current_chunk:
                         # ... (complex flush logic similar to below)
                         # To simplify: flush current_chunk -> pending -> yield
                        chunk_text = '\n'.join(current_chunk)
                        current_chunk = []
                        chunk_length = 0
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                        else:
                            if pending_chunks:
                                yield process_pending_chunks() # type: ignore
                            yield chunk_text
                    
                    if pending_chunks:
                        yield process_pending_chunks() # type: ignore
                        
                    # Yield image
                    yield line # Just the string, main loop handles string vs tuple
                    continue

                if not stripped_line:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        current_chunk = []
                        chunk_length = 0
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                yield process_pending_chunks() # type: ignore
                        else:
                            if pending_chunks:
                                yield process_pending_chunks() # type: ignore
                            yield chunk_text
                    continue
                line_length = len(line) + 1
                if chunk_length + line_length > max_chunk_size:
                    split_pos = _find_split_position(line, max_chunk_size - chunk_length)
                    if split_pos > 0:
                        current_chunk.append(line[:split_pos])
                        chunk_text = '\n'.join(current_chunk)
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                yield process_pending_chunks() # type: ignore
                        else:
                            if pending_chunks:
                                yield process_pending_chunks() # type: ignore
                            yield chunk_text
                        current_chunk = [line[split_pos:]]
                        chunk_length = len(line[split_pos:])
                    else:
                        if current_chunk:
                            chunk_text = '\n'.join(current_chunk)
                            if len(chunk_text) < min_chunk_size:
                                pending_chunks.append(chunk_text)
                                pending_length += len(chunk_text)
                                if pending_length >= max_chunk_size:
                                    yield process_pending_chunks() # type: ignore
                            else:
                                if pending_chunks:
                                    yield process_pending_chunks() # type: ignore
                                yield chunk_text
                        current_chunk = [line]
                        chunk_length = line_length
                else:
                    current_chunk.append(line)
                    chunk_length += line_length
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                if len(chunk_text) < min_chunk_size:
                    pending_chunks.append(chunk_text)
                    pending_length += len(chunk_text)
                else:
                    if pending_chunks:
                        yield process_pending_chunks() # type: ignore
                    yield chunk_text
            if pending_chunks:
                yield process_pending_chunks() # type: ignore

import json
import os

def _is_sentence_midpage_break(block_A_content: str, block_B_content: str) -> bool:
    """
    严格检测句中跨页无标点缓冲。
    根据用户提供的算法，判断 block_B 是否是 block_A 未完成句子的延续。
    """
    # 预处理：清理空白
    tail_A = block_A_content.rstrip()
    head_B = block_B_content.lstrip()

    if not tail_A or not head_B:
        return False

    # ────── 否决条件（立即返回False）──────
    # 1. Block A 以句末标点结尾
    if tail_A.endswith(('.', '?', '!')):
        return False

    # 2. Block A 是常见缩写结尾
    ABBR_ENDINGS = {'e.g.', 'i.e.', 'et al.', 'Dr.', 'Prof.', 'Fig.', 'Table.',
                    'vs.', 'cf.', 'pp.', 'No.', 'vol.', 'Sec.'}
    if any(tail_A.endswith(abbr) for abbr in ABBR_ENDINGS):
        return False

    # 3. Block A 以连字符结尾（合法拆分）
    if tail_A.endswith('-'):
        return False

    # 4. Block B 以大写开头（极可能是新句）
    if head_B[0].isupper():
        return False

    # 5. Block B 是章节标题信号
    if any(head_B.startswith(pattern) for pattern in ['Chapter', 'Section', 'Figure', 'Table']):
        return False

    # ────── 阳性信号（计分系统）──────
    score = 0

    # 信号1：Block B 首词是延续性词汇
    CONTINUATION_WORDS = {
        # 连词
        'and', 'but', 'or', 'yet', 'so', 'for', 'nor',
        # 代词
        'this', 'that', 'these', 'those', 'which', 'who', 'whom',
        # 介词（句中）
        'in', 'on', 'at', 'by', 'with', 'from', 'to', 'of',
        # 副词
        'however', 'therefore', 'thus', 'hence', 'then', 'also'
    }
    
    try:
        first_word = head_B.split()[0].lower().rstrip(',;:')
        if first_word in CONTINUATION_WORDS:
            score += 50  # 最强信号
    except IndexError:
        pass # head_B 为空或只有空白

    # 信号2：Block A 尾词是句中词汇
    try:
        last_word = tail_A.split()[-1].lower()
        if last_word not in {'conclusion', 'summary', 'result', 'effect'}:
            score += 10
    except IndexError:
        pass # tail_A 为空或只有空白

    # 信号3：Block B 开头字符小写（已保证不是新句）
    score += 20

    # ────── 阈值判定 ──────
    return score >= 60


def read_and_process_structured_paragraphs_to_json(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> str:
    """
    读取文档，将其智能切分为段落，并将过短的段落合并，最终生成一个结构化的 JSON 文件。

    该函数的核心功能是后处理（Post-Processing），它首先将文档分解为最细粒度的
    “原子”段落，然后根据 min_chunk_size 和 max_chunk_size 的约束，将过短的段落
    与后续段落进行合并，同时确保图片等特殊结构不参与合并。

    Args:
        file_path (str): 输入文件的路径。
        max_chunk_size (int): 合并后段落内容的最大长度阈值。
        min_chunk_size (int): 判断段落是否“过短”的最小长度阈值。
        preserve_structure (bool): 是否保留文档的结构信息（如标题层级）。

    Returns:
        str: 生成的 JSON 文件的绝对路径。如果处理失败或无内容，则返回空字符串。
    """
    # 步骤 1: 获取原子段落
    # 调用 read_structured_paragraphs 生成器，但设置 min_chunk_size=0。
    # 这会强制它返回所有最细粒度的段落（原子段落），而不进行任何初步合并。
    # 真正的合并逻辑由本函数在后续步骤中完全控制，从而实现更精细的控制。
    raw_paragraphs = list(read_structured_paragraphs(
        file_path,
        max_chunk_size=max_chunk_size,
        min_chunk_size=0, 
        preserve_structure=preserve_structure
    ))

    if not raw_paragraphs:
        return ""

    # 步骤 2: 标准化数据结构
    # 将生成器返回的原始段落（字符串或元组）转换为统一的字典列表。
    # 这为后续的合并和处理提供了便利的数据格式。
    processed_items = []
    for i, item in enumerate(raw_paragraphs):
        content, meta = (item[0], item[1]) if preserve_structure else (item, None)
        
        processed_items.append({
            'paragraph_number': i + 1,  # 临时段落编号
            'meta_data': meta,
            'content': content,
            'translation': '',
            'notes': '',
            'new_terms': [],
            'status': 'pending'
        })

    # 步骤 3: 核心合并逻辑（增强版）
    # 该逻辑使用一个主循环和一个内部查找循环，以实现更智能的合并策略。
    # - 它能够“跳过”图片段落，尝试合并图片前后的文本段落。
    # - 合并后的文本块可以继续参与下一轮合并，形成更大的段落。
    # - 被跳过的图片会在合并后的文本块之后被添加回来。
    merged_items = []
    i = 0
    while i < len(processed_items):
        # 将当前项作为“累加器”开始一个新的合并周期
        buffer_item = processed_items[i]
        i += 1  # 预先消耗当前项

        # 如果累加器本身是图片，则它不能合并其他内容。直接将其定稿并继续。
        is_buffer_img = buffer_item.get('meta_data') and buffer_item['meta_data'].get('is_image')
        if is_buffer_img:
            merged_items.append(buffer_item)
            continue

        # 用于存储在文本合并过程中被跳过的图片
        pending_images = []

        # 内部循环：只要合并成功，就持续尝试将后续文本合并到当前累加器中
        while True:
            # --- 向前查找下一个非图片段落 ---
            search_j = i
            images_skipped_this_round = []
            next_text_item = None
            next_text_item_index = -1

            while search_j < len(processed_items):
                candidate = processed_items[search_j]
                is_candidate_img = candidate.get('meta_data') and candidate['meta_data'].get('is_image')
                if is_candidate_img:
                    images_skipped_this_round.append(candidate)
                    search_j += 1
                else:
                    next_text_item = candidate
                    next_text_item_index = search_j
                    break  # 找到了下一个文本段落

            # 如果找不到更多的文本段落，则当前累加器的合并周期结束
            if not next_text_item:
                break  # 退出内部循环

            # --- 检查合并条件 ---
            is_buffer_short = len(buffer_item['content']) < min_chunk_size
            is_sentence_break = _is_sentence_midpage_break(buffer_item['content'], next_text_item['content'])
            
            can_merge = is_buffer_short or is_sentence_break

            if can_merge:
                combined_len = len(buffer_item['content']) + len(next_text_item['content'])
                if combined_len <= max_chunk_size * 1.2:
                    # --- 执行合并 ---
                    buffer_item['content'] += "\n\n" + next_text_item['content']
                    pending_images.extend(images_skipped_this_round)
                    
                    # 更新主循环的索引，跳过所有已处理的项（被合并的文本和跳过的图片）
                    i = next_text_item_index + 1
                    
                    # 继续内部循环，尝试用增大的累加器进行下一轮合并
                    continue
            
            # --- 无法合并 ---
            # 如果不满足合并条件（例如，合并后超长），则停止当前累加器的合并周期
            break

        # --- 定稿 ---
        # 内部循环结束后，将最终的累加器（文本块）和所有待处理的图片定稿
        merged_items.append(buffer_item)
        if pending_images:
            merged_items.extend(pending_images)

    # 步骤 4: 重新编号
    # 在所有合并操作完成后，为最终的段落列表分配正确、连续的段落号。
    final_data = []
    for idx, item in enumerate(merged_items):
        item['paragraph_number'] = idx + 1
        final_data.append(item)
    
    # 步骤 5: 构造并保存 JSON 文件
    # 将处理好的段落数据包装在 'text_info' 键下，并写入文件。
    json_output = {'text_info': final_data}
    
    input_dir = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    json_path = os.path.join(input_dir, f"{base_name}_intermediate.json")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
        
    return json_path

def _format_output(chunk, level, headers, is_continuation, return_metadata):
    formatted_text = '\n'.join(chunk)
    if not return_metadata:
        return formatted_text
    return (
        formatted_text,
        {
            'current_level': level,
            'header_path': headers.copy(),
            'is_continuation': is_continuation,
        }
    )

def _find_split_position(line, remaining_space):
    if remaining_space >= len(line):
        return -1
    for pos in range(remaining_space, max(0, remaining_space-100), -1):
        if pos < len(line) and line[pos] in ('.', '。', '!', '！', '?', '？'):
            return pos + 1
    for pos in range(remaining_space, max(0, remaining_space-50), -1):
        if pos < len(line) and line[pos] in (',', '，', ';', '；'):
            return pos + 1
    for pos in range(remaining_space, max(0, remaining_space-20), -1):
        if pos < len(line) and line[pos].isspace():
            return pos + 1
    return remaining_space
