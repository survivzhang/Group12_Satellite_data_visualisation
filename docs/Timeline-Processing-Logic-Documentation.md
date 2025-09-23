# Satellite Data Visualization System - Timeline Processing Logic Documentation

## 📋 Overview

This document provides a detailed explanation of the timeline processing logic for static images in the satellite data visualization system, covering different time processing strategies for two major satellite data sources (Himawari and Sentinel-3).

## 🛰️ Supported Satellite Data Sources

| Satellite | Parameter Code | Data Type | Time Precision | File Format |
|-----------|----------------|-----------|----------------|-------------|
| Himawari-9 | `ssth` | Sea Surface Temperature | 1-hour intervals | `YYYYMMDDHHMMSS.png` |
| Sentinel-3A | `sst-s3a` | Sea Surface Temperature | Irregular intervals | `YYYYMMDD_HHMMSS.png` |
| Sentinel-3A | `chl-s3a` | Chlorophyll Concentration | Irregular intervals | `YYYYMMDD_HHMMSS.png` |
| Sentinel-3B | `sst-s3b` | Sea Surface Temperature | Irregular intervals | `YYYYMMDD_HHMMSS.png` |
| Sentinel-3B | `chl-s3b` | Chlorophyll Concentration | Irregular intervals | `YYYYMMDD_HHMMSS.png` |

## 🔄 Timeline Processing Workflow

### Overall Process Flow
```
User Time Selection → Frontend Timestamp Generation → File Matching Algorithm → Return Corresponding PNG → Display Image
```

## 1️⃣ Himawari-9 Time Processing Logic

### Data Characteristics
- **Collection Interval**: Every hour on the hour (e.g., 00:00, 01:00, 02:00)
- **Data Delay**: 4-hour processing delay
- **Time Precision**: Hour-level (minutes and seconds always 00)

### Frontend Timestamp Generation
```typescript
// User selected time: 2025-03-31 15:26:24
const utcDate = new Date(timeRange.start.getTime());
utcDate.setUTCMinutes(0, 0, 0); // Force to hour mark: 15:00:00

// Generate timestamp format: YYYYMMDDHHMMSS
const year = utcDate.getUTCFullYear();        // 2025
const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");  // 03
const day = String(utcDate.getUTCDate()).padStart(2, "0");         // 31
const hour = String(utcDate.getUTCHours()).padStart(2, "0");       // 15
return `${year}${month}${day}${hour}0000`;    // 20250331150000
```

### File Matching Algorithm
```typescript
// Exact matching strategy - find file containing timestamp
const targetFile = files.find(file => 
  file.filename && file.filename.startsWith(currentTimestamp)
);
// Example: Search for "20250331150000.png"
```

### File Naming Convention
- **NC File**: `20250331150000.nc`
- **PNG File**: `20250331150000.png`
- **Storage Path**: `/static/himawari/sst/png/20250331150000.png`

### Processing Example
```
User Selection: 2025-03-31 15:26:24
↓
Frontend Processing: 2025-03-31 15:00:00
↓
Generate Timestamp: 20250331150000
↓
File Matching: 20250331150000.png
↓
Display Image: Himawari 15:00 Sea Surface Temperature Data
```

## 2️⃣ Sentinel-3 Time Processing Logic

### Data Characteristics
- **Collection Interval**: Irregular time intervals
- **Data Source**: Multiple time points contained in a single NC file
- **Time Precision**: Second-level precision

### Frontend Timestamp Generation
```typescript
// User selected time: 2025-03-31 15:26:24
const utcDate = new Date(timeRange.start.getTime());
// Keep user's exact selected time, no forcing to hour marks

// Generate timestamp format: YYYYMMDD_HHMMSS
const year = utcDate.getUTCFullYear();        // 2025
const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");  // 03
const day = String(utcDate.getUTCDate()).padStart(2, "0");         // 31
const hour = String(utcDate.getUTCHours()).padStart(2, "0");       // 15
const minute = String(utcDate.getUTCMinutes()).padStart(2, "0");   // 26
const second = String(utcDate.getUTCSeconds()).padStart(2, "0");   // 24
return `${year}${month}${day}_${hour}${minute}${second}`;  // 20250331_152624
```

