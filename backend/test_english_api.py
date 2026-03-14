#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试英语阅读API"""

import requests
import json
import sys

BASE_URL = 'http://localhost:5000'

print('=== 测试英语阅读API ===')

# 测试1: 获取每日文章
print('\n1. 测试 GET /api/english/daily')
try:
    r = requests.get(f'{BASE_URL}/api/english/daily', timeout=30)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    if data.get('article'):
        print(f'   文章标题: {data["article"].get("title")}')
        print(f'   词数: {data["article"].get("wordCount")}')
        print(f'   题目数量: {len(data["article"].get("questions", []))}')
except Exception as e:
    print(f'   错误: {e}')

# 测试2: 查询单词
print('\n2. 测试 GET /api/english/word?word=hello')
try:
    r = requests.get(f'{BASE_URL}/api/english/word?word=hello', timeout=10)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    if data.get('data'):
        print(f'   单词: {data["data"].get("word")}')
        print(f'   音标: {data["data"].get("phonetic")}')
        print(f'   释义数量: {len(data["data"].get("meanings", []))}')
except Exception as e:
    print(f'   错误: {e}')

# 测试3: 获取单词本
print('\n3. 测试 GET /api/english/vocabulary')
try:
    r = requests.get(f'{BASE_URL}/api/english/vocabulary', timeout=10)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    print(f'   单词数量: {data.get("count", 0)}')
except Exception as e:
    print(f'   错误: {e}')

# 测试4: 添加单词
print('\n4. 测试 POST /api/english/vocabulary')
try:
    r = requests.post(f'{BASE_URL}/api/english/vocabulary', json={
        'word': 'achievement',
        'articleId': 'test-article'
    }, timeout=10)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    print(f'   消息: {data.get("message")}')
except Exception as e:
    print(f'   错误: {e}')

# 测试5: 获取文章列表
print('\n5. 测试 GET /api/english/articles')
try:
    r = requests.get(f'{BASE_URL}/api/english/articles', timeout=10)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    print(f'   文章数量: {len(data.get("articles", []))}')
except Exception as e:
    print(f'   错误: {e}')

# 测试6: 删除单词
print('\n6. 测试 DELETE /api/english/vocabulary/achievement')
try:
    r = requests.delete(f'{BASE_URL}/api/english/vocabulary/achievement', timeout=10)
    print(f'   状态码: {r.status_code}')
    data = r.json()
    print(f'   成功: {data.get("success")}')
    print(f'   消息: {data.get("message")}')
except Exception as e:
    print(f'   错误: {e}')

print('\n=== API测试完成 ===')
