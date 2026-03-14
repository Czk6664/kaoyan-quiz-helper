import requests
import json

MINIMAX_API_KEY = 'sk-cp-8TEdW3D4r4nlNcao1PGu_xOjb8hd8gZqYaSIDOs4xAJgKdIx9IbMnFvW70tbv-rqnqBfpeEjw4wDUKXBbFa8FrdaKqlW9GG4pWFXOv8q91Nac6xX55_4GHU'

# 尝试不同的API端点
endpoints = [
    "https://api.minimax.chat/v1/text/chatcompletion_pro_2",
    "https://api.minimax.chat/v1/text/chatcompletion",
    "https://api.minimax.chat/v1/chatcompletion",
    "https://api.minimax.chat/v1/text/chatcompletion_v2"
]

models = ["abab6.5s-chat", "abab5.5s-chat", "abab6-chat", "MiniMax-text-01"]

for url in endpoints:
    for model in models:
        print(f"\n--- Testing URL: {url}, Model: {model} ---")
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
            if response.status_code != 404:
                print(f"Response: {response.text[:300]}")
                break
        except Exception as e:
            print(f"Error: {e}")
    else:
        continue
    break
