import asyncio
import time
import logging
import re
import json
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from modules.api_tool import LLMService
from modules.csv_process_tool import find_matching_terms

logger = logging.getLogger(__name__)

PARTIAL_RESULT_WARNING = "注意：该段落采用降级结果，译文正文可用，但术语/注释可能不完整，新术语未写入。"
CONSERVATIVE_RECOVERY_WARNING = "注意：该段落由保守解析恢复，已优先保留译文正文与结构边界；术语/注释可能不完整，新术语未写入，请人工复核。"
TARGETED_FALLBACK_WARNING = "注意：该段落触发定向 fallback，已切换到更保守的处理路径，优先保留译文正文与结构边界；术语/注释可能简化，新术语未写入，请人工复核。"
TARGETED_FALLBACK_PROVIDERS = {"kimi", "gemini", "doubao"}
PROVIDER_STRUCTURED_FAILURE_PATTERNS = [
    (re.compile(r"invalid json|json repair failed|json decode|unterminated", re.IGNORECASE), "bad_json_output"),
    (re.compile(r"structured|non-structured|validation", re.IGNORECASE), "structured_output_unstable"),
    (re.compile(r"expecting value|unterminated string|extra data", re.IGNORECASE), "json_shape_invalid"),
]

def _append_warning_message(notes: str, warning: str) -> str:
    note_parts = [part for part in [notes.strip(), warning] if part]
    return "\n".join(note_parts)

def _deduplicate_preserve_order(items: List[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))

def _detect_content_risk_features(paragraph_text: str, meta_data: Optional[Dict[str, Any]]) -> List[str]:
    features: List[str] = []
    metadata = meta_data or {}
    structure_kind = str(metadata.get("structure_kind", "")).strip()

    if metadata.get("is_protected_block"):
        features.append(f"protected_block:{structure_kind or 'generic'}")
    if structure_kind == "markdown_table" or re.search(r"^\s*\|.+\|\s*$", paragraph_text, re.MULTILINE):
        features.append("markdown_table")
    if structure_kind == "html_block" or (re.search(r"<[A-Za-z][^>]*>", paragraph_text) and re.search(r"</[A-Za-z][^>]*>", paragraph_text)):
        features.append("html_block")
    if structure_kind == "code_fence" or "```" in paragraph_text:
        features.append("code_fence")
    if structure_kind == "directive_block" or re.search(r"^\s*:::\s*\w*", paragraph_text, re.MULTILINE):
        features.append("directive_block")
    if re.search(r"(?m)^\s*(?:[-*+]|\d+\.)\s+.+\n(?:\s{2,}(?:[-*+]|\d+\.)\s+.+\n?){1,}", paragraph_text):
        features.append("nested_list")

    return _deduplicate_preserve_order(features)

def _extract_provider_failure_features(provider: str, error_text: str) -> List[str]:
    provider_name = (provider or "").lower()
    if provider_name not in TARGETED_FALLBACK_PROVIDERS:
        return []

    matched_features = [
        feature_name
        for pattern, feature_name in PROVIDER_STRUCTURED_FAILURE_PATTERNS
        if pattern.search(error_text or "")
    ]
    return _deduplicate_preserve_order(matched_features)

def _build_targeted_fallback_prompt(
    base_prompt: str,
    content_features: List[str],
    provider_failure_features: List[str],
) -> str:
    triggers = []
    if content_features:
        triggers.append("内容特征：" + "、".join(content_features))
    if provider_failure_features:
        triggers.append("provider失败特征：" + "、".join(provider_failure_features))

    conservative_instruction = (
        "\n\n【定向 fallback 模式】\n"
        f"触发原因：{'；'.join(triggers) if triggers else '高风险内容或结构化输出不稳定'}。\n"
        "请继续仅输出 JSON，字段严格限制为 translation 和 new_terms。\n"
        "处理优先级：1. 保住译文正文可读且不丢段；2. 尽量保持 Markdown/HTML/代码围栏/表格/列表等结构边界完整；"
        "3. 术语与注释可以简化，若不确定请让 new_terms 返回空数组。\n"
        "不要解释，不要添加额外字段，不要把说明文字写进 translation。"
    )
    return f"{base_prompt}{conservative_instruction}"

def _decode_recovered_text(raw_text: str, quote_char: str = '"') -> str:
    cleaned = raw_text.strip()
    if not cleaned:
        return ""

    normalized = cleaned
    if quote_char == "'":
        normalized = normalized.replace('"', '\\"')

    try:
        return json.loads(f'"{normalized}"')
    except Exception:
        text = cleaned
        text = text.replace(r"\\", "\\")
        text = text.replace(r"\/", "/")
        text = text.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
        text = text.replace(r"\"", '"').replace(r"\'", "'")
        return text

