import os
import time
from typing import Dict, Optional, List
from abc import ABC, abstractmethod
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(ABC):
    """LLM提供者的抽象基类"""
    
    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        """生成完成响应的抽象方法"""
        pass

class KimiProvider(LLMProvider):
    """Kimi API提供者"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv('KIMI_API_KEY'),
            base_url=os.getenv('KIMI_BASE_URL'),
        )
        self.model = "moonshot-v1-32k"
    
    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content

class GPTProvider(LLMProvider):
    """OpenAI GPT API提供者"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
        )
        self.model = "gpt-4"  # 可配置为其他模型
    
    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content

class DeepseekProvider(LLMProvider):
    """Deepseek API提供者"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url=os.getenv('DEEPSEEK_BASE_URL'),
        )
        self.model = "deepseek-chat"  # 根据实际模型名称调整
    
    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content

class LLMService:
    """LLM服务管理类"""
    
    def __init__(self, provider: str = "kimi"):
        self.max_retries = 4
        self.providers = {
            "kimi": KimiProvider,
            "gpt": GPTProvider,
            "deepseek": DeepseekProvider
        }
        self.provider = self.providers.get(provider.lower())()
        self.system_prompt = "我需要一名专业的英语翻译职业人。擅长对长难句进行严谨的结构分析，简明扼要地翻译出通顺的中文长句，还可以利用名词表中的专有名词对英文原文进行正确的翻译。"

    def create_prompt(self, paragraph: str, terms_dict: Dict[str, str]) -> str:
        """构造prompt"""
        if terms_dict:
            terms_info = '\n'.join([f"{eng} -> {chi}" for eng, chi in terms_dict.items()])
            return f"以下段落中包含专有名词及其中文译名：\n{terms_info}\n\n翻译要求：找出并加粗**所有可能是**专有名词的单词，例如虚构的名词，地点，组织名字与人名等等，将提供给你的专有名词的正确译名准确地使用到译文中。如果被找出的专有名词在指令中没有提供对应翻译，你需要在译文的对应位置后插入括号，在括号中保留专有名词的英文并说明你给出的译名的理由，以方便编辑老师查看。输出格式要求：你只需要输出译文，并在译文中插入那些没有对应翻译的专有名词的理由解释。\n请翻译以下段落：\n{paragraph}"
        else:
            return f"翻译要求：找出并加粗**所有可能是**专有名词的单词，例如虚构的名词，地点，组织名字与人名等等，将提供给你的专有名词的正确译名准确地使用到译文中。如果被找出的专有名词在指令中没有提供对应翻译，你需要在译文的对应位置后插入括号，在括号中保留专有名词的英文并说明你给出的译名的理由，以方便编辑老师查看。输出格式要求：你只需要输出译文，并在译文中插入解释\n请翻译以下段落：\n{paragraph}"

    def call_ai_model_api(self, prompt: str) -> str:
        """调用AI模型API"""
        retries = 0
        content = None
        
        while retries < self.max_retries:
            try:
                content = self.provider.generate_completion(prompt, self.system_prompt)
                break
            except Exception as e:
                retries += 1
                print(f"发生错误: {e}，正在重试...（第 {retries} 次）")
                time.sleep(1)
        
        if content is None:
            content = f"达到最大重试次数，未能获取翻译内容。此为原文：{prompt}"
        
        return content

