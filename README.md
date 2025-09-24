# 🛰️ Satellite Data Visualization System

## 📋 Project Overview

**CITS5206 Capstone Group 12**

This is a web-based satellite data visualization platform that supports real-time viewing and analysis of various satellite data sources, featuring both static image display and interactive map capabilities.

## ✨ Key Features

### 🗺️ **Multi-Map Modes**
- **📸 Static Mode**: Pre-generated high-quality PNG images
- **🎯 Interactive Mode**: Point-based interactive data viewing  
- **🎨 Canvas Heatmap Mode**: High-resolution real-time heatmap ⭐

### 🛰️ **Supported Satellites**
- **Himawari-9**: Sea Surface Temperature (SST)
- **Sentinel-3A/3B**: SST, Chlorophyll Concentration (CHL)
- **Sentinel-2A/2B**: Reflectance (B02)
- **SWOT**: Sea Surface Height Anomaly (SSHA)

### ⏱️ **Time Series Analysis**
- Automatic time series playback
- Multi-level time resolution (hours/days/weeks/months)
- Intelligent time matching algorithms

### 🎛️ **Interactive Features**
- Data range filtering
- Precise value querying  
- Fullscreen mode
- Multi-parameter comparison

## 🚀 Quick Start

### 📋 System Requirements
- **Node.js** ≥ 18.0.0
- **Python** ≥ 3.9.0
- **npm** or **yarn**

### ⚡ One-Click Start

#### 1️⃣ Backend
```bash
cd get_data
# Create and activate virtual environment (first time only)
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
python api.py
```

#### 2️⃣ Frontend
```bash
cd client
npm install
npm run dev
```

#### 3️⃣ Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

## 📚 Detailed Documentation

| Document | Description |
|----------|-------------|
| [**Deployment Guide**](DEPLOYMENT_GUIDE.md) | Complete installation & configuration |
| [**User Guide**](docs/Frontend-Features-User-Guide.md) | Frontend features manual |
| [**Timeline Logic**](docs/Timeline-Processing-Logic-Documentation.md) | Timeline processing logic |
| [**Interactive Map Features**](INTERACTIVE_MAP_FEATURES.md) | Interactive map capabilities |

## 🎯 New Feature Highlights

### 🎨 Canvas Heatmap Mode
- **Tech Stack**: Canvas → ImageURL → ImageOverlay
- **Data Completeness**: Display all NetCDF data points
- **Scientific Color Mapping**: Turbo (SST) + Viridis (CHL)
- **Map Integration**: Fully responsive to map zoom/pan

### 🎯 Intelligent Time Matching
- **Himawari**: Hourly precise matching
- **Sentinel-3**: Nearest time + intelligent fallback
- **Unified Timeline**: Synchronized time control for all maps

## 🏗️ Technical Architecture

### Frontend
```
Next.js 13 + React 18 + TypeScript
├── Leaflet.js (Map Engine)
├── React-Leaflet (React Integration)  
├── TailwindCSS (Styling Framework)
└── Radix UI (Component Library)
```

### Backend  
```
FastAPI + Python 3.9+
├── xarray (NetCDF Processing)
├── NumPy + Pandas (Data Processing)
├── Matplotlib (Image Generation)
└── Cartopy (Geographic Projection)
```

## 📁 Project Structure

```
Group12_Satellite_data_visualisation/
├── 📁 client/                    # Frontend Application
│   ├── 📁 components/
│   │   ├── 🎨 CanvasInteractiveMap.tsx    # Canvas Heatmap
│   │   ├── 🎯 InteractiveMap.tsx          # Interactive Map
│   │   └── 📸 ResearchMap.tsx             # Static Map
│   └── 📄 package.json
├── 📁 get_data/                  # Backend API
│   ├── 📄 api.py                # Main API File
│   ├── 📁 satellites/           # Satellite Data Modules
│   └── 📄 requirements.txt
├── 📁 docs/                     # 📚 Project Documentation
└── 📄 DEPLOYMENT_GUIDE.md       # 🚀 Deployment Guide
```

## 🤝 Team Members

**CITS5206 Capstone Group 12**
- Satellite Data Processing Specialists
- Frontend Development Engineers  
- GIS Specialists

## 📞 Support & Feedback

- **🐛 Bug Reports**: Submit GitHub Issues
- **📖 Documentation Issues**: Check `docs/` directory  
- **💡 Feature Requests**: Contact project team

## 📄 License

This project is for academic research and follows university policies.

---

⭐ **If this project helps you, please give us a Star!** 