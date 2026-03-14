from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import os
import uuid
from datetime import datetime, timedelta
import requests
import re
import base64
import io
import hashlib
import secrets
import bcrypt
from functools import wraps

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
QUESTIONS_FILE = os.path.join(DATA_DIR, 'questions.json')
WRONG_FILE = os.path.join(DATA_DIR, 'wrong.json')
FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')
MEMORY_FILE = os.path.join(DATA_DIR, 'memory.json')  # 记忆曲线数据
STATS_FILE = os.path.join(DATA_DIR, 'stats.json')     # 统计数据
CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')  # 分类数据

# 同步相关配置
USERS_FILE = os.path.join(DATA_DIR, 'users.json')           # 用户数据
SYNC_META_FILE = os.path.join(DATA_DIR, 'sync_meta.json')   # 同步元数据
SYNC_HISTORY_FILE = os.path.join(DATA_DIR, 'sync_history.json')  # 同步历史
JWT_SECRET = os.environ.get('JWT_SECRET', '')
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)  # 自动生成
    print("警告: JWT_SECRET 未设置，已自动生成")
TOKEN_EXPIRE_DAYS = 30

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# MiniMax API配置 - 请替换为你的API Key
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
if not MINIMAX_API_KEY:
    print("警告: MINIMAX_API_KEY 未设置")
MINIMAX_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_pro_2"

# Kimi2.5 API (支持PDF)
KIMI_API_KEY = os.environ.get('KIMI_API_KEY', '')
if not KIMI_API_KEY:
    print("警告: KIMI_API_KEY 未设置")
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# ========== 记忆曲线相关函数 ==========

# 艾宾浩斯遗忘曲线间隔（天）
EBBINGHAUS_INTERVALS = [1, 3, 7, 14, 30, 60, 90, 180]

def calculate_memory_strength(wrong_record):
    """计算记忆强度（0-100）"""
    review_count = wrong_record.get('reviewCount', 0)
    interval = wrong_record.get('interval', 1)
    last_review = wrong_record.get('lastReview')
    
    if not last_review:
        return 0
    
    # 基于复习次数和间隔计算记忆强度
    base_strength = min(review_count * 15, 75)  # 最高75分来自复习次数
    interval_bonus = min(interval * 5, 25)       # 最高25分来自间隔
    
    # 时间衰减
    days_since = (datetime.now() - datetime.fromisoformat(last_review)).days
    time_decay = max(0, 100 - days_since * 10)
    
    return min(100, base_strength + interval_bonus + time_decay - 50)

def get_review_priority(wrong_record):
    """计算复习优先级（越高越需要复习）"""
    strength = calculate_memory_strength(wrong_record)
    difficulty = wrong_record.get('difficulty', 3)
    is_give_up = wrong_record.get('isGiveUp', False)
    
    # 优先级 = (100 - 记忆强度) * 难度权重 * 放弃惩罚
    priority = (100 - strength) * (1 + difficulty * 0.2)
    if is_give_up:
        priority *= 1.5
    
    return priority

def update_memory_record(question_id, is_correct, is_give_up=False):
    """更新记忆记录"""
    memory_data = load_json(MEMORY_FILE)
    
    if question_id not in memory_data:
        memory_data[question_id] = {
            'totalReviews': 0,
            'correctCount': 0,
            'wrongCount': 0,
            'giveUpCount': 0,
            'history': [],
            'masteryLevel': 0,
            'createdAt': datetime.now().isoformat()
        }
    
    record = memory_data[question_id]
    record['totalReviews'] += 1
    record['lastReview'] = datetime.now().isoformat()
    record['history'].append({
        'time': datetime.now().isoformat(),
        'correct': is_correct,
        'giveUp': is_give_up
    })
    
    # 保持历史记录不超过50条
    if len(record['history']) > 50:
        record['history'] = record['history'][-50:]
    
    if is_correct:
        record['correctCount'] += 1
    elif is_give_up:
        record['giveUpCount'] += 1
        record['wrongCount'] += 1
    else:
        record['wrongCount'] += 1
    
    # 计算掌握程度
    if record['totalReviews'] > 0:
        record['masteryLevel'] = round(record['correctCount'] / record['totalReviews'] * 100, 1)
    
    save_json(MEMORY_FILE, memory_data)
    return record

def get_memory_stats():
    """获取记忆统计数据"""
    memory_data = load_json(MEMORY_FILE)
    
    total_questions = len(memory_data)
    mastered = sum(1 for r in memory_data.values() if r.get('masteryLevel', 0) >= 80)
    learning = sum(1 for r in memory_data.values() if 0 < r.get('masteryLevel', 0) < 80)
    weak = sum(1 for r in memory_data.values() if r.get('masteryLevel', 0) == 0)
    
    return {
        'totalQuestions': total_questions,
        'mastered': mastered,
        'learning': learning,
        'weak': weak,
        'masteryRate': round(mastered / total_questions * 100, 1) if total_questions > 0 else 0
    }

def get_memory_curve(days=30):
    """获取记忆曲线数据"""
    memory_data = load_json(MEMORY_FILE)
    
    # 按天统计
    curve = {}
    for _ in range(days):
        date = (datetime.now() - timedelta(days=_)).strftime('%Y-%m-%d')
        curve[date] = {'review': 0, 'correct': 0, 'wrong': 0}
    
    for record in memory_data.values():
        for h in record.get('history', []):
            date = h['time'][:10]
            if date in curve:
                curve[date]['review'] += 1
                if h['correct']:
                    curve[date]['correct'] += 1
                else:
                    curve[date]['wrong'] += 1
    
    # 转换为列表并排序
    result = []
    for date in sorted(curve.keys()):
        result.append({
            'date': date,
            'review': curve[date]['review'],
            'correct': curve[date]['correct'],
            'wrong': curve[date]['wrong'],
            'accuracy': round(curve[date]['correct'] / curve[date]['review'] * 100, 1) if curve[date]['review'] > 0 else 0
        })
    
    return result

# ========== PDF处理 ==========

def extract_text_from_pdf(pdf_path, max_pages=50):
    """从PDF提取文本，可设置最大页数"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        
        total_pages = len(reader)
        pages_to_read = min(total_pages, max_pages)
        
        text = ""
        for i in range(pages_to_read):
            page = reader.pages[i]
            text += page.extract_text() + "\n"
        
        return text, total_pages
    except Exception as e:
        print(f"PDF提取错误: {e}")
        return None, 0

def split_text(text, chunk_size=8000):
    """将长文本分割成小块"""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    
    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current)
            current = para + "\n\n"
    
    if current:
        chunks.append(current)
    
    return chunks

# 调用Kimi2.5 API生成题目(支持PDF)
def generate_questions_with_kimi(content, count, source="PDF文档"):
    """使用Kimi2.5生成题目"""
    prompt = f"""请根据以下内容生成{count}道选择题。每道题必须有4个选项(A,B,C,D)，其中只有一个正确答案。

要求：
1. 每道题包含题号、题目内容、4个选项、正确答案、难度等级(1-5星)
2. 难度根据内容复杂度确定
3. 返回JSON格式数组，每道题格式如下：
{{
    "question": "题目内容",
    "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
    "answer": "正确答案(A/B/C/D)",
    "difficulty": 难度(1-5)
}}

内容如下：
{content}

请直接返回JSON数组，不要有其他文字："""

    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "moonshot-v1-8k-vision-preview",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(KIMI_API_URL, headers=headers, json=payload, timeout=180)
        result = response.json()
        
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            
            for q in questions:
                q['id'] = str(uuid.uuid4())
                q['source'] = source
                q['createdAt'] = datetime.now().isoformat()
            
            return questions
        return None
    except Exception as e:
        print(f"Kimi API Error: {e}")
        return None

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 默认分类数据
DEFAULT_CATEGORIES = {
    "考研政治": {
        "icon": "📚",
        "chapters": [
            "马克思主义基本原理",
            "毛泽东思想和中国特色社会主义理论体系概论",
            "中国近现代史纲要",
            "思想道德修养与法律基础",
            "形势与政策"
        ]
    },
    "考研英语": {
        "icon": "🌍",
        "chapters": [
            "阅读理解",
            "完形填空",
            "翻译",
            "写作",
            "词汇与语法"
        ]
    },
    "考研数学": {
        "icon": "🔢",
        "chapters": [
            "高等数学",
            "线性代数",
            "概率论与数理统计"
        ]
    },
    "专业课": {
        "icon": "📖",
        "chapters": [
            "计算机基础",
            "数据结构",
            "操作系统",
            "计算机网络"
        ]
    }
}

# 初始化数据文件
def init_data_files():
    # 初始化全局数据文件
    for f in [QUESTIONS_FILE, WRONG_FILE, FAVORITES_FILE, MEMORY_FILE, STATS_FILE]:
        if not os.path.exists(f):
            if f == MEMORY_FILE:
                with open(f, 'w', encoding='utf-8') as fp:
                    json.dump({}, fp, ensure_ascii=False)
            elif f == STATS_FILE:
                with open(f, 'w', encoding='utf-8') as fp:
                    json.dump({'daily': {}, 'streak': 0, 'lastStudyDate': None}, fp, ensure_ascii=False)
            else:
                with open(f, 'w', encoding='utf-8') as fp:
                    json.dump([], fp, ensure_ascii=False)
    
    # 初始化分类数据
    if not os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'w', encoding='utf-8') as fp:
            json.dump(DEFAULT_CATEGORIES, fp, ensure_ascii=False)
    
    # 初始化用户数据文件
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as fp:
            json.dump([], fp, ensure_ascii=False)

# 加载数据
def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

init_data_files()

# 生成题目的Prompt
def build_prompt(content, count):
    return f"""请根据以下内容生成{count}道选择题。每道题必须有4个选项(A,B,C,D)，其中只有一个正确答案。

