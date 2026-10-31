import json
import os
import re
from typing import Generator, List, Optional, Tuple, Union

IMAGE_PATTERN = re.compile(r'^\s*!\[.*?\]\(.*?\)\s*$')
ATX_HEADER_PATTERN = re.compile(r'^(#{1,6})\s+(.+?)(\s+#+)?$')
SETEXT_HEADER_PATTERN = re.compile(r'^\s*(=){3,}\s*$|^\s*(-){3,}\s*$')
FENCED_CODE_PATTERN = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
CONTAINER_FENCE_PATTERN = re.compile(r'^\s*(:{3,})(.*)$')
MATH_BLOCK_PATTERN = re.compile(r'^\s*\$\$\s*$')
TABLE_SEPARATOR_PATTERN = re.compile(r'^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$')
HTML_TAG_PATTERN = re.compile(r'<(/?)([A-Za-z][\w:-]*)(?:\s[^<>]*?)?(/?)>')

HTML_BLOCK_TAGS = {
    'article', 'aside', 'blockquote', 'body', 'code', 'dd', 'details', 'div',
    'dl', 'dt', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'header', 'li', 'main', 'nav', 'ol', 'p', 'pre',
    'section', 'summary', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead',
    'tr', 'ul'
}
HTML_VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class _BufferedLineReader:
    def __init__(self, file_obj):
        self._iterator = iter(file_obj)
        self._buffer: List[str] = []

    def _fill(self, count: int) -> None:
        while len(self._buffer) < count:
            try:
                self._buffer.append(next(self._iterator).rstrip('\n'))
            except StopIteration:
                break

    def peek(self, offset: int = 0) -> Optional[str]:
        self._fill(offset + 1)
        if offset >= len(self._buffer):
            return None
        return self._buffer[offset]

    def next(self) -> Optional[str]:
        self._fill(1)
        if not self._buffer:
            return None
        return self._buffer.pop(0)


def read_markdown_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def _join_lines(lines: List[str]) -> str:
    return '\n'.join(lines)


def _build_metadata(
    level: int,
    headers: List[str],
    is_continuation: bool,
    is_image: bool = False,
    is_protected_block: bool = False,
    structure_kind: Optional[str] = None,
) -> dict:
    metadata = {
        'current_level': level,
        'header_path': headers.copy(),
        'is_continuation': is_continuation,
        'is_image': is_image,
        'is_protected_block': is_protected_block,
    }
    if structure_kind:
        metadata['structure_kind'] = structure_kind
    return metadata


def _format_output(
    chunk: List[str],
    level: int,
    headers: List[str],
    is_continuation: bool,
    return_metadata: bool,
    *,
    is_image: bool = False,
    is_protected_block: bool = False,
    structure_kind: Optional[str] = None,
):
    formatted_text = _join_lines(chunk)
    if not return_metadata:
        return formatted_text
    return (
        formatted_text,
        _build_metadata(
            level,
            headers,
            is_continuation,
            is_image=is_image,
            is_protected_block=is_protected_block,
            structure_kind=structure_kind,
        ),
    )


def _is_image_line(line: str) -> bool:
    return bool(IMAGE_PATTERN.match(line))


def _is_markdown_table_header(line: str, next_line: Optional[str]) -> bool:
    if next_line is None:
        return False
    stripped = line.strip()
    if not stripped or '|' not in stripped:
        return False
    return bool(TABLE_SEPARATOR_PATTERN.match(next_line.strip()))


def _looks_like_markdown_table_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if TABLE_SEPARATOR_PATTERN.match(stripped):
        return True
    return '|' in stripped


def _collect_markdown_table(first_line: str, second_line: str, reader: _BufferedLineReader) -> List[str]:
    lines = [first_line, second_line]
    while True:
        next_line = reader.peek()
        if next_line is None or not _looks_like_markdown_table_row(next_line):
            break
        lines.append(reader.next() or '')
    return lines


