# 考研刷题助手

一个基于AI的刷题网站，支持选择题生成、错题本、收藏夹、艾宾浩斯遗忘曲线复习。

## 项目结构

```
刷题网站/
├── backend/
│   ├── app.py           # Flask后端
│   └── requirements.txt  # Python依赖
├── frontend/
│   └── index.html       # 前端页面
├── SPEC.md             # 项目规范
└── README.md           # 使用说明
```

## 功能

- ✅ 上传文档，AI自动生成选择题
- ✅ 难度打星（1-5星）
- ✅ 每次刷题10道
- ✅ 错题自动收录
- ✅ 收藏功能
- ✅ 艾宾浩斯遗忘曲线复习

## 启动方式

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置API密钥

打开 `backend/app.py`，修改第14行的API密钥：
```python
MINIMAX_API_KEY = "你的API密钥"
```

### 3. 启动后端

```bash
python app.py
```

后端会在 http://localhost:5000 运行

### 4. 打开前端

直接在浏览器中打开 `frontend/index.html`

或者使用Python启动简单HTTP服务器：

```bash
# 在frontend目录下
python -m http.server 8080
```

然后访问 http://localhost:8080

## 使用流程

1. **上传文档**：点击"上传出题"，粘贴文档内容，设置题目数量
2. **开始刷题**：点击"开始刷题"，每次10道题
3. **复习**：点击"复习错题"，按艾宾浩斯遗忘曲线复习
4. **收藏**：点击⭐收藏喜欢的题目