要求：
1. 每道题包含题号、题目内容、4个选项、正确答案、难度等级(1-5星)
2. 难度根据内容复杂度确定
3. 返回JSON格式数组，每道题格式如下：
{{
    "question": "题目内容",
    "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
    "answer": "正确答案(A/B/C/D)",
    "difficulty": 难度(1-5)
}}

内容如下：
{content}

请直接返回JSON数组，不要有其他文字："""

# 调用MiniMax API生成题目
def generate_questions(content, count, source="自定义"):
    prompt = build_prompt(content, count)
    
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=120)
        result = response.json()
        
        # 提取JSON
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # 尝试提取JSON数组
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            
            # 添加ID和元数据
            for q in questions:
                q['id'] = str(uuid.uuid4())
                q['source'] = source
                q['createdAt'] = datetime.now().isoformat()
            
            return questions
        else:
            return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

# ========== 更新每日统计 ==========

def update_daily_stats(is_correct):
    """更新每日学习统计"""
    stats = load_json(STATS_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if 'daily' not in stats:
        stats['daily'] = {}
    
    if today not in stats['daily']:
        stats['daily'][today] = {'total': 0, 'correct': 0, 'wrong': 0, 'time': 0}
    
    stats['daily'][today]['total'] += 1
    if is_correct:
        stats['daily'][today]['correct'] += 1
    else:
        stats['daily'][today]['wrong'] += 1
    
    # 更新连续学习天数
    if stats.get('lastStudyDate'):
        last_date = datetime.fromisoformat(stats['lastStudyDate']).date()
        if (datetime.now().date() - last_date).days == 1:
            stats['streak'] = stats.get('streak', 0) + 1
        elif (datetime.now().date() - last_date).days > 1:
            stats['streak'] = 1
    else:
        stats['streak'] = 1
    
    stats['lastStudyDate'] = datetime.now().isoformat()
    
    # 保持只保留90天数据
    cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    stats['daily'] = {k: v for k, v in stats['daily'].items() if k >= cutoff}
    
    save_json(STATS_FILE, stats)
    return stats

# API: 上传文档生成题目
@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    content = data.get('content', '')
    count = data.get('count', 10)
    source = data.get('source', '自定义')
    
    questions = generate_questions(content, count, source)
    
    if questions:
        # 保存到题库
        existing = load_json(QUESTIONS_FILE)
        existing.extend(questions)
        save_json(QUESTIONS_FILE, existing)
        return jsonify({'success': True, 'count': len(questions), 'questions': questions})
    else:
        return jsonify({'success': False, 'error': '生成失败'})

# API: 上传PDF文件生成题目
@app.route('/api/generate/pdf', methods=['POST'])
def generate_from_pdf():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名空'})
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'success': False, 'error': '只支持PDF文件'})
    
    count = int(request.form.get('count', 10))
    max_pages = int(request.form.get('max_pages', 50))
    
    # 保存文件
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # 提取PDF文本
        text, total_pages = extract_text_from_pdf(filepath, max_pages)
        
        if text is None or text.strip() == "":
            return jsonify({'success': False, 'error': 'PDF文本提取失败'})
        
        # 如果文本太长，分段处理
        text = text.strip()
        if len(text) > 20000:
            # 分段处理
            chunks = split_text(text, chunk_size=15000)
            all_questions = []
            
            for i, chunk in enumerate(chunks):
                # 每段生成部分题目
                chunk_count = max(3, count // len(chunks))
                questions = generate_questions_with_kimi(chunk, chunk_count, f"{filename}(第{i+1}部分)")
                if questions:
                    all_questions.extend(questions)
                
                if len(all_questions) >= count:
                    break
            
            questions = all_questions[:count]
        else:
            # 短文本直接处理
            questions = generate_questions_with_kimi(text, count, filename)
        
        if questions:
            # 保存到题库
            existing = load_json(QUESTIONS_FILE)
            existing.extend(questions)
            save_json(QUESTIONS_FILE, existing)
            
            return jsonify({
                'success': True, 
                'count': len(questions), 
                'questions': questions,
                'total_pages': total_pages,
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'error': '生成失败'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        # 清理上传的文件
        if os.path.exists(filepath):
            os.remove(filepath)

# API: 获取刷题题目（增强：错题优先权重 + 分类筛选）
@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    count = int(request.args.get('count', 10))
    category = request.args.get('category', '')  # 分类筛选
    chapter = request.args.get('chapter', '')    # 章节筛选
    
    wrong_list = load_json(WRONG_FILE)
    questions = load_json(QUESTIONS_FILE)
    memory_data = load_json(MEMORY_FILE)
    
    # 按分类筛选
    if category:
        questions = [q for q in questions if q.get('category', '') == category]
    if chapter:
        questions = [q for q in questions if q.get('chapter', '') == chapter]
    
    if len(questions) == 0:
        return jsonify([])
    
    import random
    
    # 构建带权重的题目列表
    weighted_questions = []
    wrong_ids = {w['questionId'] for w in wrong_list}
    
    for q in questions:
        question_id = q['id']
        
        # 基础权重
        weight = 1.0
        
        # 如果是错题，增加权重
        if question_id in wrong_ids:
            # 查找错题记录
            wrong_record = next((w for w in wrong_list if w['questionId'] == question_id), None)
            if wrong_record:
                # 根据记忆强度调整权重（记忆越弱，权重越高）
                priority = get_review_priority(wrong_record)
                weight += priority / 10  # 转换为权重
        
        # 根据记忆数据调整权重
        if question_id in memory_data:
            record = memory_data[question_id]
            mastery = record.get('masteryLevel', 0)
            # 掌握程度低的题目权重更高
            if mastery < 50:
                weight += (50 - mastery) / 50
            elif mastery < 80:
                weight += (80 - mastery) / 100
        
        # 添加到加权池（重复添加实现权重）
        weight = max(1, int(weight * 3))  # 至少1次，最多约6次
        for _ in range(weight):
            weighted_questions.append(q)
    
    # 按权重随机选择
    if len(weighted_questions) >= count:
        selected = random.sample(weighted_questions, count)
    else:
        selected = weighted_questions
    
    # 去重并返回
    seen = set()
    result = []
    for q in selected:
        if q['id'] not in seen:
            seen.add(q['id'])
            q_copy = q.copy()
            q_copy.pop('answer', None)
            result.append(q_copy)
            if len(result) >= count:
                break
    
    return jsonify(result)

# API: 提交答案
@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    question_id = data.get('questionId')
    answer = data.get('answer')
    is_collected = data.get('isCollected', False)
    is_give_up = data.get('isGiveUp', False)
    
    questions = load_json(QUESTIONS_FILE)
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        return jsonify({'success': False, 'error': '题目不存在'})
    
    is_correct = answer == question.get('answer')
    
    # 更新记忆记录
    update_memory_record(question_id, is_correct, is_give_up)
    
    # 更新每日统计
    update_daily_stats(is_correct)
    
    # 如果答错或不会，记录到错题本
    if not is_correct or is_give_up:
        wrong_list = load_json(WRONG_FILE)
        
        # 检查是否已存在
        exists = any(w['questionId'] == question_id for w in wrong_list)
        
        if not exists:
            wrong_list.append({
                'questionId': question_id,
                'yourAnswer': answer if not is_give_up else '不会',
                'correctAnswer': question.get('answer'),
                'isGiveUp': is_give_up,
                'wrongAt': datetime.now().isoformat(),
                'lastReview': datetime.now().isoformat(),
                'reviewCount': 0,
                'interval': 1,
                'nextReview': (datetime.now() + timedelta(days=1)).isoformat(),
                'difficulty': question.get('difficulty', 3)
            })
            save_json(WRONG_FILE, wrong_list)
    
    # 收藏
    if is_collected:
        fav_list = load_json(FAVORITES_FILE)
        exists = any(f['questionId'] == question_id for f in fav_list)
        
        if not exists:
            fav_list.append({
                'questionId': question_id,
                'collectedAt': datetime.now().isoformat()
            })
            save_json(FAVORITES_FILE, fav_list)
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'correctAnswer': question.get('answer')
    })

# API: 获取错题本（增强：包含记忆强度）
@app.route('/api/wrong', methods=['GET'])
def get_wrong():
    wrong_list = load_json(WRONG_FILE)
    questions = load_json(QUESTIONS_FILE)
    
    result = []
    for w in wrong_list:
        q = next((q for q in questions if q['id'] == w['questionId']), None)
        if q:
            w_copy = w.copy()
            w_copy['question'] = q['question']
            w_copy['options'] = q['options']
            w_copy['answer'] = q['answer']
            w_copy['difficulty'] = q.get('difficulty', 3)
            # 添加记忆强度
            w_copy['memoryStrength'] = calculate_memory_strength(w)
            w_copy['priority'] = get_review_priority(w)
            result.append(w_copy)
    
    # 按优先级排序
    result.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    return jsonify(result)

# API: 获取收藏夹
@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    fav_list = load_json(FAVORITES_FILE)
    questions = load_json(QUESTIONS_FILE)
    
    result = []
    for f in fav_list:
        q = next((q for q in questions if q['id'] == f['questionId']), None)
        if q:
            f_copy = f.copy()
            f_copy['question'] = q['question']
            f_copy['options'] = q['options']
            f_copy['answer'] = q['answer']
            f_copy['difficulty'] = q.get('difficulty', 3)
            result.append(f_copy)
    
    return jsonify(result)

# API: 获取复习题目（增强：智能排序）
@app.route('/api/review', methods=['GET'])
def get_review():
    wrong_list = load_json(WRONG_FILE)
    questions = load_json(QUESTIONS_FILE)
    
    now = datetime.now()
    result = []
    
    for w in wrong_list:
        next_review = datetime.fromisoformat(w['nextReview'])
        if next_review <= now:
            q = next((q for q in questions if q['id'] == w['questionId']), None)
            if q:
                w_copy = w.copy()
                w_copy['question'] = q['question']
                w_copy['options'] = q['options']
                w_copy['answer'] = q['answer']
                w_copy['difficulty'] = q.get('difficulty', 3)
                w_copy['memoryStrength'] = calculate_memory_strength(w)
                w_copy['priority'] = get_review_priority(w)
                result.append(w_copy)
    
    # 按优先级排序
    result.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    return jsonify(result)

# API: 复习提交（增强：使用艾宾浩斯遗忘曲线）
@app.route('/api/review/submit', methods=['POST'])
def review_submit():
    data = request.json
    question_id = data.get('questionId')
    answer = data.get('answer')
    
    wrong_list = load_json(WRONG_FILE)
    questions = load_json(QUESTIONS_FILE)
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        return jsonify({'success': False, 'error': '题目不存在'})
    
    is_correct = answer == question.get('answer')
    
    # 更新记忆记录
    update_memory_record(question_id, is_correct)
    
    # 更新每日统计
    update_daily_stats(is_correct)
    
    # 更新错题记录
    for w in wrong_list:
        if w['questionId'] == question_id:
            w['reviewCount'] += 1
            w['lastReview'] = datetime.now().isoformat()
            
            if is_correct:
                # 答对了，使用艾宾浩斯曲线计算间隔
                review_count = w['reviewCount']
                if review_count <= len(EBBINGHAUS_INTERVALS):
                    w['interval'] = EBBINGHAUS_INTERVALS[review_count - 1]
                else:
                    w['interval'] = EBBINGHAUS_INTERVALS[-1]
                
                w['nextReview'] = (datetime.now() + timedelta(days=w['interval'])).isoformat()
            else:
                # 答错了，重置到最短间隔
                w['interval'] = 1
                w['nextReview'] = (datetime.now() + timedelta(days=1)).isoformat()
            break
    
    save_json(WRONG_FILE, wrong_list)
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'correctAnswer': question.get('answer'),
        'nextReview': wrong_list[0].get('nextReview') if wrong_list else None  # 返回下次复习时间
    })

# API: 获取统计（增强：包含记忆统计）
@app.route('/api/stats', methods=['GET'])
def get_stats():
    questions = load_json(QUESTIONS_FILE)
    wrong_list = load_json(WRONG_FILE)
    fav_list = load_json(FAVORITES_FILE)
    stats = load_json(STATS_FILE)
    memory_stats = get_memory_stats()
    
    # 计算今日统计
    today = datetime.now().strftime('%Y-%m-%d')
    daily = stats.get('daily', {}).get(today, {'total': 0, 'correct': 0, 'wrong': 0})
    
    # 计算待复习数量
    now = datetime.now()
    pending_review = sum(1 for w in wrong_list if datetime.fromisoformat(w['nextReview']) <= now)
    
    return jsonify({
        'total': len(questions),
        'wrong': len(wrong_list),
        'favorites': len(fav_list),
        'today': {
            'total': daily['total'],
            'correct': daily['correct'],
            'wrong': daily['wrong'],
            'accuracy': round(daily['correct'] / daily['total'] * 100, 1) if daily['total'] > 0 else 0
        },
        'streak': stats.get('streak', 0),
        'pendingReview': pending_review,
        'memory': memory_stats
    })

# API: 获取记忆曲线
@app.route('/api/memory/curve', methods=['GET'])
def get_memory_curve_api():
    days = int(request.args.get('days', 30))
    return jsonify(get_memory_curve(days))

# API: 获取记忆统计详情
@app.route('/api/memory/stats', methods=['GET'])
def get_memory_stats_api():
    return jsonify(get_memory_stats())

# API: 获取每日学习趋势
@app.route('/api/stats/trend', methods=['GET'])
def get_trend():
    days = int(request.args.get('days', 7))
    stats = load_json(STATS_FILE)
    
    trend = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily = stats.get('daily', {}).get(date, {'total': 0, 'correct': 0, 'wrong': 0})
        trend.append({
            'date': date,
            'total': daily['total'],
            'correct': daily['correct'],
            'wrong': daily['wrong'],
            'accuracy': round(daily['correct'] / daily['total'] * 100, 1) if daily['total'] > 0 else 0
        })
    
    trend.reverse()
    return jsonify(trend)

# API: 获取复习提醒
@app.route('/api/review/remind', methods=['GET'])
def get_review_remind():
    wrong_list = load_json(WRONG_FILE)
    questions = load_json(QUESTIONS_FILE)
    
    now = datetime.now()
    reminders = []
    
    for w in wrong_list:
        next_review = datetime.fromisoformat(w['nextReview'])
        q = next((q for q in questions if q['id'] == w['questionId']), None)
        
        if q:
            # 计算距离下次复习的时间
            diff = next_review - now
            
            # 如果是即将到期的复习（1小时内）或已过期
            if diff.total_seconds() <= 3600:
                status = "overdue" if diff.total_seconds() < 0 else "due"
                reminders.append({
                    'questionId': w['questionId'],
                    'question': q['question'][:50] + '...' if len(q['question']) > 50 else q['question'],
                    'nextReview': w['nextReview'],
                    'status': status,
                    'memoryStrength': calculate_memory_strength(w),
                    'interval': w.get('interval', 1)
                })
    
    # 按状态和时间排序
    reminders.sort(key=lambda x: (0 if x['status'] == 'overdue' else 1, x['nextReview']))
    
    return jsonify({
        'count': len(reminders),
        'reminders': reminders[:10]  # 最多返回10条
    })

# API: 删除错题
@app.route('/api/wrong/<question_id>', methods=['DELETE'])
def delete_wrong(question_id):
    wrong_list = load_json(WRONG_FILE)
    wrong_list = [w for w in wrong_list if w['questionId'] != question_id]
    save_json(WRONG_FILE, wrong_list)
    return jsonify({'success': True})

# API: 取消收藏
@app.route('/api/favorites/<question_id>', methods=['DELETE'])
def delete_favorite(question_id):
    fav_list = load_json(FAVORITES_FILE)
    fav_list = [f for f in fav_list if f['questionId'] != question_id]
    save_json(FAVORITES_FILE, fav_list)
    return jsonify({'success': True})

# API: 导入题目(测试用)
@app.route('/api/import', methods=['POST'])
def import_questions():
    data = request.json
    questions = data.get('questions', [])
    
    existing = load_json(QUESTIONS_FILE)
    existing.extend(questions)
    save_json(QUESTIONS_FILE, existing)
    
    return jsonify({'success': True, 'count': len(questions)})

# API: 清除所有数据（谨慎使用）
@app.route('/api/reset', methods=['POST'])
def reset_all():
    """清除所有学习数据"""
    save_json(QUESTIONS_FILE, [])
    save_json(WRONG_FILE, [])
    save_json(FAVORITES_FILE, [])
    save_json(MEMORY_FILE, {})
    save_json(STATS_FILE, {'daily': {}, 'streak': 0, 'lastStudyDate': None})
    return jsonify({'success': True, 'message': '所有数据已清除'})


# ==========================================
# 用户认证系统
# ==========================================

def load_users():
    """加载用户数据"""
    return load_json(USERS_FILE)

def save_users(users):
    """保存用户数据"""
    save_json(USERS_FILE, users)

def hash_password(password):
    """密码哈希 - 使用bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    """验证密码 - 使用bcrypt"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def generate_token(user_id):
    """生成JWT令牌（简化版）"""
    timestamp = datetime.now().timestamp()
    payload = f"{user_id}:{timestamp}:{secrets.token_hex(16)}"
    signature = hashlib.sha256(f"{payload}:{JWT_SECRET}".encode()).hexdigest()
    return f"{payload}.{signature}"

def verify_token(token):
    """验证令牌"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        payload = parts[0]
        signature = parts[2]
        expected_sig = hashlib.sha256(f"{payload}:{JWT_SECRET}".encode()).hexdigest()
        
        if signature != expected_sig:
            return None
        
        user_id = payload.split(':')[0]
        return user_id
    except:
        return None

