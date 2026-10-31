from typing import Tuple
import os
import json
import time
import threading
import asyncio
import re
import hashlib
import logging
import contextvars
import itertools
from typing import Dict, Any, List, Union
from abc import ABC, abstractmethod
from openai import OpenAI, AsyncOpenAI
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError, field_validator
from modules.csv_process_tool import serialize_terms_for_prompt

logger = logging.getLogger(__name__)
_PROMPT_METADATA: contextvars.ContextVar[Dict[str, Any] | None] = contextvars.ContextVar(
    "prompt_metadata",
    default=None,
)
_REQUEST_COUNTER = itertools.count(1)

class LLMProvider(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str):
        pass

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        raise NotImplementedError

class KimiProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('KIMI_BASE_URL') or 'https://api.moonshot.cn/v1'
        api_key = os.getenv('KIMI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('KIMI_MODEL', 'kimi-k2.5')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{", "partial": True} # type: ignore
            ],
            temperature=0.7,
        )
        content = "{" + (completion.choices[0].message.content or "")
        return content, completion.usage.total_tokens # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        completion = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{", "partial": True} # type: ignore
            ],
            temperature=0.7,
        )
        content = "{" + (completion.choices[0].message.content or "")
        return content, completion.usage.total_tokens # type: ignore

class GPTProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('GPT_MODEL', 'gpt-realtime')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        completion = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

class DeepseekProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('DEEPSEEK_BASE_URL')
        api_key = os.getenv('DEEPSEEK_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chatv4-flash')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        completion = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

class SiliconProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('SILICON_JSON_URL') or 'https://api.siliconflow.com/v1'
        api_key = os.getenv('SILICON_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('SILICON_JSON_MODEL', 'deepseek-ai/DeepSeek-V2.5')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        completion = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

class GeminiProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('GEMINI_BASE_URL') or None
        api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1beta', base_url=base_url) or None)
        self.model = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')

    def generate_completion(self, prompt: str, system_prompt: str):
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=TranslationResponseModel.model_json_schema(),
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=1.0,
            )
        )
        return response.text, response.usage_metadata.total_token_count # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=TranslationResponseModel.model_json_schema(),
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=1.0,
            )
        )
        return response.text, response.usage_metadata.total_token_count # type: ignore

class DoubaoProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('DOUBAO_BASE_URL')
        api_key = os.getenv('DOUBAO_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('DOUBAO_MODEL', 'doubao-seed-2-0-lite-260428')

    def generate_completion(self, prompt: str, system_prompt: str):
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            text_format=TranslationResponseModel,
            extra_body={
                "thinking": {"type": "disabled"} # 不使用深度思考能力
            }
        )
        return response.output_text, response.usage.total_tokens # type: ignore

    async def generate_completion_async(self, prompt: str, system_prompt: str):
        response = await self.async_client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            text_format=TranslationResponseModel,
            extra_body={
                "thinking": {"type": "disabled"} # 不使用深度思考能力
            }
        )
        return response.output_text, response.usage.total_tokens # type: ignore

def translation_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "translation": {"type": "string"},
            "new_terms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {"type": "string"},
                        "translation": {"type": "string"},
                        "reason": {"type": "string"}
                    },
                    "required": ["term", "translation", "reason"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["translation", "new_terms"],
        "additionalProperties": False
    }

class NewTerm(BaseModel):
    term: str
    translation: str
    reason: str

class TranslationResponseModel(BaseModel):
    translation: str
    new_terms: List[NewTerm]

class StructuredParseError(Exception):
    pass

def _try_validate_json(text: str):
    try:
        if hasattr(TranslationResponseModel, 'model_validate_json'):
            return TranslationResponseModel.model_validate_json(text)
        else:
            return TranslationResponseModel.parse_raw(text)
    except ValidationError as e:
        raise StructuredParseError(str(e))
    except Exception as e:
        raise StructuredParseError(str(e))

