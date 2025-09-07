# Refactored Satellite API Structure

## Overview

This document describes the new refactored API structure that consolidates multiple satellite APIs into a single, unified global API while maintaining clean separation of concerns and eliminating code duplication.

## Problems Solved

### Before Refactoring:
- ❌ Multiple duplicate `api_example.py` files
- ❌ Repeated FastAPI setup, CORS middleware, and similar endpoints
- ❌ Redundant Pydantic models across APIs
- ❌ Complex import handling in root API
- ❌ Difficult to maintain and extend

### After Refactoring:
- ✅ Single global API entry point (`api.py`)
- ✅ Shared utilities and models
- ✅ Clean satellite-specific modules
- ✅ No code duplication
- ✅ Easy to extend with new satellites

## New Architecture

```
/
├── api.py                          # 🌟 Global API entry point
├── satellites/                     # 📁 Satellite modules
│   ├── shared/                     # 🔧 Shared utilities
│   │   ├── models.py              # 📋 Common Pydantic models
│   │   ├── utils.py               # 🛠️ Utility functions
│   │   └── base_api.py            # 🏗️ Base API class
│   ├── himawari/                   # 🛰️ Himawari module
│   │   └── api.py                 # Himawari-specific API
│   └── sentinel3/                  # 🛰️ Sentinel-3 module
│       └── api.py                 # Sentinel-3 specific API
├── get_data/                       # 📊 Original data processors
│   ├── himawari_test_data/
│   │   └── himawari_processor.py  # Himawari business logic
│   └── saternal3/
│       └── usingtheEumetview.py   # Sentinel-3 business logic
└── [old api_example.py files]     # 🗑️ Can be removed
```

## Key Components

### 1. Global API (`api.py`)
- **Single entry point** for all satellite data
- **Unified endpoints** for consistent access
- **Proxy routing** to satellite-specific functionality
- **Error handling** and response standardization

### 2. Shared Modules (`satellites/shared/`)
- **`models.py`**: Common Pydantic models used across all satellites
- **`utils.py`**: Utility functions (file handling, system info, validation)
- **`base_api.py`**: Abstract base class defining the satellite API interface

### 3. Satellite-Specific APIs (`satellites/{satellite}/`)
- **Clean interfaces** that implement the base API
- **Business logic delegation** to existing processors
- **Satellite-specific handling** while maintaining consistency

## API Endpoints

### Unified Endpoints
```
GET  /                              # API overview
GET  /health                        # Global health check
GET  /system/status                 # Unified system status

# Satellite management
GET  /api/v1/satellites             # List all satellites
GET  /api/v1/satellites/{satellite} # Satellite info
GET  /api/v1/satellites/{satellite}/{parameter}  # Parameter info

# Data access
GET  /api/v1/satellites/{satellite}/{parameter}/{file_type}  # List files
GET  /api/v1/satellites/{satellite}/{parameter}/nc/{filename}  # Download NC
POST /api/v1/process                # Process data (any satellite)
GET  /tasks/{satellite}/{task_id}   # Task status
```

### Satellite-Specific Endpoints (Proxied)
```
# Himawari-specific
GET/POST /himawari/*                # All Himawari endpoints

# Sentinel-3 specific  
GET/POST /sentinel3/*               # All Sentinel-3 endpoints
```

## Usage Examples

### 1. List All Satellites
```bash
curl http://localhost:8000/api/v1/satellites
```

### 2. Get Himawari Files
```bash
curl http://localhost:8000/api/v1/satellites/himawari/sst/nc
```

### 3. Process Sentinel-3 Data
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "satellite": "sentinel3a",
    "parameter": "sst",
    "start_time": "2025-03-01T00:00:00",
    "end_time": "2025-03-01T12:00:00",
    "west_lon": 113.0,
    "east_lon": 115.0,
    "south_lat": -24.0,
    "north_lat": -21.0
  }'
```

### 4. Use Satellite-Specific Features
```bash
# Himawari file repair
curl -X POST http://localhost:8000/himawari/repair-files \
  -H "Content-Type: application/json" \
  -d '{...}'

# Sentinel-3 layer info
curl http://localhost:8000/sentinel3/layers
```

## Migration Guide

### For API Users:
1. **Update base URL**: Change from satellite-specific ports to single port 8000
2. **Use unified endpoints**: Replace satellite-specific endpoints with `/api/v1/satellites/*`
3. **Satellite-specific features**: Use proxy endpoints (`/himawari/*`, `/sentinel3/*`)

### For Developers:
1. **Remove old API files**: The individual `api_example.py` files can be deleted
2. **Extend new satellites**: Implement `BaseSatelliteAPI` and add to `SATELLITES` config
3. **Shared functionality**: Add common features to `satellites/shared/`

## Benefits

### 🚀 **Performance**
- Single server instance instead of multiple
- Shared resources and connection pooling
- Reduced memory footprint

### 🛠️ **Maintainability**
- No code duplication
- Centralized configuration
- Consistent error handling
- Easier testing

### 📈 **Scalability**
- Easy to add new satellites
- Shared infrastructure
- Unified monitoring and logging

### 👥 **Developer Experience**
- Single API to learn
- Consistent patterns
- Better documentation
- Unified authentication

## Running the New API

### 1. Start the Global API
```bash
cd /path/to/project
python api.py
```

### 2. Access Documentation
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API overview**: http://localhost:8000/

### 3. Check System Status
```bash
curl http://localhost:8000/system/status
```

## Future Extensions

### Adding New Satellites
1. Create `satellites/{new_satellite}/api.py`
2. Implement `BaseSatelliteAPI`
3. Add to `SATELLITES` config in `api.py`
4. Update static file mounting if needed

### Adding New Features
1. **Shared features**: Add to `satellites/shared/`
2. **Satellite-specific**: Add to respective satellite module
3. **Global features**: Add to main `api.py`

## Backward Compatibility

The new API maintains backward compatibility through:
- **Proxy endpoints**: Old satellite-specific endpoints still work
- **Same data formats**: Response formats remain consistent
- **Graceful fallbacks**: Handles missing modules gracefully

## Testing

### Health Checks
```bash
# Global health
curl http://localhost:8000/health

# Satellite-specific health
curl http://localhost:8000/himawari/health
curl http://localhost:8000/sentinel3/health
```

### System Status
```bash
curl http://localhost:8000/system/status
```

### File Listings
```bash
# Unified approach
curl http://localhost:8000/api/v1/satellites/himawari/sst/png

# Satellite-specific approach  
curl http://localhost:8000/himawari/visualizations
```

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure `himawari_processor.py` and `usingtheEumetview.py` are accessible
   - Check Python path configuration

2. **Static Files Not Serving**
   - Verify directory structure matches expected paths
   - Check file permissions

3. **Satellite Unavailable**
   - Check if underlying processor modules are working
   - Verify data directories exist

### Debug Mode
Run with debug logging:
```bash
python api.py --log-level debug
```

## Conclusion

The refactored API structure provides:
- **Unified access** to all satellite data sources
- **Clean separation** of concerns
- **No code duplication**
- **Easy extensibility** for new satellites
- **Backward compatibility** with existing clients

This architecture scales well and makes the satellite data platform much more maintainable and user-friendly.