def token_required(f):
    """装饰器：验证Token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': '缺少认证令牌'}), 401
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'success': False, 'error': '无效的令牌'}), 401
        
        # 验证用户存在
        users = load_users()
        user = next((u for u in users if u['id'] == user_id), None)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated

# API: 用户注册
@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码长度至少6位'}), 400
    
    users = load_users()
    
    # 检查用户名是否已存在
    if any(u['username'] == username for u in users):
        return jsonify({'success': False, 'error': '用户名已存在'}), 400
    
    # 创建用户
    user_id = str(uuid.uuid4())
    new_user = {
        'id': user_id,
        'username': username,
        'password': hash_password(password),
        'createdAt': datetime.now().isoformat(),
        'lastLogin': datetime.now().isoformat()
    }
    
    users.append(new_user)
    save_users(users)
    
    # 生成令牌
    token = generate_token(user_id)
    
    return jsonify({
        'success': True,
        'message': '注册成功',
        'token': token,
        'user': {
            'id': user_id,
            'username': username
        }
    })

# API: 用户登录
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
    
    users = load_users()
    user = next((u for u in users if u['username'] == username), None)
    
    if not user or not verify_password(password, user['password']):
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
    
    # 更新最后登录时间
    user['lastLogin'] = datetime.now().isoformat()
    save_users(users)
    
    # 生成令牌
    token = generate_token(user['id'])
    
    return jsonify({
        'success': True,
        'message': '登录成功',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username']
        }
    })

# API: 验证Token
@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token_api():
    """验证Token是否有效"""
    user = request.current_user
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username']
        }
    })


# ==========================================
# 数据同步系统
# ==========================================

def get_user_data_dir(user_id):
    """获取用户专属数据目录"""
    user_dir = os.path.join(DATA_DIR, 'users', user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_user_questions_file(user_id):
    """获取用户题目文件"""
    return os.path.join(get_user_data_dir(user_id), 'questions.json')

def get_user_wrong_file(user_id):
    """获取用户错题文件"""
    return os.path.join(get_user_data_dir(user_id), 'wrong.json')

def get_user_favorites_file(user_id):
    """获取用户收藏文件"""
    return os.path.join(get_user_data_dir(user_id), 'favorites.json')

def get_user_memory_file(user_id):
    """获取用户记忆数据文件"""
    return os.path.join(get_user_data_dir(user_id), 'memory.json')

def get_user_stats_file(user_id):
    """获取用户统计数据文件"""
    return os.path.join(get_user_data_dir(user_id), 'stats.json')

def get_user_sync_meta_file(user_id):
    """获取用户同步元数据文件"""
    return os.path.join(get_user_data_dir(user_id), 'sync_meta.json')

def init_user_data_files(user_id):
    """初始化用户数据文件"""
    files = [
        (get_user_questions_file(user_id), []),
        (get_user_wrong_file(user_id), []),
        (get_user_favorites_file(user_id), []),
        (get_user_memory_file(user_id), {}),
        (get_user_stats_file(user_id), {'daily': {}, 'streak': 0, 'lastStudyDate': None}),
        (get_user_sync_meta_file(user_id), {
            'lastSync': None,
            'version': 1,
            'questionVersion': 1,
            'wrongVersion': 1,
            'favoriteVersion': 1,
            'memoryVersion': 1,
            'statsVersion': 1
        })
    ]
    
    for filepath, default_data in files:
        if not os.path.exists(filepath):
            save_json(filepath, default_data)

def load_user_json(user_id, filepath):
    """加载用户数据文件"""
    try:
        return load_json(filepath)
    except:
        return []

def save_user_json(user_id, filepath, data):
    """保存用户数据文件"""
    save_json(filepath, data)

def update_sync_version(user_id):
    """更新同步版本号"""
    meta_file = get_user_sync_meta_file(user_id)
    meta = load_json(meta_file)
    
    meta['lastSync'] = datetime.now().isoformat()
    meta['version'] = meta.get('version', 1) + 1
    
    # 更新各模块版本
    meta['questionVersion'] = meta.get('questionVersion', 1) + 1
    meta['wrongVersion'] = meta.get('wrongVersion', 1) + 1
    meta['favoriteVersion'] = meta.get('favoriteVersion', 1) + 1
    meta['memoryVersion'] = meta.get('memoryVersion', 1) + 1
    meta['statsVersion'] = meta.get('statsVersion', 1) + 1
    
    save_json(meta_file, meta)
    return meta

def compute_data_hash(data):
    """计算数据哈希"""
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()

def detect_conflicts(local_data, remote_data, id_field='id'):
    """检测冲突
    
    返回格式: {
        'conflicts': [
            {'id': 'xxx', 'local': {...}, 'remote': {...}, 'localHash': '...', 'remoteHash': '...'}
        ]
    }
    """
    conflicts = []
    
    # 创建ID到数据的映射
    local_by_id = {item[id_field]: item for item in local_data if id_field in item}
    remote_by_id = {item[id_field]: item for item in remote_data if id_field in item}
    
    # 查找共同的ID
    common_ids = set(local_by_id.keys()) & set(remote_by_id.keys())
    
    for item_id in common_ids:
        local_item = local_by_id[item_id]
        remote_item = remote_by_id[item_id]
        
        # 计算哈希（排除syncedAt字段进行比对）
        local_copy = {k: v for k, v in local_item.items() if k != 'syncedAt'}
        remote_copy = {k: v for k, v in remote_item.items() if k != 'syncedAt'}
        
        local_hash = compute_data_hash(local_copy)
        remote_hash = compute_data_hash(remote_copy)
        
        if local_hash != remote_hash:
            conflicts.append({
                'id': item_id,
                'local': local_item,
                'remote': remote_item,
                'localHash': local_hash,
                'remoteHash': remote_hash
            })
    
    return {'conflicts': conflicts}

# API: 上传数据（用于同步）
@app.route('/api/sync/upload', methods=['POST'])
@token_required
def upload_data():
    """数据上传API - 接收客户端数据并合并"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    data = request.json
    
    # 获取客户端数据
    questions = data.get('questions', [])
    wrong = data.get('wrong', [])
    favorites = data.get('favorites', [])
    memory = data.get('memory', {})
    stats = data.get('stats', {})
    
    # 获取服务器当前数据
    server_questions = load_user_json(user_id, get_user_questions_file(user_id))
    server_wrong = load_user_json(user_id, get_user_wrong_file(user_id))
    server_favorites = load_user_json(user_id, get_user_favorites_file(user_id))
    server_memory = load_user_json(user_id, get_user_memory_file(user_id))
    server_stats = load_user_json(user_id, get_user_stats_file(user_id))
    
    # 检测冲突
    conflicts = {
        'questions': detect_conflicts(server_questions, questions),
        'wrong': detect_conflicts(server_wrong, wrong, 'questionId'),
        'favorites': detect_conflicts(server_favorites, favorites, 'questionId')
    }
    
    # 简单的合并策略：以服务器时间为准，保留最新的
    # 但如果客户端有新数据，则合并
    
    # 合并题目（去重，保留最新的）
    question_map = {q['id']: q for q in server_questions}
    for q in questions:
        if q.get('id') not in question_map:
            q['syncedAt'] = datetime.now().isoformat()
            question_map[q['id']] = q
        else:
            # 如果客户端版本更新，使用客户端版本
            client_time = q.get('updatedAt', q.get('createdAt', ''))
            server_time = question_map[q['id']].get('updatedAt', question_map[q['id']].get('createdAt', ''))
            if client_time > server_time:
                q['syncedAt'] = datetime.now().isoformat()
                question_map[q['id']] = q
    
    # 合并错题
    wrong_map = {w['questionId']: w for w in server_wrong}
    for w in wrong:
        if w.get('questionId') not in wrong_map:
            w['syncedAt'] = datetime.now().isoformat()
            wrong_map[w['questionId']] = w
        else:
            client_time = w.get('wrongAt', '')
            server_time = wrong_map[w['questionId']].get('wrongAt', '')
            if client_time > server_time:
                w['syncedAt'] = datetime.now().isoformat()
                wrong_map[w['questionId']] = w
    
    # 合并收藏
    fav_map = {f['questionId']: f for f in server_favorites}
    for f in favorites:
        if f.get('questionId') not in fav_map:
            f['syncedAt'] = datetime.now().isoformat()
            fav_map[f['questionId']] = f
    
    # 合并记忆数据（深合并）
    for q_id, mem_data in memory.items():
        if q_id not in server_memory:
            server_memory[q_id] = mem_data
            server_memory[q_id]['syncedAt'] = datetime.now().isoformat()
        else:
            # 保留复习次数更多的
            client_count = mem_data.get('totalReviews', 0)
            server_count = server_memory[q_id].get('totalReviews', 0)
            if client_count > server_count:
                server_memory[q_id] = mem_data
                server_memory[q_id]['syncedAt'] = datetime.now().isoformat()
    
    # 合并统计数据
    if stats:
        if 'daily' in stats:
            if 'daily' not in server_stats:
                server_stats['daily'] = {}
            for date, daily_data in stats['daily'].items():
                if date not in server_stats['daily']:
                    server_stats['daily'][date] = daily_data
                else:
                    # 累加
                    server_stats['daily'][date]['total'] = max(
                        server_stats['daily'][date].get('total', 0),
                        daily_data.get('total', 0)
                    )
                    server_stats['daily'][date]['correct'] = max(
                        server_stats['daily'][date].get('correct', 0),
                        daily_data.get('correct', 0)
                    )
        if 'streak' in stats:
            server_stats['streak'] = max(server_stats.get('streak', 0), stats.get('streak', 0))
    
    # 保存合并后的数据
    save_user_json(user_id, get_user_questions_file(user_id), list(question_map.values()))
    save_user_json(user_id, get_user_wrong_file(user_id), list(wrong_map.values()))
    save_user_json(user_id, get_user_favorites_file(user_id), list(fav_map.values()))
    save_user_json(user_id, get_user_memory_file(user_id), server_memory)
    save_user_json(user_id, get_user_stats_file(user_id), server_stats)
    
    # 更新同步版本
    meta = update_sync_version(user_id)
    
    return jsonify({
        'success': True,
        'message': '数据上传成功',
        'conflicts': conflicts,
        'syncVersion': meta['version'],
        'merged': {
            'questions': len(question_map),
            'wrong': len(wrong_map),
            'favorites': len(fav_map),
            'memory': len(server_memory)
        }
    })

