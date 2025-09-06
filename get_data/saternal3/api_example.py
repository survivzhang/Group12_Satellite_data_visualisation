"""
FastAPI Backend Example for EUMETView Sentinel-3 Satellite Data

This demonstrates how to create a REST API for EUMETView satellite data processing.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Tuple, Optional, List, Dict
import pandas as pd
from pathlib import Path
import asyncio
from datetime import datetime
import time

from usingtheEumetview import EUMETViewDataProcessor, EUMETViewWorkflow, EUMETViewFileMonitor, create_file_monitor

app = FastAPI(
    title="EUMETView Sentinel-3 Data API",
    description="API for processing and accessing EUMETView Sentinel-3 satellite data",
    version="1.0.0"
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor and workflow instances
processor = EUMETViewDataProcessor()
workflow = EUMETViewWorkflow()
file_monitor = create_file_monitor()

# Mount static files for PNG images
png_directory = Path("data/eumetview_sentinel3/png")
png_directory.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
app.mount("/static/images", StaticFiles(directory=str(png_directory)), name="images")

# Pydantic models for request/response
class ProcessingRequest(BaseModel):
    layer_keys: List[str]  # e.g., ['sentinel3a_sst', 'sentinel3a_chl']
    start_time: str  # ISO format: "2024-12-01T10:40:00.000Z"
    end_time: str
    west_lon: float
    east_lon: float
    south_lat: float
    north_lat: float
    consumer_key: Optional[str] = None
    consumer_secret: Optional[str] = None

class ProcessingStatus(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str
    progress: Optional[int] = None

class LayerInfo(BaseModel):
    key: str
    name: str
    description: str
    data_type: str  # "sst" or "chl"
    satellite: str  # "sentinel3a", "sentinel3b", "daily"

class DataManifest(BaseModel):
    available_layers: List[LayerInfo]
    supported_formats: List[str]
    region: Tuple[float, float, float, float]
    time_range: Tuple[str, str]

class FileListResponse(BaseModel):
    files: List[dict]
    total: int
    by_layer: Dict[str, int]

class FileCheckRequest(BaseModel):
    nc_file_path: str  # Path to the NC file to check

class FileCheckResponse(BaseModel):
    nc_exists: bool
    nc_modified_time: Optional[str]
    png_count: int
    needs_regeneration: bool
    message: str
    timestamp: str

class RegenerateRequest(BaseModel):
    nc_file_path: str  # Path to the NC file

class RegenerateResponse(BaseModel):
    success: bool
    message: str
    png_generated: int
    regeneration_performed: bool
    timestamp: str

# In-memory task storage (use Redis in production)
tasks = {}

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "EUMETView Sentinel-3 Data API",
        "version": "1.0.0",
        "endpoints": {
            "layers": "/layers",
            "query": "/query-data",
            "process": "/process-data",
            "status": "/status/{task_id}",
            "files": "/files",
            "visualizations": "/visualizations",
            "check_file": "/check-file",
            "regenerate_pngs": "/regenerate-pngs",
            "auto_check_regenerate": "/auto-check-regenerate",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/layers")
async def get_available_layers():
    """Get information about available data layers."""
    try:
        # Initialize processor if not already done
        if not processor.wcs:
            processor.authenticate()
        
        layer_info = []
        for key, layer_id in processor.LAYER_CONFIGS.items():
            satellite, data_type = processor._parse_layer_key(key)
            
            layer_info.append(LayerInfo(
                key=key,
                name=layer_id,
                description=f"{satellite.upper()} {data_type.upper()} data",
                data_type=data_type,
                satellite=satellite
            ))
        
        return {
            "layers": layer_info,
            "total": len(layer_info)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get layers: {str(e)}")

@app.post("/query-data", response_model=DataManifest)
async def query_available_data(request: ProcessingRequest):
    """Query available satellite data capabilities."""
    try:
        # Initialize processor if not already done
        if not processor.wcs:
            processor.authenticate(request.consumer_key, request.consumer_secret)
        
        # Get available layers info
        layer_info = []
        for key in request.layer_keys:
            if key in processor.LAYER_CONFIGS:
                satellite, data_type = processor._parse_layer_key(key)
                layer_info.append(LayerInfo(
                    key=key,
                    name=processor.LAYER_CONFIGS[key],
                    description=f"{satellite.upper()} {data_type.upper()} data",
                    data_type=data_type,
                    satellite=satellite
                ))
        
        # Get supported formats for first layer
        supported_formats = ['application/x-netcdf']
        if request.layer_keys:
            try:
                supported_formats = processor.get_supported_formats(request.layer_keys[0])
            except Exception:
                pass
        
        return DataManifest(
            available_layers=layer_info,
            supported_formats=supported_formats,
            region=(request.west_lon, request.south_lat, request.east_lon, request.north_lat),
            time_range=(request.start_time, request.end_time)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/process-data", response_model=ProcessingStatus)
async def process_satellite_data(request: ProcessingRequest, background_tasks: BackgroundTasks):
    """Start processing satellite data in the background."""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # Store task info
    tasks[task_id] = {
        "status": "pending",
        "message": f"Task queued for processing {len(request.layer_keys)} layers",
        "progress": 0,
        "request": request
    }
    
    # Add background task
    background_tasks.add_task(
        run_processing_task,
        task_id,
        request
    )
    
    return ProcessingStatus(
        task_id=task_id,
        status="pending",
        message=f"Processing task started for {len(request.layer_keys)} layers"
    )

@app.get("/status/{task_id}", response_model=ProcessingStatus)
async def get_processing_status(task_id: str):
    """Get the status of a processing task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks[task_id]
    return ProcessingStatus(
        task_id=task_id,
        status=task_info["status"],
        message=task_info["message"],
        progress=task_info.get("progress")
    )

