# 刷题网站部署指南

## 部署方案概述

本项目提供两种部署方案：

| 方案 | 前端 | 后端 | 数据存储 | 难度 | 推荐度 |
|------|------|------|----------|------|--------|
| A | Cloudflare Pages | Render | Render文件系统 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| B | Cloudflare Pages | Cloudflare Workers | Cloudflare D1 | ⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 方案A：Cloudflare Pages + Render（推荐）

### 优点
- 改动最小，几乎无需修改代码
- Render 提供文件持久化存储（适合JSON文件）
- 免费额度充足
- 部署简单

### 步骤一：部署后端到 Render

1. **创建 Render 账号**
   - 访问 https://render.com 注册账号

2. **创建 Web Service**
   - 点击 "New" → "Web Service"
   - 连接你的 GitHub 仓库

3. **配置服务**
   ```
   Name: exam-backend
   Region: Singapore (或最近的区域)
   Branch: main
   Root Directory: backend
   Build Command: pip install -r requirements.txt
   Start Command: python app.py
   Instance Type: Free
   ```

4. **添加环境变量**
   在 Render Dashboard → Environment 中添加：
   ```
   MINIMAX_API_KEY = 你的MiniMax API密钥
   KIMI_API_KEY = 你的Kimi API密钥
   JWT_SECRET = 随机生成的密钥（可用 openssl rand -hex 32）
   ```

5. **启用文件持久化（重要！）**
   - 免费版 Render 不提供持久化存储
   - 需要升级到 Starter 计划（$7/月）
   - 或者使用 Render 的 Disk 服务

   **免费替代方案**：使用 Render 的环境变量存储小量数据，或迁移到 Railway

### 步骤二：部署前端到 Cloudflare Pages

1. **准备前端目录**
   ```bash
   # 创建 frontend 目录结构
   mkdir -p deploy/frontend
   cp frontend/index.html deploy/frontend/
   ```

2. **修改 API 地址**
   编辑 `deploy/frontend/index.html`，修改第 14 行：
   ```javascript
   // 原来
   const API_BASE = 'http://localhost:5000/api';
   
   // 改为你的 Render 地址
   const API_BASE = 'https://exam-backend.onrender.com/api';
   ```

3. **部署到 Cloudflare Pages**
   - 登录 Cloudflare Dashboard
   - 进入 "Pages" → "Create a project"
   - 选择 "Direct Upload"
   - 上传 `deploy/frontend` 目录
   - 项目名称：`exam-quiz`

4. **配置自定义域名（可选）**
   - 在 Pages 设置中添加自定义域名
   - 例如：`quiz.yourdomain.com`

---

## 方案B：完全 Cloudflare 方案

### 优点
- 完全免费
- 全球 CDN 加速
- 一体化管理

### 缺点
- 需要将 JSON 存储迁移到 D1 数据库
- Python Worker 仍在 Beta

### 步骤一：创建 D1 数据库

```bash
# 安装 wrangler CLI
npm install -g wrangler

# 登录 Cloudflare
wrangler login

# 创建数据库
wrangler d1 create exam-quiz-db

# 记下返回的 database_id
```

### 步骤二：创建数据库表

```bash
wrangler d1 execute exam-quiz-db --file=./schema.sql
```

schema.sql 内容见 `cloudflare/schema.sql`

### 步骤三：部署 Worker

1. **配置 wrangler.toml**
   见 `cloudflare/wrangler.toml`

2. **修改后端代码**
   见 `cloudflare/worker.py`

3. **部署**
   ```bash
   cd cloudflare
   wrangler deploy
   ```

### 步骤四：部署前端

同方案A，但 API 地址改为 Worker 地址：
```javascript
const API_BASE = 'https://exam-backend.你的账号.workers.dev/api';
```

---

## 方案C：Railway（完全免费）

Railway 提供免费额度，且支持文件持久化。

### 步骤

1. **创建 Railway 账号**
   - 访问 https://railway.app

2. **新建项目**
   - "New Project" → "Deploy from GitHub repo"

3. **配置**
   ```
   Root Directory: backend
   Start Command: python app.py
   ```

4. **添加环境变量**
   同 Render

5. **获取 URL**
   Railway 会自动分配一个域名

---

## 环境变量清单

| 变量名 | 说明 | 必填 |
|--------|------|------|
| MINIMAX_API_KEY | MiniMax API 密钥 | 是 |
| KIMI_API_KEY | Kimi API 密钥 | 是 |
| JWT_SECRET | JWT 签名密钥 | 是 |
| PORT | 服务端口（自动设置） | 否 |

---

## 部署检查清单

- [ ] 后端服务已启动
- [ ] API 地址已修改
- [ ] 环境变量已配置
- [ ] 跨域问题已解决（后端已配置 CORS）
- [ ] 测试题目生成功能
- [ ] 测试用户注册/登录
- [ ] 测试数据同步

---

## 常见问题

### Q: 前端访问后端 API 报 CORS 错误？
A: 后端已配置 `flask-cors`，应该不会有问题。如果出现，检查 API 地址是否正确。

### Q: Render 免费版数据会丢失？
A: 是的，免费版每次重启会清空文件系统。建议：
1. 升级到付费版
2. 使用 Railway（有文件持久化）
3. 迁移到 D1 数据库

### Q: 如何绑定自定义域名？
A: 
- Cloudflare Pages：在设置中添加域名
- Render：在设置中添加域名，然后配置 DNS

---

## 推荐配置

**生产环境推荐**：
- 前端：Cloudflare Pages（免费）
- 后端：Render Starter（$7/月，有持久化）
- 数据库：SQLite（内置）或升级到 PostgreSQL

**完全免费方案**：
- 前端：Cloudflare Pages
- 后端：Railway（免费额度）
- 注意：Railway 免费额度有限，需定期检查
