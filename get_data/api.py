"""
Global Satellite Data API
========================

This is the main API entry point that consolidates all satellite data sources
into a unified interface. It imports and integrates satellite-specific modules
to provide a clean, consistent API.

Architecture:
- Global API routes for unified access
- Satellite-specific modules in /satellites/ folder  
- Shared base classes and utilities
- Clean separation of concerns

Supported Satellites:
- Himawari-9 (SST data)
- Sentinel-3A/3B (SST, Chlorophyll data)

API Structure:
/api/v1/satellites - List all satellites
/api/v1/satellites/{satellite} - Satellite info
/api/v1/satellites/{satellite}/{parameter}/{file_type} - Data files
/api/v1/process - Process data
/{satellite}/* - Satellite-specific endpoints (proxied)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
import importlib
import sys
from typing import Dict, List, Optional, Any

# Import Himawari processor (temporarily until full satellite API structure is ready)
import sys
sys.path.append('himawari_test_data')
from himawari_processor import HimawariDataProcessor, create_file_monitor

# Temporary models until proper satellite API structure
from pydantic import BaseModel
from typing import Dict, Any

class SatelliteInfo(BaseModel):
    name: str
    description: str
    available: bool
    parameters: Dict[str, Any]

class ParameterInfo(BaseModel):
    name: str
    unit: str
    description: str
    file_types: list

class ProcessingRequest(BaseModel):
    satellite: str
    parameter: str
    start_time: str
    end_time: str
    west_lon: float = 113.0
    east_lon: float = 115.0
    south_lat: float = -24.0
    north_lat: float = -21.0

class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    message: str
    progress: int = 0

class UnifiedSystemStatus(BaseModel):
    global_api: Dict[str, Any]
    satellites: Dict[str, Any]

# Initialize Himawari processor and API
himawari_processor = HimawariDataProcessor()
himawari_monitor = create_file_monitor()

# Global API instances to maintain task state
_himawari_api_instance = None
_sentinel3_api_instance = None

def get_himawari_api():
    """Get global HimawariAPI instance"""
    global _himawari_api_instance
    if _himawari_api_instance is None:
        from satellites.himawari.api import HimawariAPI
        _himawari_api_instance = HimawariAPI()
    return _himawari_api_instance

def get_sentinel3_api():
    """Get global Sentinel3API instance"""
    global _sentinel3_api_instance
    if _sentinel3_api_instance is None:
        from satellites.sentinel3.api import Sentinel3API
        _sentinel3_api_instance = Sentinel3API()
    return _sentinel3_api_instance

# Helper functions
def find_first_valid_timepoint(data_var):
    """Find the first time point with valid data"""
    import numpy as np
    
    if len(data_var.shape) <= 2:
        return data_var.values
    
    for i in range(data_var.shape[0]):
        time_data = data_var.values[i]
        valid_data = time_data[~np.isnan(time_data)]
        if len(valid_data) > 0:
            return time_data
    
    # If no valid data found, return first time point
    return data_var.values[0]

def get_parameter_units(parameter: str, satellite: str = None) -> str:
    """Get the correct units for a parameter"""
    if satellite in ['sentinel3a', 'sentinel3b']:
        # Use Sentinel-3 specific units
        sentinel3_api = get_sentinel3_api()
        return sentinel3_api.get_parameter_unit(parameter)
    else:
        # Use general units for other satellites
        if parameter == "sst":
            return "K"
        elif parameter == "chl":
            return "mg/m³"
        else:
            return "unknown"

def setup_data_directories():
    """Ensure all necessary data directories exist with unified structure"""
    from pathlib import Path
    
    # Unified data directory structure: data/{satellite}/{parameter}/{file_type}/
    base_data_dir = Path("data")
    
    # Himawari directories (unified structure)
    himawari_dirs = [
        base_data_dir / "himawari" / "sst" / "nc",
        base_data_dir / "himawari" / "sst" / "png",
        base_data_dir / "himawari" / "sst" / "temp"  # temp directory for processing
    ]
    
    # Sentinel-3 directories (unified structure)
    sentinel3_dirs = []
    for satellite in ['sentinel3a', 'sentinel3b']:
        for data_type in ['sst', 'chl']:
            sentinel3_dirs.extend([
                base_data_dir / satellite / data_type / "nc",
                base_data_dir / satellite / data_type / "png"
            ])
    
    # Create all directories
    all_dirs = himawari_dirs + sentinel3_dirs
    for directory in all_dirs:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"📁 Directory exists: {directory}")

def setup_static_files(app: FastAPI):
    """Setup static file serving for satellite data with unified structure"""
    from pathlib import Path
    
    # Unified data directory structure
    base_data_dir = Path("data")
    
    # Mount PNG files for all satellites using unified structure
    satellites_config = {
        'himawari': ['sst'],
        'sentinel3a': ['sst', 'chl'],
        'sentinel3b': ['sst', 'chl']
    }
    
    for satellite, parameters in satellites_config.items():
        for parameter in parameters:
            # Unified directory
            unified_png_dir = base_data_dir / satellite / parameter / "png"
            mount_path = f"/static/{satellite}/{parameter}/png"
            
            if unified_png_dir.exists():
                app.mount(mount_path, StaticFiles(directory=str(unified_png_dir)), name=f"{satellite}_{parameter}_png")
                print(f"✅ Mounted static files: {mount_path} -> {unified_png_dir}")
            else:
                print(f"⚠️ No PNG directory found for {satellite}/{parameter} - will create: {unified_png_dir}")
                unified_png_dir.mkdir(parents=True, exist_ok=True)

# Satellite registry (simplified for current implementation)
SATELLITES = {
    "himawari": {
        "name": "Himawari-9",
        "description": "Japanese geostationary weather satellite",
        "parameters": {
            "sst": {
                "name": "Sea Surface Temperature",
                "unit": "Kelvin",
                "description": "Ocean surface temperature data"
            }
        }
    },
    "sentinel3a": {
        "name": "Sentinel-3A",
        "description": "European ocean and land monitoring satellite",
        "parameters": {
            "sst": {
                "name": "Sea Surface Temperature",
                "unit": "Kelvin", 
                "description": "Ocean surface temperature data"
            },
            "chl": {
                "name": "Chlorophyll Concentration",
                "unit": "mg/m³",
                "description": "Ocean chlorophyll concentration data"
            }
        }
    },
    "sentinel3b": {
        "name": "Sentinel-3B", 
        "description": "European ocean and land monitoring satellite",
        "parameters": {
            "sst": {
                "name": "Sea Surface Temperature",
                "unit": "Kelvin",
                "description": "Ocean surface temperature data"
            },
            "chl": {
                "name": "Chlorophyll Concentration", 
                "unit": "mg/m³",
                "description": "Ocean chlorophyll concentration data"
            }
        }
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the application on startup"""
    print("🚀 Starting Global Satellite Data API v2.0...")
    
    # Ensure data directories exist
    setup_data_directories()
    
    # Setup static file serving for all satellites
    setup_static_files(app)
    
    # Check satellite availability
    print("📡 Checking satellite availability:")
    for satellite_id, config in SATELLITES.items():
        try:
            # For now, mark as available since we don't have the satellite APIs yet
            available = True  # await config["api"].is_available()
            status = "✅" if available else "❌"
            print(f"   {status} {satellite_id}: {config['name']}")
        except Exception as e:
            print(f"   ❌ {satellite_id}: Error - {e}")
    
    print("\n🔗 API endpoints ready:")
    print("   📊 Unified API: /api/v1/satellites")
    print("   🛰️ Himawari API: /himawari/*")
    print("   🛰️ Sentinel-3 API: /sentinel3/*")
    print("   ⚡ System Status: /system/status")
    print("   🏥 Health Check: /health")
    print("   🖼️ Static Files: /static/himawari/sst/png")
    print("   🖼️ Static Files: /static/sentinel3a/{sst,chl}/png")
    print("   🖼️ Static Files: /static/sentinel3b/{sst,chl}/png")
    print("   📚 Documentation: /docs")
    
    
    yield  # Application runs here
    
    # Cleanup on shutdown (if needed)
    print("🛑 Shutting down Global Satellite Data API...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Global Satellite Data API",
    description="Unified API for accessing multiple satellite data sources",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global API Routes

@app.get("/")
async def root():
    """API root with overview of all satellites and endpoints"""
    return {
        "message": "Global Satellite Data API",
        "version": "2.0.0",
        "architecture": "Unified API with satellite-specific modules",
        "satellites": {
            satellite_id: {
                "name": config["name"],
                "available": True,  # Simplified for now
                "parameters": list(config["parameters"].keys())
            }
            for satellite_id, config in SATELLITES.items()
        },
        "endpoints": {
            "unified": {
                "satellites": "/api/v1/satellites",
                "satellite_info": "/api/v1/satellites/{satellite}",
                "parameter_info": "/api/v1/satellites/{satellite}/{parameter}",
                "files": "/api/v1/satellites/{satellite}/{parameter}/{file_type}",
                "process": "/api/v1/process"
            },
            "satellite_specific": {
                "himawari": "/himawari/*"
            },
            "system": {
                "health": "/health",
                "system_status": "/system/status"
            },
            "static": {
                "himawari_png": "/static/himawari/sst/png"
            }
        }
    }

@app.get("/health")
async def health_check():
    """Global health check"""
    satellite_health = {}
    for satellite_id, config in SATELLITES.items():
        try:
            # Simple health check for now
            satellite_health[satellite_id] = {
                "status": "healthy",
                "name": config["name"],
                "available": True
            }
        except Exception as e:
            satellite_health[satellite_id] = {"status": "error", "error": str(e)}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "satellites": satellite_health
    }

