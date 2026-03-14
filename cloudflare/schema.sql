-- 刷题网站 D1 数据库 Schema
-- 运行: wrangler d1 execute exam-quiz-db --file=./schema.sql

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);

-- 题目表
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    options TEXT NOT NULL,  -- JSON 格式存储
    answer TEXT NOT NULL,
    difficulty INTEGER DEFAULT 3,
    category TEXT,
    source TEXT,
    explanation TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    user_id TEXT,  -- NULL 表示公共题目
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 错题记录表
CREATE TABLE IF NOT EXISTS wrong_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    your_answer TEXT,
    is_give_up INTEGER DEFAULT 0,
    wrong_at TEXT DEFAULT (datetime('now')),
    last_review TEXT,
    review_count INTEGER DEFAULT 0,
    interval_days INTEGER DEFAULT 1,
    next_review TEXT,
    difficulty INTEGER DEFAULT 3,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(question_id, user_id)
);

-- 收藏表
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    collected_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(question_id, user_id)
);

-- 记忆曲线数据表
CREATE TABLE IF NOT EXISTS memory_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    total_reviews INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    give_up_count INTEGER DEFAULT 0,
    mastery_level REAL DEFAULT 0,
    last_review TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(question_id, user_id)
);

-- 记忆历史表（每次复习记录）
CREATE TABLE IF NOT EXISTS memory_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    review_time TEXT DEFAULT (datetime('now')),
    is_correct INTEGER,
    is_give_up INTEGER,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 统计数据表
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    total INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    wrong INTEGER DEFAULT 0,
    study_time INTEGER DEFAULT 0,  -- 分钟
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, date)
);

-- 用户统计汇总表
CREATE TABLE IF NOT EXISTS user_stats (
    user_id TEXT PRIMARY KEY,
    streak INTEGER DEFAULT 0,
    last_study_date TEXT,
    total_questions INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_wrong INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 同步元数据表
CREATE TABLE IF NOT EXISTS sync_meta (
    user_id TEXT PRIMARY KEY,
    last_sync TEXT,
    version INTEGER DEFAULT 1,
    question_version INTEGER DEFAULT 1,
    wrong_version INTEGER DEFAULT 1,
    favorite_version INTEGER DEFAULT 1,
    memory_version INTEGER DEFAULT 1,
    stats_version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_questions_user ON questions(user_id);
CREATE INDEX IF NOT EXISTS idx_wrong_user ON wrong_records(user_id);
CREATE INDEX IF NOT EXISTS idx_wrong_next_review ON wrong_records(next_review);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_records(user_id);
CREATE INDEX IF NOT EXISTS idx_stats_user_date ON stats(user_id, date);
CREATE INDEX IF NOT EXISTS idx_memory_history_user ON memory_history(user_id);
