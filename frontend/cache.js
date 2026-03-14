/**
 * 前端缓存工具
 * 支持 localStorage 缓存和内存缓存
 */

const Cache = {
    // localStorage 缓存配置
    config: {
        prefix: 'quiz_',
        defaultMaxAge: 5 * 60 * 1000, // 默认5分钟
    },

    /**
     * 获取缓存数据
     * @param {string} key - 缓存键
     * @param {number} maxAge - 最大有效期（毫秒）
     * @returns {any|null} 缓存数据或null
     */
    get(key, maxAge = this.config.defaultMaxAge) {
        const storageKey = this.config.prefix + key;
        
        try {
            const item = localStorage.getItem(storageKey);
            if (!item) return null;
            
            const { data, timestamp } = JSON.parse(item);
            
            // 检查是否过期
            if (Date.now() - timestamp > maxAge) {
                this.remove(key);
                return null;
            }
            
            return data;
        } catch (e) {
            console.error('Cache get error:', e);
            return null;
        }
    },

    /**
     * 设置缓存数据
     * @param {string} key - 缓存键
     * @param {any} data - 要缓存的数据
     */
    set(key, data) {
        const storageKey = this.config.prefix + key;
        
        try {
            const item = {
                data,
                timestamp: Date.now()
            };
            localStorage.setItem(storageKey, JSON.stringify(item));
        } catch (e) {
            console.error('Cache set error:', e);
            // 可能是存储空间满，尝试清理旧缓存
            if (e.name === 'QuotaExceededError') {
                this.cleanup();
            }
        }
    },

    /**
     * 删除指定缓存
     * @param {string} key - 缓存键
     */
    remove(key) {
        const storageKey = this.config.prefix + key;
        localStorage.removeItem(storageKey);
    },

    /**
     * 清空所有缓存
     */
    clear() {
        const keys = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.config.prefix)) {
                keys.push(key);
            }
        }
        keys.forEach(key => localStorage.removeItem(key));
    },

    /**
     * 清理过期缓存
     */
    cleanup() {
        const now = Date.now();
        const keysToRemove = [];
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.config.prefix)) {
                try {
                    const item = JSON.parse(localStorage.getItem(key));
                    if (now - item.timestamp > 24 * 60 * 60 * 1000) { // 超过24小时
                        keysToRemove.push(key);
                    }
                } catch (e) {
                    keysToRemove.push(key);
                }
            }
        }
        
        keysToRemove.forEach(key => localStorage.removeItem(key));
        console.log(`[Cache] 清理了 ${keysToRemove.length} 个过期缓存`);
    },

    /**
     * 获取缓存大小
     */
    getSize() {
        let size = 0;
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(this.config.prefix)) {
                size += localStorage.getItem(key).length;
            }
        }
        return (size / 1024).toFixed(2) + ' KB';
    }
};

// ==================== API 请求缓存 ====================

const ApiCache = {
    // 内存缓存（更快的访问）
    _memoryCache: new Map(),
    
    /**
     * 带缓存的 API 请求
     * @param {string} url - 请求URL
     * @param {object} options - fetch 选项
     * @param {number} maxAge - 缓存时间（毫秒）
     */
    async fetch(url, options = {}, maxAge = 60000) {
        const cacheKey = `api_${url}`;
        
        // 尝试从内存缓存获取
        const memCached = this._memoryCache.get(cacheKey);
        if (memCached && Date.now() - memCached.timestamp < maxAge) {
            console.log(`[ApiCache] 内存缓存命中: ${url}`);
            return memCached.data;
        }
        
        // 尝试从 localStorage 获取
        const localCached = Cache.get(cacheKey, maxAge);
        if (localCached) {
            console.log(`[ApiCache] 本地缓存命中: ${url}`);
            // 同步到内存缓存
            this._memoryCache.set(cacheKey, {
                data: localCached,
                timestamp: Date.now()
            });
            return localCached;
        }
        
        // 执行网络请求
        const response = await fetch(url, options);
        const data = await response.json();
        
        // 存入缓存
        const cacheData = { data, timestamp: Date.now() };
        this._memoryCache.set(cacheKey, cacheData);
        Cache.set(cacheKey, data);
        
        return data;
    },

    /**
     * 清除指定 API 缓存
     */
    invalidate(url) {
        const cacheKey = `api_${url}`;
        this._memoryCache.delete(cacheKey);
        Cache.remove(cacheKey);
    },

    /**
     * 清除所有 API 缓存
     */
    invalidateAll() {
        this._memoryCache.clear();
        Cache.clear();
    }
};

// ==================== 分页加载 ====================

const PagedLoader = {
    /**
     * 分页加载数据
     * @param {Function} fetchFn - 获取数据的函数
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @param {string} cacheKey - 缓存键
     */
    async load(fetchFn, page = 1, pageSize = 20, cacheKey = null) {
        const key = cacheKey || `page_${page}_${pageSize}`;
        
        // 尝试从缓存获取
        const cached = Cache.get(key, 30000); // 30秒缓存
        if (cached && cached.page === page) {
            return cached;
        }
        
        // 获取新数据
        const data = await fetchFn(page, pageSize);
        
        // 缓存结果
        const result = { page, pageSize, data, total: data.length };
        Cache.set(key, result);
        
        return result;
    }
};

// ==================== 图片懒加载 ====================

const LazyLoad = {
    /**
     * 初始化懒加载
     */
    init() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.classList.remove('lazy');
                            this.observer.unobserve(img);
                        }
                    });
                },
                { rootMargin: '50px' }
            );
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                this.observer.observe(img);
            });
        } else {
            // 不支持 IntersectionObserver，回退到直接加载
            document.querySelectorAll('img[data-src]').forEach(img => {
                img.src = img.dataset.src;
            });
        }
    },

    /**
     * 观察新添加的图片
     */
    observe() {
        if (this.observer) {
            document.querySelectorAll('img[data-src].lazy').forEach(img => {
                this.observer.observe(img);
            });
        }
    }
};

// ==================== 防抖 & 节流 ====================

const Performance = {
    /**
     * 防抖函数
     * @param {Function} fn - 要执行的函数
     * @param {number} delay - 延迟时间（毫秒）
     */
    debounce(fn, delay = 300) {
        let timer = null;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /**
     * 节流函数
     * @param {Function} fn - 要执行的函数
     * @param {number} limit - 时间限制（毫秒）
     */
    throttle(fn, limit = 300) {
        let inThrottle = false;
        return function(...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * 测量函数执行时间
     */
    measure(fn, label = 'Function') {
        return function(...args) {
            const start = performance.now();
            const result = fn.apply(this, args);
            const elapsed = performance.now() - start;
            
            if (elapsed > 16) { // 超过一帧
                console.log(`[Performance] ${label}: ${elapsed.toFixed(2)}ms`);
            }
            
            return result;
        };
    }
};

// ==================== 导出 ====================

window.Cache = Cache;
window.ApiCache = ApiCache;
window.PagedLoader = PagedLoader;
window.LazyLoad = LazyLoad;
window.Performance = Performance;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 清理过期缓存
    Cache.cleanup();
    
    // 初始化懒加载
    LazyLoad.init();
});