### File Matching Algorithm
```typescript
// Nearest time matching strategy - find closest image before selected time
let bestFile = null;
let bestTimeDiff = Infinity;

for (const file of files) {
  const fileTime = extractTimeFromSentinel3Filename(file.filename);
  // Only consider files before the selected time
  if (fileTime && fileTime.getTime() <= selectedTime.getTime()) {
    const timeDiff = selectedTime.getTime() - fileTime.getTime();
    if (timeDiff < bestTimeDiff) {
      bestTimeDiff = timeDiff;
      bestFile = file;
    }
  }
}
```

### Time Extraction Function
```typescript
const extractTimeFromSentinel3Filename = (filename: string): Date | null => {
  // File format: YYYYMMDD_HHMMSS.png
  const timeMatch = filename.match(/(\d{8})_(\d{6})\.png$/);
  if (timeMatch) {
    const dateStr = timeMatch[1]; // YYYYMMDD
    const timeStr = timeMatch[2]; // HHMMSS
    
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    const hour = timeStr.substring(0, 2);
    const minute = timeStr.substring(2, 4);
    const second = timeStr.substring(4, 6);
    
    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}Z`);
  }
  return null;
};
```

### File Naming Convention
- **NC File**: `20250923_211031.nc` (contains multiple time points)
- **PNG Files**: `20250331_152000.png`, `20250331_152630.png`, `20250331_153145.png`...
- **Storage Path**: `/static/sentinel3a/sst/png/20250331_152630.png`

### Processing Example
```
User Selection: 2025-03-31 15:26:24
↓
Frontend Processing: Keep 2025-03-31 15:26:24
↓
Generate Timestamp: 20250331_152624
↓
File Matching: Find nearest historical file
  Available Files: 20250331_152000.png, 20250331_152630.png, 20250331_153145.png
  Selected Result: 20250331_152000.png (15:20:00, nearest historical file)
↓
Display Image: Sentinel-3 15:20 Sea Surface Temperature Data
```

## 🔍 Strategy Comparison

| Feature | Himawari | Sentinel-3 |
|---------|----------|------------|
| **Time Processing** | Frontend force to hour marks | Keep user's exact time |
| **Matching Strategy** | Exact match to hourly files | Nearest historical time match |
| **Data Intervals** | Fixed 1-hour intervals | Irregular time intervals |
| **File Relationship** | 1:1 (one NC per PNG) | 1:N (one NC to multiple PNGs) |
| **Timestamp Format** | `YYYYMMDDHHMMSS` (last 6 digits: 000000) | `YYYYMMDD_HHMMSS` (precise to second) |
| **User Experience** | Timeline jumps to hour marks | Smooth timeline transition |

## 📊 Core Implementation Code

### Generic File Finding Function
```typescript
const findBestFileForTime = (files: any[], selectedTime: Date) => {
  if (parameter === "ssth") {
    // Himawari: Exact matching strategy
    return files.find(file => 
      file.filename && file.filename.startsWith(currentTimestamp)
    );
  } else {
    // Sentinel-3: Nearest time matching strategy
    let bestFile = null;
    let bestTimeDiff = Infinity;

    for (const file of files) {
      const fileTime = extractTimeFromSentinel3Filename(file.filename);
      if (fileTime && fileTime.getTime() <= selectedTime.getTime()) {
        const timeDiff = selectedTime.getTime() - fileTime.getTime();
        if (timeDiff < bestTimeDiff) {
          bestTimeDiff = timeDiff;
          bestFile = file;
        }
      }
    }
    return bestFile;
  }
};
```

## 🎯 Design Principles

### Himawari Design Considerations
1. **Data Characteristics**: Himawari data is naturally collected on the hour
2. **Processing Simplification**: Avoid complex time interpolation
3. **User Expectations**: Hour-level precision is sufficient for oceanographic data
4. **System Performance**: Exact matching avoids search algorithm overhead

### Sentinel-3 Design Considerations
1. **Data Richness**: Sentinel-3 provides higher temporal resolution
2. **Optimal Experience**: Display data closest to user's selected time
3. **Historical Principle**: Avoid displaying "future" data
4. **Data Continuity**: Support smooth playback of time series

## 🔮 System Advantages

1. **Intelligent Adaptation**: Adopt optimal strategies based on different satellite characteristics
2. **User-Friendly**: Automatically handle complex time matching logic
3. **Data Integrity**: Ensure displayed data matches the timeline
4. **Performance Optimization**: Efficient file searching algorithms
5. **Extensibility**: Easy to add new satellite data sources

## 3️⃣ Canvas Interactive Map Time Processing Logic

### System Architecture Overview
Canvas interactive map time processing adopts a **Frontend Timestamp Generation + Backend Time Slice Extraction** hybrid strategy, combining static image file location logic with real-time data processing capabilities.

### Data Flow Diagram
```
User Time Selection → Frontend Timestamp Generation → NC File Location → Backend Time Slice Extraction → Canvas Heatmap Rendering
```

## 1️⃣ Himawari Canvas Time Processing

### Frontend Timestamp Generation (Same as Static Images)
```typescript
// User selected time: 2025-03-31 15:26:24
const utcDate = new Date(timeRange.start.getTime());
utcDate.setUTCMinutes(0, 0, 0); // Force to hour mark: 15:00:00