# API: 全量下载（用于同步）
@app.route('/api/sync/download', methods=['GET'])
@token_required
def download_all_data():
    """全量下载API - 下载所有用户数据"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    questions = load_user_json(user_id, get_user_questions_file(user_id))
    wrong = load_user_json(user_id, get_user_wrong_file(user_id))
    favorites = load_user_json(user_id, get_user_favorites_file(user_id))
    memory = load_user_json(user_id, get_user_memory_file(user_id))
    stats = load_user_json(user_id, get_user_stats_file(user_id))
    meta = load_user_json(user_id, get_user_sync_meta_file(user_id))
    
    # 计算数据哈希
    data_hash = {
        'questions': compute_data_hash(questions),
        'wrong': compute_data_hash(wrong),
        'favorites': compute_data_hash(favorites),
        'memory': compute_data_hash(memory),
        'stats': compute_data_hash(stats)
    }
    
    return jsonify({
        'success': True,
        'data': {
            'questions': questions,
            'wrong': wrong,
            'favorites': favorites,
            'memory': memory,
            'stats': stats
        },
        'meta': meta,
        'dataHash': data_hash,
        'downloadTime': datetime.now().isoformat()
    })

# API: 增量同步
@app.route('/api/sync/incremental', methods=['GET'])
@token_required
def incremental_download():
    """增量下载API - 只下载变化的版本"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    # 获取客户端传递的版本信息
    client_versions = {
        'questionVersion': int(request.args.get('questionVersion', 0)),
        'wrongVersion': int(request.args.get('wrongVersion', 0)),
        'favoriteVersion': int(request.args.get('favoriteVersion', 0)),
        'memoryVersion': int(request.args.get('memoryVersion', 0)),
        'statsVersion': int(request.args.get('statsVersion', 0))
    }
    
    # 获取服务器元数据
    meta = load_user_json(user_id, get_user_sync_meta_file(user_id))
    
    # 确定哪些数据需要同步
    changes = {}
    
    if client_versions['questionVersion'] < meta.get('questionVersion', 1):
        changes['questions'] = load_user_json(user_id, get_user_questions_file(user_id))
    
    if client_versions['wrongVersion'] < meta.get('wrongVersion', 1):
        changes['wrong'] = load_user_json(user_id, get_user_wrong_file(user_id))
    
    if client_versions['favoriteVersion'] < meta.get('favoriteVersion', 1):
        changes['favorites'] = load_user_json(user_id, get_user_favorites_file(user_id))
    
    if client_versions['memoryVersion'] < meta.get('memoryVersion', 1):
        changes['memory'] = load_user_json(user_id, get_user_memory_file(user_id))
    
    if client_versions['statsVersion'] < meta.get('statsVersion', 1):
        changes['stats'] = load_user_json(user_id, get_user_stats_file(user_id))
    
    return jsonify({
        'success': True,
        'hasChanges': len(changes) > 0,
        'changes': changes,
        'serverVersions': {
            'questionVersion': meta.get('questionVersion', 1),
            'wrongVersion': meta.get('wrongVersion', 1),
            'favoriteVersion': meta.get('favoriteVersion', 1),
            'memoryVersion': meta.get('memoryVersion', 1),
            'statsVersion': meta.get('statsVersion', 1)
        },
        'syncTime': datetime.now().isoformat()
    })

