import requests

MINIMAX_API_KEY = 'sk-cp-8TEdW3D4r4nlNcao1PGu_xOjb8hd8gZqYaSIDOs4xAJgKdIx9IbMnFvW70tbv-rqnqBfpeEjw4wDUKXBbFa8FrdaKqlW9GG4pWFXOv8q91Nac6xX55_4GHU'

url = "https://api.minimax.chat/v1/text/chatcompletion"

# 尝试不同的模型名称格式
models = [
    "abab6.5s-chat",
    "abab5.5s-chat", 
    "abab6.5-chat",
    "abab5.5-chat",
    "abab6s-chat",
    "abab5s-chat",
    "MiniMax-text-01",
    "MiniMax-text-01-v2",
]

for model in models:
    print(f"\n--- Testing model: {model} ---")
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in 3 words"}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:400]}")
    except Exception as e:
        print(f"Error: {e}")
