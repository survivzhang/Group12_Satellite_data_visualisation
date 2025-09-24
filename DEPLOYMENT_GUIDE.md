# Satellite Data Visualization System - Deployment Guide

## 📋 Project Overview

This is a satellite data visualization web application that includes:
- **Frontend**: Next.js + React + TypeScript + Leaflet interactive maps
- **Backend**: FastAPI + Python satellite data processing API  
- **Data Sources**: Himawari-9, Sentinel-3A/3B, Sentinel-2A/2B, SWOT satellite data

---

## 🚀 Quick Start

### System Requirements
- **Node.js**: ≥ 18.0.0
- **Python**: ≥ 3.9.0
- **npm** or **yarn**
- **Git**

### ⚡ Team Collaboration Workflow

#### 🔄 Get Latest Code
```bash
# Clone repository (first time)
git clone [repository-url]
cd Group12_Satellite_data_visualisation

# Or pull latest updates (existing repo)
git pull origin main
```

#### ✅ One-Click Start Confirmation
After pushing to main branch, team members only need to:

1. **Pull code**: `git pull origin main`
2. **Install dependencies**: Follow steps below
3. **Start services**: No additional config needed

---

## 📦 Complete Installation Steps

### 1️⃣ Clone Repository
```bash
git clone [your-repository-url]
cd Group12_Satellite_data_visualisation
```

### 2️⃣ Backend Setup

#### Create Python Virtual Environment
```bash
cd get_data
python -m venv venv

# Windows activation
venv\Scripts\activate

# macOS/Linux activation
source venv/bin/activate
```

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Configure Authentication Files
```bash
# Create NASA Earthdata credentials (optional)
echo "machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD" > ~/.netrc

# Create EUMETSAT API credentials (if needed)
echo "YOUR_API_KEY" > eumetsat_api_credentials.txt
```

#### Start Backend Service
```bash
# Simple start method (recommended)
python api.py

# Or use uvicorn command
uvicorn api:app --reload --port 8000

# Production mode
uvicorn api:app --host 0.0.0.0 --port 8000
```

Backend service will start at http://localhost:8000

### 3️⃣ Frontend Setup

#### Navigate to Frontend Directory
```bash
cd ../client
```

#### Install Node.js Dependencies
```bash
npm install
# or use yarn
yarn install
```

#### Start Frontend Development Server
```bash
npm run dev
# or
yarn dev
```

Frontend application will start at http://localhost:3000

---

## 🔧 Detailed Configuration

### Frontend Dependencies

#### Core Dependencies
```json
{
  "next": "13.5.1",           // Next.js framework
  "react": "18.2.0",          // React library
  "typescript": "5.2.2",      // TypeScript support
  "leaflet": "^1.9.4",       // Mapping library
  "react-leaflet": "^4.2.1"   // React Leaflet components
}
```

