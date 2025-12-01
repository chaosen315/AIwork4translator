import os
from typing import Dict, Any
from abc import ABC, abstractmethod
from openai import OpenAI
from google import genai
from google.genai import types
import requests

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
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content, completion.usage.total_tokens

class GPTProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('GPT_MODEL', 'gpt-realtime')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content, completion.usage.total_tokens

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
            temperature=1.3,
        )
        return completion.choices[0].message.content, completion.usage.total_tokens

class SillionProvider(LLMProvider):
    def generate_completion(self, prompt: str, system_prompt: str):
        payload = {
            "model": os.getenv('SILLION_MODEL', 'deepseek-ai/DeepSeek-V3.1-Terminus'),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "max_tokens": 4096,
            "enable_thinking": False,
            "thinking_budget": 4096,
            "min_p": 0.05,
            "stop": None,
            "temperature": 0.3,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": { "type": "text" }
        }
        url=os.getenv('SILLION_BASE_URL') or 'https://api.siliconflow.cn/v1/chat/completions'
        headers = {
            "Authorization": f"Bearer {os.getenv('SILLION_API_KEY')}",
            "Content-Type": "application/json"
        }
        # 添加30秒超时设置，增加等待时长
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return str(response.json()["choices"][0]["message"]["content"]), int(response.json()["usage"]["total_tokens"])

class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    def generate_completion(self, prompt: str, system_prompt: str):
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0), # Disables thinking
                temperature=0.3)
        )
        return response.text, response.usage_metadata.total_token_count

class DoubaoProvider(LLMProvider):
    def __init__(self):
        base_url = os.getenv('DOUBAO_BASE_URL')
        api_key = f"Bearer {os.getenv('DOUBAO_API_KEY')}"
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv('DOUBAO_MODEL', 'doubao-seed-1-6-251015')

    def generate_completion(self, prompt: str, system_prompt: str):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content, completion.usage.total_tokens

class LLMService:
    def __init__(self, provider: str = "kimi"):
        self.providers = {
            "kimi": KimiProvider,
            "gpt": GPTProvider,
            "deepseek": DeepseekProvider,
            "sillion": SillionProvider,
            "gemini": GeminiProvider,
            "doubao": DoubaoProvider,
        }
        self.provider_name = provider.lower()
        self.Linkedprovider = self.providers.get(self.provider_name)()
        self.system_prompt = os.getenv('SYSTEM_PROMPT')

    @property
    def provider(self):
        return self.provider_name

    @provider.setter
    def provider(self, value: str):
        self.provider_name = value.lower()
        self.Linkedprovider = self.providers.get(self.provider_name)()

    def create_prompt(self, paragraph: str, terms_dict: Dict[str, str]) -> str:
        base_prompt = (
            f"{os.getenv('BASE_PROMPT')}\n以下为原文段落：\n{paragraph}"
        )
        if terms_dict:
            terms_info = '\n'.join([f"{eng} -> {chi}" for eng, chi in terms_dict.items()])
            return f"以下段落中包含专有术语及其中文译名：\n{terms_info}\n\n{base_prompt}"
        return base_prompt

    def call_ai_model_api(self, prompt: str):
        content, total_tokens = self.Linkedprovider.generate_completion(prompt, self.system_prompt)
        return content, total_tokens

    def test_api(self) -> Dict[str, Any]:
        results = {
            "provider": self.provider_name,
            "success": True,
            "test_cases": [],
            "error": None,
        }
        test_cases = [
            {"name": "简单翻译", "prompt": "请翻译：Hello, this is a simple test for API functionality."},
            {"name": "专有术语翻译", "prompt": "请翻译：Night City is a dangerous place in Cyberpunk 2077."},
            {"name": "长句翻译", "prompt": "请翻译：In the vast expanse of the digital frontier, where information flows like a river and technology evolves at an unprecedented pace, we find ourselves navigating through a landscape of endless possibilities and unforeseen challenges."},
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