@app.get("/files", response_model=FileListResponse)
async def list_processed_files():
    """List all processed NetCDF data files."""
    try:
        # List files in the nc directory
        nc_dir = processor.nc_dir
        if not nc_dir.exists():
            return FileListResponse(files=[], total=0, by_layer={})
        
        files = []
        by_layer = {}
        
        # Walk through all subdirectories
        for file_path in nc_dir.rglob("*.nc"):
            stat = file_path.stat()
            
            # Determine layer from path
            parts = file_path.relative_to(nc_dir).parts
            layer_key = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else "unknown"
            
            files.append({
                "filename": file_path.name,
                "layer": layer_key,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file_path)
            })
            
            by_layer[layer_key] = by_layer.get(layer_key, 0) + 1
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return FileListResponse(files=files, total=len(files), by_layer=by_layer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/visualizations")
async def list_visualizations():
    """List all generated visualization files."""
    try:
        png_dir = processor.png_dir
        if not png_dir.exists():
            return {"images": [], "total": 0, "by_layer": {}}
        
        images = []
        by_layer = {}
        
        # Walk through all subdirectories
        for file_path in png_dir.rglob("*.png"):
            stat = file_path.stat()
            
            # Determine layer from path
            parts = file_path.relative_to(png_dir).parts
            layer_key = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else "unknown"
            
            # Create relative URL for static file serving
            relative_path = file_path.relative_to(png_directory)
            
            images.append({
                "filename": file_path.name,
                "layer": layer_key,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/static/images/{relative_path}"
            })
            
            by_layer[layer_key] = by_layer.get(layer_key, 0) + 1
        
        images.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"images": images, "total": len(images), "by_layer": by_layer}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