@app.get("/system/status", response_model=UnifiedSystemStatus)
async def get_system_status():
    """Get comprehensive system status across all satellites"""
    satellite_statuses = {}
    
    for satellite_id, config in SATELLITES.items():
        try:
            # For Himawari, get actual system status
            if satellite_id == "himawari":
                # Check if directories exist and get file counts
                from pathlib import Path
                
                # Check unified directories only
                base_data_dir = Path("data")
                unified_nc_dir = base_data_dir / "himawari" / "sst" / "nc"
                unified_png_dir = base_data_dir / "himawari" / "sst" / "png"
                
                # Count files from unified structure
                nc_count = len(list(unified_nc_dir.glob("*.nc"))) if unified_nc_dir.exists() else 0
                png_count = len(list(unified_png_dir.glob("*.png"))) if unified_png_dir.exists() else 0
                
                satellite_statuses[satellite_id] = {
                    "available": True,
                    "status": {
                        "data_files": {
                            "nc_files": nc_count,
                            "png_files": png_count
                        },
                        "directories": {
                            "base_directory": str(base_data_dir / "himawari"),
                            "nc_dir_exists": unified_nc_dir.exists(),
                            "png_dir_exists": unified_png_dir.exists()
                        }
                    }
                }
            elif satellite_id.startswith("sentinel3"):
                # For Sentinel-3, check if API and directories exist
                from pathlib import Path
                
                # Check unified directories only
                base_data_dir = Path("data")
                
                total_nc_files = 0
                total_png_files = 0
                dirs_status = {}
                
                for data_type in ['sst', 'chl']:
                    # Check unified directories
                    unified_nc_dir = base_data_dir / satellite_id / data_type / "nc"
                    unified_png_dir = base_data_dir / satellite_id / data_type / "png"
                    
                    # Count files from unified structure
                    if unified_nc_dir.exists():
                        total_nc_files += len(list(unified_nc_dir.glob("*.nc")))
                    if unified_png_dir.exists():
                        total_png_files += len(list(unified_png_dir.glob("*.png")))
                    
                    dirs_status[data_type] = {
                        "nc_exists": unified_nc_dir.exists(),
                        "png_exists": unified_png_dir.exists()
                    }
                
                # Check if Sentinel-3 API is available
                api_available = True
                try:
                    sentinel3_api = get_sentinel3_api()
                    api_available = await sentinel3_api.is_available()
                except Exception:
                    api_available = False
                
                satellite_statuses[satellite_id] = {
                    "available": api_available,
                    "status": {
                        "api_available": api_available,
                        "data_files": {
                            "nc_files": total_nc_files,
                            "png_files": total_png_files
                        },
                        "directories": {
                            "base_directory": str(base_data_dir / satellite_id),
                            "data_types": dirs_status
                        }
                    }
                }
            else:
                satellite_statuses[satellite_id] = {
                    "available": False,
                    "status": "Not implemented yet"
                }
        except Exception as e:
            satellite_statuses[satellite_id] = {
                "available": False,
                "error": str(e)
            }
    
    return UnifiedSystemStatus(
        global_api={
            "status": "healthy",
            "version": "2.0.0", 
            "timestamp": datetime.utcnow().isoformat()
        },
        satellites=satellite_statuses
    )

