# 卫星数据可视化系统 - 部署指南
# Satellite Data Visualization System - Deployment Guide

## 📋 项目概述 / Project Overview

这是一个卫星数据可视化Web应用，包含：
- **前端**: Next.js + React + TypeScript + Leaflet 交互式地图
- **后端**: FastAPI + Python 卫星数据处理API
- **数据源**: Himawari-9, Sentinel-3A/3B, Sentinel-2A/2B, SWOT 卫星数据

This is a satellite data visualization web application that includes:
- **Frontend**: Next.js + React + TypeScript + Leaflet interactive maps
- **Backend**: FastAPI + Python satellite data processing API  
- **Data Sources**: Himawari-9, Sentinel-3A/3B, Sentinel-2A/2B, SWOT satellite data

---

## 🚀 快速启动 / Quick Start

### 系统要求 / System Requirements
- **Node.js**: ≥ 18.0.0
- **Python**: ≥ 3.9.0
- **npm** 或 **yarn**
- **Git**

### ⚡ 团队协作流程 / Team Collaboration Workflow

#### 🔄 获取最新代码 / Get Latest Code
```bash
# 克隆仓库 (首次) / Clone repository (first time)
git clone [仓库URL]
cd Group12_Satellite_data_visualisation

# 或者拉取最新更新 (已有仓库) / Or pull latest updates (existing repo)
git pull origin main
```

#### ✅ 一键启动确认 / One-Click Start Confirmation
推送到主分支后，团队成员只需要：
After pushing to main branch, team members only need to:

1. **拉取代码** / Pull code: `git pull origin main`
2. **安装依赖** / Install dependencies: 按下面步骤 / Follow steps below
3. **启动服务** / Start services: 无需额外配置 / No additional config needed

---

## 📦 完整安装步骤 / Complete Installation Steps

### 1️⃣ 克隆项目 / Clone Repository
```bash
git clone [你的仓库URL / Your Repository URL]
cd Group12_Satellite_data_visualisation
```

### 2️⃣ 后端设置 / Backend Setup

#### 创建Python虚拟环境 / Create Python Virtual Environment
```bash
cd get_data
python -m venv venv

# Windows 激活
venv\Scripts\activate

# macOS/Linux 激活
source venv/bin/activate
```

#### 安装Python依赖 / Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 配置认证文件 / Configure Authentication Files
```bash
# 创建NASA Earthdata认证文件 (可选)
# Create NASA Earthdata credentials (optional)
echo "machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD" > ~/.netrc

# 创建EUMETSAT API认证文件 (如果需要)
# Create EUMETSAT API credentials (if needed)
echo "YOUR_API_KEY" > eumetsat_api_credentials.txt
```

#### 启动后端服务 / Start Backend Service
```bash
# 简单启动方式 (推荐) / Simple start method (recommended)
python api.py

# 或者使用uvicorn命令 / Or use uvicorn command
uvicorn api:app --reload --port 8000

# 生产模式 / Production mode
uvicorn api:app --host 0.0.0.0 --port 8000
```

后端服务将在 http://localhost:8000 启动
Backend service will start at http://localhost:8000

### 3️⃣ 前端设置 / Frontend Setup

#### 切换到前端目录 / Navigate to Frontend Directory
```bash
cd ../client
```

#### 安装Node.js依赖 / Install Node.js Dependencies
```bash
npm install
# 或者使用 yarn / or use yarn
yarn install
```

#### 启动前端开发服务器 / Start Frontend Development Server
```bash
npm run dev
# 或者 / or
yarn dev
```

前端应用将在 http://localhost:3000 启动
Frontend application will start at http://localhost:3000

---

## 🔧 详细配置说明 / Detailed Configuration

### 前端依赖 / Frontend Dependencies

#### 核心依赖 / Core Dependencies
```json
{
  "next": "13.5.1",           // Next.js 框架
  "react": "18.2.0",          // React 库
  "typescript": "5.2.2",      // TypeScript 支持
  "leaflet": "^1.9.4",       // 地图库
  "react-leaflet": "^4.2.1"   // React Leaflet 组件
}
```

