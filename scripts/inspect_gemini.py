from google import genai
print("genai attributes:", dir(genai))
if hasattr(genai, 'Client'):
    print("Client attributes:", dir(genai.Client))
    client = genai.Client(api_key='test')
    print("Instance attributes:", dir(client))
    if hasattr(client, 'models'):
        print("client.models attributes:", dir(client.models))
    if hasattr(client, 'aio'):
        print("client.aio exists!")
        print("client.aio attributes:", dir(client.aio))
