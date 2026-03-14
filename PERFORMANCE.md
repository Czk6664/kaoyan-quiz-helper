# 性能优化说明文档

## 概述

本文档说明刷题网站项目的性能优化方案，包括后端缓存、前端优化和 API 响应优化。

---

## 1. 后端缓存

### 1.1 文件位置
`backend/cache.py`

### 1.2 缓存策略

| 数据类型 | TTL (秒) | 说明 |
|---------|---------|------|
| 题目列表 | 300 (5分钟) | 变化较少，全局共享 |
| 统计数据 | 60 (1分钟) | 频繁更新 |
| 错题列表 | 120 (2分钟) | 偶尔更新 |
| 收藏列表 | 120 (2分钟) | 偶尔更新 |
| 刷题记录 | 30 (30秒) | 快速变化 |
| 复习列表 | 60 (1分钟) | 基于艾宾浩斯曲线 |

### 1.3 使用示例

```python
from cache import ttl_cache, cache_invalidate

# 题目缓存（5分钟）
@ttl_cache('questions', ttl=300)
def get_cached_questions():
    return load_json(QUESTIONS_FILE)

# 统计数据缓存（1分钟）
@ttl_cache('stats', ttl=60)
def get_cached_stats():
    return calculate_stats()

# 添加题目后清除缓存
@cache_invalidate('questions', 'stats')
def add_question(question):
    # 添加题目逻辑
    save_json(QUESTIONS_FILE, questions)
```

### 1.4 在 app.py 中集成

```python
from cache import ttl_cache, cache_manager, compress_response
from functools import wraps
import time

# 统计缓存
_stats_cache = {}

def get_cached_stats():
    """统计数据缓存（1分钟）"""
    cache_key = datetime.now().strftime('%Y-%m-%d-%H-%M')
    
    if cache_key not in _stats_cache:
        _stats_cache[cache_key] = calculate_stats()
    
    # 清理旧缓存
    current_minute = datetime.now().strftime('%Y-%m-%d-%H-%M')
    _stats_cache = {k: v for k, v in _stats_cache.items() 
                   if k >= current_minute}
    
    return _stats_cache[cache_key]

# API 慢查询日志装饰器
def log_slow_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        
        if elapsed > 200:
            print(f"[SLOW] {func.__name__} took {elapsed:.2f}ms")
        
        return result
    return wrapper
```

---

## 2. 前端优化

### 2.1 文件位置
`frontend/cache.js`

### 2.2 localStorage 缓存

```javascript
// 获取缓存
const questions = Cache.get('questions', 300000); // 5分钟

// 设置缓存
Cache.set('questions', data);

// 清除缓存
Cache.remove('questions');
```

### 2.3 API 请求缓存

```javascript
// 带缓存的 API 请求（1分钟）
const data = await ApiCache.fetch('/api/quiz?count=10', {}, 60000);

// 提交答案后清除相关缓存
ApiCache.invalidate('/api/quiz');
```

### 2.4 分页加载

```javascript
// 分页加载题目
const result = await PagedLoader.load(
    (page, pageSize) => fetchQuestionsAPI(page, pageSize),
    1,  // 页码
    20, // 每页数量
    'questions_page' // 缓存键
);
```

### 2.5 图片懒加载

```html
<!-- 使用 loading 属性 -->
<img loading="lazy" src="image.jpg" alt="题目配图">

<!-- 或使用 data-src -->
<img data-src="image.jpg" class="lazy" alt="题目配图">
```

### 2.6 防抖和节流

```javascript
// 搜索防抖
const handleSearch = Performance.debounce((keyword) => {
    searchAPI(keyword);
}, 300);

// 滚动节流
const handleScroll = Performance.throttle(() => {
    checkLazyLoad();
}, 100);
```

---

## 3. API 响应优化

### 3.1 减少不必要字段

```python
# 只返回必要字段
@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    questions = load_json(QUESTIONS_FILE)
    
    # 只返回前端需要的字段
    result = []
    for q in questions[:count]:
        result.append({
            'id': q['id'],
            'question': q['question'],
            'options': q['options'],
            'difficulty': q.get('difficulty', 3)
        })
    
    return jsonify(result)
```

### 3.2 添加分页参数

```python
@app.route('/api/questions', methods=['GET'])
def get_questions():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    
    questions = load_json(QUESTIONS_FILE)
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    
    return jsonify({
        'data': questions[start:end],
        'total': len(questions),
        'page': page,
        'page_size': page_size,
        'total_pages': (len(questions) + page_size - 1) // page_size
    })
```

### 3.3 响应压缩

```python
from flask import jsonify, make_response

@app.after_request
def compress_response(response):
    # 启用 gzip 压缩
    if response.content_type == 'application/json':
        # Flask 配合 gevent 等会自动压缩
        pass
    return response
```

---

## 4. 性能监控

### 4.1 缓存命中率统计

```python
from cache import cache_manager

@app.route('/api/debug/cache_stats')
def get_cache_stats():
    return jsonify(cache_manager.get_stats())
```

### 4.2 前端性能监控

```javascript
// 页面加载性能
window.addEventListener('load', () => {
    const timing = performance.timing;
    const loadTime = timing.loadEventEnd - timing.navigationStart;
    console.log(`页面加载时间: ${loadTime}ms`);
});
```

---

## 5. 缓存失效策略

### 5.1 自动失效

- **TTL 过期**: 缓存数据在指定时间后自动失效
- **手动失效**: 数据变更时主动清除相关缓存

### 5.2 失效场景

```python
@cache_invalidate('questions', 'stats', 'quiz')
def submit_answer(data):
    # 提交答案后清除所有相关缓存
    save_json(WRONG_FILE, wrong_list)
    update_daily_stats(is_correct)
```

---

## 6. 优化效果预估

| 优化项 | 预期提升 |
|-------|---------|
| 题目列表缓存 | 响应时间 500ms → 10ms |
| 统计数据缓存 | 响应时间 200ms → 5ms |
| 前端缓存 | 减少 50%+ 重复请求 |
| 分页加载 | 首屏加载减少 80%+ 数据量 |
| 图片懒加载 | 首屏加载减少 60%+ 图片请求 |
| 响应字段精简 | 网络传输减少 40%+ |

---

## 7. 注意事项

1. **缓存一致性**: 重要数据（如用户提交）需要及时失效缓存
2. **缓存大小**: localStorage 限制约 5-10MB，需要定期清理
3. **缓存安全**: 敏感数据不要使用 localStorage 缓存
4. **内存管理**: 后端缓存需要设置合理的 maxsize 防止内存溢出

---

## 8. 后续可优化项

- [ ] 引入 Redis 分布式缓存
- [ ] 添加 CDN 加速静态资源
- [ ] 实现 Service Worker 离线缓存
- [ ] 添加 HTTP/2 多路复用
- [ ] 图片 WebP 格式转换