#### UI 组件库 / UI Components
- **@radix-ui/***: 现代UI组件库 / Modern UI components
- **tailwindcss**: CSS框架 / CSS framework
- **lucide-react**: 图标库 / Icon library

#### 地图相关 / Map-related
- **leaflet**: 主要地图库 / Main mapping library
- **react-leaflet**: React集成 / React integration
- **@types/leaflet**: TypeScript类型定义 / TypeScript type definitions

### 后端依赖 / Backend Dependencies

#### Web框架 / Web Framework
```python
fastapi>=0.104.0           # 现代Python Web框架
uvicorn[standard]>=0.24.0  # ASGI服务器
pydantic>=2.4.0           # 数据验证
```

#### 科学计算 / Scientific Computing
```python
numpy>=1.24.0      # 数值计算
pandas>=2.0.0      # 数据处理
xarray>=2023.1.0   # 多维数组处理 (NetCDF核心库)
scipy>=1.10.0      # 科学计算
matplotlib>=3.7.0  # 数据可视化
```

#### 地理空间 / Geospatial
```python
pyproj>=3.5.0      # 投影转换
cartopy>=0.21.0    # 地理制图
rasterio>=1.3.0    # 栅格数据处理
geopandas>=0.13.0  # 地理数据处理
```

#### 卫星数据 / Satellite Data
```python
earthaccess>=0.8.0  # NASA数据访问
eumdac>=1.0.0       # EUMETSAT数据访问
netcdf4>=1.6.4      # NetCDF文件处理
h5py>=3.9.0         # HDF5文件处理
```

---

## 🌟 新增功能 / New Features

### 交互式地图功能 / Interactive Map Features

本次更新新增了三种地图显示模式：
This update adds three map display modes:

#### 1. 📸 Static Mode (静态模式)
- 预生成的高质量PNG图像 / Pre-generated high-quality PNG images
- 快速加载 / Fast loading
- 严格时间匹配 / Strict time matching

#### 2. 🎯 Interactive Mode (交互模式)  
- 点式数据显示 / Point-based data display
- 可点击查看数值 / Clickable for values
- 性能优化采样 / Performance-optimized sampling

#### 3. 🎨 Canvas Heatmap Mode (画布热力图模式) ⭐ **新功能**
- **完整数据点显示** / Complete data point display
- **实时渲染** / Real-time rendering  
- **与地图完全集成** / Fully integrated with map
- **Canvas → ImageURL → ImageOverlay 技术栈** / Technical stack

### 新增组件 / New Components
- **CanvasInteractiveMap.tsx**: 画布热力图组件
- **InteractiveMap.tsx**: 交互式点地图组件
- **时间轴处理逻辑**: 智能时间匹配算法

---

## 🔍 故障排除 / Troubleshooting

### 常见问题 / Common Issues

#### 前端问题 / Frontend Issues

**问题**: `npm install` 失败
**解决**: 
```bash
# 清除缓存
npm cache clean --force
# 删除node_modules和package-lock.json
rm -rf node_modules package-lock.json
# 重新安装
npm install
```

**问题**: Leaflet地图不显示
**解决**: 确保正确导入CSS
```javascript
import 'leaflet/dist/leaflet.css'
```

**问题**: TypeScript类型错误
**解决**: 确保安装了类型定义
```bash
npm install --save-dev @types/leaflet
```

#### 后端问题 / Backend Issues

**问题**: Python包安装失败
**解决**:
```bash
# 升级pip
pip install --upgrade pip
# 使用国内镜像 (中国用户)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**问题**: NetCDF文件读取错误
**解决**: 确保安装了正确的netcdf4版本
```bash
pip install netcdf4>=1.6.4
```

**问题**: CORS错误
**解决**: 检查FastAPI CORS设置
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 性能优化 / Performance Optimization

#### 前端优化 / Frontend Optimization
```bash
# 生产构建
npm run build
npm start
```

#### 后端优化 / Backend Optimization
```bash
# 使用更多工作进程
uvicorn api:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## 📁 项目结构 / Project Structure

```
Group12_Satellite_data_visualisation/
├── client/                    # 前端应用 / Frontend App
│   ├── app/                   # Next.js应用目录
│   ├── components/            # React组件
│   │   ├── CanvasInteractiveMap.tsx  # 🎨 画布热力图 (新)
│   │   ├── InteractiveMap.tsx        # 🎯 交互地图 (新)
│   │   ├── ResearchMap.tsx          # 📸 主地图组件
│   │   └── ...
│   ├── package.json          # Node.js依赖
│   └── ...
├── get_data/                 # 后端API / Backend API
│   ├── api.py               # 主API文件
│   ├── satellites/          # 卫星数据处理模块
│   ├── data/               # 数据存储目录
│   ├── requirements.txt    # Python依赖
│   └── ...
├── docs/                   # 📚 文档目录 (新)
│   ├── 前端功能使用说明.md
│   ├── Frontend-Features-User-Guide.md
│   ├── 时间轴处理逻辑文档.md
│   └── Timeline-Processing-Logic-Documentation.md
└── README.md              # 项目说明
```

---

## 🔐 环境变量 / Environment Variables

### 可选配置 / Optional Configuration

创建 `.env` 文件:
Create `.env` file:

```bash
# 后端配置 / Backend Configuration
API_PORT=8000
DEBUG=True

# 前端配置 / Frontend Configuration  
NEXT_PUBLIC_API_URL=http://localhost:8000

# 数据源配置 / Data Source Configuration
NASA_EARTHDATA_USERNAME=your_username
NASA_EARTHDATA_PASSWORD=your_password
EUMETSAT_API_KEY=your_api_key
```

---

## 🚦 验证安装 / Verify Installation

### 1. 检查后端 / Check Backend
访问: http://localhost:8000/docs
应该看到FastAPI交互式文档

Visit: http://localhost:8000/docs
Should see FastAPI interactive documentation

### 2. 检查前端 / Check Frontend  
访问: http://localhost:3000
应该看到卫星数据可视化界面

Visit: http://localhost:3000
Should see satellite data visualization interface

### 3. 测试交互式地图 / Test Interactive Maps
1. 点击"+ Add Map"添加地图
2. 选择参数 (如 SST - Himawari)
3. 切换到"Canvas"模式
4. 应该看到热力图显示

1. Click "+ Add Map" to add a map
2. Select parameter (e.g., SST - Himawari)  
3. Switch to "Canvas" mode
4. Should see heatmap display

---

## 📞 技术支持 / Technical Support

### 团队联系方式 / Team Contact
- **项目负责人**: Group 12 Team
- **技术问题**: 提交GitHub Issue
- **文档问题**: 查看 `docs/` 目录

### 有用链接 / Useful Links
- **Leaflet文档**: https://leafletjs.com/
- **React-Leaflet文档**: https://react-leaflet.js.org/
- **FastAPI文档**: https://fastapi.tiangolo.com/
- **Next.js文档**: https://nextjs.org/docs

---

## 🎯 下一步 / Next Steps

1. **配置数据源**: 添加你的卫星数据文件到 `get_data/data/` 目录
2. **自定义配置**: 根据需求修改API端口和前端配置
3. **生产部署**: 使用Docker或云服务部署到生产环境
4. **性能调优**: 根据数据量和用户数调整服务器配置

1. **Configure Data Sources**: Add your satellite data files to `get_data/data/` directory
2. **Custom Configuration**: Modify API ports and frontend config as needed
3. **Production Deployment**: Deploy to production using Docker or cloud services  
4. **Performance Tuning**: Adjust server config based on data volume and users

---

*最后更新: 2025年9月 | Last Updated: September 2025*
*版本: 2.0 (包含交互式地图功能) | Version: 2.0 (Including Interactive Map Features)*