def _collect_fenced_block(first_line: str, reader: _BufferedLineReader) -> Tuple[str, List[str]]:
    fence_match = FENCED_CODE_PATTERN.match(first_line)
    if fence_match:
        opening_fence = fence_match.group(1)
        fence_char = opening_fence[0]
        min_length = len(opening_fence)
        closing_pattern = re.compile(rf'^\s*{re.escape(fence_char)}{{{min_length},}}\s*$')
        kind = 'code_fence'
    elif MATH_BLOCK_PATTERN.match(first_line):
        closing_pattern = MATH_BLOCK_PATTERN
        kind = 'math_block'
    else:
        opening_fence = CONTAINER_FENCE_PATTERN.match(first_line)
        min_length = len(opening_fence.group(1)) if opening_fence else 3
        closing_pattern = re.compile(rf'^\s*:{{{min_length},}}\s*$')
        kind = 'paired_block'

    lines = [first_line]
    while True:
        line = reader.next()
        if line is None:
            break
        lines.append(line)
        if closing_pattern.match(line):
            break
    return kind, lines


def _extract_html_boundary_tag(line: str) -> Tuple[Optional[str], Optional[str]]:
    stripped = line.strip()
    opening_tag: Optional[str] = None
    closing_tag: Optional[str] = None
    for is_closing, tag_name, self_closing in HTML_TAG_PATTERN.findall(stripped):
        tag = tag_name.lower()
        if tag not in HTML_BLOCK_TAGS or tag in HTML_VOID_TAGS:
            continue
        if is_closing:
            closing_tag = tag
        elif not self_closing:
            opening_tag = tag
    return opening_tag, closing_tag


def _update_html_stack(stack: List[str], line: str) -> None:
    stripped = line.strip()
    if stripped.startswith('<!--'):
        return

    for is_closing, tag_name, self_closing in HTML_TAG_PATTERN.findall(line):
        tag = tag_name.lower()
        if tag not in HTML_BLOCK_TAGS or tag in HTML_VOID_TAGS:
            continue
        if is_closing:
            for idx in range(len(stack) - 1, -1, -1):
                if stack[idx] == tag:
                    del stack[idx:]
                    break
        elif not self_closing:
            stack.append(tag)