// Generate Himawari timestamp: YYYYMMDDHHMMSS
const year = utcDate.getUTCFullYear();        // 2025
const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");  // 03
const day = String(utcDate.getUTCDate()).padStart(2, "0");         // 31
const hour = String(utcDate.getUTCHours()).padStart(2, "0");       // 15
return `${year}${month}${day}${hour}0000`;    // 20250331150000
```

### NC File Location
```typescript
// Canvas uses same filename logic as static images
const ncFilename = `${currentTimestamp}.nc`; // 20250331150000.nc
```

### Backend Data Processing
```typescript
// API call - pass target time to backend
const targetTime = timeRange.start.toISOString(); // 2025-03-31T15:26:24.000Z
const apiUrl = `http://localhost:8000/api/v1/satellites/himawari/sst/simple-data/20250331150000.nc?target_time=${encodeURIComponent(targetTime)}`;
```

### Backend Time Slice Extraction
```python
# Backend processing logic (simplified)
if len(data_var.shape) > 2:  # Multi-time dimension data
    if target_time:
        target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
        time_coords = ds['time'].values
        # Find closest time index
        time_diffs = [abs((t - target_dt).total_seconds()) for t in time_coords]
        closest_time_idx = np.argmin(time_diffs)
        data = data_var.values[closest_time_idx]  # Extract corresponding time slice
    else:
        data = find_first_valid_timepoint(data_var)  # Default first valid time point
else:
    data = data_var.values  # Single time data
```

### Canvas Processing Example
```
User Selection: 2025-03-31 15:26:24
↓
Frontend Timestamp: 20250331150000
↓
NC File: 20250331150000.nc
↓
Target Time: 2025-03-31T15:26:24.000Z
↓
Backend Processing: Extract closest time slice to 15:26:24 from NC file
↓
Canvas Rendering: Generate heatmap based on extracted data (Canvas → ImageURL → ImageOverlay)
```

## 2️⃣ Sentinel-3 Canvas Time Processing

### Frontend Timestamp Generation (Same as Static Images)
```typescript
// User selected time: 2025-03-31 15:26:24
const utcDate = new Date(timeRange.start.getTime());
// Keep exact time, no forcing to hour marks

