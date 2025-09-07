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
def setup_data_directories():
    """Ensure all necessary data directories exist"""
    from pathlib import Path
    
    # Himawari directories
    himawari_base = Path("himawari_test_data/data/himawari_l3c")
    himawari_dirs = [
        himawari_base,
        himawari_base / "parts",
        himawari_base / "png", 
        himawari_base / "temp"
    ]
    
    for directory in himawari_dirs:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"📁 Directory exists: {directory}")
    
    # Sentinel-3 directories
    sentinel3_base = Path("saternal3/data/eumetview_sentinel3")
    sentinel3_dirs = []
    
    # Create satellite/datatype/nc and satellite/datatype/png directories
    for satellite in ['sentinel3a', 'sentinel3b']:
        for data_type in ['sst', 'chl']:
            sentinel3_dirs.extend([
                sentinel3_base / satellite / data_type / "nc",
                sentinel3_base / satellite / data_type / "png"
            ])
    
    for directory in sentinel3_dirs:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"📁 Directory exists: {directory}")

def setup_static_files(app: FastAPI):
    """Setup static file serving for satellite data"""
    from pathlib import Path
    
    # Mount Himawari PNG files
    himawari_png_dir = Path("himawari_test_data/data/himawari_l3c/png")
    if himawari_png_dir.exists():
        app.mount("/static/himawari/sst/png", StaticFiles(directory=str(himawari_png_dir)), name="himawari_png")
        print(f"✅ Mounted static files: /static/himawari/sst/png -> {himawari_png_dir}")
    else:
        print(f"⚠️ PNG directory not found: {himawari_png_dir}")
    
    # Mount Sentinel-3 PNG files
    sentinel3_base = Path("saternal3/data/eumetview_sentinel3")
    for satellite in ['sentinel3a', 'sentinel3b']:
        for data_type in ['sst', 'chl']:
            png_dir = sentinel3_base / satellite / data_type / "png"
            if png_dir.exists():
                mount_path = f"/static/{satellite}/{data_type}/png"
                app.mount(mount_path, StaticFiles(directory=str(png_dir)), name=f"{satellite}_{data_type}_png")
                print(f"✅ Mounted static files: {mount_path} -> {png_dir}")
            else:
                print(f"⚠️ PNG directory not found: {png_dir}")

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
                himawari_base = Path("himawari_test_data/data/himawari_l3c")
                parts_count = len(list((himawari_base / "parts").glob("*.nc"))) if (himawari_base / "parts").exists() else 0
                png_count = len(list((himawari_base / "png").glob("*.png"))) if (himawari_base / "png").exists() else 0
                
                satellite_statuses[satellite_id] = {
                    "available": True,
                    "status": {
                        "data_files": {
                            "nc_files": parts_count,
                            "png_files": png_count
                        },
                        "directories": {
                            "base": str(himawari_base),
                            "parts_exists": (himawari_base / "parts").exists(),
                            "png_exists": (himawari_base / "png").exists()
                        }
                    }
                }
            elif satellite_id.startswith("sentinel3"):
                # For Sentinel-3, check if API and directories exist
                from pathlib import Path
                sentinel3_base = Path("saternal3/data/eumetview_sentinel3")
                
                # Check if directories exist
                nc_dirs_exist = True
                png_dirs_exist = True
                total_nc_files = 0
                total_png_files = 0
                
                for data_type in ['sst', 'chl']:
                    nc_dir = sentinel3_base / satellite_id / data_type / "nc"
                    png_dir = sentinel3_base / satellite_id / data_type / "png"
                    
                    if not nc_dir.exists():
                        nc_dirs_exist = False
                    else:
                        total_nc_files += len(list(nc_dir.glob("*.nc")))
                    
                    if not png_dir.exists():
                        png_dirs_exist = False
                    else:
                        total_png_files += len(list(png_dir.glob("*.png")))
                
                # Check if Sentinel-3 API is available
                api_available = True
                try:
                    sentinel3_api = get_sentinel3_api()
                    api_available = await sentinel3_api.is_available()
                except Exception:
                    api_available = False
                
                satellite_statuses[satellite_id] = {
                    "available": api_available and nc_dirs_exist and png_dirs_exist,
                    "status": {
                        "api_available": api_available,
                        "data_files": {
                            "nc_files": total_nc_files,
                            "png_files": total_png_files
                        },
                        "directories": {
                            "base": str(sentinel3_base / satellite_id),
                            "nc_dirs_exist": nc_dirs_exist,
                            "png_dirs_exist": png_dirs_exist
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
        # For Himawari, list actual files
        if satellite == "himawari" and parameter == "sst":
            from pathlib import Path
            himawari_base = Path("himawari_test_data/data/himawari_l3c")
            
            if file_type == "nc":
                files_dir = himawari_base / "parts"
                pattern = "*.nc"
            elif file_type == "png":
                files_dir = himawari_base / "png"
                pattern = "*.png"
            else:
                files = []
            
            if files_dir.exists():
                files = [{"filename": f.name, "size": f.stat().st_size} for f in files_dir.glob(pattern)]
            else:
                files = []
        else:
            files = []
        
        return {
            "satellite": satellite,
            "parameter": parameter,
            "file_type": file_type,
            "files": files,
            "total": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/api/v1/satellites/{satellite}/{parameter}/nc/{filename}")
async def download_nc_file(satellite: str, parameter: str, filename: str):
    """Download a specific NC file"""
    if satellite not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite '{satellite}' not found")
    
    try:
        if satellite == "himawari" and parameter == "sst":
            from pathlib import Path
            file_path = Path(f"himawari_test_data/data/himawari_l3c/parts/{filename}")
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/x-netcdf"
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

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
