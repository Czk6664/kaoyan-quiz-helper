# 📚 考研刷题助手

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/Czk6664/kaoyan-quiz-helper?style=flat)](https://github.com/Czk6664/kaoyan-quiz-helper/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Czk6664/kaoyan-quiz-helper?style=flat)](https://github.com/Czk6664/kaoyan-quiz-helper/network)
[![License](https://img.shields.io/github/license/Czk6664/kaoyan-quiz-helper?style=flat)](https://github.com/Czk6664/kaoyan-quiz-helper/blob/master/LICENSE)

**基于 AI 的智能刷题系统 | 支持艾宾浩斯遗忘曲线 | 云端同步**

[🌐 在线演示](#-) · [📖 文档](#-) · [🐛 问题反馈](https://github.com/Czk6664/kaoyan-quiz-helper/issues)

</div>

---

## ✨ 特性

| 功能 | 描述 |
|------|------|
| 🤖 **AI 生成题目** | 上传文档/PDF，AI 自动生成选择题 |
| 🧠 **艾宾浩斯记忆** | 科学复习计划，记得更牢 |
| 📝 **错题本** | 智能记录，高频错题重点复习 |
| ⭐ **收藏夹** | 收藏心仪题目，随时回顾 |
| 👤 **用户系统** | 注册登录，学习数据云端同步 |
| 📴 **离线模式** | 无网也能刷题，数据本地保存 |

---

## 🖼️ 预览

<div align="center">
<img src="https://picsum.photos/800/450" alt="预览图" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
</div>

---

## 🚀 快速部署

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/Czk6664/kaoyan-quiz-helper.git
cd kaoyan-quiz-helper

# 2. 安装依赖
cd backend
pip install -r requirements.txt

# 3. 配置 API Key（可选，默认使用内置 Demo Key）
# 编辑 app.py 修改 MINIMAX_API_KEY

# 4. 启动后端
python app.py
# 后端地址: http://localhost:5000

# 5. 启动前端
# 直接用浏览器打开 frontend/index.html
# 或使用 Python 内置服务器
cd ../frontend
python -m http.server 8080
# 访问: http://localhost:8080
```

### 云端部署（推荐）

| 平台 | 部署方式 |
|------|----------|
| 🟣 **Cloudflare Pages** | 前端静态文件 |
| 🟠 **Render** | Python Flask 后端 |

详细部署教程见 [DEPLOY.md](./DEPLOY.md)

---

## 📁 项目结构

```
kaoyan-quiz-helper/
├── backend/                  # Flask 后端
│   ├── app.py               # 主程序
│   ├── requirements.txt     # Python 依赖
│   └── data/               # 数据存储（JSON）
├── frontend/                # 前端页面
│   └── index.html          # 单页应用
├── cloudflare/             # Cloudflare Workers 配置
├── deploy/                 # 部署配置
├── render.yaml             # Render 一键部署
├── DEPLOY.md               # 部署文档
├── README.md               # 本文件
└── SPEC.md                 # 项目规范
```

---

## 🛠️ 技术栈

<div align="center">

| 层级 | 技术 |
|------|------|
| 前端 | HTML5 · CSS3 · Vanilla JS |
| 后端 | Python Flask |
| AI | MiniMax API · Kimi API |
| 部署 | Cloudflare Pages · Render |

</div>

---

## 📋 使用流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  上传文档   │ -> │  AI 生成题  │ -> │  开始刷题   │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  艾宾浩斯   │ <- │  错题复习   │ <- │  答题结果   │
│  遗忘曲线   │    │  强化记忆   │    │  记录错题   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 🤝 贡献

欢迎提交 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 打开 Pull Request

---

## 📄 许可证

MIT License · © 2024 Czk6664

---

<div align="center">

**⭐ Star 本项目，支持开发者继续更新 ⭐**

</div>
