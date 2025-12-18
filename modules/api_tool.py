from typing import Tuple
import os
import json
import time
import threading
from typing import Dict, Any, List, Union
from abc import ABC, abstractmethod
from openai import OpenAI
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError, field_validator

class LLMProvider(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str):
        pass

class KimiProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('KIMI_BASE_URL') or 'https://api.moonshot.cn/v1'
        api_key = os.getenv('KIMI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('KIMI_MODEL', 'kimi-k2-turbo-preview')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{", "partial": True} # type: ignore
            ],
            temperature=0.1,
        )
        content = "{" + (completion.choices[0].message.content or "")
        return content, completion.usage.total_tokens # type: ignore

class GPTProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('GPT_MODEL', 'gpt-realtime')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

class DeepseekProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('DEEPSEEK_BASE_URL')
        api_key = os.getenv('DEEPSEEK_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content, completion.usage.total_tokens # type: ignore

class SiliconProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('SILICON_JSON_URL') or 'https://api.siliconflow.com/v1'
        api_key = os.getenv('SILICON_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
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

class GeminiProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('GEMINI_BASE_URL') or None
        api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1beta', base_url=base_url) or None)
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    def generate_completion(self, prompt: str, system_prompt: str):
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=TranslationResponseModel.model_json_schema(),
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                temperature=0.1,
            )
        )
        return response.text, response.usage_metadata.total_token_count # type: ignore

class DoubaoProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('DOUBAO_BASE_URL')
        api_key = os.getenv('DOUBAO_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('DOUBAO_MODEL', 'doubao-seed-1-6-251015')

    def generate_completion(self, prompt: str, system_prompt: str):
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
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

def parse_translation_response(text: str) -> Dict[str, Any]:
    try:
        model = _try_validate_json(text)
    except Exception:
        try:
            s = text.find('{')
            e = text.rfind('}')
            if s != -1 and e != -1 and e > s:
                return {"origin_text": text,
                        "error": "Invalid JSON format"}
            else:
                raise ValueError('no_json')
        except Exception:
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

    @property
    def provider(self):
        return self.provider_name

    @provider.setter
    def provider(self, value: str):
        self.provider_name = value.lower()
        self.Linkedprovider = self.providers.get(self.provider_name)() # type: ignore

    def create_prompt(self, paragraph: str, terms_dict: Dict[str, str]) -> str:
        base_prompt = (
            f"\n原文段落：\n{paragraph}{os.getenv('BASE_PROMPT')}"
        )
        if terms_dict:
            terms_info = '\n'.join([f"{eng} -> {chi}" for eng, chi in terms_dict.items()])
            return f"术语表：{terms_info}\n{base_prompt}"
        return base_prompt

    def call_ai_model_api(self, prompt: str):
        self._enforce_rate_limit()
        content, total_tokens = self.Linkedprovider.generate_completion(prompt, self.system_prompt)
        if self.structured:
            parsed = parse_translation_response(content)
            return parsed, total_tokens
        return {"translation": content, "notes": "", "new_terms": []}, total_tokens

    def repair_json(self, origin_text: str) -> Tuple[Dict[str, Any], int]:
        repair_prompt = "".join([f"请修复以下无效的JSON字符串，只返回修复后的JSON字符串，不要包含任何其他内容。\nInvalid json:{origin_text}\nJson format example:",r"{\"translation\": \"...\", \"new_terms\": [{\"term\": \"...\", \"translation\": \"...\", \"reason\": \"...\"}]}。"])
        self._enforce_rate_limit()
        response_obj, total_tokens = self.Linkedprovider.generate_completion(repair_prompt, '你是一个专业的JSON修复助手，只能修复JSON字符串，不能返回其他内容。')
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
        self._enforce_rate_limit()
        content, total_tokens = self.Linkedprovider.generate_completion(prompt, self.system_prompt or "你是术语一致性编辑助手")
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
