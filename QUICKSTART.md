# 快速部署指南

## 推荐部署方案

### 方案A：Render + Cloudflare Pages（推荐）

#### 1. 部署后端到 Render

1. 注册 Render 账号：https://render.com
2. 在 GitHub 上传本项目代码
3. 在 Render 创建 Web Service：
   - 连接 GitHub 仓库
   - 设置：
     ```
     Name: exam-quiz-backend
     Region: Singapore
     Root Directory: backend
     Build Command: pip install -r requirements.txt
     Start Command: python app.py
     ```
   - 添加环境变量：
     ```
     MINIMAX_API_KEY = 你的MiniMax API密钥
     KIMI_API_KEY = 你的Kimi API密钥（如果没有可设为空）
     JWT_SECRET = 随机字符串（用于加密）
     ```
4. 等待部署完成，记录 URL（如 `https://exam-quiz-backend.onrender.com`）

**注意**：Render 免费版每小时休眠一次，首次访问可能较慢（30秒启动时间）。

#### 2. 部署前端到 Cloudflare Pages

1. 打开 PowerShell，运行部署脚本：
   ```powershell
   cd F:\openclaw\openclawwork\刷题网站\deploy
   .\deploy.ps1 -ApiBase "https://你的Render地址/api"
   ```

2. 登录 Cloudflare：https://dash.cloudflare.com
3. 进入 Pages → Create a project
4. 选择 "Direct Upload"
5. 上传 `deploy\frontend` 文件夹
6. 完成部署，获得 Pages URL

### 方案B：Railway（完全免费）

Railway 的免费额度更慷慨，支持文件持久化。

1. 注册 Railway：https://railway.app
2. 新建项目 → Deploy from GitHub repo
3. 选择本项目
4. 添加环境变量（同 Render）
5. 部署完成后，使用部署脚本更新前端 API 地址

### 方案C：Vercel（前端）+ Render（后端）

适合前端快速部署。

1. 前端：连接 GitHub 到 Vercel
2. 后端：同方案A部署到 Render
3. 在 Vercel 环境变量中设置 API_BASE

---

## 配置 API 密钥

你需要获取以下 API 密钥：

1. **MiniMax API Key**：
   - 访问 https://platform.minimaxi.com
   - 注册并获取 API Key

2. **Kimi API Key**（可选，用于 PDF 功能）：
   - 访问 https://platform.moonshot.cn
   - 注册并获取 API Key

---

## 域名配置

### Cloudflare Pages 绑定自定义域名

1. 在 Pages 项目设置中找到 "Custom domains"
2. 添加你的域名（如 `quiz.yourdomain.com`）
3. 按照提示配置 DNS

### Render 绑定自定义域名

1. 在 Render Dashboard 中找到你的服务
2. Settings → Custom Domains
3. 添加域名并配置 DNS

---

## 离线模式说明

前端已实现离线模式支持：

- 所有题目数据会缓存到浏览器 localStorage
- 离线时可以使用已缓存的题目
- 联网后自动同步数据到服务器
- 需要登录才能同步

---

## 故障排除

### 问题1：后端启动失败

**检查：**
- 环境变量是否配置正确
- API 密钥是否有效

### 问题2：前端无法连接后端

**检查：**
- API_BASE 地址是否正确
- 后端服务是否正常运行
- 浏览器控制台是否有 CORS 错误

### 问题3：题目生成失败

**检查：**
- MINIMAX_API_KEY 是否有效
- 账号是否有足够额度

---

## 费用估算

| 项目 | 免费额度 | 超出费用 |
|------|----------|----------|
| Cloudflare Pages | 无限请求，500 构建/月 | 免费 |
| Render Web Service | 每月 750 小时 | $7/月起 |
| Railway | 每月 $5 免费额度 | 按使用量 |
| MiniMax API | 新用户有免费额度 | 按 token |

**总计：完全免费方案约 $0/月（使用 Cloudflare Pages + Railway）**