# API: 增量上传
@app.route('/api/sync/incremental/upload', methods=['POST'])
@token_required
def incremental_upload():
    """增量上传API - 只上传变化的模块"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    data = request.json
    
    # 获取服务器当前版本
    meta = load_user_json(user_id, get_user_sync_meta_file(user_id))
    
    # 上传变化的模块
    results = {}
    
    if 'questions' in data:
        questions = data['questions']
        server_questions = load_user_json(user_id, get_user_questions_file(user_id))
        
        # 检测冲突
        conflicts = detect_conflicts(server_questions, questions)
        
        # 合并
        question_map = {q['id']: q for q in server_questions}
        for q in questions:
            if q.get('id') not in question_map:
                q['syncedAt'] = datetime.now().isoformat()
                question_map[q['id']] = q
        
        save_user_json(user_id, get_user_questions_file(user_id), list(question_map.values()))
        results['questions'] = {'merged': len(question_map), 'conflicts': len(conflicts['conflicts'])}
    
    if 'wrong' in data:
        wrong = data['wrong']
        server_wrong = load_user_json(user_id, get_user_wrong_file(user_id))
        
        conflicts = detect_conflicts(server_wrong, wrong, 'questionId')
        
        wrong_map = {w['questionId']: w for w in server_wrong}
        for w in wrong:
            if w.get('questionId') not in wrong_map:
                w['syncedAt'] = datetime.now().isoformat()
                wrong_map[w['questionId']] = w
        
        save_user_json(user_id, get_user_wrong_file(user_id), list(wrong_map.values()))
        results['wrong'] = {'merged': len(wrong_map), 'conflicts': len(conflicts['conflicts'])}
    
    if 'favorites' in data:
        favorites = data['favorites']
        server_favorites = load_user_json(user_id, get_user_favorites_file(user_id))
        
        fav_map = {f['questionId']: f for f in server_favorites}
        for f in favorites:
            if f.get('questionId') not in fav_map:
                f['syncedAt'] = datetime.now().isoformat()
                fav_map[f['questionId']] = f
        
        save_user_json(user_id, get_user_favorites_file(user_id), list(fav_map.values()))
        results['favorites'] = {'merged': len(fav_map)}
    
    if 'memory' in data:
        memory = data['memory']
        server_memory = load_user_json(user_id, get_user_memory_file(user_id))
        
        for q_id, mem_data in memory.items():
            if q_id not in server_memory:
                server_memory[q_id] = mem_data
                server_memory[q_id]['syncedAt'] = datetime.now().isoformat()
        
        save_user_json(user_id, get_user_memory_file(user_id), server_memory)
        results['memory'] = {'merged': len(server_memory)}
    
    if 'stats' in data:
        stats = data['stats']
        server_stats = load_user_json(user_id, get_user_stats_file(user_id))
        
        if stats and 'daily' in stats:
            if 'daily' not in server_stats:
                server_stats['daily'] = {}
            for date, daily_data in stats['daily'].items():
                if date not in server_stats['daily']:
                    server_stats['daily'][date] = daily_data
                else:
                    server_stats['daily'][date]['total'] = max(
                        server_stats['daily'][date].get('total', 0),
                        daily_data.get('total', 0)
                    )
        
        save_user_json(user_id, get_user_stats_file(user_id), server_stats)
        results['stats'] = {'merged': True}
    
    # 更新版本
    meta = update_sync_version(user_id)
    
    return jsonify({
        'success': True,
        'message': '增量上传成功',
        'results': results,
        'newVersions': {
            'questionVersion': meta.get('questionVersion', 1),
            'wrongVersion': meta.get('wrongVersion', 1),
            'favoriteVersion': meta.get('favoriteVersion', 1),
            'memoryVersion': meta.get('memoryVersion', 1),
            'statsVersion': meta.get('statsVersion', 1)
        }
    })

# API: 冲突检测
@app.route('/api/sync/conflicts', methods=['POST'])
@token_required
def check_conflicts():
    """冲突检测API - 检测本地和服务器数据是否有冲突"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    data = request.json
    local_data = data.get('localData', {})
    
    # 获取服务器数据
    server_questions = load_user_json(user_id, get_user_questions_file(user_id))
    server_wrong = load_user_json(user_id, get_user_wrong_file(user_id))
    server_favorites = load_user_json(user_id, get_user_favorites_file(user_id))
    
    conflicts = {
        'questions': {'conflicts': []},
        'wrong': {'conflicts': []},
        'favorites': {'conflicts': []}
    }
    
    # 检测题目冲突
    if 'questions' in local_data:
        conflicts['questions'] = detect_conflicts(
            server_questions, 
            local_data['questions']
        )
    
    # 检测错题冲突
    if 'wrong' in local_data:
        conflicts['wrong'] = detect_conflicts(
            server_wrong, 
            local_data['wrong'], 
            'questionId'
        )
    
    # 检测收藏冲突
    if 'favorites' in local_data:
        conflicts['favorites'] = detect_conflicts(
            server_favorites, 
            local_data['favorites'], 
            'questionId'
        )
    
    total_conflicts = (
        len(conflicts['questions']['conflicts']) + 
        len(conflicts['wrong']['conflicts']) + 
        len(conflicts['favorites']['conflicts'])
    )
    
    return jsonify({
        'success': True,
        'hasConflicts': total_conflicts > 0,
        'totalConflicts': total_conflicts,
        'conflicts': conflicts,
        'checkTime': datetime.now().isoformat()
    })