// Generate Sentinel-3 timestamp: YYYYMMDD_HHMMSS
const year = utcDate.getUTCFullYear();        // 2025
const month = String(utcDate.getUTCMonth() + 1).padStart(2, "0");  // 03
const day = String(utcDate.getUTCDate()).padStart(2, "0");         // 31
const hour = String(utcDate.getUTCHours()).padStart(2, "0");       // 15
const minute = String(utcDate.getUTCMinutes()).padStart(2, "0");   // 26
const second = String(utcDate.getUTCSeconds()).padStart(2, "0");   // 24
return `${year}${month}${day}_${hour}${minute}${second}`;  // 20250331_152624
```

### NC File Location
```typescript
// Canvas uses dynamic NC file retrieval (different from static images)
const getNcFilename = async () => {
  try {
    const ncFiles = await getParameterFiles(parameter, "nc");
    if (ncFiles && ncFiles.length > 0) {
      return ncFiles[0].filename; // Use latest NC file
    } else {
      return getSentinel3FallbackFilename(parameter); // Use fallback file
    }
  } catch (error) {
    return getSentinel3FallbackFilename(parameter);
  }
};
```

### Backend Sentinel-3 Specific Processing
```python
# Sentinel-3 specific time processing logic
if satellite in ['sentinel3a', 'sentinel3b']:
    sentinel3_api = get_sentinel3_api()
    time_coords = ds['time'].values
    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
    # Sentinel-3 API internally implements intelligent time matching
```

### Canvas Processing Example
```
User Selection: 2025-03-31 15:26:24
↓
Frontend Timestamp: 20250331_152624 (for display logging)
↓
NC File Retrieval: Dynamic fetch of latest NC file (e.g., 20250923_211031.nc)
↓
Target Time: 2025-03-31T15:26:24.000Z
↓
Backend Sentinel-3 Processing: Use specialized API to intelligently extract best matching time slice from multi-temporal data
↓
Canvas Rendering: Generate heatmap based on extracted data
```

## 🔄 Canvas vs Static Image Time Processing Comparison

| Feature | Static Image Processing | Canvas Interactive Processing |
|---------|------------------------|------------------------------|
| **Frontend Timestamp** | Generated for file matching | Generated for display and transmission |
| **File Location** | PNG file exact matching | NC file dynamic retrieval |
| **Backend Processing** | Direct return of pre-generated PNG | Real-time NC time slice extraction |
| **Time Precision** | Limited by PNG file availability | Limited by NC data time dimensions |
| **Data Freshness** | Depends on PNG generation time | Real-time extraction from raw NC data |
| **Performance Characteristics** | Fast file serving | Real-time data processing |

## 🎯 Canvas Time Processing Core Code

### Frontend Data Loading
```typescript
const loadMapData = useCallback(async () => {
  try {
    setIsLoading(true);
    
    // 1. Get NC filename (dynamic or fixed)
    const ncFilename = await getNcFilename();
    
    // 2. Build API request - Key: pass target_time
    const targetTime = timeRange.start.toISOString();
    const apiUrl = `http://localhost:8000/api/v1/satellites/${satelliteMapping.satellite}/${satelliteMapping.parameter}/simple-data/${ncFilename}?target_time=${encodeURIComponent(targetTime)}`;
    
    // 3. Get processed data
    const response = await fetch(apiUrl);
    const data = await response.json();
    setNCData(data);
    
  } catch (error) {
    setError(error.message);
  } finally {
    setIsLoading(false);
  }
}, [satelliteMapping, getNcFilename, timeRange.start]);
```

### Backend Time Slice Extraction
```python
def get_simple_nc_data(satellite, parameter, filename, target_time=None):
    with xr.open_dataset(file_path) as ds:
        # Find data variable
        data_var = find_data_variable(ds, parameter)
        
        # Handle multi-time dimension data
        if len(data_var.shape) > 2:
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Sentinel-3 specific processing
                data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
            else:
                # Himawari general processing
                if target_time:
                    target_dt = datetime.fromisoformat(target_time)
                    closest_time_idx = find_closest_time_index(time_coords, target_dt)
                    data = data_var.values[closest_time_idx]
                else:
                    data = find_first_valid_timepoint(data_var)
        else:
            data = data_var.values
            
        return {
            "data": data.tolist(),
            "lats": lats.tolist(), 
            "lons": lons.tolist(),
            "min_value": float(np.min(valid_data)),
            "max_value": float(np.max(valid_data)),
            # ... other metadata
        }
