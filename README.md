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

#### 1️⃣ Get Latest Code
```bash
# If first time
git clone [repository-url]
cd Group12_Satellite_data_visualisation

# If already have local repository
git pull origin main
```

#### 2️⃣ Start Backend (in get_data directory)
```bash
cd get_data

# First run: create virtual environment
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start backend (simple way)
python api.py
```

✅ **Success indicator**: See `Uvicorn running on http://0.0.0.0:8000`

#### 3️⃣ Start Frontend (in client directory)
```bash
# Open new terminal window
cd client

# First run: install dependencies
npm install

# Start frontend
npm run dev
```

✅ **Success indicator**: See `ready - started server on 0.0.0.0:3000`

#### 4️⃣ Experience New Features
1. Open browser: http://localhost:3000
2. Click "+ Add Map" to add map
3. Select parameter (e.g., "SST - Himawari")
4. Click **"Canvas"** button 🎨
5. Enjoy your developed interactive heatmap!

#### 5️⃣ Access Application
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

### 🔧 Key Dependencies

#### ✅ Frontend Dependencies (included in package.json)
```json
{
  "leaflet": "^1.9.4",           // Map core library
  "react-leaflet": "^4.2.1",    // React integration
  "@types/leaflet": "^1.9.20"   // TypeScript support
}
```

#### ✅ Backend Dependencies (included in requirements.txt)
```python
xarray>=2023.1.0      # NetCDF data processing
numpy>=1.24.0         # Numerical computing
fastapi>=0.104.0      # API framework
matplotlib>=3.7.0     # Color mapping
```

#### ✅ Canvas Features (no additional dependencies needed)
- HTML5 Canvas API (browser native)
- React Hooks (React built-in)
- ImageOverlay (Leaflet built-in)

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

## 💡 Important Setup Notes

### ✅ Team Member Operation Confirmation

After you **push code to main branch**, other team members can:

1. **Directly pull code** ✅
2. **One-click start and run** ✅  
3. **Immediately experience Canvas heatmap features** ✅

**No additional configuration or dependency installation required!**

### 🎊 Success Confirmation

#### 🎯 New Feature Highlights
- **🎨 Canvas Heatmap**: High-resolution real-time heatmap
- **📍 Complete Data Display**: All NetCDF data points, no sampling
- **🗺️ Map Integration**: Fully responsive to zoom and pan
- **🎨 Scientific Colors**: Turbo (SST) + Viridis (CHL)

#### 🚀 Recommended Startup Method
```bash
# Backend (recommended way)
python api.py

# Frontend
npm run dev
```

### 💡 Important Reminders

1. **Virtual Environment**: Backend must run in `get_data/venv` virtual environment
2. **Startup Command**: Using `python api.py` is simplest and most reliable
3. **Complete Dependencies**: All Canvas heatmap dependencies are included, no additional installation needed
4. **Plug and Play**: Ready to use immediately after `git pull`

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

🎉 **Congratulations! Your interactive map features have been perfectly integrated into the project!**

⭐ **If this project helps you, please give us a Star!** 