# API: 解决冲突
@app.route('/api/sync/conflicts/resolve', methods=['POST'])
@token_required
def resolve_conflicts():
    """冲突解决API - 由客户端决定保留哪个版本"""
    user_id = request.current_user['id']
    
    data = request.json
    resolutions = data.get('resolutions', [])
    
    # 获取当前服务器数据
    questions = load_user_json(user_id, get_user_questions_file(user_id))
    wrong = load_user_json(user_id, get_user_wrong_file(user_id))
    favorites = load_user_json(user_id, get_user_favorites_file(user_id))
    
    question_map = {q['id']: q for q in questions}
    wrong_map = {w['questionId']: w for w in wrong}
    fav_map = {f['questionId']: f for f in favorites}
    
    resolved = {'questions': 0, 'wrong': 0, 'favorites': 0}
    
    for resolution in resolutions:
        item_type = resolution.get('type')
        item_id = resolution.get('id')
        choice = resolution.get('choice')  # 'local' 或 'remote'
        
        if choice == 'remote':
            resolved[item_type] = resolved.get(item_type, 0) + 1
    
    # 更新版本
    meta = update_sync_version(user_id)
    
    # 保存
    save_user_json(user_id, get_user_questions_file(user_id), list(question_map.values()))
    save_user_json(user_id, get_user_wrong_file(user_id), list(wrong_map.values()))
    save_user_json(user_id, get_user_favorites_file(user_id), list(fav_map.values()))
    
    return jsonify({
        'success': True,
        'message': '冲突已解决',
        'resolved': resolved,
        'newVersion': meta['version']
    })

# API: 获取同步状态
@app.route('/api/sync/status', methods=['GET'])
@token_required
def get_sync_status():
    """获取同步状态"""
    user_id = request.current_user['id']
    init_user_data_files(user_id)
    
    meta = load_user_json(user_id, get_user_sync_meta_file(user_id))
    
    questions = load_user_json(user_id, get_user_questions_file(user_id))
    wrong = load_user_json(user_id, get_user_wrong_file(user_id))
    favorites = load_user_json(user_id, get_user_favorites_file(user_id))
    memory = load_user_json(user_id, get_user_memory_file(user_id))
    
    return jsonify({
        'success': True,
        'status': {
            'lastSync': meta.get('lastSync'),
            'version': meta.get('version', 1),
            'versions': {
                'questions': meta.get('questionVersion', 1),
                'wrong': meta.get('wrongVersion', 1),
                'favorites': meta.get('favoriteVersion', 1),
                'memory': meta.get('memoryVersion', 1),
                'stats': meta.get('statsVersion', 1)
            },
            'counts': {
                'questions': len(questions),
                'wrong': len(wrong),
                'favorites': len(favorites),
                'memory': len(memory)
            }
        }
    })

# API: 同步历史记录
@app.route('/api/sync/history', methods=['GET'])
@token_required
def get_sync_history():
    """获取同步历史记录"""
    user_id = request.current_user['id']
    
    history_file = os.path.join(get_user_data_dir(user_id), 'sync_history.json')
    history = load_json(history_file)
    
    return jsonify({
        'success': True,
        'history': history
    })


# ==========================================
# 英语阅读模块 - 每日英语阅读
# ==========================================

# 英语阅读数据文件配置
ENGLISH_ARTICLES_FILE = os.path.join(DATA_DIR, 'english_articles.json')
ENGLISH_VOCABULARY_FILE = os.path.join(DATA_DIR, 'english_vocabulary.json')

# 英语阅读相关文章主题库（用于AI生成）
ENGLISH_TOPICS = [
    "Technology and Innovation",
    "Environmental Protection",
    "Education and Learning",
    "Health and Lifestyle",
    "Travel and Culture",
    "Science and Discovery",
    "Business and Economy",
    "Social Media and Communication",
    "Art and Music",
    "Sports and Fitness",
    "History and Heritage",
    "Future and Dreams",
    "Family and Relationships",
    "Work and Career",
    "City Life vs Country Life"
]

def init_english_data_files():
    """初始化英语阅读数据文件"""
    if not os.path.exists(ENGLISH_ARTICLES_FILE):
        save_json(ENGLISH_ARTICLES_FILE, {})
    if not os.path.exists(ENGLISH_VOCABULARY_FILE):
        save_json(ENGLISH_VOCABULARY_FILE, [])

def generate_daily_article_with_ai():
    """使用AI生成每日英语阅读文章"""
    import random
    
    topic = random.choice(ENGLISH_TOPICS)
    
    prompt = f"""请生成一篇高考英语阅读理解难度的文章，主题：{topic}

要求：
1. 文章长度：250-350词
2. 难度：高考英语阅读理解水平
3. 包含5道阅读理解选择题（A、B、C、D四选一）
4. 每道题要有详细的解析

请按以下JSON格式返回：
{{
    "title": "文章标题",
    "content": ["段落1", "段落2", "段落3"],
    "questions": [
        {{
            "id": 1,
            "question": "题目内容",
            "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
            "answer": "A",
            "explanation": "详细解析"
        }}
    ],
    "source": "AI生成",
    "wordCount": 300,
    "difficulty": "medium"
}}

只返回JSON数据，不要有其他文字。"""

    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    }
    
    try:
        response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()
        
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # 提取JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            article = json.loads(json_match.group())
            
            # 添加元数据
            article['id'] = str(uuid.uuid4())
            article['date'] = datetime.now().strftime('%Y-%m-%d')
            
            # 计算词数
            content_text = ' '.join(article.get('content', []))
            article['wordCount'] = len(content_text.split())
            
            return article
        
        return None
    except Exception as e:
        print(f"生成文章失败: {e}")
        return None

def get_or_create_daily_article():
    """获取或创建今日文章"""
    init_english_data_files()
    
    today = datetime.now().strftime('%Y-%m-%d')
    articles = load_json(ENGLISH_ARTICLES_FILE)
    
    # 检查今日文章是否已存在
    if today in articles:
        return articles[today]
    
    # 生成新文章
    article = generate_daily_article_with_ai()
    
    if not article:
        # 如果生成失败，使用示例文章
        article = get_sample_article()
    
    # 保存文章
    articles[today] = article
    save_json(ENGLISH_ARTICLES_FILE, articles)
    return article

