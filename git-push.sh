#!/bin/bash
# GitHub 推送脚本 - 考研刷题助手
# 用法: ./git-push.sh

REPO_NAME="kaoyan-quiz-helper"
GITHUB_USER="czk6664"
TOKEN="$1"

if [ -z "$TOKEN" ]; then
    echo "用法: ./git-push.sh <你的GitHub Token>"
    echo "例如: ./git-push.sh ghp_xxxxxxxxxxxx"
    exit 1
fi

echo "🚀 开始推送到 GitHub..."

# 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "❌ 请先安装 Git"
    exit 1
fi

# 初始化 git
git init

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
git remote remove origin 2>/dev/null
git remote add origin "https://${GITHUB_USER}:${TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"

# 推送到 main 分支
git branch -M main
git push -u origin main --force

if [ $? -eq 0 ]; then
    echo "✅ 推送成功！"
    echo "📎 仓库地址: https://github.com/${GITHUB_USER}/${REPO_NAME}"
    echo ""
    echo "下一步："
    echo "1. 去 GitHub 确认仓库已创建"
    echo "2. 在 Render 连接此仓库部署后端"
    echo "3. 在 Cloudflare Pages 部署前端"
else
    echo "❌ 推送失败，请检查 Token 是否正确"
fi