def _unwrap_json_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped

def _extract_balanced_json_object(text: str) -> str:
    start = None
    depth = 0
    in_string = False
    quote_char = ""
    escaped = False

    for idx, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                in_string = False
            continue

        if char in ('"', "'"):
            in_string = True
            quote_char = char
            continue

        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:idx + 1]

    return ""

def parse_translation_response(text: str) -> Dict[str, Any]:
    """
    解析模型返回的结构化结果。

    当前策略分三层：
    1. 直接校验完整 JSON；
    2. 尝试从代码块或前后缀文本中抽取平衡 JSON；
    3. 若仍失败但能看出结构化意图，则返回可供上层继续 repair / 保守恢复的错误对象。
    """
    candidates = []
    stripped = text.strip()
    if stripped:
        candidates.append(stripped)

    unfenced = _unwrap_json_code_fence(stripped)
    if unfenced and unfenced not in candidates:
        candidates.append(unfenced)

    for candidate_source in list(candidates):
        balanced = _extract_balanced_json_object(candidate_source)
        if balanced and balanced not in candidates:
            candidates.append(balanced)

    for candidate in candidates:
        try:
            model = _try_validate_json(candidate)
            break
        except Exception:
            model = None
    else:
        if "{" in text or '"translation"' in text or "'translation'" in text:
            return {"origin_text": text, "error": "Invalid JSON format"}
        raise StructuredParseError('Non-structured or invalid JSON output')

    data = model.model_dump() if hasattr(model, 'model_dump') else model.dict()
    
    new_terms = data.get("new_terms", [])
    notes_list = []
    for nt in new_terms:
        t = nt.get("translation", "")
        o = nt.get("term", "")
        r = nt.get("reason", "")
        if t and o:
            notes_list.append(f"- {t} (原文: {o})：{r}")
        elif o:
             notes_list.append(f"- {o}：{r}")
    
    normalized_notes = "\n".join(notes_list)

    return {
        "translation": data.get("translation", ""),
        "notes": normalized_notes,
        "new_terms": [
            {
                "term": nt.get("term", ""),
                "translation": nt.get("translation", ""),
                "reason": nt.get("reason", ""),
            }
            for nt in new_terms
        ],
    }

