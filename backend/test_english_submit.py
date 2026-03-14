#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试英语阅读提交答案API"""

import requests
import json

BASE_URL = 'http://localhost:5000'

print('=== 测试提交答案API ===')

# 先获取今日文章
print('\n1. 获取今日文章...')
r = requests.get(f'{BASE_URL}/api/english/daily', timeout=30)
data = r.json()

if data.get('success') and data.get('article'):
    article = data['article']
    article_id = article['id']
    questions = article['questions']
    
    print(f'   文章ID: {article_id}')
    print(f'   题目数量: {len(questions)}')
    
    # 构造答案（模拟用户作答）
    answers = []
    for i, q in enumerate(questions):
        # 模拟：前3题选A，后2题选B
        user_answer = 'A' if i < 3 else 'B'
        answers.append({
            'questionId': q['id'],
            'answer': user_answer
        })
    
    print(f'\n2. 提交答案...')
    print(f'   提交的答案: {[a["answer"] for a in answers]}')
    
    r = requests.post(f'{BASE_URL}/api/english/submit', json={
        'articleId': article_id,
        'answers': answers
    }, timeout=10)
    
    result = r.json()
    print(f'   状态码: {r.status_code}')
    print(f'   成功: {result.get("success")}')
    print(f'   得分: {result.get("score")}%')
    print(f'   正确数: {result.get("correctCount")}/{result.get("totalCount")}')
    
    if result.get('results'):
        print('\n   详细结果:')
        for res in result['results']:
            status = '✓' if res['isCorrect'] else '✗'
            print(f'   题目{res["questionId"]}: 你的答案={res["yourAnswer"]}, 正确答案={res["correctAnswer"]} {status}')

print('\n=== 测试完成 ===')