@app.get("/system-status")
async def get_system_status():
    """Get system status and health check"""
    try:
        # System info
        import psutil
        
        # Count files
        nc_files = len(list(processor.nc_dir.rglob("*.nc"))) if processor.nc_dir.exists() else 0
        png_files = len(list(processor.png_dir.rglob("*.png"))) if processor.png_dir.exists() else 0
        
        system_info = {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time()
            },
            "data_status": {
                "nc_files": nc_files,
                "png_files": png_files,
                "authenticated": processor.wcs is not None
            },
            "storage": {
                "base_dir": str(processor.base_dir),
                "nc_dir": str(processor.nc_dir),
                "png_dir": str(processor.png_dir)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return system_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System status check failed: {str(e)}")

@app.post("/describe-coverage/{layer_key}")
async def describe_coverage(layer_key: str):
    """Get detailed coverage description for a layer."""
    try:
        if not processor.wcs:
            processor.authenticate()
        
        description = processor.describe_coverage(layer_key)
        
        return {
            "layer_key": layer_key,
            "layer_id": processor.LAYER_CONFIGS.get(layer_key),
            "description": description
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to describe coverage: {str(e)}")

@app.post("/check-file", response_model=FileCheckResponse)
async def check_file_status(request: FileCheckRequest):
    """Check NC file status and PNG regeneration needs"""
    try:
        # Check file status
        results = file_monitor.check_file_status(request.nc_file_path)
        
        return FileCheckResponse(
            nc_exists=results['nc_exists'],
            nc_modified_time=results['nc_modified_time'],
            png_count=results['png_count'],
            needs_regeneration=results['needs_regeneration'],
            message=results['message'],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File check failed: {str(e)}")

@app.post("/regenerate-pngs", response_model=RegenerateResponse)
async def regenerate_png_files(request: RegenerateRequest):
    """Regenerate all PNG files from NC file"""
    try:
        # Regenerate PNGs
        results = file_monitor.regenerate_all_pngs(request.nc_file_path)
        
        return RegenerateResponse(
            success=results['success'],
            message=results['message'],
            png_generated=results['png_generated'],
            regeneration_performed=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PNG regeneration failed: {str(e)}")

@app.post("/auto-check-regenerate", response_model=RegenerateResponse)
async def auto_check_and_regenerate(request: RegenerateRequest):
    """Automatically check file status and regenerate PNGs if needed"""
    try:
        # Auto check and regenerate if needed
        results = file_monitor.check_and_regenerate_if_needed(request.nc_file_path)
        
        return RegenerateResponse(
            success=results.get('regeneration_success', True),
            message=results['final_message'],
            png_generated=results.get('png_generated', 0),
            regeneration_performed=results['regeneration_performed'],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto check and regenerate failed: {str(e)}")

@app.get("/test-endpoints")
async def test_endpoints():
    """Test page to show available endpoints and how to use them"""
    return {
        "message": "EUMETView API Test Page",
        "available_endpoints": {
            "GET /": "API information",
            "GET /health": "Health check",
            "GET /layers": "List available layers",
            "GET /files": "List NC files",
            "GET /visualizations": "List PNG files",
            "GET /test-endpoints": "This test page",
            "POST /check-file": "Check file status (requires nc_file_path in JSON body)",
            "POST /regenerate-pngs": "Regenerate PNGs (requires nc_file_path in JSON body)",
            "POST /auto-check-regenerate": "Auto check and regenerate (requires nc_file_path in JSON body)"
        },
        "example_usage": {
            "check_file": {
                "method": "POST",
                "url": "/check-file",
                "body": {"nc_file_path": "data/eumetview_sentinel3/nc/sentinel3a/sst/example.nc"}
            },
            "auto_regenerate": {
                "method": "POST", 
                "url": "/auto-check-regenerate",
                "body": {"nc_file_path": "data/eumetview_sentinel3/nc/sentinel3a/sst/example.nc"}
            }
        },
        "note": "Use /docs for interactive API documentation"
    }

async def run_processing_task(task_id: str, request: ProcessingRequest):
    """Background task for processing satellite data."""
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Authenticating..."
        tasks[task_id]["progress"] = 10
        
        # Run the actual processing using the workflow
        await asyncio.to_thread(
            workflow.run_complete_workflow,
            layer_keys=request.layer_keys,
            region=(request.west_lon, request.south_lat, request.east_lon, request.north_lat),
            time_range=(request.start_time, request.end_time),
            consumer_key=request.consumer_key,
            consumer_secret=request.consumer_secret
        )
        
        # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = f"Processing completed successfully for {len(request.layer_keys)} layers"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Processing failed: {str(e)}"
        tasks[task_id]["progress"] = 0


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_example:app", 
        host="0.0.0.0", 
        port=8000,  
        reload=True,
        log_level="info"
    )