def _is_html_block_start(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith('<!--'):
        return True
    if not stripped.startswith('<') or stripped.startswith('</'):
        return False
    opening_tag, _ = _extract_html_boundary_tag(line)
    return opening_tag is not None


def _collect_html_block(first_line: str, reader: _BufferedLineReader) -> List[str]:
    lines = [first_line]
    stripped = first_line.strip()
    if stripped.startswith('<!--') and '-->' not in stripped:
        while True:
            line = reader.next()
            if line is None:
                break
            lines.append(line)
            if '-->' in line:
                break
        return lines

    stack: List[str] = []
    _update_html_stack(stack, first_line)
    while stack:
        line = reader.next()
        if line is None:
            break
        lines.append(line)
        _update_html_stack(stack, line)
    return lines


def _split_plain_text(text: str, max_size: int) -> List[str]:
    if max_size <= 0 or len(text) <= max_size:
        return [text]

    pieces = []
    remaining = text
    while remaining:
        if len(remaining) <= max_size:
            pieces.append(remaining)
            break
        split_pos = _find_split_position(remaining, max_size)
        if split_pos <= 0:
            split_pos = max_size
        piece = remaining[:split_pos].rstrip()
        if not piece:
            piece = remaining[:max_size]
            split_pos = len(piece)
        pieces.append(piece)
        remaining = remaining[split_pos:].lstrip()
    return pieces


def _split_long_line_with_wrappers(
    line: str,
    max_chunk_size: int,
    prefix_lines: Optional[List[str]] = None,
    suffix_lines: Optional[List[str]] = None,
) -> List[str]:
    prefix_lines = prefix_lines or []
    suffix_lines = suffix_lines or []
    if len(_join_lines(prefix_lines + ['x'] + suffix_lines)) > max_chunk_size:
        return [_join_lines(prefix_lines + [line] + suffix_lines)]

    pieces = []
    low = 1
    high = len(line)
    available_space = 0
    while low <= high:
        mid = (low + high) // 2
        candidate = _join_lines(prefix_lines + [('x' * mid)] + suffix_lines)
        if len(candidate) <= max_chunk_size:
            available_space = mid
            low = mid + 1
        else:
            high = mid - 1

    if available_space <= 0:
        return [_join_lines(prefix_lines + [line] + suffix_lines)]

    for piece in _split_plain_text(line, available_space):
        candidate = _join_lines(prefix_lines + [piece] + suffix_lines)
        if len(candidate) <= max_chunk_size:
            pieces.append(candidate)
        else:
            return [_join_lines(prefix_lines + [line] + suffix_lines)]
    return pieces


def _split_block_by_lines(
    body_lines: List[str],
    max_chunk_size: int,
    prefix_lines: Optional[List[str]] = None,
    suffix_lines: Optional[List[str]] = None,
) -> List[str]:
    prefix_lines = prefix_lines or []
    suffix_lines = suffix_lines or []

    chunks: List[str] = []
    current_body: List[str] = []

    for line in body_lines:
        candidate = _join_lines(prefix_lines + current_body + [line] + suffix_lines)
        if current_body and len(candidate) > max_chunk_size:
            chunks.append(_join_lines(prefix_lines + current_body + suffix_lines))
            current_body = []

        single_line_candidate = _join_lines(prefix_lines + [line] + suffix_lines)
        if len(single_line_candidate) > max_chunk_size:
            chunks.extend(_split_long_line_with_wrappers(line, max_chunk_size, prefix_lines, suffix_lines))
            continue

        current_body.append(line)

    if current_body or not body_lines:
        final_chunk = _join_lines(prefix_lines + current_body + suffix_lines)
        if final_chunk:
            chunks.append(final_chunk)
    return chunks


def _split_special_block(kind: str, lines: List[str], max_chunk_size: int) -> List[str]:
    block_text = _join_lines(lines)
    if len(block_text) <= max_chunk_size:
        return [block_text]

    if kind == 'markdown_table' and len(lines) > 2:
        return _split_block_by_lines(lines[2:], max_chunk_size, prefix_lines=lines[:2])

    if kind in {'code_fence', 'paired_block', 'math_block'} and len(lines) > 2:
        return _split_block_by_lines(lines[1:-1], max_chunk_size, prefix_lines=[lines[0]], suffix_lines=[lines[-1]])

    if kind == 'html_block' and len(lines) > 2:
        opening_tag, _ = _extract_html_boundary_tag(lines[0])
        _, closing_tag = _extract_html_boundary_tag(lines[-1])
        if opening_tag and closing_tag and opening_tag == closing_tag:
            return _split_block_by_lines(lines[1:-1], max_chunk_size, prefix_lines=[lines[0]], suffix_lines=[lines[-1]])
        return _split_block_by_lines(lines, max_chunk_size)

    return _split_block_by_lines(lines, max_chunk_size)


def _detect_special_block(line: str, reader: _BufferedLineReader) -> Optional[Tuple[str, List[str]]]:
    if _is_image_line(line):
        return 'image', [line]

    if FENCED_CODE_PATTERN.match(line) or MATH_BLOCK_PATTERN.match(line) or CONTAINER_FENCE_PATTERN.match(line):
        return _collect_fenced_block(line, reader)

    next_line = reader.peek()
    if _is_markdown_table_header(line, next_line):
        second_line = reader.next()
        if second_line is not None:
            return 'markdown_table', _collect_markdown_table(line, second_line, reader)

    if _is_html_block_start(line):
        return 'html_block', _collect_html_block(line, reader)

    return None


def _emit_special_block(
    kind: str,
    lines: List[str],
    current_level: int,
    header_stack: List[str],
    preserve_structure: bool,
    max_chunk_size: int,
) -> Generator[Union[str, Tuple[str, dict]], None, None]:
    if kind == 'image':
        yield _format_output(
            lines,
            current_level,
            header_stack.copy(),
            False,
            preserve_structure,
            is_image=True,
        )
        return

    split_chunks = _split_special_block(kind, lines, max_chunk_size)
    for index, chunk_text in enumerate(split_chunks):
        yield _format_output(
            [chunk_text],
            current_level,
            header_stack.copy(),
            index > 0,
            preserve_structure,
            is_protected_block=True,
            structure_kind=kind,
        )


def read_structured_paragraphs(
    file_path: str,
    max_chunk_size: int = 600,
    min_chunk_size: int = 300,
    preserve_structure: bool = True
) -> Generator[Union[str, Tuple[str, dict]], None, None]:
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = _BufferedLineReader(file)

        if preserve_structure:
            current_chunk: List[str] = []
            chunk_length = 0
            current_level = 0
            header_stack: List[str] = []
            continuation_flag = False

            while True:
                line = reader.next()
                if line is None:
                    break

                stripped_line = line.strip()
                special_block = _detect_special_block(line, reader)
                if special_block:
                    if current_chunk:
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure,
                        )
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False
                    kind, lines = special_block
                    yield from _emit_special_block(kind, lines, current_level, header_stack, preserve_structure, max_chunk_size)
                    continue

                next_line = reader.peek()
                header_match = ATX_HEADER_PATTERN.match(line)
                setext_match = bool(stripped_line and next_line and SETEXT_HEADER_PATTERN.match(next_line.strip()))

                if header_match or setext_match:
                    if header_match:
                        header_level = len(header_match.group(1))
                        header_text = header_match.group(2).strip()
                        header_line = line
                    else:
                        underline = reader.next() or ''
                        header_level = 1 if '=' in underline else 2
                        header_text = stripped_line
                        header_line = f"{'#' * header_level} {header_text}"

                    should_yield = False
                    if current_chunk:
                        if header_level <= current_level:
                            should_yield = True
                        elif chunk_length + len(header_line) > max_chunk_size * 0.8:
                            should_yield = True

                    if should_yield:
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure,
                        )
                        current_chunk = []
                        chunk_length = 0
                        continuation_flag = False

                    current_level = header_level
                    while len(header_stack) >= current_level:
                        header_stack.pop()
                    header_stack.append(f"{'#' * header_level} {header_text}")
                    current_chunk.append(header_line)
                    chunk_length += len(header_line) + 1
                    continuation_flag = False
                    continue

                if not stripped_line:
                    if current_chunk and (not current_chunk or current_chunk[-1] != ''):
                        current_chunk.append('')
                        chunk_length += 1
                    continue

                line_length = len(line) + 1
                if chunk_length + line_length > max_chunk_size:
                    if current_chunk:
                        yield _format_output(
                            current_chunk,
                            current_level,
                            header_stack.copy(),
                            continuation_flag,
                            preserve_structure,
                        )
                    current_chunk = []
                    chunk_length = 0

                    split_pieces = _split_plain_text(line, max_chunk_size)
                    for split_index, piece in enumerate(split_pieces[:-1]):
                        yield _format_output(
                            [piece],
                            current_level,
                            header_stack.copy(),
                            continuation_flag or split_index > 0,
                            preserve_structure,
                        )
                    current_chunk = [split_pieces[-1]]
                    chunk_length = len(split_pieces[-1]) + 1
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
                    preserve_structure,
                )
            return

        pending_chunks: List[str] = []
        pending_length = 0
        current_chunk: List[str] = []
        chunk_length = 0

        def flush_pending() -> Optional[str]:
            nonlocal pending_chunks, pending_length
            if not pending_chunks:
                return None
            combined_text = '\n\n'.join(pending_chunks)
            pending_chunks = []
            pending_length = 0
            return combined_text

        def commit_text_chunk(chunk_text: str, min_size: int = min_chunk_size) -> Generator[str, None, None]:
            nonlocal pending_length
            if not chunk_text:
                return
            if len(chunk_text) < min_size:
                pending_chunks.append(chunk_text)
                pending_length += len(chunk_text)
                if pending_length >= max_chunk_size:
                    flushed = flush_pending()
                    if flushed:
                        yield flushed
                return
            flushed = flush_pending()
            if flushed:
                yield flushed
            yield chunk_text

        while True:
            line = reader.next()
            if line is None:
                break

            special_block = _detect_special_block(line, reader)
            if special_block:
                if current_chunk:
                    chunk_text = _join_lines(current_chunk)
                    current_chunk = []
                    chunk_length = 0
                    yield from commit_text_chunk(chunk_text)
                flushed = flush_pending()
                if flushed:
                    yield flushed
                kind, lines = special_block
                if kind == 'image':
                    yield lines[0]
                else:
                    for chunk_text in _split_special_block(kind, lines, max_chunk_size):
                        yield chunk_text
                continue

            stripped_line = line.strip()
            if not stripped_line:
                if current_chunk:
                    chunk_text = _join_lines(current_chunk)
                    current_chunk = []
                    chunk_length = 0
                    yield from commit_text_chunk(chunk_text)
                continue

            line_length = len(line) + 1
            if chunk_length + line_length > max_chunk_size:
                if current_chunk:
                    yield from commit_text_chunk(_join_lines(current_chunk))
                    current_chunk = []
                    chunk_length = 0
                split_pieces = _split_plain_text(line, max_chunk_size)
                for piece in split_pieces[:-1]:
                    yield from commit_text_chunk(piece)
                current_chunk = [split_pieces[-1]]
                chunk_length = len(split_pieces[-1]) + 1
            else:
                current_chunk.append(line)
                chunk_length += line_length

        if current_chunk:
            yield from commit_text_chunk(_join_lines(current_chunk))
        flushed = flush_pending()
        if flushed:
            yield flushed

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
    读取文档，将其切分为适合翻译的段落，并将过短的纯文本段落合并，最终生成结构化 JSON。

    该函数的核心功能是后处理（Post-Processing）：
    1. 先把文档分解成最细粒度的“原子”段落；
    2. 对纯文本短段落做受控合并；
    3. 对表格、HTML 块、代码围栏、成对容器等受保护结构保持硬边界，
       仅在块体本身超长时按安全规则拆分。

    Args:
        file_path (str): 输入文件的路径。
        max_chunk_size (int): 合并后段落内容的最大长度阈值。
        min_chunk_size (int): 判断段落是否“过短”的最小长度阈值。
        preserve_structure (bool): 是否保留文档的结构信息（如标题层级）。

    Returns:
        str: 生成的 JSON 文件的绝对路径。如果处理失败或无内容，则返回空字符串。
    """
    # 步骤 1: 获取原子段落。
    # 这里强制 min_chunk_size=0，让 read_structured_paragraphs 只负责边界识别和安全拆分，
    # 后续是否合并完全由本函数控制，避免边界判断与合并策略互相干扰。
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
            'matched_terms': [],
            'status': 'pending'
        })

    # 步骤 3: 核心合并逻辑（增强版）。
    # 当前策略只允许跨图片跳过合并；表格、HTML、代码围栏等受保护结构会强制作为边界保留。
    # 这样做的目标是减少“半截结构段”进入翻译环节。
    merged_items = []
    i = 0
    while i < len(processed_items):
        # 将当前项作为“累加器”开始一个新的合并周期
        buffer_item = processed_items[i]
        i += 1  # 预先消耗当前项

        # 如果累加器本身是图片，则它不能合并其他内容。直接将其定稿并继续。
        buffer_meta = buffer_item.get('meta_data') or {}
        is_buffer_protected = buffer_meta.get('is_image') or buffer_meta.get('is_protected_block')
        if is_buffer_protected:
            merged_items.append(buffer_item)
            continue

        # 仅允许跨图片跳过合并；其他受保护结构必须保留为硬边界。
        pending_images = []

        # 内部循环：只要合并成功，就持续尝试将后续文本合并到当前累加器中
        while True:
            # --- 向前查找下一个可合并的纯文本段落 ---
            search_j = i
            images_skipped_this_round = []
            next_text_item = None
            next_text_item_index = -1

            while search_j < len(processed_items):
                candidate = processed_items[search_j]
                candidate_meta = candidate.get('meta_data') or {}
                if candidate_meta.get('is_image'):
                    images_skipped_this_round.append(candidate)
                    search_j += 1
                elif candidate_meta.get('is_protected_block'):
                    next_text_item = None
                    next_text_item_index = -1
                    break
                else:
                    next_text_item = candidate
                    next_text_item_index = search_j
                    break  # 找到了下一个文本段落

            # 如果找不到更多的可合并纯文本段落，则当前累加器的合并周期结束。
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
            # 如果不满足合并条件（例如，合并后超长），则停止当前累加器的合并周期。
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

def _find_split_position(line, remaining_space):
    if remaining_space <= 0:
        return 0
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
