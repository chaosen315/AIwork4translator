from google import genai
import asyncio

async def inspect_async():
    client = genai.Client(api_key='test')
    if hasattr(client, 'aio'):
        print("client.aio.models attributes:", dir(client.aio.models))
        if hasattr(client.aio.models, 'generate_content'):
            print("Has generate_content in aio.models!")

if __name__ == "__main__":
    asyncio.run(inspect_async())