class LLMService:
    def __init__(self, provider: str = "kimi"):
        self.providers = {
            "kimi": KimiProvider,
            "gpt": GPTProvider,
            "deepseek": DeepseekProvider,
            "silicon": SiliconProvider,
            "gemini": GeminiProvider,
            "doubao": DoubaoProvider,
        }
        self.provider_name = provider.lower()
        self.Linkedprovider = self.providers.get(self.provider_name)() # type: ignore
        self.system_prompt = os.getenv('SYSTEM_PROMPT')
        self.structured = os.getenv('STRUCTURED_OUTPUT', 'True').lower() in ('1', 'true', 'yes')
        self._rpm_limit = int(os.getenv('Requests_Per_Minute', '0'))
        self._req_ts: List[float] = []
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self.last_prefix_hash: str = ""
        self.last_prompt_metadata: Dict[str, Any] = {}

    @property
    def provider(self):
        return self.provider_name

    @provider.setter
    def provider(self, value: str):
        self.provider_name = value.lower()
        self.Linkedprovider = self.providers.get(self.provider_name)() # type: ignore

    def _build_prefix_hash(self, system_prompt: str, base_prompt: str, stable_terms_text: str) -> str:
        stable_payload = {
            "system_prompt": system_prompt or "",
            "base_prompt": base_prompt or "",
            "structured_output": self.structured,
            "glossary_prefix": stable_terms_text or "",
        }
        serialized = json.dumps(stable_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def build_prompt_parts(self, paragraph: str, terms_dict: Dict[str, Any]) -> Dict[str, Any]:
        stable_terms_text = serialize_terms_for_prompt(terms_dict)
        stable_prefix_parts = []
        if stable_terms_text:
            stable_prefix_parts.append(f"术语表：\n{stable_terms_text}")
        stable_prefix_parts.append("原文段落：")
        prompt_prefix = "\n".join(stable_prefix_parts) + "\n"
        paragraph_body = paragraph
        prompt_suffix = os.getenv('BASE_PROMPT') or ""
        prompt = f"{prompt_prefix}{paragraph_body}{prompt_suffix}"
        prefix_hash = self._build_prefix_hash(self.system_prompt or "", prompt_suffix, stable_terms_text)
        request_id = f"{self.provider_name}-{next(_REQUEST_COUNTER)}"
        metadata = {
            "request_id": request_id,
            "provider": self.provider_name,
            "prefix_hash": prefix_hash,
            "structured": self.structured,
            "prompt_kind": "translation",
            "glossary_entries": len(stable_terms_text.splitlines()) if stable_terms_text else 0,
            "prefix_length": len(prompt_prefix) + len(prompt_suffix),
        }
        self.last_prefix_hash = prefix_hash
        self.last_prompt_metadata = metadata
        return {
            "prompt_prefix": prompt_prefix,
            "paragraph_body": paragraph_body,
            "prompt_suffix": prompt_suffix,
            "prompt": prompt,
            "metadata": metadata,
        }

    def create_prompt(self, paragraph: str, terms_dict: Dict[str, Any]) -> str:
        prompt_parts = self.build_prompt_parts(paragraph, terms_dict)
        _PROMPT_METADATA.set(prompt_parts["metadata"])
        return prompt_parts["prompt"]

    def _get_prompt_metadata(self, prompt: str, prompt_metadata: Dict[str, Any] | None = None, prompt_kind: str = "generic") -> Dict[str, Any]:
        metadata = prompt_metadata or _PROMPT_METADATA.get() or {}
        if metadata:
            return metadata
        fallback_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        return {
            "request_id": f"{self.provider_name}-{next(_REQUEST_COUNTER)}",
            "provider": self.provider_name,
            "prefix_hash": fallback_hash,
            "structured": self.structured,
            "prompt_kind": prompt_kind,
            "glossary_entries": 0,
            "prefix_length": len(prompt),
        }

    def _log_request_start(self, metadata: Dict[str, Any]) -> None:
        logger.info(
            "LLM request start provider=%s request_id=%s prefix_hash=%s structured=%s prompt_kind=%s glossary_entries=%s prefix_length=%s",
            metadata.get("provider", self.provider_name),
            metadata.get("request_id", ""),
            metadata.get("prefix_hash", ""),
            metadata.get("structured", self.structured),
            metadata.get("prompt_kind", "generic"),
            metadata.get("glossary_entries", 0),
            metadata.get("prefix_length", 0),
        )

    def _log_request_finish(self, metadata: Dict[str, Any], total_tokens: int) -> None:
        logger.info(
            "LLM request finish provider=%s request_id=%s prefix_hash=%s structured=%s prompt_kind=%s total_tokens=%s",
            metadata.get("provider", self.provider_name),
            metadata.get("request_id", ""),
            metadata.get("prefix_hash", ""),
            metadata.get("structured", self.structured),
            metadata.get("prompt_kind", "generic"),
            total_tokens,
        )

    def call_ai_model_api(self, prompt: str, prompt_metadata: Dict[str, Any] | None = None):
        metadata = self._get_prompt_metadata(prompt, prompt_metadata, prompt_kind="translation")
        self._log_request_start(metadata)
        self._enforce_rate_limit()
        content, total_tokens = self.Linkedprovider.generate_completion(prompt, self.system_prompt)
        self._log_request_finish(metadata, total_tokens)
        if self.structured:
            parsed = parse_translation_response(content)
            return parsed, total_tokens
        return {"translation": content, "notes": "", "new_terms": []}, total_tokens

    async def call_ai_model_api_async(self, prompt: str, prompt_metadata: Dict[str, Any] | None = None):
        metadata = self._get_prompt_metadata(prompt, prompt_metadata, prompt_kind="translation")
        self._log_request_start(metadata)
        await self._enforce_rate_limit_async()
        try:
            content, total_tokens = await self.Linkedprovider.generate_completion_async(prompt, self.system_prompt)
        except NotImplementedError:
            content, total_tokens = await asyncio.to_thread(self.Linkedprovider.generate_completion, prompt, self.system_prompt)
        self._log_request_finish(metadata, total_tokens)
        if self.structured:
            parsed = parse_translation_response(content)
            return parsed, total_tokens
        return {"translation": content, "notes": "", "new_terms": []}, total_tokens

    def repair_json(self, origin_text: str) -> Tuple[Dict[str, Any], int]:
        format = r"{'translation':'...','new_terms':[{'term': '...','translation':'...','reason':'...'}]}"
        repair_prompt = "".join([f"请修复以下无效的JSON字符串，只返回修复后的JSON字符串，不要包含任何其他内容。\nInvalid json:{origin_text}\nJson format example:{format}。"])
        repair_meta = self._get_prompt_metadata(repair_prompt, prompt_kind="repair_json")
        self._log_request_start(repair_meta)
        self._enforce_rate_limit()
        response_obj, total_tokens = self.Linkedprovider.generate_completion(repair_prompt, '你是一个专业的JSON修复助手，只能修复JSON字符串，不能返回其他内容。')
        self._log_request_finish(repair_meta, total_tokens)
        parsed = parse_translation_response(response_obj)
        return parsed, total_tokens

    async def repair_json_async(self, origin_text: str) -> Tuple[Dict[str, Any], int]:
        format = r"{'translation':'...','new_terms':[{'term': '...','translation':'...','reason':'...'}]}"
        repair_prompt = "".join([f"请修复以下无效的JSON字符串，只返回修复后的JSON字符串，不要包含任何其他内容。\nInvalid json:{origin_text}\nJson format example:{format}。"])
        repair_meta = self._get_prompt_metadata(repair_prompt, prompt_kind="repair_json")
        self._log_request_start(repair_meta)
        await self._enforce_rate_limit_async()
        
        try:
            response_obj, total_tokens = await self.Linkedprovider.generate_completion_async(repair_prompt, '你是一个专业的JSON修复助手，只能修复JSON字符串，不能返回其他内容。')
        except NotImplementedError:
            response_obj, total_tokens = await asyncio.to_thread(self.Linkedprovider.generate_completion, repair_prompt, '你是一个专业的JSON修复助手，只能修复JSON字符串，不能返回其他内容。')
        self._log_request_finish(repair_meta, total_tokens)
        parsed = parse_translation_response(response_obj)
        return parsed, total_tokens

    def rewrite_with_glossary(self, translation: str, notes: str, corrections: Dict[str, str]) -> Tuple[Dict[str, Any], int]:
        if not corrections:
            return {"translation": translation, "notes": notes, "new_terms": []}, 0
        terms_info = '\n'.join([f"{eng} -> {chi}" for eng, chi in corrections.items()])
        prompt = (
            "请根据以下术语映射，复写现有译文，使其中的术语全部采用映射中的译名；"
            "保持语义与行文不变，只进行术语规范化。"
            "仅输出JSON，包含translation和new_terms（请根据现有注释还原，并移除已在术语映射中修正的项）。\n"
            f"术语映射：\n{terms_info}\n"
            f"现有译文：\n{translation}\n"
            f"现有注释：\n{notes}"
        )
        rewrite_meta = self._get_prompt_metadata(prompt, prompt_kind="rewrite_glossary")
        self._enforce_rate_limit()
        self._log_request_start(rewrite_meta)
        content, total_tokens = self.Linkedprovider.generate_completion(prompt, self.system_prompt or "你是术语一致性编辑助手")
        self._log_request_finish(rewrite_meta, total_tokens)
        parsed = parse_translation_response(content)
        return parsed, total_tokens

    async def rewrite_with_glossary_async(self, translation: str, notes: str, corrections: Dict[str, str]) -> Tuple[Dict[str, Any], int]:
        if not corrections:
            return {"translation": translation, "notes": notes, "new_terms": []}, 0
        terms_info = '\n'.join([f"{eng} -> {chi}" for eng, chi in corrections.items()])
        prompt = (
            "请根据以下术语映射，复写现有译文，使其中的术语全部采用映射中的译名；"
            "保持语义与行文不变，只进行术语规范化。"
            "仅输出JSON，包含translation和new_terms（请根据现有注释还原，并移除已在术语映射中修正的项）。\n"
            f"术语映射：\n{terms_info}\n"
            f"现有译文：\n{translation}\n"
            f"现有注释：\n{notes}"
        )
        rewrite_meta = self._get_prompt_metadata(prompt, prompt_kind="rewrite_glossary")
        await self._enforce_rate_limit_async()
        self._log_request_start(rewrite_meta)
        try:
            content, total_tokens = await self.Linkedprovider.generate_completion_async(prompt, self.system_prompt or "你是术语一致性编辑助手")
        except NotImplementedError:
            content, total_tokens = await asyncio.to_thread(self.Linkedprovider.generate_completion, prompt, self.system_prompt or "你是术语一致性编辑助手")
        self._log_request_finish(rewrite_meta, total_tokens)
        parsed = parse_translation_response(content)
        return parsed, total_tokens

    def test_api(self) -> Dict[str, Any]:
        results = {
            "provider": self.provider_name,
            "success": True,
            "test_cases": [],
            "error": None,
        }
        test_cases = [
            {"name": "简单翻译", "prompt": "请以JSON输出：translation、new_terms。内容：Hello, this is a simple test for API functionality."},
            {"name": "专有术语翻译", "prompt": "请以JSON输出：translation、new_terms。内容：Night City is a dangerous place in Cyberpunk 2077."},
            {"name": "长句翻译", "prompt": "请以JSON输出：translation、new_terms。内容：In the vast expanse of the digital frontier, where information flows like a river and technology evolves at an unprecedented pace, we find ourselves navigating through a landscape of endless possibilities and unforeseen challenges."},
        ]
        for case in test_cases:
            try:
                result, tokens = self.call_ai_model_api(case["prompt"])
                results["test_cases"].append({
                    "name": case["name"],
                    "success": True,
                    "tokens": tokens,
                    "result": result,
                    "error": None,
                })
            except Exception as e:
                results["success"] = False
                results["test_cases"].append({
                    "name": case["name"],
                    "success": False,
                    "tokens": 0,
                    "result": None,
                    "error": str(e),
                })
        return results

    def _enforce_rate_limit(self) -> None:
        if self._rpm_limit <= 0:
            return
            
        while True:
            with self._lock:
                now = time.time()
                # Clean up expired timestamps
                self._req_ts = [t for t in self._req_ts if now - t < 60.0]
                
                if len(self._req_ts) < self._rpm_limit:
                    self._req_ts.append(now)
                    return # Slot acquired
                
                # Calculate wait time
                wait = 60.0 - (now - self._req_ts[0])
            
            # Sleep outside the lock to avoid blocking other threads
            # (though they will likely hit the limit too)
            if wait > 0:
                time.sleep(wait)

    async def _enforce_rate_limit_async(self) -> None:
        if self._rpm_limit <= 0:
            return
            
        while True:
            with self._lock:
                now = time.time()
                # Clean up expired timestamps
                self._req_ts = [t for t in self._req_ts if now - t < 60.0]
                
                if len(self._req_ts) < self._rpm_limit:
                    self._req_ts.append(now)
                    return # Slot acquired
                
                # Calculate wait time
                wait = 60.0 - (now - self._req_ts[0])
            
            if wait > 0:
                await asyncio.sleep(wait)
