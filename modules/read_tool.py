from typing import Generator, Tuple, Union
import re

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
                if not stripped_line:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        current_chunk = []
                        chunk_length = 0
                        if len(chunk_text) < min_chunk_size:
                            pending_chunks.append(chunk_text)
                            pending_length += len(chunk_text)
                            if pending_length >= max_chunk_size:
                                yield process_pending_chunks()
                        else:
                            if pending_chunks:
                                yield process_pending_chunks()
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
                                yield process_pending_chunks()
                        else:
                            if pending_chunks:
                                yield process_pending_chunks()
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
                                    yield process_pending_chunks()
                            else:
                                if pending_chunks:
                                    yield process_pending_chunks()
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
                        yield process_pending_chunks()
                    yield chunk_text
            if pending_chunks:
                yield process_pending_chunks()

import json
import os

def read_and_process_structured_paragraphs_to_json(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> str:
    """
    一次性读取并切分文档，合并过短段落，最终保存为 JSON 文件。
    返回 JSON 文件的绝对路径。
    """
    # 1. 调用原有的生成器，一次性获取所有段落
    # 注意：我们这里传入 min_chunk_size=0，是为了让 read_structured_paragraphs 不做合并，
    # 而是返回"原子"段落。合并逻辑完全由本函数后续步骤控制。
    raw_paragraphs = list(read_structured_paragraphs(
        file_path,
        max_chunk_size=max_chunk_size,
        min_chunk_size=0, 
        preserve_structure=preserve_structure
    ))

    # 2. 转换为中间列表结构
    processed_items = []
    
    # 如果 preserve_structure=False, raw_paragraphs 是 str 列表
    # 如果 preserve_structure=True, raw_paragraphs 是 (str, dict) 元组列表
    # 为了统一处理，我们将它们标准化
    
    for i, item in enumerate(raw_paragraphs):
        if preserve_structure:
            content, meta = item
        else:
            content = item
            meta = None
        
        processed_items.append({
            'paragraph_number': i + 1, # 临时编号，稍后可能重排
            'meta_data': meta,
            'content': content,
            'translation': '',
            'notes': '',
            'new_terms': [],
            'status': 'pending'
        })

    # 3. 合并过短的段落 (Post-Processing)
    # 策略：如果当前段落长度小于 min_chunk_size，尝试合并到上一个段落（如果存在）
    # 或者合并到下一个段落。这里我们采取向后合并或向前合并的贪心策略。
    # 简单实现：遍历列表，如果发现短段落，且能合并，则合并。
    
    merged_items = []
    if not processed_items:
        return ""

    # 使用一个缓冲区来处理合并
    buffer_item = processed_items[0]

    for next_item in processed_items[1:]:
        # 检查 buffer_item 是否过短
        buffer_len = len(buffer_item['content'])
        
        # 判断是否需要合并:
        # 1. 长度不够
        # 2. 合并后不超过 max_chunk_size * 1.5 (稍微放宽上限以允许合并)
        # 注意：这里我们主要依据 min_chunk_size 来判断是否"过短"
        
        if buffer_len < min_chunk_size:
            # 尝试合并到 next_item? 或者把 next_item 合并到 buffer_item?
            # 通常是将短的 buffer_item 合并到 next_item 可能会导致 next_item 太大
            # 这里的逻辑是：累积 buffer 到 next_item
            
            # 合并 content
            # 如果是结构化模式，合并时要注意元数据的处理，通常保留第一个或合并header_path
            # 这里简单处理：保留 buffer 的 meta (如果是向后合并，可能保留 next 的更好？)
            # 让我们采用：将当前短段落追加到下一个段落的开头？不，通常是追加到上一个。
            # 但我们在遍历，buffer 是"当前待处理的累积块"。
            
            combined_len = len(buffer_item['content']) + len(next_item['content']) + 1
            if combined_len <= max_chunk_size * 1.2: # 允许溢出一点
                # 执行合并: buffer + next -> new buffer
                new_content = buffer_item['content'] + "\n\n" + next_item['content']
                # 元数据处理：优先保留 buffer 的，或者根据层级决定
                # 简单起见，保留 buffer 的 meta
                
                buffer_item['content'] = new_content
                # buffer_item['meta_data'] = buffer_item['meta_data'] # 保持不变
                # 继续下一次循环，buffer_item 变得更大了
            else:
                # 无法合并（太大了），buffer_item 必须独立存在
                merged_items.append(buffer_item)
                buffer_item = next_item
        else:
            # buffer 足够长，不需要合并，直接定稿
            merged_items.append(buffer_item)
            buffer_item = next_item
    
    # 处理最后一个 buffer
    merged_items.append(buffer_item)

    # 4. 重新编号
    final_data = []
    for idx, item in enumerate(merged_items):
        item['paragraph_number'] = idx + 1
        final_data.append(item)
    
    # 5. 构造最终 JSON 结构
    json_output = {'text_info': final_data}
    
    # 6. 保存文件
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
