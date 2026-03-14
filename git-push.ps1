# GitHub 推送脚本 (Windows PowerShell)
# 用法: .\git-push.ps1 -Token "你的GitHub Token"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$RepoName = "kaoyan-quiz-helper"
$GithubUser = "czk6664"

Write-Host "🚀 开始推送到 GitHub..." -ForegroundColor Green

# 检查 git 是否安装
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 请先安装 Git" -ForegroundColor Red
    exit 1
}

# 初始化 git
git init

# 配置 git 用户信息（如果未设置）
$gitUser = git config user.name
$gitEmail = git config user.email
if (-not $gitUser) {
    git config user.name "czk6664"
    git config user.email "czk6664@users.noreply.github.com"
}

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: 考研刷题助手 v1.0

功能特性:
- AI 自动生成选择题（支持文本/PDF）
- 智能刷题模式（艾宾浩斯遗忘曲线）
- 错题本、收藏夹管理
- 用户系统（注册/登录/云端同步）
- 离线模式支持

技术栈:
- 前端: 纯 HTML/CSS/JS
- 后端: Flask + MiniMax API
- 部署: Cloudflare Pages + Render"

# 添加远程仓库（使用 Token）
git remote remove origin 2>$null
git remote add origin "https://${GithubUser}:${Token}@github.com/${GithubUser}/${RepoName}.git"

# 推送到 main 分支
git branch -M main
$pushResult = git push -u origin main --force 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 推送成功！" -ForegroundColor Green
    Write-Host "📎 仓库地址: https://github.com/$GithubUser/$RepoName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Yellow
    Write-Host "1. 去 GitHub 确认仓库已创建"
    Write-Host "2. 在 Render 连接此仓库部署后端"
    Write-Host "3. 在 Cloudflare Pages 部署前端"
} else {
    Write-Host "❌ 推送失败" -ForegroundColor Red
    Write-Host $pushResult
    Write-Host ""
    Write-Host "可能的解决方案：" -ForegroundColor Yellow
    Write-Host "1. 检查 Token 是否有 repo 权限"
    Write-Host "2. 手动在 GitHub 创建空仓库: https://github.com/new"
    Write-Host "3. 如果仓库已存在，确保 Token 可以访问该仓库"
}
