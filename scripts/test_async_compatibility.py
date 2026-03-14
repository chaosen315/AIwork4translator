import asyncio
import os
import json
from typing import Dict, Any, List
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="data/.env")

# --- Mocks & Models for Testing ---

class NewTerm(BaseModel):
    term: str
    translation: str
    reason: str

class TranslationResponseModel(BaseModel):
    translation: str
    new_terms: List[NewTerm]

# --- Test Functions ---

async def test_kimi_async():
    print("\n--- Testing Kimi (Async) ---")
    base_url = os.getenv('KIMI_BASE_URL') or 'https://api.moonshot.cn/v1'
    api_key = os.getenv('KIMI_API_KEY')
    
    if not api_key:
        print("Skipping Kimi: No API Key found.")
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = os.getenv('KIMI_MODEL', 'kimi-k2-turbo-preview')

    print(f"Client initialized with URL: {base_url}")
    
    try:
        print("Sending request...")
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a translator."},
                {"role": "user", "content": "Hello, world!"}
            ],
            temperature=0.7,
        )
        print("Response received:")
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error testing Kimi: {e}")

async def test_doubao_async():
    print("\n--- Testing Doubao (Async Structured) ---")
    base_url = os.getenv('DOUBAO_BASE_URL')
    api_key = os.getenv('DOUBAO_API_KEY')
    
    if not api_key or not base_url:
        print("Skipping Doubao: No API Key or Base URL found.")
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = os.getenv('DOUBAO_MODEL', 'doubao-seed-1-6-251015')

    print(f"Client initialized with URL: {base_url}")

    try:
        print("Sending request (with client.beta.chat.completions.parse equivalent logic if available)...")
        # Note: AsyncOpenAI also has .beta.chat.completions.parse
        # Let's try standard parse if available, or fallback to manual
        
        if hasattr(client.beta.chat.completions, 'parse'):
             print("Using client.beta.chat.completions.parse...")
             response = await client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": "Translate to Chinese."},
                    {"role": "user", "content": "Hello, world!"}
                ],
                response_format=TranslationResponseModel,
                extra_body={
                    "thinking": {"type": "disabled"} 
                }
            )
             print("Response received:")
             print(response.choices[0].message.parsed)
        else:
            print("AsyncOpenAI beta.parse not found, trying raw request with json_schema...")
            # Fallback test for raw json mode if parse helper is missing
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Translate to Chinese. Output JSON."},
                    {"role": "user", "content": "Hello, world!"}
                ],
                response_format={"type": "json_object"}
            )
            print("Response received (Raw JSON):")
            print(completion.choices[0].message.content)

    except Exception as e:
        print(f"Error testing Doubao: {e}")

async def test_cancellation():
    print("\n--- Testing Cancellation (Simulated) ---")
    # Simulate a long running task that gets cancelled
    try:
        print("Starting long task...")
        await asyncio.sleep(5)
        print("Task finished (Unexpected if cancelled)")
    except asyncio.CancelledError:
        print("Task was successfully cancelled!")

async def main():
    print("Starting Async Compatibility Tests...")
    
    # 1. Test Kimi
    await test_kimi_async()
    
    # 2. Test Doubao
    await test_doubao_async()
    
    # 3. Test Cancellation (Simulate Ctrl+C effect)
    task = asyncio.create_task(test_cancellation())
    await asyncio.sleep(1)
    print("Simulating Ctrl+C (Cancelling task)...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass # Already handled in task, but await might raise it too
        
    print("Tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
