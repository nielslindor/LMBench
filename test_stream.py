import httpx
import asyncio
import json

async def test():
    url = "http://localhost:1234/v1/chat/completions"
    # Using a real ID from the previous step
    payload = {
        "model": "meta-llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": "Say hello world"}],
        "stream": True
    }
    print("Connecting to LM Studio...")
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status: {response.status_code}")
                if response.status_code != 200:
                    print(await response.aread())
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]": break
                        chunk = json.loads(data)
                        content = chunk["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end="", flush=True)
        except Exception as e:
            print(f"Error: {e}")
    print("\nStream finished.")

asyncio.run(test())