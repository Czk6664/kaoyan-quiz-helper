"""
高性能缓存装饰器模块
支持 LRU 缓存、TTL 缓存和统计缓存
"""
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import threading
import hashlib
import json
from typing import Any, Callable, Optional

# ==================== 配置 ====================
CACHE_CONFIG = {
    'questions': {'maxsize': 1, 'ttl': 300},      # 5分钟
    'stats': {'maxsize': 1, 'ttl': 60},           # 1分钟
    'wrong_list': {'maxsize': 1, 'ttl': 120},     # 2分钟
    'favorites': {'maxsize': 1, 'ttl': 120},      # 2分钟
    'memory': {'maxsize': 1, 'ttl': 60},          # 1分钟
    'quiz': {'maxsize': 10, 'ttl': 30},           # 30秒（快速变化）
    'review': {'maxsize': 5, 'ttl': 60},          # 1分钟
}

# ==================== 内存缓存存储 ====================
_memory_cache = {}
_cache_lock = threading.Lock()
_cache_hits = {}
_cache_misses = {}


class CacheManager:
    """缓存管理器 - 支持TTL和LRU"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Any:
        """获取缓存值，过期返回None"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            data, expiry = self._cache[key]
            if datetime.now() > expiry:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return data
    
    def set(self, key: str, value: Any, ttl: int = 60):
        """设置缓存值，ttl单位为秒"""
        with self._lock:
            expiry = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """删除指定缓存"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear_pattern(self, pattern: str):
        """清除匹配模式的缓存"""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
    
    def clear_all(self):
        """清除所有缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'size': len(self._cache)
            }


# 全局缓存管理器实例
cache_manager = CacheManager()


# ==================== 装饰器 ====================

def ttl_cache(key_prefix: str, ttl: int = 60, key_func: Optional[Callable] = None):
    """
    TTL缓存装饰器
    
    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒）
        key_func: 自定义缓存键生成函数
    
    Example:
        @ttl_cache('questions', ttl=300)
        def get_questions():
            return load_json(QUESTIONS_FILE)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # 基于参数生成哈希
                key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
                key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix}:{key_hash}"
            
            # 尝试从缓存获取
            cached = cache_manager.get(cache_key)
            if cached is not None:
                return cached
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        # 添加清除方法
        wrapper.cache_clear = lambda: cache_manager.clear_pattern(key_prefix)
        wrapper.cache_key_prefix = key_prefix
        
        return wrapper
    return decorator


def cached_property(ttl: int = 60):
    """
    带缓存的property装饰器
    
    Example:
        class MyClass:
            @cached_property(ttl=300)
            def expensive_data(self):
                return expensive_calculation()
    """
    def decorator(func: Callable) -> property:
        cache_attr = f"_cache_{func.__name__}"
        
        @property
        @wraps(func)
        def wrapper(self):
            now = datetime.now()
            
            # 检查缓存是否有效
            if hasattr(self, cache_attr):
                value, expiry = getattr(self, cache_attr)
                if now < expiry:
                    return value
            
            # 计算新值并缓存
            value = func(self)
            setattr(self, cache_attr, (value, now + timedelta(seconds=ttl)))
            return value
        
        return wrapper
    return decorator


def cache_invalidate(*key_patterns: str):
    """
    函数执行后清除指定缓存模式
    
    Example:
        @cache_invalidate('questions', 'stats')
        def add_question(question):
            # 添加题目后清除相关缓存
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 清除匹配的缓存
            for pattern in key_patterns:
                cache_manager.clear_pattern(pattern)
            return result
        return wrapper
    return decorator


# ==================== 便捷函数 ====================

def cached_questions():
    """题目列表缓存（5分钟）"""
    return ttl_cache('questions', ttl=300)


def cached_stats():
    """统计数据缓存（1分钟）"""
    return ttl_cache('stats', ttl=60)


def cached_wrong_list():
    """错题列表缓存（2分钟）"""
    return ttl_cache('wrong_list', ttl=120)


def cached_favorites():
    """收藏列表缓存（2分钟）"""
    return ttl_cache('favorites', ttl=120)


def cached_memory_data():
    """记忆数据缓存（1分钟）"""
    return ttl_cache('memory', ttl=60)


def cached_quiz():
    """刷题列表缓存（30秒）"""
    return ttl_cache('quiz', ttl=30)


def cached_review():
    """复习列表缓存（1分钟）"""
    return ttl_cache('review', ttl=60)


# ==================== 缓存统计装饰器 ====================

def cache_stats(func: Callable) -> Callable:
    """记录函数执行时间统计"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        elapsed = (datetime.now() - start).total_seconds() * 1000
        
        # 打印慢查询警告
        if elapsed > 100:  # 超过100ms
            print(f"[SLOW] {func.__name__} took {elapsed:.2f}ms")
        
        return result
    return wrapper


# ==================== 预热缓存 ====================

def warm_up_cache(data_dir: str, questions_file: str, stats_file: str):
    """
    应用启动时预热缓存
    """
    from utils import load_json
    
    try:
        # 预热题目缓存
        questions = load_json(questions_file)
        cache_manager.set('warmup:questions', questions, 300)
        print(f"[Cache] 预热题目缓存: {len(questions)} 题")
        
        # 预热统计缓存
        stats = load_json(stats_file)
        cache_manager.set('warmup:stats', stats, 60)
        print(f"[Cache] 预热统计缓存完成")
        
    except Exception as e:
        print(f"[Cache] 预热缓存失败: {e}")


# ==================== API响应压缩 ====================

def compress_response(data: dict) -> dict:
    """
    压缩API响应，移除不必要的字段
    """
    # 移除空值
    def remove_empty(obj):
        if isinstance(obj, dict):
            return {k: remove_empty(v) for k, v in obj.items() 
                   if v is not None and v != '' and v != []}
        elif isinstance(obj, list):
            return [remove_empty(item) for item in obj]
        return obj
    
    return remove_empty(data)


# ==================== 导出 ====================

__all__ = [
    'CacheManager',
    'cache_manager',
    'ttl_cache',
    'cached_property',
    'cache_invalidate',
    'cached_questions',
    'cached_stats',
    'cached_wrong_list',
    'cached_favorites',
    'cached_memory_data',
    'cached_quiz',
    'cached_review',
    'cache_stats',
    'warm_up_cache',
    'compress_response',
]
