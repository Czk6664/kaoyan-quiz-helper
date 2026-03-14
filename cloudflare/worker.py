"""
Cloudflare Worker 后端适配版本
基于原 Flask 后端简化，适配 Cloudflare Workers + D1

注意：这是简化版本，完整功能请参考 backend/app.py
"""

import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta

# ========== 工具函数 ==========

def json_response(data, status=200):
    """返回 JSON 响应"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype="application/json"
    )

def get_json_body(request):
    """获取请求体 JSON"""
    try:
        return json.loads(request.text)
    except:
        return {}

# ========== 密码哈希 ==========

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_id):
    timestamp = datetime.now().timestamp()
    payload = f"{user_id}:{timestamp}:{secrets.token_hex(16)}"
    signature = hashlib.sha256(f"{payload}:{JWT_SECRET}".encode()).hexdigest()
    return f"{payload}.{signature}"

def verify_token(token):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[0]
        signature = parts[2]
        expected_sig = hashlib.sha256(f"{payload}:{JWT_SECRET}".encode()).hexdigest()
        if signature != expected_sig:
            return None
        return payload.split(':')[0]
    except:
        return None

# ========== D1 数据库操作 ==========

async def db_get_one(sql, *args):
    """执行查询，返回单条"""
    stmt = env.DB.prepare(sql)
    if args:
        stmt = stmt.bind(*args)
    result = await stmt.first()
    return result

async def db_get_all(sql, *args):
    """执行查询，返回全部"""
    stmt = env.DB.prepare(sql)
    if args:
        stmt = stmt.bind(*args)
    result = await stmt.all()
    return result.results if result else []

async def db_run(sql, *args):
    """执行插入/更新/删除"""
    stmt = env.DB.prepare(sql)
    if args:
        stmt = stmt.bind(*args)
    result = await stmt.run()
    return result.success

# ========== 用户认证 ==========

async def handle_register(request):
    """用户注册"""
    data = get_json_body(request)
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return json_response({'success': False, 'error': '用户名和密码不能为空'}, 400)
    if len(password) < 6:
        return json_response({'success': False, 'error': '密码长度至少6位'}, 400)

    # 检查用户名是否已存在
    existing = await db_get_one("SELECT id FROM users WHERE username = ?", username)
    if existing:
        return json_response({'success': False, 'error': '用户名已存在'}, 400)

    user_id = str(uuid.uuid4())
    await db_run(
        "INSERT INTO users (id, username, password, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
        user_id, username, hash_password(password), datetime.now().isoformat(), datetime.now().isoformat()
    )

    token = generate_token(user_id)
    return json_response({
        'success': True,
        'message': '注册成功',
        'token': token,
        'user': {'id': user_id, 'username': username}
    })

async def handle_login(request):
    """用户登录"""
    data = get_json_body(request)
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return json_response({'success': False, 'error': '用户名和密码不能为空'}, 400)

    user = await db_get_one("SELECT * FROM users WHERE username = ?", username)
    if not user or user['password'] != hash_password(password):
        return json_response({'success': False, 'error': '用户名或密码错误'}, 401)

    # 更新最后登录
    await db_run("UPDATE users SET last_login = ? WHERE id = ?", datetime.now().isoformat(), user['id'])

    token = generate_token(user['id'])
    return json_response({
        'success': True,
        'message': '登录成功',
        'token': token,
        'user': {'id': user['id'], 'username': user['username']}
    })

async def handle_verify_token(request):
    """验证 Token"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')

    user_id = verify_token(token)
    if not user_id:
        return json_response({'success': False, 'error': '无效的令牌'}, 401)

    user = await db_get_one("SELECT id, username FROM users WHERE id = ?", user_id)
    if not user:
        return json_response({'success': False, 'error': '用户不存在'}, 401)

    return json_response({'success': True, 'user': user})

# ========== 题目管理 ==========

async def handle_generate(request):
    """AI 生成题目（简化版，需要调用外部 API）"""
    data = get_json_body(request)
    content = data.get('content', '')
    count = data.get('count', 10)
    source = data.get('source', '自定义')

    # 这里需要调用 MiniMax API 生成题目
    # 由于 Worker 环境中调用外部 API 有特殊处理，请参考完整代码
    # 这里返回模拟数据
    return json_response({'success': True, 'count': 0, 'error': 'AI生成需要配置外部API'})

async def handle_get_questions(request):
    """获取题目列表"""
    auth_header = request.headers.get('Authorization', '')
    user_id = verify_token(auth_header.replace('Bearer ', ''))

    # 获取该用户的题目
    questions = await db_get_all(
        "SELECT id, question, options, answer, difficulty, category, source, explanation, created_at FROM questions WHERE user_id IS NULL OR user_id = ? ORDER BY created_at DESC LIMIT 100",
        user_id or ""
    )

    # 处理 JSON 字段
    for q in questions:
        q['options'] = json.loads(q['options'])

    return json_response(questions)

