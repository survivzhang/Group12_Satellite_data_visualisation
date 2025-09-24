# 🗺️ Interactive Map Features

## 🎉 New Features Overview

We have added **three map display modes** to the satellite data visualization system, allowing users to switch freely according to their needs:

### 1. 📷 Static View Mode
- **Original functionality**: Unchanged PNG static image display
- **Features**: All existing functionality including data filtering and path display fully preserved
- **Advantages**: Continuous fill effects, close to scientific visualization standards

### 2. 📍 Point Interactive Mode
- **Implementation**: Leaflet + CircleMarker
- **Features**: Each data point is a clickable circular marker
- **Interactivity**: Click to view precise values, map zoom and pan
- **Performance**: Automatic data downsampling (when >50K points)

### 3. 🎨 Canvas Heatmap Mode - **New Core Feature**
- **Implementation**: Canvas + Gaussian diffusion algorithm
- **Visual effects**: Simulates matplotlib's continuous fill effect
- **Performance optimization**: GPU-accelerated Canvas rendering
- **Interactivity**: Mouse hover displays data details

## 🔧 Technical Implementation Details

### Core Algorithm for Canvas Heatmap

1. **Data Point Diffusion**:
   ```
   Each NC data point → Gaussian diffusion to surrounding pixels
   Diffusion radius = f(data density)
   ```

2. **Adaptive Diffusion Radius**:
   ```
   High density data: 2 pixel diffusion
   Medium density data: 4-6 pixel diffusion  
   Low density data: 8-12 pixel diffusion
   ```

3. **Gaussian Mixing Rendering**:
   ```
   intensity = exp(-(distance²)/(2σ²))
   Color mixing = additive blending mode
   ```

### Color Mapping Strategy

- **Sea Surface Temperature (SST)**: Blue (cold) → Green → Red (hot)
- **Chlorophyll (CHL)**: Dark blue → Cyan → Green → Yellow → Red

## 🚀 Usage Instructions

### Switching View Modes

1. **From Static View**:
   - Click "Canvas Heatmap" button in bottom-left → Canvas heatmap
   - Click "Point Interactive" button in bottom-left → Point interactive mode

2. **Switch Between Interactive Modes**:
   - Buttons in top-right allow free switching between three modes
   - Static / Canvas / Points

### Interactive Features

- **Canvas Heatmap**:
  - 🖱️ Mouse hover: Display detailed information of nearest data point
  - 🔍 Map zoom: Real-time re-render heatmap
  - 📱 Pan and drag: Smooth map navigation

- **Point Interactive Mode**:
  - 📍 Click data point: Pop-up detailed information window
  - 🗺️ Full map control: Zoom, pan, layer switching

## 📊 Performance Optimization

### Data Transfer Optimization
- **Automatic downsampling**: Automatic downsampling when exceeding 50,000 points
- **Intelligent thresholds**: Reduce transfer volume while maintaining data distribution characteristics
- **Compressed transfer**: Only transfer valid data points (excluding NaN values)

### Rendering Optimization  
- **Canvas acceleration**: 10-100 times faster than DOM operations
- **Gaussian caching**: Pre-computed Gaussian kernel functions
- **Incremental rendering**: Re-render only when map changes

## 🎯 Use Cases

### Canvas Heatmap Best For:
- ✅ Scientific data visualization (continuous distribution effects)
- ✅ Large dataset display (excellent performance)
- ✅ Overall trend analysis
- ✅ Presentation purposes (beautiful and professional)

### Point Interactive Mode Best For:
- ✅ Precise data queries
- ✅ Data quality checking
- ✅ Point-by-point analysis
- ✅ Data exploration

### Static Image Mode Best For:
- ✅ Data filtering analysis
- ✅ Historical record keeping
- ✅ Batch processing
- ✅ Report generation

## 🔌 API Endpoints

New backend API endpoint:
```
GET /api/v1/satellites/{satellite}/{parameter}/data/{filename}
```

**Parameters**:
- `target_time`: Target time (ISO format)
- `min_value`: Minimum value filter (optional)
- `max_value`: Maximum value filter (optional)

**Returns**:
```json
{
  "satellite": "himawari",
  "parameter": "sst", 
  "data_points": [
    {"lat": -22.0, "lon": 114.0, "value": 298.5}
  ],
  "bounds": {"north": -19.0, "south": -25.0, "east": 117.0, "west": 111.0},
  "statistics": {"min": 295.0, "max": 305.0, "mean": 300.0, "count": 25000, "units": "K"},
  "metadata": {"downsampled": true, "downsample_factor": 2}
}
```

## 🎨 Visual Comparison

| Mode | Visual Effects | Performance | Interactivity | Use Cases |
|------|----------------|-------------|---------------|-----------|
| Static Image | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | Analysis, filtering |
| Canvas Heatmap | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Visualization, presentation |
| Point Interactive | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Exploration, queries |

## 🛠️ Dependencies

New npm packages:
```json
{
  "leaflet": "^1.9.x",
  "react-leaflet": "^4.2.1", 
  "@types/leaflet": "^1.9.x"
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Map not displaying**:
   - Check if Leaflet CSS is correctly imported
   - Confirm backend API is running on port 8000

2. **Data points not rendering**:
   - Check if NC files exist
   - Verify data_points array in API response

3. **Performance issues**:
   - Large datasets will be automatically downsampled
   - Canvas rendering is many times faster than DOM

### Debugging Tips
- Open browser developer tools to check API requests
- Check Console logs to understand data loading status
- Monitor data transfer size in Network panel

---

🎊 **Congratulations! You now have a fully functional three-in-one satellite data visualization system!**