"""
FastAPI Backend Example for Himawari Satellite Data

This demonstrates how to create a REST API for your satellite data processing.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Tuple, Optional, List
import pandas as pd
from pathlib import Path
import asyncio
from datetime import datetime
import time

from himawari_processor import HimawariDataProcessor, HimawariFileMonitor, create_file_monitor

app = FastAPI(
    title="Himawari Satellite Data API",
    description="API for processing and accessing Himawari satellite data",
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

# Global processor and monitor instances
processor = HimawariDataProcessor()
file_monitor = create_file_monitor()

# Mount static files for PNG images
png_directory = Path("data/himawari_l3c/png")
png_directory.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
app.mount("/static/images", StaticFiles(directory=str(png_directory)), name="images")

# Pydantic models for request/response
class ProcessingRequest(BaseModel):
    start_time: str  # ISO format: "2025-03-01T00:00:00"
    end_time: str
    west_lon: float
    east_lon: float
    south_lat: float
    north_lat: float
    time_step_hours: int = 1

class ProcessingStatus(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str
    progress: Optional[int] = None

class DataManifest(BaseModel):
    total_files: int
    time_range: Tuple[str, str]
    files: List[dict]

class FileCheckRequest(BaseModel):
    start_time: str  # ISO format: "2025-03-01T00:00:00"
    end_time: str
    time_step_hours: int = 1
    check_nc: bool = True
    check_png: bool = True

class FileCheckResponse(BaseModel):
    expected_files: int
    nc_files: dict
    png_files: dict
    summary: dict
    timestamp: str

class RepairRequest(BaseModel):
    start_time: str
    end_time: str
    west_lon: float
    east_lon: float
    south_lat: float
    north_lat: float
    time_step_hours: int = 1
    repair_nc: bool = True
    repair_png: bool = True

# In-memory task storage (use Redis in production)
tasks = {}

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Himawari Satellite Data API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/query-data",
            "process": "/process-data",
            "status": "/status/{task_id}",
            "files": "/files",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/query-data", response_model=DataManifest)
async def query_available_data(request: ProcessingRequest):
    """Query available satellite data for given parameters."""
    try:
        # Query manifest
        manifest_df = processor.query_data_manifest(
            timelims=(request.start_time, request.end_time),
            lonlims=(request.west_lon, request.east_lon),
            latlims=(request.south_lat, request.north_lat)
        )
        
        # Convert to response format
        files = manifest_df.to_dict('records') if not manifest_df.empty else []
        
        return DataManifest(
            total_files=len(files),
            time_range=(request.start_time, request.end_time),
            files=files
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
        "message": "Task queued for processing",
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
        message="Processing task started"
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

@app.get("/files")
async def list_processed_files():
    """List all processed data files."""
    try:
        # List files in the parts directory
        parts_dir = processor.parts_dir
        if not parts_dir.exists():
            return {"files": [], "total": 0}
        
        files = []
        for file_path in parts_dir.glob("*.nc"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file_path)
            })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files, "total": len(files)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/visualizations")
async def list_visualizations():
    """List all generated visualization files."""
    try:
        png_dir = processor.png_dir
        if not png_dir.exists():
            return {"images": [], "total": 0}
        
        images = []
        for file_path in png_dir.glob("*.png"):
            stat = file_path.stat()
            images.append({
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/static/images/{file_path.name}"  # Static file serving
            })
        
        images.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"images": images, "total": len(images)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

@app.post("/check-files", response_model=FileCheckResponse)
async def check_file_completeness(request: FileCheckRequest):
    """Check file integrity"""
    try:
    # Perform file integrity check
        results = file_monitor.check_file_completeness(
            timelims=(request.start_time, request.end_time),
            tstep=request.time_step_hours * 3600,  # Convert to seconds
            check_nc=request.check_nc,
            check_png=request.check_png
        )
        
        return FileCheckResponse(
            expected_files=results['expected_files'],
            nc_files=results['nc_files'],
            png_files=results['png_files'], 
            summary=results['summary'],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File check failed: {str(e)}")

@app.post("/repair-files", response_model=ProcessingStatus)
async def repair_missing_files(request: RepairRequest, background_tasks: BackgroundTasks):
    """Repair missing files"""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # First check file integrity
    try:
        check_results = file_monitor.check_file_completeness(
            timelims=(request.start_time, request.end_time),
            tstep=request.time_step_hours * 3600
        )
        
    # Count number of operations to repair
        nc_repairs = len(check_results['nc_files']['missing']) + len(check_results['nc_files']['corrupted'])
        png_only_repairs = [t for t in check_results['png_files']['missing'] 
                           if t in check_results['nc_files']['existing']]
        total_operations = nc_repairs + len(png_only_repairs)
        
        if total_operations == 0:
            return ProcessingStatus(
                task_id=task_id,
                status="completed",
                message="No files need repair - all files are complete",
                progress=100
            )
        
    # Store task info
        tasks[task_id] = {
            "status": "pending",
            "message": f"Queued repair for {total_operations} operations ({nc_repairs} NC + {len(png_only_repairs)} PNG)",
            "progress": 0,
            "request": request,
            "check_results": check_results
        }
        
    # Add background task
        background_tasks.add_task(
            run_repair_task,
            task_id,
            request,
            check_results
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="pending",
            message=f"Repair task started for {total_operations} operations"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair initialization failed: {str(e)}")

@app.get("/system-status")
async def get_system_status():
    """Get system status and health check"""
    try:
    # Check data integrity for test time range
        from datetime import datetime, timedelta
        
    # Use fixed test time range
        end_time = datetime.fromisoformat('2025-03-01T12:00:00')
        start_time = datetime.fromisoformat('2025-03-01T00:00:00')
        
        recent_check = file_monitor.check_file_completeness(
            timelims=(start_time.isoformat(), end_time.isoformat()),
            tstep=3600  # 每小时检查
        )
        
    # System info
        import psutil
        import os
        
        system_info = {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time()
            },
            "data_status": recent_check['summary'],
            "storage": {
                "base_dir": str(file_monitor.base_dir),
                "parts_files": len(list(file_monitor.parts_dir.glob("*.nc"))),
                "png_files": len(list(file_monitor.png_dir.glob("*.png")))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return system_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System status check failed: {str(e)}")

@app.post("/auto-monitor-repair")
async def auto_monitor_and_repair(background_tasks: BackgroundTasks):
    """Automatically monitor and repair missing files"""
    try:
    # Check file integrity
        check_results = file_monitor.check_file_completeness(
            timelims=('2025-03-01T00:00:00', '2025-03-01T12:00:00'),
            tstep=3600
        )
        
    # Count number of missing files
        total_missing = (len(check_results['nc_files']['missing']) + 
                        len(check_results['nc_files']['corrupted']) + 
                        len(check_results['png_files']['missing']))
        
        if total_missing == 0:
            return {
                "status": "complete",
                "message": "No missing files detected - all files are present",
                "missing_files": 0
            }
        
    # If missing files exist, automatically start repair
        import uuid
        task_id = str(uuid.uuid4())
        
        repair_request = RepairRequest(
            start_time='2025-03-01T00:00:00',
            end_time='2025-03-01T12:00:00',
            west_lon=113.0,
            east_lon=115.0,
            south_lat=-24.0,
            north_lat=-21.0,
            time_step_hours=1,
            repair_nc=True,
            repair_png=True
        )
        
    # Store task info
        tasks[task_id] = {
            "status": "pending",
            "message": f"Auto repair queued for {total_missing} missing files",
            "progress": 0,
            "request": repair_request,
            "check_results": check_results,
            "auto_triggered": True
        }
        
    # Add background task
        background_tasks.add_task(
            run_repair_task,
            task_id,
            repair_request,
            check_results
        )
        
        return {
            "status": "repair_started",
            "message": f"Auto repair started for {total_missing} missing files",
            "task_id": task_id,
            "missing_files": total_missing
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto monitor repair failed: {str(e)}")

async def run_processing_task(task_id: str, request: ProcessingRequest):
    """Background task for processing satellite data."""
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Processing satellite data..."
        tasks[task_id]["progress"] = 10
        
    # Run the actual processing
        await asyncio.to_thread(
            processor.process_time_series,
            timelims=(request.start_time, request.end_time),
            lonlims=(request.west_lon, request.east_lon),
            latlims=(request.south_lat, request.north_lat),
            tstep=request.time_step_hours * 3600  # Convert hours to seconds
        )
        
        # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "Processing completed successfully"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Processing failed: {str(e)}"
        tasks[task_id]["progress"] = 0

async def run_repair_task(task_id: str, request: RepairRequest, check_results: dict):
    """Background task for repairing missing files."""
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Repairing missing files..."
        tasks[task_id]["progress"] = 10
        
    # Count total number of files to repair
        nc_files_to_repair = len(check_results['nc_files']['missing']) + len(check_results['nc_files']['corrupted'])
        
    # PNG files are of two types: those needing NC download and those generated from existing NC
        png_files_missing = check_results['png_files']['missing']
        nc_existing = check_results['nc_files']['existing']
        png_only_repairs = [t for t in png_files_missing if t in nc_existing]
        
        total_operations = nc_files_to_repair
        if request.repair_png:
            total_operations += len(png_only_repairs)
        
        print(f"Starting repair: {nc_files_to_repair} NC files, {len(png_only_repairs)} PNG-only files...")
        
    # Update progress
        tasks[task_id]["progress"] = 20
        tasks[task_id]["message"] = f"Processing {total_operations} operations ({nc_files_to_repair} NC + {len(png_only_repairs)} PNG)..."
        
    # Run the actual repair
        await asyncio.to_thread(
            file_monitor.repair_missing_files,
            check_results=check_results,
            lonlims=(request.west_lon, request.east_lon),
            latlims=(request.south_lat, request.north_lat),
            repair_nc=request.repair_nc,
            repair_png=request.repair_png
        )
        
    # Update progress
        tasks[task_id]["progress"] = 90
        tasks[task_id]["message"] = "Verifying repaired files..."
        
    # Re-check file integrity to verify repair results
        verification_results = file_monitor.check_file_completeness(
            timelims=(request.start_time, request.end_time),
            tstep=request.time_step_hours * 3600,
            check_nc=request.repair_nc,
            check_png=request.repair_png
        )
        
    # Recalculate post-repair status
        remaining_nc = len(verification_results['nc_files']['missing']) + len(verification_results['nc_files']['corrupted'])
        remaining_png_only = [t for t in verification_results['png_files']['missing'] 
                             if t in verification_results['nc_files']['existing']]
        
        remaining_operations = remaining_nc + (len(remaining_png_only) if request.repair_png else 0)
        repaired_count = total_operations - remaining_operations
        
    # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = f"Repair completed: {repaired_count}/{total_operations} operations successful"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["verification_results"] = verification_results
        
        print(f"Repair completed: {repaired_count}/{total_operations} operations successful")
        
    except Exception as e:
    # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"File repair failed: {str(e)}"
        tasks[task_id]["progress"] = 0
        print(f"Repair failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_example:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