```

## 💡 Canvas Time Processing Advantages

### 1. **Data Freshness**
- Direct real-time extraction from raw NC files
- No dependency on pre-generated PNG files
- Support for precise data queries at any time point

### 2. **Time Precision Enhancement**
- **Himawari**: Improved from hour-level to actual time precision within NC files
- **Sentinel-3**: Full utilization of high temporal resolution data

### 3. **Data Consistency**
- Canvas and static images use the same NC data sources
- Visual consistency ensured through identical color mapping
- Unified backend time processing logic

### 4. **System Flexibility**
- Support for dynamic time queries
- Easy to extend new time processing strategies
- Decoupled frontend-backend time processing architecture

## 🔮 Technical Innovation Points

1. **Hybrid Time Strategy**: Combines static image file location with real-time data time slicing
2. **Intelligent Fallback Mechanism**: Sentinel-3's dynamic NC file retrieval + fallback strategy
3. **Canvas Real-time Rendering**: Efficient Canvas → ImageURL → ImageOverlay rendering pipeline
4. **Time Dimension Decoupling**: Frontend handles timestamp generation, backend handles time slice extraction

## ⚠️ Critical Discovery: Time Processing Differences Between Static Images and Canvas

### 📊 Key Problem Description

Under identical time selections, **static images show "no data available" while Canvas displays data normally**. This phenomenon stems from fundamentally different time matching principles employed by the two systems.

### 🔍 Phenomenon Analysis Example

#### Actual Observed Scenario
```
User Selected Time: 2025-03-01 09:12 AM
├── Static Image Result: "No satellite data for 20250301_010000"
└── Canvas Result: Normal display of chlorophyll concentration heatmap
```

#### NC File Content Assumption
```
NC File: 20250923_211031.nc contains multiple time slices:
├── 2025-03-02 14:30:00 (has valid data)
├── 2025-03-03 08:15:00 (has valid data)  
├── 2025-03-04 16:45:00 (has valid data)
└── ... more time points
```

### 🎯 Fundamental Difference: Time Matching Strategies

| Feature | Static Image Strategy | Canvas Strategy |
|---------|----------------------|-----------------|
| **Matching Principle** | Strict historical principle | Nearest time principle + intelligent fallback |
| **Time Constraint** | Only select data ≤ user selected time | Select closest data to user time (regardless of before/after) |
| **When No Match** | Display "no data available" | Auto fallback to first valid time point |
| **Data Source** | Pre-generated PNG files | Any time slice within NC files |

### 📋 Detailed Processing Logic Comparison

#### 1️⃣ Static Images: Strict Historical Matching
```typescript
// Frontend file search logic
const findBestFileForTime = (files, selectedTime) => {
  let bestFile = null;
  let bestTimeDiff = Infinity;

  for (const file of files) {
    const fileTime = extractTimeFromSentinel3Filename(file.filename);
    
    // 🔑 Key constraint: only consider historical files
    if (fileTime && fileTime.getTime() <= selectedTime.getTime()) {
      const timeDiff = selectedTime.getTime() - fileTime.getTime();
      if (timeDiff < bestTimeDiff) {
        bestTimeDiff = timeDiff;
        bestFile = file;
      }
    }
  }
  
  // May return null, causing "No data available"
  return bestFile;
};
```

**Result**: User selects 2025-03-01, but all PNGs are after 2025-03-02, so returns null.

#### 2️⃣ Canvas: Intelligent Time Matching + Fallback Mechanism
```python
# Backend time slice extraction logic
def get_sentinel3_data(data_var, target_time=None, time_coords=None):
    if target_time and time_coords is not None:
        try:
            target_dt = datetime.fromisoformat(target_time)
            
            # 🔑 Key difference: find closest time (regardless of before/after)
            time_diffs = [abs((t - target_dt).total_seconds()) for t in time_coords]
            closest_time_idx = np.argmin(time_diffs)
            data = data_array[closest_time_idx]
            
            # Check data validity
            valid_data = data[~np.isnan(data)]
            if len(valid_data) == 0:
                # 🛡️ Intelligent fallback: use first valid time point
                return find_first_valid_timepoint(data_var)
            else:
                return data
                
        except Exception:
            # 🛡️ Exception fallback: use first valid time point
            return find_first_valid_timepoint(data_var)
    else:
        # 🛡️ Default fallback: use first valid time point
        return find_first_valid_timepoint(data_var)

