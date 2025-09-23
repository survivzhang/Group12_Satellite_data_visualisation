# 🛰️ 卫星数据可视化系统 | Satellite Data Visualization System

## 📋 项目概述 | Project Overview

**CITS5206 Capstone Group 12**

这是一个基于Web的卫星数据可视化平台，支持多种卫星数据源的实时查看和分析，包含静态图像显示和交互式地图功能。

This is a web-based satellite data visualization platform that supports real-time viewing and analysis of various satellite data sources, featuring both static image display and interactive map capabilities.

## ✨ 主要功能 | Key Features

### 🗺️ **多地图模式 | Multi-Map Modes**
- **📸 Static Mode**: 预生成高质量PNG图像 | Pre-generated high-quality PNG images
- **🎯 Interactive Mode**: 点式数据交互查看 | Point-based interactive data viewing  
- **🎨 Canvas Heatmap Mode**: 高分辨率实时热力图 ⭐ | High-resolution real-time heatmap ⭐

### 🛰️ **支持的卫星 | Supported Satellites**
- **Himawari-9**: 海表温度 | Sea Surface Temperature (SST)
- **Sentinel-3A/3B**: 海表温度、叶绿素浓度 | SST, Chlorophyll Concentration (CHL)
- **Sentinel-2A/2B**: 反射率 | Reflectance (B02)
- **SWOT**: 海表高度异常 | Sea Surface Height Anomaly (SSHA)

### ⏱️ **时间序列分析 | Time Series Analysis**
- 自动播放时间序列 | Automatic time series playback
- 多级时间分辨率 (小时/日/周/月) | Multi-level time resolution (hours/days/weeks/months)
- 智能时间匹配算法 | Intelligent time matching algorithms

### 🎛️ **交互功能 | Interactive Features**
- 数据范围过滤 | Data range filtering
- 精确数值查询 | Precise value querying  
- 全屏模式 | Fullscreen mode
- 多参数对比 | Multi-parameter comparison

## 🚀 快速开始 | Quick Start

### 📋 系统要求 | System Requirements
- **Node.js** ≥ 18.0.0
- **Python** ≥ 3.9.0
- **npm** 或 **yarn**

### ⚡ 一键启动 | One-Click Start

#### 1️⃣ 后端 | Backend
```bash
cd get_data
# 创建并激活虚拟环境 (首次运行)
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
python api.py
```

#### 2️⃣ 前端 | Frontend
```bash
cd client
npm install
npm run dev
```

#### 3️⃣ 访问应用 | Access Application
- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000/docs

## 📚 详细文档 | Detailed Documentation

| 文档 | 说明 | Document | Description |
|------|------|----------|-------------|
| [**部署指南**](DEPLOYMENT_GUIDE.md) | 完整安装配置说明 | [**Deployment Guide**](DEPLOYMENT_GUIDE.md) | Complete installation & configuration |
| [**功能说明**](docs/前端功能使用说明.md) | 前端功能使用手册 | [**User Guide**](docs/Frontend-Features-User-Guide.md) | Frontend features manual |
| [**时间处理**](docs/时间轴处理逻辑文档.md) | 时间轴处理逻辑 | [**Timeline Logic**](docs/Timeline-Processing-Logic-Documentation.md) | Timeline processing logic |

## 🎯 新功能亮点 | New Feature Highlights

### 🎨 Canvas Heatmap 热力图模式
- **技术栈**: Canvas → ImageURL → ImageOverlay
- **数据完整性**: 显示所有NetCDF数据点 | Display all NetCDF data points
- **科学色彩映射**: Turbo (SST) + Viridis (CHL) | Scientific color mapping
- **地图集成**: 完全响应地图缩放和平移 | Fully responsive to map zoom/pan

### 🎯 智能时间匹配
- **Himawari**: 小时级精确匹配 | Hourly precise matching
- **Sentinel-3**: 最近时间点 + 智能回退 | Nearest time + intelligent fallback
- **统一时间轴**: 所有地图同步时间控制 | Unified timeline for all maps

## 🏗️ 技术架构 | Technical Architecture

### 前端 | Frontend
```
Next.js 13 + React 18 + TypeScript
├── Leaflet.js (地图引擎)
├── React-Leaflet (React集成)  
├── TailwindCSS (样式框架)
└── Radix UI (组件库)
```

### 后端 | Backend  
```
FastAPI + Python 3.9+
├── xarray (NetCDF处理)
├── NumPy + Pandas (数据处理)
├── Matplotlib (图像生成)
└── Cartopy (地理投影)
```

## 📁 项目结构 | Project Structure

```
Group12_Satellite_data_visualisation/
├── 📁 client/                    # 前端应用
│   ├── 📁 components/
│   │   ├── 🎨 CanvasInteractiveMap.tsx    # 画布热力图
│   │   ├── 🎯 InteractiveMap.tsx          # 交互地图
│   │   └── 📸 ResearchMap.tsx             # 静态地图
│   └── 📄 package.json
├── 📁 get_data/                  # 后端API
│   ├── 📄 api.py                # 主API文件
│   ├── 📁 satellites/           # 卫星数据模块
│   └── 📄 requirements.txt
├── 📁 docs/                     # 📚 项目文档
└── 📄 DEPLOYMENT_GUIDE.md       # 🚀 部署指南
```

## 🤝 团队成员 | Team Members

**CITS5206 Capstone Group 12**
- 卫星数据处理专家 | Satellite Data Processing Specialists
- 前端开发工程师 | Frontend Development Engineers  
- 地理信息系统专家 | GIS Specialists

## 📞 支持与反馈 | Support & Feedback

- **🐛 问题报告**: 提交GitHub Issue | Submit GitHub Issues
- **📖 文档问题**: 查看 `docs/` 目录 | Check `docs/` directory  
- **💡 功能建议**: 联系项目团队 | Contact project team

## 📄 许可证 | License

本项目为学术研究项目，遵循大学相关政策。
This project is for academic research and follows university policies.

---

⭐ **如果这个项目对你有帮助，请给我们一个Star！**
⭐ **If this project helps you, please give us a Star!** 
