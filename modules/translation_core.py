import asyncio
import time
import logging
import re
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel

from modules.api_tool import LLMService
from modules.csv_process_tool import find_matching_terms

logger = logging.getLogger(__name__)

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
    header_path: List[str]
    success: bool = True
    error: Optional[str] = None

class TranslationCore:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def execute_translation_step(
        self,
        segment: Dict[str, Any],
        terms_dict: Dict[str, str],
        aggregated_new_terms: Dict[str, str],
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
        4. 术语一致性复写（可选）
        5. 结果封装
        """
        
        paragraph_text = segment.get("content", "")
        meta_data = segment.get("meta_data", {})
        header_path = meta_data.get("header_path", []) if meta_data else []
        
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
                header_path=header_path,
                success=True
            )
        
        # 1. 准备术语表：基础词表 + 已聚合的新术语
        # 注意：这里只读不写 aggregated_new_terms，写入由调用方处理
        current_terms = terms_dict.copy()
        current_terms.update(aggregated_new_terms)
        
        matched_terms = await asyncio.to_thread(find_matching_terms, paragraph_text, current_terms)
        
        # 2. 构造 Prompt
        prompt = self.llm_service.create_prompt(paragraph_text, matched_terms)
        
        # 3. API 调用与重试循环
        attempts = 0
        last_error = None
        last_response_data = {}
        repair_tokens = 0
        while attempts < max_api_retries:
            try:
                # 异步调用 API（如果 LLMService 内部是同步的，使用 to_thread）
                # 注意：llm_service.call_ai_model_api 内部已经包含了解析逻辑
                # 但我们需要处理网络层面的重试，以及 JSON 修复层面的重试
                
                # 这里假设 call_ai_model_api 是同步的，我们把它放到线程里跑
                # 如果它本身支持异步，可以直接 await。目前看它是同步的。
                response_data, tokens = await asyncio.to_thread(self.llm_service.call_ai_model_api, prompt)
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
                            # 修复也是 IO 操作，放线程里
                            response_data, add_tokens = await asyncio.to_thread(self.llm_service.repair_json, origin_text)
                            repair_tokens += add_tokens
                            if "error" not in response_data:
                                repaired = True
                                break
                        except Exception:
                            pass
                        repair_attempts += 1
                    
                    if not repaired:
                        raise ValueError(f"JSON repair failed after {max_repair} attempts: {response_data.get('error')}")

                # 4. 术语一致性复写 (Rewrite with Glossary)
                # 检查新生成的术语是否与已知术语冲突
                new_terms_list = response_data.get("new_terms", [])
                corrections = {}
                
                if terminology_policy == TerminologyPolicy.MERGE_ON_CONFLICT:
                    for item in new_terms_list:
                        term = item.get("term", "").strip()
                        translation = item.get("translation", "").strip()
                        if not term or not translation:
                            continue
                        
                        # 如果该术语已在权威词表中，且译名不一致
                        if term in current_terms:
                            expected = current_terms[term]
                            if translation != expected:
                                corrections[term] = expected
                
                # 如果有冲突，进行复写
                if corrections:
                    if hasattr(self.llm_service, 'rewrite_with_glossary'):
                        translation = response_data.get("translation", "")
                        notes = response_data.get("notes", "")
                        # 复写
                        rewrite_result, rewrite_tokens = await asyncio.to_thread(
                            self.llm_service.rewrite_with_glossary, 
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
                                    rewrite_result, add_tokens = await asyncio.to_thread(self.llm_service.repair_json, origin_text)
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
                    header_path=header_path,
                    success=True
                )

            except Exception as e:
                last_error = str(e)
                attempts += 1
                # 简单的指数退避
                await asyncio.sleep(1 * attempts)
        
        # 如果重试耗尽
        # 检查是否可以降级使用部分有效的数据
        if last_response_data and isinstance(last_response_data, dict) and "error" not in last_response_data:
            final_translation = last_response_data.get("translation", "")
            final_notes = last_response_data.get("notes", "")
            
            # 如果有译文，说明至少解析出了 translation 字段
            if final_translation:
                # 构造警告信息
                warning_msg = "注意：该段落译注、术语录入异常。"
                
                # 如果 notes 也有内容，说明可能只是术语部分解析失败
                if final_notes:
                    final_notes += f"\n{warning_msg}"
                else:
                    final_notes = warning_msg
                
                logger.warning(f"Returning partial result after max retries. Error: {last_error}")
                
                return TranslationResult(
                    content=final_translation,
                    notes=final_notes,
                    tokens=tokens, 
                    repair_tokens=repair_tokens,
                    new_terms_delta=[], # 术语录入异常，不返回新术语
                    header_path=header_path,
                    success=True # 标记为成功以便写入文件，但带有警告
                )

        # 尝试从无效 JSON 中提取（降级逻辑补充）
        if last_response_data and isinstance(last_response_data, dict) and "error" in last_response_data and "origin_text" in last_response_data:
            origin_text = last_response_data.get("origin_text", "")
            # 简单的正则提取，尝试获取 translation 和 notes
            # 注意：这只是一个基本的降级处理，无法处理复杂的转义或嵌套
            translation_match = re.search(r'"translation"\s*:\s*"(.*?)(?<!\\)"', origin_text, re.DOTALL)
            
            if translation_match:
                final_translation = translation_match.group(1)
                # 处理常见的 JSON 转义
                final_translation = final_translation.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                
                notes_match = re.search(r'"notes"\s*:\s*"(.*?)(?<!\\)"', origin_text, re.DOTALL)
                final_notes = ""
                if notes_match:
                    final_notes = notes_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                
                warning_msg = "注意：该段落由降级逻辑解析（JSON格式错误），可能存在排版问题。"
                if final_notes:
                    final_notes += f"\n{warning_msg}"
                else:
                    final_notes = warning_msg
                
                logger.warning(f"Recovered translation from invalid JSON. Original Error: {last_response_data.get('error')}")
                
                return TranslationResult(
                    content=final_translation,
                    notes=final_notes,
                    tokens=tokens,
                    repair_tokens=repair_tokens,
                    new_terms_delta=[], 
                    header_path=header_path,
                    success=True
                )

        return TranslationResult(
            content="",
            notes="",
            tokens=0,
            repair_tokens=0,
            new_terms_delta=[],
            header_path=header_path,
            success=False,
            error=f"Max retries ({max_api_retries}) reached. Last error: {last_error}"
        )