# Unified Satellite API Routes

@app.get("/api/v1/satellites")
async def list_satellites():
    """List all available satellites with their capabilities"""
    satellites = {}
    
    for satellite_id, config in SATELLITES.items():
        satellites[satellite_id] = SatelliteInfo(
            name=config["name"],
            description=config["description"],
            available=True,  # Simplified for now
            parameters=config["parameters"]
        )
    
    return {
        "satellites": satellites,
        "total": len(satellites),
        "available": sum(1 for s in satellites.values() if s.available)
    }

@app.get("/api/v1/satellites/{satellite}")
async def get_satellite_info(satellite: str):
    """Get detailed information about a specific satellite"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    config = SATELLITES[satellite]
    return {
        "satellite": satellite,
        "info": SatelliteInfo(
            name=config["name"],
            description=config["description"],
            available=True,  # Simplified for now
            parameters=config["parameters"]
        ),
        "endpoints": {
            param: f"/api/v1/satellites/{satellite}/{param}"
            for param in config["parameters"]
        }
    }

@app.get("/api/v1/satellites/{satellite}/{parameter}")
async def get_parameter_info(satellite: str, parameter: str):
    """Get information about a specific parameter for a satellite"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    config = SATELLITES[satellite]
    if parameter not in config["parameters"]:
        raise HTTPException(
            status_code=404, 
            detail=f"Parameter '{parameter}' not found for satellite '{satellite}'"
        )
    
    param_config = config["parameters"][parameter]
    return {
        "satellite": satellite,
        "parameter": parameter,
        "info": ParameterInfo(
            name=param_config["name"],
            unit=param_config["unit"],
            description=param_config["description"],
            file_types=["nc", "png"]
        ),
        "endpoints": {
            "nc_files": f"/api/v1/satellites/{satellite}/{parameter}/nc",
            "png_files": f"/api/v1/satellites/{satellite}/{parameter}/png",
            "static_images": f"/static/{satellite}/{parameter}/png"
        }
    }

