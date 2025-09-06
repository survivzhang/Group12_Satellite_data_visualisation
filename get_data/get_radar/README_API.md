# AODN HF Radar API Documentation

## Overview

The `aodn_hf_radar_api_example.py` provides a FastAPI-based REST API for processing AODN HF Radar current data, following the same design patterns as the Himawari satellite data API.

## Key Differences from Himawari API

### 1. Data Structure Differences

**Himawari (Time-series based):**
- Processes data by time ranges (start_time, end_time)
- Downloads individual timestamp files
- Merges time series into single NetCDF files

**HF Radar (Month-based):**
- Processes data by year/month combinations
- Downloads monthly collections of hourly files
- Optionally combines daily files
- Creates animated GIFs from time series

### 2. Request Parameters

**Himawari ProcessingRequest:**
```python
start_time: str  # ISO format
end_time: str
west_lon: float
east_lon: float
south_lat: float
north_lat: float
time_step_hours: int = 1
```

**HF Radar ProcessingRequest:**
```python
year: int
month: int
region: str = "NWA"  # Region code instead of coordinates
qc_dir: str = "gridded_1h-avg-current-map_non-QC"
west_lon: float = 111.0  # For visualization bounds only
east_lon: float = 114.0
south_lat: float = -25.0
north_lat: float = -20.0
download: bool = True
combine_daily: bool = False
make_gif: bool = True
step: int = 1
gif_duration: float = 0.4
```

### 3. File Organization

**Himawari:**
- `temp/` - Temporary downloads
- `parts/` - Processed individual files
- `png/` - Visualizations
- `merged_sst.nc` - Final merged file

**HF Radar:**
- `DATA/RAW/` - Downloaded hourly files (preserves S3 structure)
- `DATA/DAILY/` - Optional daily combined files
- `PNG/` - Individual frame visualizations
- `GIF/` - Monthly animation files

### 4. Visualization Differences

**Himawari:**
- Creates static PNG images of SST data
- Uses turbo colormap for temperature

**HF Radar:**
- Creates quiver plots showing current vectors
- Generates animated GIFs showing current evolution
- Uses speed colormap (cmocean.speed if available)
- Supports Cartopy for geographic projections

## API Endpoints

### Core Endpoints

1. **GET /** - API information
2. **GET /health** - Health check
3. **POST /query-data** - Query available data keys
4. **POST /process-data** - Start processing task
5. **GET /status/{task_id}** - Check processing status
6. **GET /files** - List processed files
7. **GET /visualizations** - List PNG/GIF files
8. **POST /check-files** - Check file integrity
9. **POST /repair-files** - Repair missing files
10. **GET /system-status** - System health metrics

### Static File Serving

- `/static/images/` - PNG visualizations
- `/static/gifs/` - GIF animations

## Key Assumptions Made

### 1. Region-based Processing
- Assumed region codes like "NWA" (North West Australia) are standard
- Spatial bounds are used for visualization cropping, not data selection
- Data selection is primarily by region code in S3 structure

### 2. File Structure Assumptions
- Raw files follow AODN S3 structure: `{region}/{YYYY}/{MM}/{DD}/*.nc`
- Daily files named: `ACORN_{region}_{YYYYMMDD}.nc`
- GIF files named: `HFRadar_{region}_{YYYY-MM}.gif`

### 3. Processing Workflow
- Downloads are anonymous (no authentication required)
- Daily combination is optional (default: false)
- GIF generation is default behavior
- Visualization bounds are separate from data query bounds

### 4. Error Handling
- S3 connectivity issues handled gracefully
- Missing data days are tracked and reported
- Corrupted files are detected during integrity checks

### 5. Background Processing
- Long-running operations use FastAPI BackgroundTasks
- Task status tracked in-memory (production should use Redis)
- Progress reporting for user feedback

## Usage Examples

### Query Available Data
```bash
curl -X POST "http://localhost:8001/query-data" \
     -H "Content-Type: application/json" \
     -d '{
       "year": 2025,
       "month": 8,
       "region": "NWA"
     }'
```

### Process Month Data
```bash
curl -X POST "http://localhost:8001/process-data" \
     -H "Content-Type: application/json" \
     -d '{
       "year": 2025,
       "month": 8,
       "region": "NWA",
       "west_lon": 111.0,
       "east_lon": 114.0,
       "south_lat": -25.0,
       "north_lat": -20.0,
       "make_gif": true
     }'
```

### Check File Integrity
```bash
curl -X POST "http://localhost:8001/check-files" \
     -H "Content-Type: application/json" \
     -d '{
       "year": 2025,
       "month": 8,
       "region": "NWA"
     }'
```

## Production Considerations

1. **Task Storage**: Replace in-memory task storage with Redis
2. **Authentication**: Add authentication for write operations
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Monitoring**: Add proper logging and metrics
5. **File Cleanup**: Implement automatic cleanup of old files
6. **Caching**: Cache S3 query results to reduce API calls
7. **Validation**: Add more comprehensive input validation
8. **Error Recovery**: Implement retry mechanisms for failed downloads

## Dependencies

- FastAPI
- Pydantic
- asyncio
- s3fs (for AODN S3 access)
- xarray
- matplotlib
- cartopy (optional, for geographic projections)
- cmocean (optional, for oceanographic colormaps)
- imageio (for GIF creation)

## Running the API

```bash
cd get_data/get_radar/
python aodn_hf_radar_api_example.py
```

The API will be available at `http://localhost:8001` with automatic documentation at `http://localhost:8001/docs`.