def get_sample_article():
    """获取示例文章（备用）"""
    return {
        "id": "sample-article",
        "title": "The Power of Reading",
        "content": [
            "Reading is one of the most important skills we can develop. It opens doors to knowledge, imagination, and personal growth. In today's fast-paced digital world, taking time to read has become more valuable than ever.",
            "Studies show that regular reading improves vocabulary, enhances critical thinking, and reduces stress. Whether it's fiction or non-fiction, books allow us to experience different perspectives and understand the world better.",
            "Many successful people credit reading as a key factor in their achievements. Bill Gates reads about 50 books a year, and Warren Buffett spends most of his day reading. This shows that continuous learning through reading is essential for success."
        ],
        "questions": [
            {
                "id": 1,
                "question": "According to the passage, why has reading become more valuable today?",
                "options": {
                    "A": "Because it's faster than watching videos",
                    "B": "Because we live in a fast-paced digital world",
                    "C": "Because books are cheaper now",
                    "D": "Because schools require more reading"
                },
                "answer": "B",
                "explanation": "The passage mentions 'In today's fast-paced digital world, taking time to read has become more valuable than ever.'"
            },
            {
                "id": 2,
                "question": "What benefit of reading is NOT mentioned in the passage?",
                "options": {
                    "A": "Improving vocabulary",
                    "B": "Reducing stress",
                    "C": "Making more money",
                    "D": "Enhancing critical thinking"
                },
                "answer": "C",
                "explanation": "The passage mentions improving vocabulary, reducing stress, and enhancing critical thinking, but does not mention making more money."
            },
            {
                "id": 3,
                "question": "How many books does Bill Gates read per year according to the passage?",
                "options": {
                    "A": "About 30 books",
                    "B": "About 40 books",
                    "C": "About 50 books",
                    "D": "About 60 books"
                },
                "answer": "C",
                "explanation": "The passage states 'Bill Gates reads about 50 books a year.'"
            },
            {
                "id": 4,
                "question": "What does the passage suggest about successful people?",
                "options": {
                    "A": "They don't have time to read",
                    "B": "They consider reading important for success",
                    "C": "They only read fiction books",
                    "D": "They read less than average people"
                },
                "answer": "B",
                "explanation": "The passage says 'Many successful people credit reading as a key factor in their achievements.'"
            },
            {
                "id": 5,
                "question": "What is the main idea of the passage?",
                "options": {
                    "A": "Reading is important for personal development and success",
                    "B": "Digital books are better than paper books",
                    "C": "Bill Gates is the best reader in the world",
                    "D": "Reading is becoming less popular"
                },
                "answer": "A",
                "explanation": "The passage discusses the importance of reading for knowledge, personal growth, and success."
            }
        ],
        "source": "示例文章",
        "date": datetime.now().strftime('%Y-%m-%d'),
        "wordCount": 168,
        "difficulty": "medium"
    }

