# Satellite Data Visualization System - Frontend Features User Guide

## 📋 Overview

This system is a web-based satellite data visualization platform that supports real-time viewing and analysis of various satellite data sources. Users can browse scientific data such as sea surface temperature and chlorophyll concentration from different satellites through an intuitive interface.

## 🗺️ Main Features

### 1. **Multi-Map Instance Management**
- **Function**: Display up to 4 map windows simultaneously
- **Purpose**: Compare different satellite data or parameters
- **Operation**: Click the "+ Add Map" button to add new maps

### 2. **Parameter Selector (Data Parameters)**
- **Function**: Select satellite data parameters to display
- **Available Parameters**:
  - 🌡️ **Sea Surface Temperature (SST)**: Himawari, Sentinel-3A, Sentinel-3B
  - 🌿 **Chlorophyll Concentration (CHL)**: Sentinel-3A, Sentinel-3B
  - 👁️ **Reflectance (B02)**: Sentinel-2A, Sentinel-2B
  - 🌊 **Sea Surface Height Anomaly (SSHA)**: SWOT
- **Operation**: Expand the parameter panel, click parameter names to add to map

### 3. **Timeline Control (Temporal Analysis)**
- **Function**: Select viewing time point and time range
- **Time Resolution Options**:
  - 📅 **Months**: Monthly level
  - 📅 **Weeks**: Weekly level  
  - 📅 **Days**: Daily level
  - ⏰ **Hours**: Hourly level
- **Playback Controls**:
  - ▶️ **Play/Pause**: Automatic timeline playback
  - ⏮️ **Rewind**: Jump to beginning
  - ⏯️ **Step**: Step forward/backward
  - ⏭️ **Fast Forward**: Jump to end
- **Operation**: Drag timeline slider or use playback controls

### 4. **Map View Modes**

Each map supports three display modes:

#### 📸 **Static (Static Image Mode)**
- **Purpose**: View pre-generated high-quality satellite images
- **Features**: 
  - Fast loading speed
  - High image quality
  - Strict time matching
- **Use Case**: Precise time point data viewing

#### 🎯 **Interactive (Interactive Map Mode)**  
- **Purpose**: Point-based data interactive viewing
- **Features**:
  - Clickable for specific values
  - Based on Leaflet maps
  - Sampling for performance optimization
- **Use Case**: Exploratory data analysis

#### 🎨 **Canvas Heatmap (Canvas Heatmap Mode)**
- **Purpose**: High-resolution heatmap display
- **Features**:
  - Complete data point display
  - Real-time rendering
  - Fully integrated with map
- **Use Case**: Detailed spatial analysis

### 5. **Data Range Filtering (Range Control)**
- **Function**: Set display range for data values
- **Purpose**: Highlight data within specific value ranges
- **Operation**: 
  1. Click "Range" button on the map
  2. Enter minimum and maximum values
  3. Click "Apply" to apply filter
  4. Click "Reset" to restore original range

### 6. **Image Information Viewing**
- **Function**: View detailed information about currently displayed image
- **Information Content**:
  - 📁 Filename
  - 📊 Data statistics (min, max, mean values)
  - 🌐 URL path
  - 💾 Local path
- **Operation**: Click "Image Info" button on the map

### 7. **Fullscreen Mode**
- **Function**: Expand a single map to fullscreen display
- **Purpose**: Detailed data examination
- **Operation**: Click fullscreen button in the top-right corner of the map

### 8. **Data Updates**
- **Function**: Manually refresh data sources
- **Purpose**: Get latest satellite data
- **Operation**: Click refresh button on main interface
- **Status Display**: Shows last update time and missing file count

## 🎛️ Interface Layout

### Top Control Bar
```
[🛰️ Data Parameters (8 available)] [+ Add Map (2/4)] [📈 Expand]
```

### Main Display Area
```
┌─────────────────┬─────────────────┐
│      Map 1      │      Map 2      │
│ [Parameter]     │ [Parameter]     │
│ [View Mode]     │ [View Mode]     │
│ [Controls]      │ [Controls]      │
└─────────────────┴─────────────────┘
┌─────────────────┬─────────────────┐
│      Map 3      │      Map 4      │
│   (Optional)    │   (Optional)    │
└─────────────────┴─────────────────┘
```

### Bottom Time Control
```
📅 Time Resolution: [Months] [Weeks] [Days] [Hours]
⏰ Saturday, March 1, 2025 at 09:12 AM
🎛️ [⏮️] [⏯️] [▶️] [⏯️] [⏭️]
━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━
08:00    10:00    12:00    14:00    16:00    18:00    20:00
```

## 🔄 Workflow Examples

### Basic Usage Workflow
1. **Select Parameters**: Expand "Data Parameters", choose satellite data of interest
2. **Add Maps**: Click parameters to add to map windows
3. **Set Time**: Use timeline to select time point to view
4. **Choose View**: Switch between Static/Interactive/Canvas modes based on needs
5. **Data Analysis**: View data values, set range filters, get detailed information

### Comparative Analysis Workflow
1. **Add Multiple Maps**: Add up to 4 map instances
2. **Select Different Parameters**: Choose different satellites or parameters for each map
3. **Synchronize Time**: All maps share the same timeline
4. **Compare Observations**: Simultaneously observe trends across different data sources

## ⚙️ Advanced Features

### 🎯 Precise Data Querying
- **Interactive Mode**: Click anywhere on map to view precise values
- **Data Tooltips**: Mouse hover displays coordinate and value information
- **Statistical Information**: Automatically calculates and displays min, max, mean values

### 🖼️ Image Export and Sharing
- **URL Copying**: Get image URLs through Image Info
- **Path Information**: View local file paths
- **Snapshot Function**: Right-click in browser to save current view

### ⏱️ Time Series Analysis
- **Playback Mode**: Automatically play time series to observe data changes
- **Precise Positioning**: Precisely select specific time points through timeline
- **Multi-Resolution**: Support different time granularities from hours to months

## 🔧 Technical Features

### Performance Optimization
- **Data Sampling**: Interactive mode automatically samples large datasets
- **Smart Caching**: Automatically cache loaded images
- **On-Demand Loading**: Only load data for currently displayed time points

### Responsive Design
- **Adaptive Layout**: Support different screen sizes
- **Fullscreen Support**: Each map can be independently fullscreen
- **Mobile Friendly**: Support touch operations

### Data Consistency
- **Unified Timeline**: All maps share the same time control
- **Synchronized Updates**: All maps update simultaneously when time changes
- **State Persistence**: Maintain user settings after page refresh

## 🚨 Important Notes

### Data Availability
- Different satellites may have different data availability times
- Some time points may have no data, system will display "No data available"
- Canvas mode may display closest available data

### Performance Recommendations
- Displaying 4 maps simultaneously may affect performance
- Large datasets are recommended to be viewed in Static mode
- Reduce number of simultaneously displayed maps when network is slow

### Browser Compatibility
- Recommended modern browsers: Chrome, Firefox, Safari
- JavaScript must be enabled
- Latest browser versions recommended for optimal experience

---

*Last Updated: March 2025*
*Version: 1.0*
