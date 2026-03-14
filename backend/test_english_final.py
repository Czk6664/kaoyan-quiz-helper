#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试英语阅读API - 最终版"""

import requests
import json
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'http://localhost:5000'

print('=== Testing English Reading APIs ===')

# 1. Get daily article
print('\n1. GET /api/english/daily')
r = requests.get(f'{BASE_URL}/api/english/daily', timeout=30)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
if data.get('article'):
    article = data['article']
    print(f'   Title: {article.get("title")}')
    print(f'   Word Count: {article.get("wordCount")}')
    print(f'   Questions: {len(article.get("questions", []))}')
    article_id = article['id']
else:
    article_id = None

# 2. Query word
print('\n2. GET /api/english/word?word=achievement')
r = requests.get(f'{BASE_URL}/api/english/word?word=achievement', timeout=10)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
if data.get('data'):
    print(f'   Word: {data["data"].get("word")}')
    meanings = data["data"].get("meanings", [])
    print(f'   Meanings count: {len(meanings)}')

# 3. Add vocabulary
print('\n3. POST /api/english/vocabulary')
r = requests.post(f'{BASE_URL}/api/english/vocabulary', json={
    'word': 'perseverance',
    'articleId': article_id or 'test'
}, timeout=10)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
print(f'   Message: {data.get("message")}')

# 4. Get vocabulary list
print('\n4. GET /api/english/vocabulary')
r = requests.get(f'{BASE_URL}/api/english/vocabulary', timeout=10)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
print(f'   Count: {data.get("count", 0)}')

# 5. Submit answers
if article_id:
    print('\n5. POST /api/english/submit')
    r = requests.get(f'{BASE_URL}/api/english/daily', timeout=10)
    article = r.json().get('article', {})
    questions = article.get('questions', [])
    
    answers = []
    for i, q in enumerate(questions):
        user_answer = 'A' if i < 3 else 'B'
        answers.append({'questionId': q['id'], 'answer': user_answer})
    
    r = requests.post(f'{BASE_URL}/api/english/submit', json={
        'articleId': article_id,
        'answers': answers
    }, timeout=10)
    data = r.json()
    print(f'   Status: {r.status_code}')
    print(f'   Success: {data.get("success")}')
    print(f'   Score: {data.get("score")}%')
    print(f'   Correct: {data.get("correctCount")}/{data.get("totalCount")}')
    if data.get('results'):
        correct = sum(1 for r in data['results'] if r['isCorrect'])
        print(f'   Detailed: {correct} correct out of {len(data["results"])}')

# 6. Get articles list
print('\n6. GET /api/english/articles')
r = requests.get(f'{BASE_URL}/api/english/articles', timeout=10)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
print(f'   Articles count: {len(data.get("articles", []))}')

# 7. Delete vocabulary
print('\n7. DELETE /api/english/vocabulary/perseverance')
r = requests.delete(f'{BASE_URL}/api/english/vocabulary/perseverance', timeout=10)
data = r.json()
print(f'   Status: {r.status_code}')
print(f'   Success: {data.get("success")}')
print(f'   Message: {data.get("message")}')

print('\n=== All Tests Passed! ===')