@app.get("/api/v1/satellites/{satellite}/{parameter}/{file_type}")
async def list_files(satellite: str, parameter: str, file_type: str):
    """List files for a specific satellite/parameter/file_type combination"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    config = SATELLITES[satellite]
    if parameter not in config["parameters"]:
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{parameter}' not found for satellite '{satellite}'"
        )
    
    if file_type not in ["nc", "png"]:
        raise HTTPException(status_code=400, detail="File type must be 'nc' or 'png'")
    
    try:
        from pathlib import Path
        
        # Unified directory structure: data/{satellite}/{parameter}/{file_type}/
        base_data_dir = Path("data")
        files_dir = base_data_dir / satellite / parameter / file_type
        
        pattern = f"*.{file_type}"
        files = []
        
        # Get files from unified directory structure
        if files_dir.exists():
            for f in files_dir.glob(pattern):
                file_info = {
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "url": f"/static/{satellite}/{parameter}/{file_type}/{f.name}" if file_type == "png" else None,
                    "modified": f.stat().st_mtime
                }
                files.append(file_info)
        
        # Sort by modification time (newest first)
        files = sorted(files, key=lambda x: x["modified"], reverse=True)
        
        # Remove modified timestamp from response for cleaner API
        for f in files:
            if "modified" in f:
                del f["modified"]
        
        return {
            "satellite": satellite,
            "parameter": parameter,
            "file_type": file_type,
            "files": files,
            "total": len(files),
            "directory": str(files_dir)
        }
        
    except Exception as e:
        # Enhanced error logging
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "file_type": file_type,
            "directory": str(files_dir) if 'files_dir' in locals() else None
        }
        print(f"❌ Error listing files: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/nc/{filename}")
async def download_nc_file(satellite: str, parameter: str, filename: str):
    """Download a specific NC file"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        from pathlib import Path
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/x-netcdf"
            )
        
        # File not found
        error_msg = f"File not found: {filename}"
        file_search_info = {
            "filename": filename,
            "satellite": satellite,
            "parameter": parameter,
            "path_checked": str(file_path),
            "directory_exists": file_path.parent.exists()
        }
        print(f"❌ {error_msg}: {file_search_info}")
        raise HTTPException(status_code=404, detail=error_msg)
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Enhanced error logging for other errors
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error downloading file: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/stats/{filename}")
async def get_data_stats(satellite: str, parameter: str, filename: str, target_time: str = None):
    """Get data statistics (min, max, mean) from a specific NC file"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        import xarray as xr
        import numpy as np
        from pathlib import Path
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Read the NetCDF file
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Find the data variable (SST, chlorophyll, etc.)
            data_var = None
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Use Sentinel-3 specific variable lookup
                sentinel3_api = get_sentinel3_api()
                data_var = sentinel3_api.find_data_variable(ds, parameter)
            else:
                # Use general variable lookup for other satellites
                for var_name in ["sea_surface_temperature"]:
                    if var_name in ds.data_vars:
                        data_var = ds[var_name]
                        break
            
            if data_var is None:
                raise HTTPException(status_code=400, detail="No data variable found in file")
            
            # Handle multi-time data using satellite-specific modules
            if len(data_var.shape) > 2:  # Multi-time data
                if satellite in ['sentinel3a', 'sentinel3b']:
                    # Use Sentinel-3 specific data processing
                    sentinel3_api = get_sentinel3_api()
                    time_coords = ds['time'].values
                    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
                else:
                    # For other satellites, use general target_time logic
                    if target_time:
                        from datetime import datetime
                        try:
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                            time_coords = ds['time'].values
                            time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                            closest_time_idx = np.argmin(time_diffs)
                            data = data_var.values[closest_time_idx]
                            
                            # Check if the closest time point has valid data
                            valid_data = data[~np.isnan(data)]
                            if len(valid_data) == 0:
                                # If closest time point has no valid data, try other time points
                                print(f"Closest time point has no valid data, trying other time points...")
                                data = find_first_valid_timepoint(data_var)
                        except Exception as e:
                            data = find_first_valid_timepoint(data_var) # Fallback to first valid time point
                    else:
                        data = find_first_valid_timepoint(data_var) # Default to first valid time point
            else:
                data = data_var.values # Single time data
            
            # Get valid data (exclude NaN values)
            valid_data = data[~np.isnan(data)]
            
            if len(valid_data) == 0:
                raise HTTPException(status_code=400, detail="No valid data found in file")
            
            # Calculate statistics
            stats = {
                "min": float(np.min(valid_data)),
                "max": float(np.max(valid_data)),
                "mean": float(np.mean(valid_data)),
                "std": float(np.std(valid_data)),
                "count": int(len(valid_data)),
                "units": get_parameter_units(parameter, satellite),
                "parameter": parameter,
                "satellite": satellite,
                "filename": filename
            }
            
            return stats
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error getting data stats: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get data statistics: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/filtered-image/{filename}")
async def get_filtered_image(
    satellite: str, 
    parameter: str, 
    filename: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    target_time: str = None
):
    """Generate a filtered image based on value range"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        import xarray as xr
        import numpy as np
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        from pathlib import Path
        import io
        import base64
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Read the NetCDF file
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Find the data variable
            data_var = None
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Use Sentinel-3 specific variable lookup
                sentinel3_api = get_sentinel3_api()
                data_var = sentinel3_api.find_data_variable(ds, parameter)
            else:
                # Use general variable lookup for other satellites
                for var_name in ["sea_surface_temperature"]:
                    if var_name in ds.data_vars:
                        data_var = ds[var_name]
                        break
            
            if data_var is None:
                raise HTTPException(status_code=400, detail="No data variable found in file")
            
            # Handle multi-time data using satellite-specific modules
            if len(data_var.shape) > 2:  # Multi-time data
                if satellite in ['sentinel3a', 'sentinel3b']:
                    # Use Sentinel-3 specific data processing
                    sentinel3_api = get_sentinel3_api()
                    time_coords = ds['time'].values
                    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
                else:
                    # For other satellites, use general target_time logic
                    if target_time:
                        from datetime import datetime
                        try:
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                            time_coords = ds['time'].values
                            time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                            closest_time_idx = np.argmin(time_diffs)
                            data = data_var.values[closest_time_idx]
                            
                            # Check if the closest time point has valid data
                            valid_data = data[~np.isnan(data)]
                            if len(valid_data) == 0:
                                # If closest time point has no valid data, try other time points
                                print(f"Closest time point has no valid data, trying other time points...")
                                data = find_first_valid_timepoint(data_var)
                        except Exception as e:
                            data = find_first_valid_timepoint(data_var) # Fallback to first valid time point
                    else:
                        data = find_first_valid_timepoint(data_var) # Default to first valid time point
            else:
                data = data_var.values # Single time data
            
            # Get coordinates
            lon_name = None
            lat_name = None
            for coord in ["lon", "longitude"]:
                if coord in ds.coords:
                    lon_name = coord
                    break
            for coord in ["lat", "latitude"]:
                if coord in ds.coords:
                    lat_name = coord
                    break
            
            if not lon_name or not lat_name:
                raise HTTPException(status_code=400, detail="Coordinate variables not found")
            
            # Get coordinates
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            
            # Squeeze data to remove single dimensions
            data = np.squeeze(data)
            lons = np.squeeze(lons)
            lats = np.squeeze(lats)
            
            # Get the full data range for absolute colormap
            full_data = data.copy()
            valid_full_data = full_data[~np.isnan(full_data)]
            full_min = np.min(valid_full_data) if len(valid_full_data) > 0 else 0
            full_max = np.max(valid_full_data) if len(valid_full_data) > 0 else 1
            
            # Apply range filtering
            if min_value is not None or max_value is not None:
                mask = np.ones_like(data, dtype=bool)
                if min_value is not None:
                    mask &= (data >= min_value)
                if max_value is not None:
                    mask &= (data <= max_value)
                # Set values outside range to NaN
                data = np.where(mask, data, np.nan)
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={'projection': None})
            
            # Use appropriate colormap based on satellite and parameter
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Use Sentinel-3 specific colormap
                sentinel3_api = get_sentinel3_api()
                colormap_name = sentinel3_api.get_parameter_colormap(parameter)
                cmap = getattr(plt.cm, colormap_name, plt.cm.viridis)
            else:
                # Use general colormap for other satellites
                if parameter == "sst":
                    cmap = plt.cm.turbo  # Use turbo for SST (same as original)
                elif parameter == "chl":
                    cmap = plt.cm.viridis  # Use viridis for chlorophyll
                else:
                    cmap = plt.cm.viridis
            
            # Create meshgrid for plotting
            if lons.ndim == 1 and lats.ndim == 1:
                LON, LAT = np.meshgrid(lons, lats)
            else:
                LON, LAT = lons, lats
            
            # Plot the data with absolute colormap
            im = ax.pcolormesh(LON, LAT, data, cmap=cmap, shading='nearest', vmin=full_min, vmax=full_max)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label(f'{parameter.upper()} ({get_parameter_units(parameter, satellite)})')
            
            # Set title
            ax.set_title(f'{satellite.upper()} {parameter.upper()} - {filename}')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
            
            return {
                "image": f"data:image/png;base64,{image_base64}",
                "satellite": satellite,
                "parameter": parameter,
                "filename": filename,
                "filter_range": {
                    "min": min_value,
                    "max": max_value
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error generating filtered image: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to generate filtered image: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/data/{filename}")
async def get_nc_data_for_map(
    satellite: str, 
    parameter: str, 
    filename: str,
    target_time: str = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
):
    """Get NetCDF data in JSON format for interactive mapping"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        import xarray as xr
        import numpy as np
        from pathlib import Path
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Read the NetCDF file
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Find the data variable
            data_var = None
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Use Sentinel-3 specific variable lookup
                sentinel3_api = get_sentinel3_api()
                data_var = sentinel3_api.find_data_variable(ds, parameter)
            else:
                # Use general variable lookup for other satellites
                for var_name in ["sea_surface_temperature"]:
                    if var_name in ds.data_vars:
                        data_var = ds[var_name]
                        break
            
            if data_var is None:
                raise HTTPException(status_code=400, detail="No data variable found in file")
            
            # Handle multi-time data using satellite-specific modules
            if len(data_var.shape) > 2:  # Multi-time data
                if satellite in ['sentinel3a', 'sentinel3b']:
                    # Use Sentinel-3 specific data processing
                    sentinel3_api = get_sentinel3_api()
                    time_coords = ds['time'].values
                    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
                else:
                    # For other satellites, use general target_time logic
                    if target_time:
                        from datetime import datetime
                        try:
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                            time_coords = ds['time'].values
                            time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                            closest_time_idx = np.argmin(time_diffs)
                            data = data_var.values[closest_time_idx]
                            
                            # Check if the closest time point has valid data
                            valid_data = data[~np.isnan(data)]
                            if len(valid_data) == 0:
                                # If closest time point has no valid data, try other time points
                                print(f"Closest time point has no valid data, trying other time points...")
                                data = find_first_valid_timepoint(data_var)
                        except Exception as e:
                            data = find_first_valid_timepoint(data_var) # Fallback to first valid time point
                    else:
                        data = find_first_valid_timepoint(data_var) # Default to first valid time point
            else:
                data = data_var.values # Single time data
            
            # Get coordinates
            lon_name = None
            lat_name = None
            for coord in ["lon", "longitude"]:
                if coord in ds.coords:
                    lon_name = coord
                    break
            for coord in ["lat", "latitude"]:
                if coord in ds.coords:
                    lat_name = coord
                    break
            
            if not lon_name or not lat_name:
                raise HTTPException(status_code=400, detail="Coordinate variables not found")
            
            # Get coordinates
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            
            # Squeeze data to remove single dimensions
            data = np.squeeze(data)
            lons = np.squeeze(lons)
            lats = np.squeeze(lats)
            
            # Apply range filtering if specified
            if min_value is not None or max_value is not None:
                mask = np.ones_like(data, dtype=bool)
                if min_value is not None:
                    mask &= (data >= min_value)
                if max_value is not None:
                    mask &= (data <= max_value)
                # Set values outside range to NaN
                data = np.where(mask, data, np.nan)
            
            # Prepare coordinates based on data dimensions
            if lons.ndim == 1 and lats.ndim == 1:
                # 1D coordinates - create meshgrid
                lon_grid, lat_grid = np.meshgrid(lons, lats)
            else:
                # 2D coordinates
                lon_grid, lat_grid = lons, lats
            
            # Convert to lists and handle NaN values
            data_points = []
            
            # Downsample for performance if dataset is too large
            max_points = 50000  # Limit for performance
            height, width = data.shape
            total_points = height * width
            
            if total_points > max_points:
                # Calculate downsampling factor
                downsample_factor = int(np.sqrt(total_points / max_points)) + 1
                data = data[::downsample_factor, ::downsample_factor]
                lon_grid = lon_grid[::downsample_factor, ::downsample_factor]
                lat_grid = lat_grid[::downsample_factor, ::downsample_factor]
            
            # Extract data points
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    value = data[i, j]
                    if not np.isnan(value):
                        data_points.append({
                            "lat": float(lat_grid[i, j]),
                            "lon": float(lon_grid[i, j]),
                            "value": float(value)
                        })
            
            # Calculate data statistics
            valid_values = [p["value"] for p in data_points]
            if valid_values:
                data_min = min(valid_values)
                data_max = max(valid_values)
                data_mean = sum(valid_values) / len(valid_values)
            else:
                data_min = data_max = data_mean = 0
            
            return {
                "satellite": satellite,
                "parameter": parameter,
                "filename": filename,
                "data_points": data_points,
                "bounds": {
                    "north": float(np.max(lat_grid)),
                    "south": float(np.min(lat_grid)),
                    "east": float(np.max(lon_grid)),
                    "west": float(np.min(lon_grid))
                },
                "statistics": {
                    "min": data_min,
                    "max": data_max,
                    "mean": data_mean,
                    "count": len(data_points),
                    "units": get_parameter_units(parameter, satellite)
                },
                "metadata": {
                    "downsampled": total_points > max_points,
                    "downsample_factor": downsample_factor if total_points > max_points else 1,
                    "original_size": total_points,
                    "processed_size": len(data_points)
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error getting NC data for map: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get NC data: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/grid-data/{filename}")
async def get_nc_grid_data_for_heatmap(
    satellite: str, 
    parameter: str, 
    filename: str,
    target_time: str = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    max_grid_size: int = 200
):
    """Get NetCDF data as a regular grid for heatmap visualization - mimics matplotlib's pcolormesh"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        import xarray as xr
        import numpy as np
        from pathlib import Path
        from scipy.interpolate import griddata
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Read the NetCDF file
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Find the data variable
            data_var = None
            if satellite in ['sentinel3a', 'sentinel3b']:
                # Use Sentinel-3 specific variable lookup
                sentinel3_api = get_sentinel3_api()
                data_var = sentinel3_api.find_data_variable(ds, parameter)
            else:
                # Use general variable lookup for other satellites
                for var_name in ["sea_surface_temperature"]:
                    if var_name in ds.data_vars:
                        data_var = ds[var_name]
                        break
            
            if data_var is None:
                raise HTTPException(status_code=400, detail="No data variable found in file")
            
            # Handle multi-time data using satellite-specific modules
            if len(data_var.shape) > 2:  # Multi-time data
                if satellite in ['sentinel3a', 'sentinel3b']:
                    # Use Sentinel-3 specific data processing
                    sentinel3_api = get_sentinel3_api()
                    time_coords = ds['time'].values
                    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
                else:
                    # For other satellites, use general target_time logic
                    if target_time:
                        from datetime import datetime
                        try:
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                            time_coords = ds['time'].values
                            time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                            closest_time_idx = np.argmin(time_diffs)
                            data = data_var.values[closest_time_idx]
                            
                            # Check if the closest time point has valid data
                            valid_data = data[~np.isnan(data)]
                            if len(valid_data) == 0:
                                print(f"Closest time point has no valid data, trying other time points...")
                                data = find_first_valid_timepoint(data_var)
                        except Exception as e:
                            data = find_first_valid_timepoint(data_var) # Fallback to first valid time point
                    else:
                        data = find_first_valid_timepoint(data_var) # Default to first valid time point
            else:
                data = data_var.values # Single time data
            
            # Get coordinates
            lon_name = None
            lat_name = None
            for coord in ["lon", "longitude"]:
                if coord in ds.coords:
                    lon_name = coord
                    break
            for coord in ["lat", "latitude"]:
                if coord in ds.coords:
                    lat_name = coord
                    break
            
            if not lon_name or not lat_name:
                raise HTTPException(status_code=400, detail="Coordinate variables not found")
            
            # Get coordinates
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            
            # Squeeze data to remove single dimensions
            data = np.squeeze(data)
            lons = np.squeeze(lons)
            lats = np.squeeze(lats)
            
            # Apply range filtering if specified
            if min_value is not None or max_value is not None:
                mask = np.ones_like(data, dtype=bool)
                if min_value is not None:
                    mask &= (data >= min_value)
                if max_value is not None:
                    mask &= (data <= max_value)
                # Set values outside range to NaN
                data = np.where(mask, data, np.nan)
            
            # Handle coordinate dimensions
            if lons.ndim == 1 and lats.ndim == 1:
                # 1D coordinates - create meshgrid (regular grid case)
                lon_grid, lat_grid = np.meshgrid(lons, lats)
                
                # For regular grids, we can directly use the data
                # Ensure data shape matches grid
                if data.shape != lon_grid.shape:
                    # Try transpose if dimensions don't match
                    if data.T.shape == lon_grid.shape:
                        data = data.T
                    else:
                        raise HTTPException(status_code=400, detail=f"Data shape {data.shape} doesn't match coordinate grid {lon_grid.shape}")
                
                grid_data = data
                grid_lons = lon_grid
                grid_lats = lat_grid
                
            else:
                # 2D coordinates - irregular grid, need interpolation
                lon_grid = lons
                lat_grid = lats
                
                # Create regular grid for interpolation
                min_lon, max_lon = np.nanmin(lons), np.nanmax(lons)
                min_lat, max_lat = np.nanmin(lats), np.nanmax(lats)
                
                # Determine grid resolution
                original_points = data.size
                if original_points > max_grid_size * max_grid_size:
                    grid_resolution = max_grid_size
                else:
                    grid_resolution = min(max_grid_size, int(np.sqrt(original_points)))
                
                # Create regular grid
                regular_lons = np.linspace(min_lon, max_lon, grid_resolution)
                regular_lats = np.linspace(min_lat, max_lat, grid_resolution)
                grid_lons, grid_lats = np.meshgrid(regular_lons, regular_lats)
                
                # Flatten for interpolation
                valid_mask = ~np.isnan(data)
                if np.sum(valid_mask) < 3:
                    raise HTTPException(status_code=400, detail="Not enough valid data points for interpolation")
                
                points = np.column_stack((lons[valid_mask].flatten(), lats[valid_mask].flatten()))
                values = data[valid_mask].flatten()
                
                # Interpolate to regular grid
                grid_points = np.column_stack((grid_lons.flatten(), grid_lats.flatten()))
                
                try:
                    interpolated_values = griddata(
                        points, values, grid_points, 
                        method='linear', fill_value=np.nan
                    )
                    grid_data = interpolated_values.reshape(grid_lons.shape)
                except Exception as e:
                    # Fallback to nearest neighbor if linear fails
                    interpolated_values = griddata(
                        points, values, grid_points, 
                        method='nearest', fill_value=np.nan
                    )
                    grid_data = interpolated_values.reshape(grid_lons.shape)
            
            # Calculate statistics
            valid_data = grid_data[~np.isnan(grid_data)]
            if len(valid_data) > 0:
                data_min = float(np.min(valid_data))
                data_max = float(np.max(valid_data))
                data_mean = float(np.mean(valid_data))
            else:
                data_min = data_max = data_mean = 0
            
            # Convert to nested lists for JSON serialization
            grid_data_list = []
            grid_lons_list = []
            grid_lats_list = []
            
            for i in range(grid_data.shape[0]):
                data_row = []
                lon_row = []
                lat_row = []
                for j in range(grid_data.shape[1]):
                    if np.isnan(grid_data[i, j]):
                        data_row.append(None)
                    else:
                        data_row.append(float(grid_data[i, j]))
                    lon_row.append(float(grid_lons[i, j]))
                    lat_row.append(float(grid_lats[i, j]))
                grid_data_list.append(data_row)
                grid_lons_list.append(lon_row)
                grid_lats_list.append(lat_row)
            
            return {
                "satellite": satellite,
                "parameter": parameter,
                "filename": filename,
                "grid_data": grid_data_list,
                "grid_lons": grid_lons_list,
                "grid_lats": grid_lats_list,
                "shape": list(grid_data.shape),
                "bounds": {
                    "north": float(np.max(grid_lats)),
                    "south": float(np.min(grid_lats)),
                    "east": float(np.max(grid_lons)),
                    "west": float(np.min(grid_lons))
                },
                "statistics": {
                    "min": data_min,
                    "max": data_max,
                    "mean": data_mean,
                    "valid_pixels": len(valid_data),
                    "total_pixels": grid_data.size,
                    "units": get_parameter_units(parameter, satellite)
                },
                "metadata": {
                    "grid_type": "regular" if lons.ndim == 1 else "interpolated",
                    "original_shape": list(data.shape) if lons.ndim == 1 else "irregular",
                    "grid_resolution": grid_data.shape
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error getting grid data for heatmap: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get grid data: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/simple-data/{filename}")
async def get_simple_nc_data(
    satellite: str, 
    parameter: str, 
    filename: str,
    target_time: str = None
):
    """Get NetCDF data in the simplest format possible - just like matplotlib reads it"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        import xarray as xr
        import numpy as np
        from pathlib import Path
        
        # Unified directory structure
        base_data_dir = Path("data")
        file_path = base_data_dir / satellite / parameter / "nc" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Read the NetCDF file - exactly like matplotlib does
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Find the data variable
            data_var = None
            if satellite in ['sentinel3a', 'sentinel3b']:
                sentinel3_api = get_sentinel3_api()
                data_var = sentinel3_api.find_data_variable(ds, parameter)
            else:
                for var_name in ["sea_surface_temperature"]:
                    if var_name in ds.data_vars:
                        data_var = ds[var_name]
                        break
            
            if data_var is None:
                raise HTTPException(status_code=400, detail="No data variable found in file")
            
            # Handle multi-time data
            if len(data_var.shape) > 2:
                if satellite in ['sentinel3a', 'sentinel3b']:
                    sentinel3_api = get_sentinel3_api()
                    time_coords = ds['time'].values
                    data = sentinel3_api.get_sentinel3_data(data_var, target_time, time_coords)
                else:
                    if target_time:
                        from datetime import datetime
                        try:
                            target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                            time_coords = ds['time'].values
                            time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                            closest_time_idx = np.argmin(time_diffs)
                            data = data_var.values[closest_time_idx]
                        except Exception as e:
                            data = find_first_valid_timepoint(data_var)
                    else:
                        data = find_first_valid_timepoint(data_var)
            else:
                data = data_var.values
            
            # Get coordinates
            lon_name = None
            lat_name = None
            for coord in ["lon", "longitude"]:
                if coord in ds.coords:
                    lon_name = coord
                    break
            for coord in ["lat", "latitude"]:
                if coord in ds.coords:
                    lat_name = coord
                    break
            
            if not lon_name or not lat_name:
                raise HTTPException(status_code=400, detail="Coordinate variables not found")
            
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            
            # Squeeze data
            data = np.squeeze(data)
            lons = np.squeeze(lons)
            lats = np.squeeze(lats)
            
            # 确保数据是2D的
            if data.ndim != 2:
                raise HTTPException(status_code=400, detail=f"Expected 2D data, got {data.ndim}D")
            
            # 转换为列表格式，处理NaN
            data_list = []
            for i in range(data.shape[0]):
                row = []
                for j in range(data.shape[1]):
                    val = data[i, j]
                    if np.isnan(val):
                        row.append(None)
                    else:
                        row.append(float(val))
                data_list.append(row)
            
            # 计算统计信息
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                min_value = float(np.min(valid_data))
                max_value = float(np.max(valid_data))
                mean_value = float(np.mean(valid_data))
            else:
                min_value = max_value = mean_value = 0
            
            return {
                "data": data_list,
                "lons": lons.tolist(),
                "lats": lats.tolist(),
                "min_value": min_value,
                "max_value": max_value,
                "mean_value": mean_value,
                "units": get_parameter_units(parameter, satellite),
                "shape": list(data.shape),
                "satellite": satellite,
                "parameter": parameter,
                "filename": filename
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "satellite": satellite,
            "parameter": parameter,
            "filename": filename
        }
        print(f"❌ Error getting simple NC data: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get simple NC data: {str(e)}")

# Simple processing endpoint (placeholder for now)
@app.post("/api/v1/process", response_model=ProcessingStatus)
async def process_data(request: ProcessingRequest, background_tasks: BackgroundTasks):
    """Process satellite data (simplified implementation)"""
    satellite = request.satellite
    
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    config = SATELLITES[satellite]
    if request.parameter not in config["parameters"]:
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{request.parameter}' not found for satellite '{satellite}'"
        )
    
    # For now, return a simple response
    import uuid
    task_id = str(uuid.uuid4())
    
    return ProcessingStatus(
        task_id=task_id,
        status="pending",
        message=f"Processing {satellite}/{request.parameter} data (placeholder implementation)",
        progress=0
    )

# Task status tracking for Himawari (must be before the general proxy route)
@app.get("/tasks/himawari/{task_id}", response_model=ProcessingStatus)
async def get_himawari_task_status(task_id: str):
    """Get Himawari task status"""
    try:
        # Use global Himawari API instance
        himawari_api = get_himawari_api()
        return await himawari_api.get_task_status(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

# Alternative status endpoint that matches the frontend expectation (must be before the general proxy route)
@app.get("/himawari/status/{task_id}", response_model=ProcessingStatus)
async def get_himawari_status_alt(task_id: str):
    """Get Himawari task status (alternative endpoint)"""
    try:
        # Use global Himawari API instance
        himawari_api = get_himawari_api()
        return await himawari_api.get_task_status(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

# Himawari-specific API routes (proxy to dedicated Himawari API) - must be after specific routes
@app.api_route("/himawari/{path:path}", methods=["GET", "POST"])
async def himawari_proxy(path: str, request: Request, background_tasks: BackgroundTasks = None):
    """Proxy requests to Himawari-specific API"""
    try:
        # Use global Himawari API instance
        himawari_api = get_himawari_api()
        
        if request.method == "GET":
            return await himawari_api.handle_get_request(path, dict(request.query_params))
        elif request.method == "POST":
            try:
                request_data = await request.json() if request.headers.get("content-type") == "application/json" else {}
            except:
                request_data = {}
            return await himawari_api.handle_post_request(path, request_data, background_tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Himawari proxy error: {str(e)}")

# Sentinel-3-specific API routes (proxy to dedicated Sentinel-3 API)
@app.api_route("/sentinel3/{path:path}", methods=["GET", "POST"])
async def sentinel3_proxy(path: str, request: Request, background_tasks: BackgroundTasks = None):
    """Proxy requests to Sentinel-3-specific API"""
    try:
        # Use global Sentinel-3 API instance
        sentinel3_api = get_sentinel3_api()
        
        if request.method == "GET":
            return await sentinel3_api.handle_get_request(path, dict(request.query_params))
        elif request.method == "POST":
            try:
                request_data = await request.json() if request.headers.get("content-type") == "application/json" else {}
            except:
                request_data = {}
            return await sentinel3_api.handle_post_request(path, request_data, background_tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentinel-3 proxy error: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint was not found",
            "available_endpoints": {
                "unified": "/api/v1/satellites",
                "himawari": "/himawari/health",
                "system": "/system/status",
                "health": "/health",
                "docs": "/docs"
            }
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
