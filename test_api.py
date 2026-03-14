import requests
import json

MINIMAX_API_KEY = 'sk-cp-8TEdW3D4r4nlNcao1PGu_xOjb8hd8gZqYaSIDOs4xAJgKdIx9IbMnFvW70tbv-rqnqBfpeEjw4wDUKXBbFa8FrdaKqlW9GG4pWFXOv8q91Nac6xX55_4GHU'
MINIMAX_API_URL = 'https://api.minimax.chat/v1/text/chatcompletion_pro_2'

prompt = '''请生成1道关于Python的选择题，要求：
1. 4个选项(A,B,C,D)，只有一个是正确答案
2. 包含题目内容、选项、正确答案、难度(1-5)
3. 返回JSON格式数组，格式如下：
[{
    "question": "题目内容",
    "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
    "answer": "正确答案(A/B/C/D)",
    "difficulty": 难度(1-5)
}]
只返回JSON数组，不要其他文字。'''

headers = {
    "Authorization": f"Bearer {MINIMAX_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "abab6.5s-chat",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.7
}

print("Testing MiniMax API...")
try:
    response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response preview: {response.text[:500]}")
    
    if response.status_code == 200:
        result = response.json()
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"\nGenerated content: {text[:500]}")
except Exception as e:
    print(f"Error: {e}")
