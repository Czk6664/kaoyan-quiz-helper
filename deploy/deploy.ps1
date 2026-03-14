# 部署脚本 - 将前端部署到 Cloudflare Pages
# 使用方法: .\deploy.ps1 -ApiBase "https://your-backend.onrender.com/api"

param(
    [string]$ApiBase = "https://your-backend.onrender.com/api"
)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  刷题网站部署脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 设置路径
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DeployDir = Join-Path $ProjectRoot "deploy\frontend"

Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray
Write-Host "前端目录: $FrontendDir" -ForegroundColor Gray
Write-Host "部署目录: $DeployDir" -ForegroundColor Gray
Write-Host "API 地址: $ApiBase" -ForegroundColor Yellow
Write-Host ""

# 创建部署目录
if (Test-Path $DeployDir) {
    Remove-Item -Path $DeployDir -Recurse -Force
}
New-Item -ItemType Directory -Path $DeployDir -Force | Out-Null

# 复制前端文件
Write-Host "复制前端文件..." -ForegroundColor Green
Copy-Item -Path "$FrontendDir\*" -Destination $DeployDir -Recurse -Force

# 修改 API 地址
$IndexFile = Join-Path $DeployDir "index.html"
Write-Host "修改 API 地址..." -ForegroundColor Green

$content = Get-Content $IndexFile -Raw -Encoding UTF8
$content = $content -replace "const API_BASE = 'http://localhost:5000/api';", "const API_BASE = '$ApiBase';"
Set-Content $IndexFile -Value $content -Encoding UTF8

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  部署准备完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "后续步骤:" -ForegroundColor Yellow
Write-Host ""
Write-Host "方案1: 使用 Cloudflare Dashboard" -ForegroundColor White
Write-Host "  1. 登录 https://dash.cloudflare.com" -ForegroundColor Gray
Write-Host "  2. 进入 Pages -> Create a project" -ForegroundColor Gray
Write-Host "  3. 选择 'Direct Upload'" -ForegroundColor Gray
Write-Host "  4. 上传目录: $DeployDir" -ForegroundColor Gray
Write-Host ""
Write-Host "方案2: 使用 wrangler CLI" -ForegroundColor White
Write-Host "  1. 安装: npm install -g wrangler" -ForegroundColor Gray
Write-Host "  2. 登录: wrangler login" -ForegroundColor Gray
Write-Host "  3. 部署: wrangler pages deploy $DeployDir --project-name=exam-quiz" -ForegroundColor Gray
Write-Host ""
Write-Host "部署后端:" -ForegroundColor Yellow
Write-Host "  请参考 DEPLOY.md 中的后端部署说明" -ForegroundColor Gray
Write-Host ""
