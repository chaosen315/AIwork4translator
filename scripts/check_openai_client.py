from openai import OpenAI, AsyncOpenAI
import asyncio

async def check_async():
    try:
        client = AsyncOpenAI(api_key='test')
        print(f"Async Has responses attribute: {hasattr(client, 'responses')}")
        if hasattr(client, 'responses'):
            print(f"Async responses type: {type(client.responses)}")
            # Note: Async resource usually has methods that return coroutines
            print(f"Async Has parse: {hasattr(client.responses, 'parse')}")
            
        print(f"Async Has chat attribute: {hasattr(client, 'chat')}")
        if hasattr(client, 'chat'):
            print(f"Async Has completions: {hasattr(client.chat, 'completions')}")
            if hasattr(client.chat.completions, 'create'):
                print("Async Has create: True")
    except Exception as e:
        print(f"Async Error: {e}")

if __name__ == "__main__":
    try:
        # Check Sync (Already done, but for completeness)
        client = OpenAI(api_key='test')
        print(f"Sync Has responses attribute: {hasattr(client, 'responses')}")
        
        # Check Async
        asyncio.run(check_async())
    except Exception as e:
        print(f"Error: {e}")