def _find_field_value_start(text: str, field_name: str) -> int:
    field_pattern = re.compile(
        rf'(?:"{re.escape(field_name)}"|\'{re.escape(field_name)}\'|\b{re.escape(field_name)}\b)\s*:\s*',
        re.IGNORECASE,
    )
    match = field_pattern.search(text)
    return match.end() if match else -1

def _find_next_field_boundary(text: str, start: int, next_fields: List[str]) -> int:
    boundary = len(text)

    if next_fields:
        names = "|".join(re.escape(field) for field in next_fields)
        next_field_pattern = re.compile(
            rf',\s*(?:"(?:{names})"|\'(?:{names})\'|(?:{names}))\s*:',
            re.IGNORECASE,
        )
        match = next_field_pattern.search(text, start)
        if match:
            boundary = min(boundary, match.start())

    closing_brace = text.find("}", start)
    if closing_brace != -1:
        boundary = min(boundary, closing_brace)

    return boundary

def _read_quoted_value(text: str, quote_start: int, next_fields: List[str]) -> tuple[str, bool]:
    quote_char = text[quote_start]
    index = quote_start + 1
    escaped = False

    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote_char:
            return text[quote_start + 1:index], True
        index += 1

    boundary = _find_next_field_boundary(text, quote_start + 1, next_fields)
    recovered = text[quote_start + 1:boundary].rstrip().rstrip(",").rstrip()
    return recovered, False

def _extract_string_field(text: str, field_name: str, next_fields: List[str]) -> tuple[str, bool]:
    value_start = _find_field_value_start(text, field_name)
    if value_start == -1:
        return "", False

    while value_start < len(text) and text[value_start].isspace():
        value_start += 1

    if value_start >= len(text):
        return "", False

    first_char = text[value_start]
    if first_char in ('"', "'"):
        raw_value, closed = _read_quoted_value(text, value_start, next_fields)
        return _decode_recovered_text(raw_value, first_char), closed

    boundary = _find_next_field_boundary(text, value_start, next_fields)
    raw_value = text[value_start:boundary].strip().rstrip(",")
    return _decode_recovered_text(raw_value), False

def _recover_from_invalid_json(origin_text: str) -> Optional[Dict[str, str]]:
    translation, _ = _extract_string_field(origin_text, "translation", ["notes", "new_terms"])
    if not translation.strip():
        return None

    notes, _ = _extract_string_field(origin_text, "notes", ["new_terms"])
    return {"translation": translation, "notes": notes}

def _extract_request_metadata(llm_service: Any) -> Dict[str, Any]:
    metadata = getattr(llm_service, "last_prompt_metadata", {})
    if not isinstance(metadata, dict):
        return {}
    return dict(metadata)

class WritePolicy(Enum):
    PLAIN_MD = "plain_md"
    ORDERED_JSON = "ordered_json"

class RepairPolicy(Enum):
    RETRY_MAX_5 = 5
    RETRY_MAX_3 = 3
    NONE = 0

class TerminologyPolicy(Enum):
    MERGE_ON_CONFLICT = "merge_on_conflict"
    KEEP_ORIGINAL = "keep_original"

class TranslationResult(BaseModel):
    content: str
    notes: str
    tokens: int
    repair_tokens: int
    new_terms_delta: List[Dict[str, str]]
    matched_terms_delta: List[Dict[str, str]] = []
    header_path: List[str]
    request_metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