async def handle_get_quiz(request):
    """获取刷题题目"""
    auth_header = request.headers.get('Authorization', '')
    user_id = verify_token(auth_header.replace('Bearer ', ''))

    count = int(request.params.get('count', 10))

    # 简化：随机获取题目（实际应考虑错题权重）
    questions = await db_get_all(
        "SELECT id, question, options, difficulty, category FROM questions WHERE user_id IS NULL OR user_id = ? ORDER BY RANDOM() LIMIT ?",
        user_id or "", count
    )

    for q in questions:
        q['options'] = json.loads(q['options'])

    return json_response(questions)

# ========== 答题记录 ==========

async def handle_submit(request):
    """提交答案"""
    auth_header = request.headers.get('Authorization', '')
    user_id = verify_token(auth_header.replace('Bearer ', ''))

    if not user_id:
        return json_response({'success': False, 'error': '请先登录'}, 401)

    data = get_json_body(request)
    question_id = data.get('questionId')
    answer = data.get('answer')
    is_collected = data.get('isCollected', False)
    is_give_up = data.get('isGiveUp', False)

    # 获取题目正确答案
    question = await db_get_one("SELECT answer FROM questions WHERE id = ?", question_id)
    if not question:
        return json_response({'success': False, 'error': '题目不存在'}, 404)

    is_correct = answer == question['answer']

    # 更新记忆记录
    memory = await db_get_one("SELECT * FROM memory_records WHERE question_id = ? AND user_id = ?", question_id, user_id)

    if memory:
        await db_run("""
            UPDATE memory_records SET
                total_reviews = total_reviews + 1,
                correct_count = correct_count + ?,
                wrong_count = wrong_count + ?,
                give_up_count = give_up_count + ?,
                mastery_level = ROUND(CAST(correct_count AS REAL) / total_reviews * 100, 1),
                last_review = ?
            WHERE question_id = ? AND user_id = ?
        """, 1 if is_correct else 0, 1 if not is_correct and not is_give_up else 0, 1 if is_give_up else 0,
           datetime.now().isoformat(), question_id, user_id)
    else:
        await db_run("""
            INSERT INTO memory_records (question_id, user_id, total_reviews, correct_count, wrong_count, give_up_count, mastery_level, last_review, created_at)
            VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, question_id, user_id, 1 if is_correct else 0, 1 if not is_correct and not is_give_up else 0, 
           1 if is_give_up else 0, 100.0 if is_correct else 0.0, datetime.now().isoformat(), datetime.now().isoformat())

    # 记录到错题本
    if not is_correct or is_give_up:
        existing = await db_get_one("SELECT id FROM wrong_records WHERE question_id = ? AND user_id = ?", question_id, user_id)
        if not existing:
            await db_run("""
                INSERT INTO wrong_records (question_id, user_id, your_answer, is_give_up, wrong_at, last_review, review_count, interval_days, next_review, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, 3)
            """, question_id, user_id, answer if not is_give_up else '不会', 1 if is_give_up else 0,
               datetime.now().isoformat(), datetime.now().isoformat(), 
               (datetime.now() + timedelta(days=1)).isoformat())

    # 收藏
    if is_collected:
        existing = await db_get_one("SELECT id FROM favorites WHERE question_id = ? AND user_id = ?", question_id, user_id)
        if not existing:
            await db_run("INSERT INTO favorites (question_id, user_id, collected_at) VALUES (?, ?, ?)",
                question_id, user_id, datetime.now().isoformat())

    return json_response({'success': True, 'correct': is_correct, 'correctAnswer': question['answer']})

# ========== 数据同步 ==========

async def handle_sync(request):
    """数据同步"""
    auth_header = request.headers.get('Authorization', '')
    user_id = verify_token(auth_header.replace('Bearer ', ''))

    if not user_id:
        return json_response({'success': False, 'error': '请先登录'}, 401)

    data = get_json_body(request)

    # 这里实现数据合并逻辑（简化版）
    # 实际需要处理冲突检测

    return json_response({'success': True, 'message': '同步成功'})

# ========== 路由处理 ==========

async def handle_api(request):
    """API 路由分发"""
    path = request.params.get('path', '')
    method = request.method

    # 认证相关
    if path == 'auth/register' and method == 'POST':
        return await handle_register(request)
    if path == 'auth/login' and method == 'POST':
        return await handle_login(request)
    if path == 'auth/verify' and method == 'GET':
        return await handle_verify_token(request)

    # 题目相关
    if path == 'generate' and method == 'POST':
        return await handle_generate(request)
    if path == 'questions' and method == 'GET':
        return await handle_get_questions(request)
    if path == 'quiz' and method == 'GET':
        return await handle_get_quiz(request)
    if path == 'submit' and method == 'POST':
        return await handle_submit(request)

    # 同步
    if path == 'sync' and method == 'POST':
        return await handle_sync(request)

    return json_response({'error': 'Not Found'}, 404)

# ========== 主入口 ==========

def onfetch(request, env):
    """Cloudflare Worker 入口"""
    global env
    env = env

    # CORS 预检
    if request.method == 'OPTIONS':
        return Response(None, {
            'status': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        })

    # API 路由
    if request.url.startswith('/api/'):
        return handle_api(request)

    # 静态文件（可选：可以在这里返回 index.html）
    return Response('刷题网站 API 服务运行中', {'status': 200})
