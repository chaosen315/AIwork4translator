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