class TranslationCore:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def execute_translation_step(
        self,
        segment: Dict[str, Any],
        terms_dict: Dict[str, Any],
        aggregated_new_terms: Dict[str, Any],
        tracker_state: Optional[Any] = None,
        repair_policy: RepairPolicy = RepairPolicy.RETRY_MAX_5,
        terminology_policy: TerminologyPolicy = TerminologyPolicy.MERGE_ON_CONFLICT,
        max_api_retries: int = 3
    ) -> TranslationResult:
        """
        执行单段翻译的核心流程：
        1. 术语匹配（合并全局新术语）
        2. Prompt 构造
        3. API 调用与重试（含 JSON 修复）
        4. 针对高风险内容或 provider 结构化失败启用定向 fallback
        5. 术语一致性复写（仅在常规路径下执行）
        6. 若结构化解析仍失败，则尝试保守恢复正文与结构边界
        """
        
        paragraph_text = segment.get("content", "")
        meta_data = segment.get("meta_data", {})
        header_path = meta_data.get("header_path", []) if meta_data else []
        request_metadata: Dict[str, Any] = {}
        
        # 0. 检查是否为非文本内容（如图片）
        # 如果是图片，直接返回原始内容，不调用 LLM
        if meta_data and meta_data.get('is_image'):
            logger.info("Skipping translation for image/non-text content.")
            return TranslationResult(
                content=paragraph_text, # 原样返回
                notes="",
                tokens=0,
                repair_tokens=0,
                new_terms_delta=[],
                matched_terms_delta=[],
                header_path=header_path,
                request_metadata=request_metadata,
                success=True
            )
        
        # 1. 准备术语表：基础词表 + 已聚合的新术语
        # 注意：这里只读不写 aggregated_new_terms，写入由调用方处理
        current_terms = terms_dict.copy()
        current_terms.update(aggregated_new_terms)
        
        matched_terms = await asyncio.to_thread(find_matching_terms, paragraph_text, current_terms)
        
        matched_terms_list = []
        for term, info in matched_terms.items():
            if isinstance(info, dict):
                matched_terms_list.append({
                    "term": term,
                    "translation": info.get('translation', ''),
                    "reason": info.get('reason', '')
                })
            else:
                matched_terms_list.append({
                    "term": term,
                    "translation": str(info),
                    "reason": ""
                })

        # 2. 构造 Prompt
        prompt = self.llm_service.create_prompt(paragraph_text, matched_terms)
        request_metadata = _extract_request_metadata(self.llm_service)
        provider_name = str(getattr(self.llm_service, "provider", "") or "").lower()
        content_risk_features = _detect_content_risk_features(paragraph_text, meta_data)
        provider_failure_features: List[str] = []
        # 高风险内容会预先启用更保守的 JSON 输出约束；
        # 普通内容则在检测到 provider 的结构化失败模式后再切换。
        targeted_fallback_active = bool(content_risk_features)
        if targeted_fallback_active:
            logger.info(
                "Targeted fallback pre-armed for provider=%s, paragraph features=%s",
                provider_name or "unknown",
                ",".join(content_risk_features),
            )
        
        # 3. API 调用与重试循环
        attempts = 0
        last_error = None
        last_response_data = {}
        repair_tokens = 0
        tokens = 0
        while attempts < max_api_retries:
            try:
                active_prompt = prompt
                if targeted_fallback_active:
                    active_prompt = _build_targeted_fallback_prompt(
                        prompt,
                        content_risk_features,
                        provider_failure_features,
                    )

                # llm_service.call_ai_model_api_async 内部已经处理了同步/异步兼容与基础解析。
                response_data, tokens = await self.llm_service.call_ai_model_api_async(active_prompt)
                last_response_data = response_data
                # 检查是否需要 JSON 修复
                # call_ai_model_api 已经在 structured=True 时尝试了解析，如果失败会返回 error 字段
                if "error" in response_data:
                    # 尝试修复
                    repair_attempts = 0
                    max_repair = repair_policy.value
                    origin_text = response_data.get("origin_text", "")
                    
                    repaired = False
                    while repair_attempts < max_repair:
                        try:
                            # 修复调用异步接口
                            response_data, add_tokens = await self.llm_service.repair_json_async(origin_text)
                            repair_tokens += add_tokens
                            if "error" not in response_data:
                                repaired = True
                                break
                        except Exception:
                            pass
                        repair_attempts += 1
                    
                    if not repaired:
                        raise ValueError(f"JSON repair failed after {max_repair} attempts: {response_data.get('error')}")

                if targeted_fallback_active:
                    fallback_notes = response_data.get("notes", "")
                    response_data["notes"] = _append_warning_message(
                        fallback_notes,
                        TARGETED_FALLBACK_WARNING,
                    )
                    response_data["new_terms"] = []

                # 4. 术语一致性复写 (Rewrite with Glossary)
                # 检查新生成的术语是否与已知术语冲突
                new_terms_list = response_data.get("new_terms", [])
                corrections = {}
                
                if terminology_policy == TerminologyPolicy.MERGE_ON_CONFLICT and not targeted_fallback_active:
                    for item in new_terms_list:
                        term = item.get("term", "").strip()
                        translation = item.get("translation", "").strip()
                        if not term or not translation:
                            continue
                        
                        # 如果该术语已在权威词表中，且译名不一致
                        if term in current_terms:
                            # Check if current_terms value is dict or string
                            expected_val = current_terms[term]
                            expected = expected_val.get('translation', '') if isinstance(expected_val, dict) else str(expected_val)
                            
                            if translation != expected:
                                corrections[term] = expected
                
                # 如果有冲突，进行复写
                if corrections:
                    if hasattr(self.llm_service, 'rewrite_with_glossary_async'):
                        translation = response_data.get("translation", "")
                        notes = response_data.get("notes", "")
                        # 复写（异步）
                        rewrite_result, rewrite_tokens = await self.llm_service.rewrite_with_glossary_async(
                            translation, 
                            notes, 
                            corrections
                        )
                        tokens += rewrite_tokens
                        
                        # 检查复写结果是否包含错误，并尝试修复
                        if "error" in rewrite_result:
                            repair_attempts = 0
                            max_repair = repair_policy.value
                            origin_text = rewrite_result.get("origin_text", "")
                            
                            repaired = False
                            while repair_attempts < max_repair:
                                try:
                                    rewrite_result, add_tokens = await self.llm_service.repair_json_async(origin_text)
                                    tokens += add_tokens
                                    if "error" not in rewrite_result:
                                        repaired = True
                                        break
                                except Exception:
                                    pass
                                repair_attempts += 1
                            
                            if not repaired:
                                logger.warning(f"Glossary rewrite JSON repair failed after {max_repair} attempts: {rewrite_result.get('error')}. Using original translation.")
                                # 如果修复失败，rewrite_result 仍然是错误的，下面的 .get() 会回退到原值，这符合预期降级行为
                        
                        # 更新结果
                        response_data["translation"] = rewrite_result.get("translation", translation)
                        response_data["notes"] = rewrite_result.get("notes", notes)
                        
                        # 从新术语列表中移除被纠正的术语
                        # 因为它们已经被复写为标准译名，不再视为"新术语"
                        response_data["new_terms"] = [
                            t for t in new_terms_list 
                            if t.get("term") not in corrections
                        ]
                    else:
                        # 如果服务不支持术语复写（如接口未实现），则跳过复写步骤
                        # 保持原译文和新术语列表
                        logger.warning("LLMService instance missing 'rewrite_with_glossary' method. Skipping glossary rewrite step.")
                        pass

                # 成功返回
                return TranslationResult(
                    content=response_data.get("translation", ""),
                    notes=response_data.get("notes", ""),
                    tokens=tokens,
                    repair_tokens=repair_tokens,
                    new_terms_delta=response_data.get("new_terms", []),
                    matched_terms_delta=matched_terms_list,
                    header_path=header_path,
                    request_metadata=request_metadata,
                    success=True
                )

            except Exception as e:
                last_error = str(e)
                error_fragments = [last_error]
                if isinstance(last_response_data, dict):
                    response_error = str(last_response_data.get("error", "")).strip()
                    if response_error:
                        error_fragments.append(response_error)
                provider_failure_features = _extract_provider_failure_features(
                    provider_name,
                    " | ".join(fragment for fragment in error_fragments if fragment),
                )
                if provider_failure_features and not targeted_fallback_active:
                    targeted_fallback_active = True
                    logger.warning(
                        "Enabling targeted fallback for provider=%s after failure features=%s",
                        provider_name or "unknown",
                        ",".join(provider_failure_features),
                    )
                attempts += 1
                # 简单的指数退避
                await asyncio.sleep(1 * attempts)
        
        # 如果重试耗尽，优先保可读正文，其次保守恢复结构边界，不强求完整术语输出。
        if last_response_data and isinstance(last_response_data, dict) and "error" not in last_response_data:
            final_translation = last_response_data.get("translation", "")
            final_notes = last_response_data.get("notes", "")
            
            # 如果有译文，说明至少解析出了 translation 字段
            if final_translation:
                final_notes = _append_warning_message(final_notes, PARTIAL_RESULT_WARNING)
                
                logger.warning(f"Returning partial result after max retries. Error: {last_error}")
                
                return TranslationResult(
                    content=final_translation,
                    notes=final_notes,
                    tokens=tokens, 
                    repair_tokens=repair_tokens,
                    new_terms_delta=[], # 术语录入异常，不返回新术语
                    matched_terms_delta=matched_terms_list,
                    header_path=header_path,
                    request_metadata=request_metadata,
                    success=True # 标记为成功以便写入文件，但带有警告
                )

        # 兜底：尝试从坏 JSON 中仅恢复 translation / notes，放弃 new_terms 回写。
        if last_response_data and isinstance(last_response_data, dict) and "error" in last_response_data and "origin_text" in last_response_data:
            origin_text = last_response_data.get("origin_text", "")
            recovered_payload = _recover_from_invalid_json(origin_text)

            if recovered_payload:
                final_translation = recovered_payload["translation"]
                final_notes = _append_warning_message(
                    recovered_payload.get("notes", ""),
                    CONSERVATIVE_RECOVERY_WARNING,
                )

                logger.warning(f"Recovered translation from invalid JSON. Original Error: {last_response_data.get('error')}")
                
                return TranslationResult(
                    content=final_translation,
                    notes=final_notes,
                    tokens=tokens,
                    repair_tokens=repair_tokens,
                    new_terms_delta=[], 
                    matched_terms_delta=matched_terms_list,
                    header_path=header_path,
                    request_metadata=request_metadata,
                    success=True
                )

        return TranslationResult(
            content="",
            notes="",
            tokens=0,
            repair_tokens=0,
            new_terms_delta=[],
            matched_terms_delta=[],
            header_path=header_path,
            request_metadata=request_metadata,
            success=False,
            error=f"Max retries ({max_api_retries}) reached. Last error: {last_error}"
        )