#### UI Components
- **@radix-ui/***: Modern UI components
- **tailwindcss**: CSS framework
- **lucide-react**: Icon library

#### Map-related
- **leaflet**: Main mapping library
- **react-leaflet**: React integration
- **@types/leaflet**: TypeScript type definitions

### Backend Dependencies

#### Web Framework
```python
fastapi>=0.104.0           # Modern Python web framework
uvicorn[standard]>=0.24.0  # ASGI server
pydantic>=2.4.0           # Data validation
```

#### Scientific Computing
```python
numpy>=1.24.0      # Numerical computing
pandas>=2.0.0      # Data processing
xarray>=2023.1.0   # Multi-dimensional array processing (NetCDF core)
scipy>=1.10.0      # Scientific computing
matplotlib>=3.7.0  # Data visualization
```

#### Geospatial
```python
pyproj>=3.5.0      # Projection transformations
cartopy>=0.21.0    # Geographic mapping
rasterio>=1.3.0    # Raster data processing
geopandas>=0.13.0  # Geographic data processing
```

#### Satellite Data
```python
earthaccess>=0.8.0  # NASA data access
eumdac>=1.0.0       # EUMETSAT data access
netcdf4>=1.6.4      # NetCDF file processing
h5py>=3.9.0         # HDF5 file processing
```

---

## 🌟 New Features

### Interactive Map Features

This update adds three map display modes:

#### 1. 📸 Static Mode
- Pre-generated high-quality PNG images
- Fast loading
- Strict time matching

#### 2. 🎯 Interactive Mode  
- Point-based data display
- Clickable for values
- Performance-optimized sampling

#### 3. 🎨 Canvas Heatmap Mode ⭐ **New Feature**
- **Complete data point display**
- **Real-time rendering**  
- **Fully integrated with map**
- **Canvas → ImageURL → ImageOverlay technical stack**

### New Components
- **CanvasInteractiveMap.tsx**: Canvas heatmap component
- **InteractiveMap.tsx**: Interactive point map component
- **Timeline processing logic**: Intelligent time matching algorithms

---

## 🔍 Troubleshooting

### Common Issues

#### Frontend Issues

**Issue**: `npm install` fails
**Solution**: 
```bash
# Clear cache
npm cache clean --force
# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json
# Reinstall
npm install
```

**Issue**: Leaflet map not displaying
**Solution**: Ensure correct CSS import
```javascript
import 'leaflet/dist/leaflet.css'
```

**Issue**: TypeScript type errors
**Solution**: Ensure type definitions are installed
```bash
npm install --save-dev @types/leaflet
```

#### Backend Issues

**Issue**: Python package installation fails
**Solution**:
```bash
# Upgrade pip
pip install --upgrade pip
# Use alternative index (for China users)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**Issue**: NetCDF file reading errors
**Solution**: Ensure correct netcdf4 version
```bash
pip install netcdf4>=1.6.4
```

**Issue**: CORS errors
**Solution**: Check FastAPI CORS settings
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

### Performance Optimization

#### Frontend Optimization
```bash
# Production build
npm run build
npm start
```

#### Backend Optimization
```bash
# Use more worker processes
uvicorn api:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## 📁 Project Structure

```
Group12_Satellite_data_visualisation/
├── client/                    # Frontend Application
│   ├── app/                   # Next.js app directory
│   ├── components/            # React components
│   │   ├── CanvasInteractiveMap.tsx  # 🎨 Canvas heatmap (new)
│   │   ├── InteractiveMap.tsx        # 🎯 Interactive map (new)
│   │   ├── ResearchMap.tsx          # 📸 Main map component
│   │   └── ...
│   ├── package.json          # Node.js dependencies
│   └── ...
├── get_data/                 # Backend API
│   ├── api.py               # Main API file
│   ├── satellites/          # Satellite data processing modules
│   ├── data/               # Data storage directory
│   ├── requirements.txt    # Python dependencies
│   └── ...
├── docs/                   # 📚 Documentation directory
│   ├── Frontend-Features-User-Guide.md
│   └── Timeline-Processing-Logic-Documentation.md
└── README.md              # Project documentation
```

---

## 🔐 Environment Variables

### Optional Configuration

Create `.env` file:

```bash
# Backend Configuration
API_PORT=8000
DEBUG=True

# Frontend Configuration  
NEXT_PUBLIC_API_URL=http://localhost:8000

# Data Source Configuration
NASA_EARTHDATA_USERNAME=your_username
NASA_EARTHDATA_PASSWORD=your_password
EUMETSAT_API_KEY=your_api_key
```

---

## 🚦 Verify Installation

### 1. Check Backend
Visit: http://localhost:8000/docs
Should see FastAPI interactive documentation

### 2. Check Frontend  
Visit: http://localhost:3000
Should see satellite data visualization interface

### 3. Test Interactive Maps
1. Click "+ Add Map" to add a map
2. Select parameter (e.g., SST - Himawari)  
3. Switch to "Canvas" mode
4. Should see heatmap display

---

## 📞 Technical Support

### Team Contact
- **Project Lead**: Group 12 Team
- **Technical Issues**: Submit GitHub Issues
- **Documentation Issues**: Check `docs/` directory

### Useful Links
- **Leaflet Documentation**: https://leafletjs.com/
- **React-Leaflet Documentation**: https://react-leaflet.js.org/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Next.js Documentation**: https://nextjs.org/docs

---

## 🎯 Next Steps

1. **Configure Data Sources**: Add your satellite data files to `get_data/data/` directory
2. **Custom Configuration**: Modify API ports and frontend config as needed
3. **Production Deployment**: Deploy to production using Docker or cloud services  
4. **Performance Tuning**: Adjust server config based on data volume and users

---

*Last Updated: September 2025*
*Version: 2.0 (Including Interactive Map Features)*