def find_first_valid_timepoint(data_var):
    """Ensure always returning valid data"""
    for i in range(data_var.shape[0]):
        time_data = data_var.values[i]
        valid_data = time_data[~np.isnan(time_data)]
        if len(valid_data) > 0:
            return time_data  # Return first time slice with data
    
    return data_var.values[0]  # Fallback return
```

**Result**: User selects 2025-03-01, system finds closest 2025-03-02 data and displays it.

### 💡 Design Philosophy Comparison

#### 🎯 Static Image Design Principles
- **Time Accuracy Priority**: Ensure displayed data strictly corresponds to user selected time
- **Scientific Rigor**: Follow "don't show future events" scientific principle
- **Precise Matching**: One-to-one time-image mapping relationship
- **User Expectation**: Conform to traditional data analysis tool behavior

#### 🎨 Canvas Design Principles  
- **Data Availability Priority**: Prioritize ensuring users can see relevant data
- **User Experience**: Avoid "no data" blank interfaces
- **Intelligent Matching**: Select most relevant content from available data
- **Fault Tolerance**: Multiple fallback mechanisms ensure system stability

### 🚨 Potential Issues and Risks

#### 1. **Time Misleading**
- **Issue**: Canvas may display "future" data while UI shows historical time
- **Risk**: Users may mistakenly believe that time point actually has data
- **Impact**: Scientific analysis accuracy is affected

#### 2. **Data Consistency**
- **Issue**: Same time point shows different results in different views
- **Risk**: User confusion, decreased system credibility
- **Impact**: User experience and system professionalism

#### 3. **Time Traceability Difficulty**
- **Issue**: Canvas displayed data is difficult to trace to specific time points
- **Risk**: Cannot perform precise time series analysis
- **Impact**: Reduced research and analysis value

### 🔧 Optimization Recommendations

#### Solution 1: Unified Time Matching Strategy
```typescript
// Recommendation: Add strict historical mode for Canvas
const canvasTimeMode = {
  strict: "only_historical_data",    // Strict historical mode (consistent with static images)
  smart: "closest_available_data",   // Intelligent matching mode (current mode)
  hybrid: "historical_with_indicator" // Hybrid mode (prioritize historical, annotate non-historical)
};
```

#### Solution 2: Transparent Time Information
```typescript
// Recommendation: Canvas displays actual data time
const dataTimeIndicator = {
  selectedTime: "2025-03-01 09:12:00",
  actualDataTime: "2025-03-02 14:30:00", // Actual displayed data time
  timeOffset: "+1 day 5 hours 18 minutes",
  isHistorical: false
};
```

#### Solution 3: Configurable Time Strategy
```typescript
// Recommendation: User selectable time matching mode
interface TimeMatchingConfig {
  mode: "strict" | "smart" | "hybrid";
  maxTimeOffset?: number; // Maximum allowed time offset (hours)
  showTimeIndicator?: boolean; // Whether to show time offset indicator
  fallbackBehavior?: "show_empty" | "show_closest" | "show_first_valid";
}
```

### 📈 Specific Implementation Recommendations

#### 1. **Short-term Optimization (Backward Compatible)**
- Add actual data time display in Canvas interface
- Add warning prompts when displaying non-target time data
- Provide "strict mode" toggle, consistent with static image behavior

#### 2. **Medium-term Optimization (Feature Enhancement)**
- Implement configurable time matching strategies
- Add visual indicators for time offset amounts
- Provide time range search functionality

#### 3. **Long-term Optimization (Architecture Refactoring)**
- Unify frontend-backend time processing framework
- Implement intelligent time recommendation system
- Add data coverage range visualization

### 🎯 Developer Notes

1. **Understand Differences**: New developers must understand different behaviors of two time systems
2. **Test Coverage**: Conduct thorough testing for boundary time points
3. **Documentation Updates**: Timely update user documentation explaining time processing logic
4. **Monitoring Metrics**: Add monitoring and alerting for time offset amounts
5. **User Feedback**: Collect user feedback on time processing behavior

---

*Last Updated: March 2025*
*Version: 1.2 - Added Static Image vs Canvas Time Processing Difference Analysis and Optimization Recommendations*