# API: 获取每日文章
@app.route('/api/english/daily', methods=['GET'])
def get_daily_article():
    """获取今日英语阅读理解文章"""
    try:
        article = get_or_create_daily_article()
        
        # 返回时隐藏答案（只返回题目，不返回答案和解析）
        response_article = {
            "id": article.get("id"),
            "title": article.get("title"),
            "content": article.get("content"),
            "questions": [
                {
                    "id": q["id"],
                    "question": q["question"],
                    "options": q["options"]
                }
                for q in article.get("questions", [])
            ],
            "source": article.get("source"),
            "date": article.get("date"),
            "wordCount": article.get("wordCount"),
            "difficulty": article.get("difficulty")
        }
        
        return jsonify({
            "success": True,
            "article": response_article
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 提交答案
@app.route('/api/english/submit', methods=['POST'])
def submit_english_answers():
    """提交英语阅读答案"""
    try:
        data = request.json
        article_id = data.get('articleId')
        answers = data.get('answers', [])
        
        if not article_id or not answers:
            return jsonify({
                "success": False,
                "error": "缺少必要参数"
            }), 400
        
        # 获取文章
        articles = load_json(ENGLISH_ARTICLES_FILE)
        article = None
        for date, art in articles.items():
            if art.get('id') == article_id:
                article = art
                break
        
        if not article:
            return jsonify({
                "success": False,
                "error": "文章不存在"
            }), 404
        
        # 批改答案
        questions = article.get('questions', [])
        results = []
        correct_count = 0
        
        for answer_item in answers:
            question_id = answer_item.get('questionId')
            user_answer = answer_item.get('answer', '').upper()
            
            # 查找对应题目
            question = next((q for q in questions if q['id'] == question_id), None)
            
            if question:
                correct_answer = question.get('answer', '').upper()
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    correct_count += 1
                
                results.append({
                    "questionId": question_id,
                    "yourAnswer": user_answer,
                    "correctAnswer": correct_answer,
                    "isCorrect": is_correct,
                    "explanation": question.get('explanation', '')
                })
        
        total = len(answers)
        score = round(correct_count / total * 100, 1) if total > 0 else 0
        
        return jsonify({
            "success": True,
            "results": results,
            "score": score,
            "correctCount": correct_count,
            "totalCount": total
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 查询单词
@app.route('/api/english/word', methods=['GET'])
def query_word():
    """查询单词释义"""
    word = request.args.get('word', '').strip().lower()
    
    if not word:
        return jsonify({
            "success": False,
            "error": "请输入单词"
        }), 400
    
    try:
        # 使用免费词典API
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # 解析API返回的数据
            result = {
                "word": word,
                "phonetic": "",
                "meanings": []
            }
            
            if data and len(data) > 0:
                entry = data[0]
                
                # 获取音标
                phonetics = entry.get('phonetics', [])
                for p in phonetics:
                    if p.get('text'):
                        result['phonetic'] = p.get('text')
                        break
                
                # 获取释义
                meanings = entry.get('meanings', [])
                for m in meanings:
                    part_of_speech = m.get('partOfSpeech', '')
                    definitions = m.get('definitions', [])
                    
                    defs = []
                    for d in definitions[:3]:  # 只取前3个释义
                        defs.append({
                            "definition": d.get('definition', ''),
                            "example": d.get('example', '')
                        })
                    
                    result['meanings'].append({
                        "partOfSpeech": part_of_speech,
                        "definitions": defs
                    })
            
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({
                "success": False,
                "error": "未找到该单词"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500

# API: 获取单词本
@app.route('/api/english/vocabulary', methods=['GET'])
def get_vocabulary():
    """获取单词本"""
    try:
        init_english_data_files()
        vocabulary = load_json(ENGLISH_VOCABULARY_FILE)
        
        # 按添加时间倒序排列
        vocabulary.sort(key=lambda x: x.get('addedAt', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "vocabulary": vocabulary,
            "count": len(vocabulary)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 添加单词到单词本
@app.route('/api/english/vocabulary', methods=['POST'])
def add_vocabulary():
    """添加单词到单词本"""
    try:
        data = request.json
        word = data.get('word', '').strip().lower()
        meaning = data.get('meaning', '').strip()
        phonetic = data.get('phonetic', '').strip()
        article_id = data.get('articleId', '')
        
        if not word:
            return jsonify({
                "success": False,
                "error": "单词不能为空"
            }), 400
        
        init_english_data_files()
        vocabulary = load_json(ENGLISH_VOCABULARY_FILE)
        
        # 检查是否已存在
        existing = next((v for v in vocabulary if v['word'].lower() == word), None)
        if existing:
            return jsonify({
                "success": False,
                "error": "该单词已存在于单词本中"
            }), 400
        
        # 如果没有提供释义，自动查询
        if not meaning:
            try:
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        entry = data[0]
                        meanings_list = []
                        for m in entry.get('meanings', []):
                            pos = m.get('partOfSpeech', '')
                            for d in m.get('definitions', [])[:1]:
                                meanings_list.append(f"{pos}. {d.get('definition', '')}")
                        meaning = '; '.join(meanings_list[:2])
                        
                        # 获取音标
                        if not phonetic:
                            for p in entry.get('phonetics', []):
                                if p.get('text'):
                                    phonetic = p.get('text')
                                    break
            except:
                pass
        
        # 添加新单词
        vocabulary.append({
            "word": word,
            "meaning": meaning or "暂无释义",
            "phonetic": phonetic or "",
            "articleId": article_id,
            "addedAt": datetime.now().isoformat()
        })
        
        save_json(ENGLISH_VOCABULARY_FILE, vocabulary)
        
        return jsonify({
            "success": True,
            "message": "添加成功",
            "word": word
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 从单词本删除单词
@app.route('/api/english/vocabulary/<word>', methods=['DELETE'])
def delete_vocabulary(word):
    """从单词本删除单词"""
    try:
        word = word.strip().lower()
        
        if not word:
            return jsonify({
                "success": False,
                "error": "单词不能为空"
            }), 400
        
        init_english_data_files()
        vocabulary = load_json(ENGLISH_VOCABULARY_FILE)
        
        # 查找并删除
        original_count = len(vocabulary)
        vocabulary = [v for v in vocabulary if v['word'].lower() != word]
        
        if len(vocabulary) == original_count:
            return jsonify({
                "success": False,
                "error": "单词不存在"
            }), 404
        
        save_json(ENGLISH_VOCABULARY_FILE, vocabulary)
        
        return jsonify({
            "success": True,
            "message": "删除成功",
            "word": word
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 获取历史文章列表
@app.route('/api/english/articles', methods=['GET'])
def get_english_articles():
    """获取历史文章列表"""
    try:
        init_english_data_files()
        articles = load_json(ENGLISH_ARTICLES_FILE)
        
        # 转换为列表并按日期倒序
        article_list = []
        for date, article in articles.items():
            article_list.append({
                "id": article.get("id"),
                "title": article.get("title"),
                "date": date,
                "wordCount": article.get("wordCount"),
                "difficulty": article.get("difficulty"),
                "source": article.get("source")
            })
        
        article_list.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "articles": article_list
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 获取指定日期的文章
@app.route('/api/english/articles/<date>', methods=['GET'])
def get_article_by_date(date):
    """获取指定日期的文章"""
    try:
        init_english_data_files()
        articles = load_json(ENGLISH_ARTICLES_FILE)
        
        if date not in articles:
            return jsonify({
                "success": False,
                "error": "该日期没有文章"
            }), 404
        
        article = articles[date]
        
        # 返回时隐藏答案
        response_article = {
            "id": article.get("id"),
            "title": article.get("title"),
            "content": article.get("content"),
            "questions": [
                {
                    "id": q["id"],
                    "question": q["question"],
                    "options": q["options"]
                }
                for q in article.get("questions", [])
            ],
            "source": article.get("source"),
            "date": article.get("date"),
            "wordCount": article.get("wordCount"),
            "difficulty": article.get("difficulty")
        }
        
        return jsonify({
            "success": True,
            "article": response_article
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API: 手动触发获取新文章（管理员功能）
@app.route('/api/english/refresh', methods=['POST'])
def refresh_daily_article():
    """手动刷新今日文章"""
    try:
        # 强制生成新文章
        article = generate_daily_article_with_ai()
        
        if article:
            init_english_data_files()
            articles = load_json(ENGLISH_ARTICLES_FILE)
            
            today = datetime.now().strftime('%Y-%m-%d')
            articles[today] = article
            save_json(ENGLISH_ARTICLES_FILE, articles)
            
            return jsonify({
                "success": True,
                "message": "文章已刷新",
                "article": {
                    "id": article.get("id"),
                    "title": article.get("title"),
                    "date": article.get("date")
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": "生成文章失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 初始化英语阅读数据文件
init_english_data_files()


# ==========================================
# 题目分类系统
# ==========================================

# API: 获取所有分类
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有分类和章节"""
    categories = load_json(CATEGORIES_FILE)
    return jsonify(categories)

# API: 添加/更新分类
@app.route('/api/categories', methods=['POST'])
def save_categories():
    """保存分类数据"""
    data = request.json
    save_json(CATEGORIES_FILE, data)
    return jsonify({'success': True, 'message': '分类已保存'})

# API: 更新题目分类
@app.route('/api/questions/category', methods=['POST'])
def update_question_category():
    """更新题目的分类信息"""
    data = request.json
    question_ids = data.get('questionIds', [])
    category = data.get('category', '')
    chapter = data.get('chapter', '')
    
    questions = load_json(QUESTIONS_FILE)
    
    for q in questions:
        if q['id'] in question_ids:
            q['category'] = category
            q['chapter'] = chapter
    
    save_json(QUESTIONS_FILE, questions)
    return jsonify({'success': True, 'message': '分类已更新'})

# API: 批量设置题目分类
@app.route('/api/questions/batch-category', methods=['POST'])
def batch_update_category():
    """批量设置题目的分类"""
    data = request.json
    question_ids = data.get('questionIds', [])
    category = data.get('category', '')
    chapter = data.get('chapter', '')
    
    questions = load_json(QUESTIONS_FILE)
    
    updated = 0
    for q in questions:
        if q['id'] in question_ids:
            q['category'] = category
            q['chapter'] = chapter
            updated += 1
    
    save_json(QUESTIONS_FILE, questions)
    return jsonify({'success': True, 'updated': updated})


# ==========================================
# 学习统计图表
# ==========================================

# API: 获取图表数据
@app.route('/api/stats/chart', methods=['GET'])
def get_chart_data():
    """获取图表数据"""
    days = int(request.args.get('days', 30))
    stats = load_json(STATS_FILE)
    questions = load_json(QUESTIONS_FILE)
    memory_data = load_json(MEMORY_FILE)
    
    # 每日答题数据
    daily = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        daily_data = stats.get('daily', {}).get(date, {'total': 0, 'correct': 0, 'wrong': 0})
        daily.append({
            'date': date,
            'total': daily_data.get('total', 0),
            'correct': daily_data.get('correct', 0),
            'wrong': daily_data.get('wrong', 0),
            'accuracy': round(daily_data.get('correct', 0) / daily_data.get('total', 1) * 100, 1) if daily_data.get('total', 0) > 0 else 0
        })
    
    # 正确率趋势
    accuracy = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        daily_data = stats.get('daily', {}).get(date, {'total': 0, 'correct': 0})
        acc = round(daily_data.get('correct', 0) / daily_data.get('total', 1) * 100, 1) if daily_data.get('total', 0) > 0 else 0
        accuracy.append({
            'date': date,
            'accuracy': acc
        })
    
    # 分类正确率统计
    category_stats = {}
    for q in questions:
        category = q.get('category', '未分类')
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'correct': 0}
        
        q_id = q.get('id')
        if q_id in memory_data:
            record = memory_data[q_id]
            category_stats[category]['total'] += record.get('totalReviews', 0)
            category_stats[category]['correct'] += record.get('correctCount', 0)
    
    category_breakdown = []
    for cat, data in category_stats.items():
        acc = round(data['correct'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        category_breakdown.append({
            'category': cat,
            'total': data['total'],
            'correct': data['correct'],
            'accuracy': acc
        })
    
    # 排序按正确率
    category_breakdown.sort(key=lambda x: x['accuracy'])
    
    return jsonify({
        'daily': daily,
        'accuracy': accuracy,
        'categoryBreakdown': category_breakdown
    })

# API: 获取本周/本月统计
@app.route('/api/stats/report', methods=['GET'])
def get_stats_report():
    """获取学习报告"""
    period = request.args.get('period', 'week')  # week or month
    stats = load_json(STATS_FILE)
    questions = load_json(QUESTIONS_FILE)
    memory_data = load_json(MEMORY_FILE)
    wrong_list = load_json(WRONG_FILE)
    
    if period == 'week':
        days = 7
    else:
        days = 30
    
    # 本周/本月统计
    total_answered = 0
    total_correct = 0
    total_wrong = 0
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_data = stats.get('daily', {}).get(date, {'total': 0, 'correct': 0, 'wrong': 0})
        total_answered += daily_data.get('total', 0)
        total_correct += daily_data.get('correct', 0)
        total_wrong += daily_data.get('wrong', 0)
    
    accuracy = round(total_correct / total_answered * 100, 1) if total_answered > 0 else 0
    
    # 薄弱知识点分析（错题多的题目）
    weak_points = {}
    for w in wrong_list:
        q_id = w.get('questionId')
        if q_id not in weak_points:
            weak_points[q_id] = {'wrongCount': 0, 'question': ''}
        weak_points[q_id]['wrongCount'] += 1
    
    # 获取题目内容
    weak_list = []
    for q_id, data in weak_points.items():
        q = next((q for q in questions if q['id'] == q_id), None)
        if q:
            memory_record = memory_data.get(q_id, {})
            weak_list.append({
                'questionId': q_id,
                'question': q.get('question', '')[:100] + '...' if len(q.get('question', '')) > 100 else q.get('question', ''),
                'wrongCount': data['wrongCount'],
                'masteryLevel': memory_record.get('masteryLevel', 0),
                'category': q.get('category', '未分类'),
                'chapter': q.get('chapter', '未分类')
            })
    
    # 按错题次数排序
    weak_list.sort(key=lambda x: x['wrongCount'], reverse=True)
    weak_list = weak_list[:10]  # 取前10个
    
    # 知识点掌握情况
    mastery_stats = {'new': 0, 'learning': 0, 'review': 0, 'mastered': 0}
    for record in memory_data.values():
        mastery = record.get('masteryLevel', 0)
        if mastery == 0:
            mastery_stats['new'] += 1
        elif mastery < 50:
            mastery_stats['learning'] += 1
        elif mastery < 80:
            mastery_stats['review'] += 1
        else:
            mastery_stats['mastered'] += 1
    
    return jsonify({
        'period': period,
        'totalAnswered': total_answered,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracy': accuracy,
        'weakPoints': weak_list,
        'masteryStats': mastery_stats,
        'totalQuestions': len(questions),
        'totalWrongQuestions': len(wrong_list)
    })

# API: 获取分类统计
@app.route('/api/stats/by-category', methods=['GET'])
def get_stats_by_category():
    """获取按分类的统计"""
    questions = load_json(QUESTIONS_FILE)
    memory_data = load_json(MEMORY_FILE)
    
    category_stats = {}
    for q in questions:
        category = q.get('category', '未分类')
        chapter = q.get('chapter', '未分类')
        
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'questions': [], 'chapters': {}}
        
        category_stats[category]['total'] += 1
        category_stats[category]['questions'].append(q['id'])
        
        if chapter not in category_stats[category]['chapters']:
            category_stats[category]['chapters'][chapter] = {'total': 0, 'questions': []}
        
        category_stats[category]['chapters'][chapter]['total'] += 1
        category_stats[category]['chapters'][chapter]['questions'].append(q['id'])
    
    # 添加记忆数据
    for cat in category_stats:
        total_correct = 0
        total_reviews = 0
        for q_id in category_stats[cat]['questions']:
            if q_id in memory_data:
                record = memory_data[q_id]
                total_correct += record.get('correctCount', 0)
                total_reviews += record.get('totalReviews', 0)
        
        category_stats[cat]['accuracy'] = round(total_correct / total_reviews * 100, 1) if total_reviews > 0 else 0
        category_stats[cat]['correctCount'] = total_correct
        category_stats[cat]['reviewCount'] = total_reviews
    
    return jsonify(category_stats)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
