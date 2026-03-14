# 刷题网站部署配置文件说明

## 创建的文件清单

```
刷题网站/
├── DEPLOY.md              # 详细部署指南
├── QUICKSTART.md          # 快速部署指南
├── render.yaml            # Render 平台配置
├── vercel.json            # Vercel 平台配置
├── deploy.sh              # Bash 部署脚本（Linux/Mac）
├── deploy/
│   ├── deploy.ps1         # PowerShell 部署脚本（Windows）
│   └── frontend/
│       ├── index.html     # 修改后的前端文件（API地址待配置）
│       └── _headers       # Cloudflare Pages 配置
└── cloudflare/
    ├── wrangler.toml      # Cloudflare Workers 配置
    ├── schema.sql         # D1 数据库表结构
    └── worker.py          # Worker 后端代码（简化版）
```

---

## 配置文件用途

### 1. DEPLOY.md
完整的部署方案说明，包含三种部署方案：
- 方案A：Cloudflare Pages + Render（推荐）
- 方案B：完全 Cloudflare（Pages + Workers + D1）
- 方案C：Railway（完全免费）

### 2. QUICKSTART.md
简化版的快速部署指南，适合快速上手。

### 3. render.yaml
Render 平台的配置文件，定义：
- Python 版本
- 依赖安装命令
- 启动命令
- 环境变量

### 4. vercel.json
Vercel 平台的配置文件（可选方案）。

### 5. deploy/deploy.ps1
Windows 部署脚本，自动：
- 复制前端文件
- 修改 API 地址
- 输出部署指导

### 6. deploy/frontend/index.html
修改后的前端文件，API_BASE 已改为配置项，部署时需要替换为实际后端地址。

### 7. deploy/frontend/_headers
Cloudflare Pages 的 HTTP 头配置：
- 缓存策略优化
- CORS 头设置

### 8. cloudflare/wrangler.toml
Cloudflare Workers 的配置：
- D1 数据库绑定
- 路由配置
- 环境变量

### 9. cloudflare/schema.sql
D1 数据库的完整表结构，包含：
- 用户表
- 题目表
- 错题记录表
- 收藏表
- 记忆曲线表
- 统计表

### 10. cloudflare/worker.py
适配 Cloudflare Workers 的简化后端代码。

---

## 推荐部署流程

### 最快方案：Render + Cloudflare Pages

1. **部署后端到 Render**
   ```
   1. 注册 render.com
   2. 连接 GitHub 仓库
   3. 配置环境变量（MINIMAX_API_KEY, JWT_SECRET）
   4. 获取部署 URL
   ```

2. **修改前端 API 地址**
   ```powershell
   cd deploy
   .\deploy.ps1 -ApiBase "https://your-backend.onrender.com/api"
   ```

3. **部署前端到 Cloudflare Pages**
   ```
   1. 登录 Cloudflare Dashboard
   2. Pages → Create a project → Direct Upload
   3. 上传 deploy/frontend 目录
   4. 获取网站 URL
   ```

4. **完成**
   - 前端：Cloudflare Pages 地址
   - 后端：Render 地址

---

## 注意事项

1. **API 密钥安全**
   - 不要将 API 密钥提交到 GitHub
   - 使用环境变量配置

2. **Render 免费版限制**
   - 免费版会在 15 分钟无活动后休眠
   - 首次访问需要等待 30 秒启动
   - 每月 750 小时运行时间

3. **跨域问题**
   - 后端已配置 CORS，通常不需要额外处理
   - 如果出现问题，检查 API 地址是否正确

4. **数据持久化**
   - Render 免费版不保证文件持久化
   - 建议定期备份 data/ 目录
   - 生产环境建议使用付费版或 D1 数据库

---

## 下一步行动

1. 获取 MiniMax API Key（必需）
2. 选择部署方案（推荐方案A）
3. 按照 QUICKSTART.md 操作
4. 测试各项功能
