# 🚀 Quick Start Guide

## ⚡ 5-Minute Quick Experience

### 🎯 Goal
Quickly start the satellite data visualization system and experience interactive map features.

---

## 📋 Prerequisites

Make sure your system has:

```bash
✅ Node.js (≥ 18.0)     # Check version: node --version  
✅ Python (≥ 3.9)       # Check version: python --version
✅ npm or yarn          # Check version: npm --version
✅ Git                  # Check version: git --version
```

---

## 🔥 One-Click Start Commands

### Step 1: Get Latest Code
```bash
# First time
git clone [your-repository-url]
cd Group12_Satellite_data_visualisation

# Or update existing code
git pull origin main
```

💡 **Team Tip**: After pushing to main branch, other members just need `git pull` and follow steps below!

### Step 2: Start Backend
```bash
# Enter backend directory
cd get_data

# Create and activate virtual environment (first time)
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# Install Python dependencies (first time)
pip install -r requirements.txt

# Start backend service
python api.py
```

✅ **Success indicator**: See `Uvicorn running on http://0.0.0.0:8000`

### Step 3: Start Frontend
```bash
# Open new terminal, enter frontend directory
cd client

# Install Node.js dependencies (first time)
npm install

# Start frontend service
npm run dev
```

✅ **Success indicator**: See `ready - started server on 0.0.0.0:3000`

### Step 4: Experience Features
1. **Open browser**: http://localhost:3000
2. **Add map**: Click "+ Add Map" 
3. **Select parameter**: Expand "Data Parameters", select "SST (Himawari)"
4. **Switch mode**: Click "Canvas" button to experience heatmap
5. **Time control**: Use bottom timeline to play animation

---

## 🎮 Core Feature Experience Checklist

### ✅ Basic Function Tests

- [ ] **Page loading**: Visit http://localhost:3000 displays normally
- [ ] **API connection**: Visit http://localhost:8000/docs shows API documentation
- [ ] **Add map**: Click "+ Add Map" successfully adds new map window
- [ ] **Parameter selection**: Expand parameter panel, select different satellite data

### ✅ Interactive Map Tests

- [ ] **Static mode**: Default Static mode displays PNG images
- [ ] **Interactive mode**: Click "Interactive" displays point data
- [ ] **Heatmap mode**: Click "Canvas" displays continuous heatmap ⭐
- [ ] **Map interaction**: Zoom, drag map functions work normally

### ✅ Time Control Tests

- [ ] **Timeline dragging**: Drag time slider, map data updates
- [ ] **Play control**: Click play button, automatically plays time series
- [ ] **Resolution switching**: Switch time resolution (hour/day/week/month)

### ✅ Advanced Feature Tests

- [ ] **Data range filtering**: Click "Range" button to set value ranges
- [ ] **Image information**: Click "Image Info" to view detailed data statistics
- [ ] **Fullscreen mode**: Click fullscreen button to enlarge map
- [ ] **Multi-map comparison**: Add multiple maps to compare different parameters

---

## 🔧 Common Startup Issues Quick Fix

### 🚨 Backend Issues

**Issue**: `pip install` fails
**Solution**: 
```bash
# Upgrade pip
python -m pip install --upgrade pip
# Use alternative mirror (for China users)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**Issue**: `uvicorn: command not found`
**Solution**:
```bash
# Ensure in correct virtual environment
pip install uvicorn[standard]
# Or run directly
python -m uvicorn api:app --reload --port 8000
```

**Issue**: Port 8000 occupied
**Solution**:
```bash
# Use different port
uvicorn api:app --reload --port 8001
# Remember to update API address in frontend config
```

### 🚨 Frontend Issues

**Issue**: `npm install` slow or fails
**Solution**:
```bash
# Clear cache
npm cache clean --force
# Use alternative registry (for China users)  
npm install --registry https://registry.npmmirror.com
```

**Issue**: Map not displaying
**Solution**:
```bash
# Ensure backend service is running
# Check browser console for CORS errors
# Refresh page and retry
```

**Issue**: TypeScript compilation errors
**Solution**:
```bash
# Delete .next directory and rebuild
rm -rf .next
npm run dev
```

---

## 📊 Verify Successful Installation

### 🎯 Backend Verification
Visit: http://localhost:8000/docs
Should see: FastAPI interactive API documentation page

### 🎯 Frontend Verification  
Visit: http://localhost:3000
Should see: Satellite data visualization main interface with:

```
✅ Top: "Data Parameters (8 available)" 
✅ Middle: Map display area
✅ Bottom: Timeline controller
✅ Top-right: "Add Map" button
```

### 🎯 Feature Verification
1. **Add map**: Click "+ Add Map" → New map window appears
2. **Select parameter**: Expand parameter panel → See 8 satellite data options
3. **Canvas mode**: Switch to Canvas → See colorful heatmap
4. **Time playback**: Click play button → Map data updates automatically

---

## 🎉 Next Steps After Successful Launch

### 🔍 Explore Features
1. **Try different satellite data**: Himawari SST vs Sentinel-3 CHL
2. **Comparative analysis**: Add 4 maps to display different parameters simultaneously  
3. **Time series**: Use playback function to observe data trend changes
4. **Precise queries**: Click map in Interactive mode to view specific values

### 📚 Deep Learning
- Read [User Guide](docs/Frontend-Features-User-Guide.md) for detailed features
- Check [Deployment Guide](DEPLOYMENT_GUIDE.md) for production deployment
- Study [Timeline Logic](docs/Timeline-Processing-Logic-Documentation.md) to understand algorithms

### 🛠️ Development Customization
- Modify React components in `client/components/`
- Add your own satellite data in `get_data/data/`
- Adjust API endpoints in `get_data/api.py`

---

## 💡 Pro Tips

### ⚡ Performance Optimization
```bash
# Production build
cd client && npm run build && npm start

# Backend multi-process
uvicorn api:app --workers 4 --host 0.0.0.0 --port 8000
```

### 🔧 Development Tools
```bash
# Real-time code checking
cd client && npm run lint

# Python code formatting
cd get_data && black . && isort .
```

### 📱 Mobile Access
```bash
# Get local IP address
ipconfig  # Windows
ifconfig  # macOS/Linux

# Mobile access: http://your-ip:3000
```

---

## 🆘 Get Help

### Quick Help
- **🐛 Encountered Bug**: Check browser console and terminal output
- **📖 Feature Questions**: Check detailed documentation in `docs/` directory  
- **💡 Want New Features**: Contact project team for discussion

### Contact
- **GitHub**: Submit Issues to project repository
- **Documentation**: Check project `docs/` directory
- **Team**: CITS5206 Capstone Group 12

---

🎊 **Congratulations! You have successfully launched the satellite data visualization system!**

Now you can start exploring the wonderful world of ocean satellite data! 🌊🛰️