#!/bin/bash
# 部署脚本 - 将前端部署到 Cloudflare Pages
# 使用方法: ./deploy.sh <后端API地址>

API_BASE=${1:-"https://your-backend.onrender.com/api"}

echo "部署刷题网站前端"
echo "API 地址: $API_BASE"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 复制前端文件
cp -r frontend/* $TEMP_DIR/

# 修改 API 地址
sed -i "s|const API_BASE = 'http://localhost:5000/api';|const API_BASE = '$API_BASE';|g" $TEMP_DIR/index.html

echo "已修改 API 地址"

# 使用 wrangler 部署到 Cloudflare Pages
# 需要先安装 wrangler: npm install -g wrangler
echo ""
echo "部署到 Cloudflare Pages..."
echo "请运行: wrangler pages deploy $TEMP_DIR"

# 清理
rm -rf $TEMP_DIR

echo ""
echo "部署配置完成！"
echo ""
echo "后续步骤:"
echo "1. 在 Cloudflare Dashboard 创建 Pages 项目"
echo "2. 上传 deploy/frontend 目录"
echo "3. 或者使用 wrangler: wrangler pages project create exam-quiz"
echo "4. 然后: wrangler pages deploy deploy/frontend"
