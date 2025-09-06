"""
FastAPI Backend Example for AODN HF Radar Current Data

This demonstrates how to create a REST API for AODN HF Radar data processing,
following the same patterns as the Himawari satellite data API.
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
import calendar
import uuid
import os
import glob

from aodn_hf_radar_processor import HFRadarProcessor

app = FastAPI(
    title="AODN HF Radar Data API",
    description="API for processing and accessing AODN HF Radar current data",
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

# Global processor instance
processor = HFRadarProcessor()

# Mount static files for PNG images and GIF animations
png_directory = processor.png_dir
gif_directory = processor.gif_dir
png_directory.mkdir(parents=True, exist_ok=True)
gif_directory.mkdir(parents=True, exist_ok=True)

app.mount("/static/images", StaticFiles(directory=str(png_directory)), name="images")
app.mount("/static/gifs", StaticFiles(directory=str(gif_directory)), name="gifs")

# Pydantic models for request/response
class RadarProcessingRequest(BaseModel):
    year: int
    month: int
    region: str = "NWA"  # Default to North West Australia
    qc_dir: str = "gridded_1h-avg-current-map_non-QC"
    # Spatial bounds for visualization (different from Himawari's lonlims/latlims)
    west_lon: float = 111.0
    east_lon: float = 114.0
    south_lat: float = -25.0
    north_lat: float = -20.0
    download: bool = True
    combine_daily: bool = False
    make_gif: bool = True
    step: int = 1  # Quiver plot decimation step
    gif_duration: float = 0.4

class RadarQueryRequest(BaseModel):
    year: int
    month: int
    region: str = "NWA"
    qc_dir: str = "gridded_1h-avg-current-map_non-QC"

class ProcessingStatus(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str
    progress: Optional[int] = None

class RadarDataManifest(BaseModel):
    total_keys: int
    year_month: str
    region: str
    qc_directory: str
    keys: List[str]
    sample_keys: List[str]  # First few keys for preview

class FileCheckRequest(BaseModel):
    year: int
    month: int
    region: str = "NWA"
    qc_dir: str = "gridded_1h-avg-current-map_non-QC"
    check_raw: bool = True
    check_daily: bool = True
    check_png: bool = True
    check_gif: bool = True

class FileCheckResponse(BaseModel):
    expected_days: int
    raw_files: dict
    daily_files: dict
    png_files: dict
    gif_file: dict
    summary: dict
    timestamp: str

class RepairRequest(BaseModel):
    year: int
    month: int
    region: str = "NWA"
    qc_dir: str = "gridded_1h-avg-current-map_non-QC"
    west_lon: float = 111.0
    east_lon: float = 114.0
    south_lat: float = -25.0
    north_lat: float = -20.0
    repair_raw: bool = True
    repair_daily: bool = False
    repair_visualizations: bool = True

# In-memory task storage (use Redis in production)
tasks = {}

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "AODN HF Radar Data API",
        "version": "1.0.0",
        "description": "API for IMOS ACORN HF Radar gridded current maps from AODN S3",
        "endpoints": {
            "query": "/query-data",
            "process": "/process-data", 
            "status": "/status/{task_id}",
            "files": "/files",
            "visualizations": "/visualizations",
            "check-files": "/check-files",
            "repair-files": "/repair-files",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/query-data", response_model=RadarDataManifest)
async def query_available_data(request: RadarQueryRequest):
    """Query available HF Radar data keys for given year/month/region."""
    try:
        # Query available keys from S3
        keys = processor.month_keys(
            year=request.year,
            month=request.month,
            region=request.region,
            qc_dir=request.qc_dir
        )
        
        # Get sample keys for preview (first 10)
        sample_keys = keys[:10] if len(keys) > 10 else keys
        
        return RadarDataManifest(
            total_keys=len(keys),
            year_month=f"{request.year}-{request.month:02d}",
            region=request.region,
            qc_directory=request.qc_dir,
            keys=keys,
            sample_keys=sample_keys
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/process-data", response_model=ProcessingStatus)
async def process_radar_data(request: RadarProcessingRequest, background_tasks: BackgroundTasks):
    """Start processing HF Radar data in the background."""
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
        run_radar_processing_task,
        task_id,
        request
    )
    
    return ProcessingStatus(
        task_id=task_id,
        status="pending",
        message="HF Radar processing task started"
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
        files_info = {
            "raw_files": [],
            "daily_files": [],
            "total_raw": 0,
            "total_daily": 0
        }
        
        # List raw files
        raw_dir = processor.data_dir / "RAW"
        if raw_dir.exists():
            for file_path in raw_dir.rglob("*.nc"):
                stat = file_path.stat()
                files_info["raw_files"].append({
                    "filename": file_path.name,
                    "relative_path": str(file_path.relative_to(raw_dir)),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # List daily combined files
        daily_dir = processor.data_dir / "DAILY"
        if daily_dir.exists():
            for file_path in daily_dir.rglob("*.nc"):
                stat = file_path.stat()
                files_info["daily_files"].append({
                    "filename": file_path.name,
                    "relative_path": str(file_path.relative_to(daily_dir)),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by modification time (newest first)
        files_info["raw_files"].sort(key=lambda x: x["modified"], reverse=True)
        files_info["daily_files"].sort(key=lambda x: x["modified"], reverse=True)
        
        files_info["total_raw"] = len(files_info["raw_files"])
        files_info["total_daily"] = len(files_info["daily_files"])
        
        return files_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/visualizations")
async def list_visualizations():
    """List all generated visualization files (PNGs and GIFs)."""
    try:
        viz_info = {
            "png_files": [],
            "gif_files": [],
            "total_png": 0,
            "total_gif": 0
        }
        
        # List PNG files
        if processor.png_dir.exists():
            for file_path in processor.png_dir.rglob("*.png"):
                stat = file_path.stat()
                viz_info["png_files"].append({
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/static/images/{file_path.name}"
                })
        
        # List GIF files
        if processor.gif_dir.exists():
            for file_path in processor.gif_dir.glob("*.gif"):
                stat = file_path.stat()
                viz_info["gif_files"].append({
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/static/gifs/{file_path.name}"
                })
        
        # Sort by modification time (newest first)
        viz_info["png_files"].sort(key=lambda x: x["modified"], reverse=True)
        viz_info["gif_files"].sort(key=lambda x: x["modified"], reverse=True)
        
        viz_info["total_png"] = len(viz_info["png_files"])
        viz_info["total_gif"] = len(viz_info["gif_files"])
        
        return viz_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list visualizations: {str(e)}")

@app.post("/check-files", response_model=FileCheckResponse)
async def check_file_completeness(request: FileCheckRequest):
    """Check file integrity for HF Radar data."""
    try:
        # Generate expected file structure based on year/month
        ndays = calendar.monthrange(request.year, request.month)[1]
        expected_days = ndays
        
        results = {
            'expected_days': expected_days,
            'raw_files': {'existing_days': 0, 'missing_days': [], 'total_files': 0},
            'daily_files': {'existing': [], 'missing': []},
            'png_files': {'existing': 0, 'total_expected': 0},
            'gif_file': {'exists': False, 'path': None},
            'summary': {}
        }
        
        # Check raw files
        if request.check_raw:
            results['raw_files'] = _check_raw_files(request, ndays)
        
        # Check daily combined files  
        if request.check_daily:
            results['daily_files'] = _check_daily_files(request, ndays)
        
        # Check PNG files
        if request.check_png:
            results['png_files'] = _check_png_files(request)
        
        # Check GIF file
        if request.check_gif:
            results['gif_file'] = _check_gif_file(request)
        
        # Generate summary
        results['summary'] = _generate_file_summary(results)
        
        return FileCheckResponse(
            expected_days=results['expected_days'],
            raw_files=results['raw_files'],
            daily_files=results['daily_files'],
            png_files=results['png_files'],
            gif_file=results['gif_file'],
            summary=results['summary'],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File check failed: {str(e)}")

@app.post("/repair-files", response_model=ProcessingStatus)
async def repair_missing_files(request: RepairRequest, background_tasks: BackgroundTasks):
    """Repair missing HF Radar files."""
    task_id = str(uuid.uuid4())
    
    try:
        # First check what needs repair
        check_request = FileCheckRequest(
            year=request.year,
            month=request.month,
            region=request.region,
            qc_dir=request.qc_dir,
            check_raw=request.repair_raw,
            check_daily=request.repair_daily,
            check_png=request.repair_visualizations,
            check_gif=request.repair_visualizations
        )
        
        check_results = await check_file_completeness(check_request)
        
        # Count operations needed
        operations_needed = 0
        if request.repair_raw:
            operations_needed += len(check_results.raw_files.get('missing_days', []))
        if request.repair_daily:
            operations_needed += len(check_results.daily_files.get('missing', []))
        if request.repair_visualizations:
            if not check_results.gif_file.get('exists', False):
                operations_needed += 1
        
        if operations_needed == 0:
            return ProcessingStatus(
                task_id=task_id,
                status="completed",
                message="No files need repair - all files are complete",
                progress=100
            )
        
        # Store task info
        tasks[task_id] = {
            "status": "pending",
            "message": f"Queued repair for {operations_needed} operations",
            "progress": 0,
            "request": request,
            "check_results": check_results
        }
        
        # Add background task
        background_tasks.add_task(
            run_radar_repair_task,
            task_id,
            request,
            check_results
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="pending",
            message=f"Repair task started for {operations_needed} operations"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair initialization failed: {str(e)}")

@app.get("/system-status")
async def get_system_status():
    """Get system status and health check."""
    try:
        # Use current month for status check
        current_date = datetime.utcnow()
        
        # Check data integrity for current month
        recent_check = await check_file_completeness(FileCheckRequest(
            year=current_date.year,
            month=current_date.month,
            region="NWA"  # Default region
        ))
        
        # System info
        try:
            import psutil
            system_info = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time()
            }
        except ImportError:
            system_info = {"note": "psutil not available for system metrics"}
        
        status_info = {
            "system": system_info,
            "data_status": recent_check.summary,
            "storage": {
                "base_dir": str(processor.base_dir),
                "raw_files": len(list(processor.data_dir.rglob("*.nc"))) if processor.data_dir.exists() else 0,
                "png_files": len(list(processor.png_dir.glob("*.png"))) if processor.png_dir.exists() else 0,
                "gif_files": len(list(processor.gif_dir.glob("*.gif"))) if processor.gif_dir.exists() else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return status_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System status check failed: {str(e)}")

# Background task functions
async def run_radar_processing_task(task_id: str, request: RadarProcessingRequest):
    """Background task for processing HF Radar data."""
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Processing HF Radar data..."
        tasks[task_id]["progress"] = 10
        
        # Run the actual processing using the end-to-end method
        await asyncio.to_thread(
            processor.run_month_end_to_end,
            year=request.year,
            month=request.month,
            region=request.region,
            qc_dir=request.qc_dir,
            download=request.download,
            combine_daily=request.combine_daily,
            make_gif=request.make_gif,
            lon_range=(request.west_lon, request.east_lon),
            lat_range=(request.south_lat, request.north_lat),
            step=request.step
        )
        
        # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "HF Radar processing completed successfully"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Processing failed: {str(e)}"
        tasks[task_id]["progress"] = 0

async def run_radar_repair_task(task_id: str, request: RepairRequest, check_results):
    """Background task for repairing missing HF Radar files."""
    try:
        # Update status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["message"] = "Repairing missing HF Radar files..."
        tasks[task_id]["progress"] = 10
        
        repair_count = 0
        
        # Repair raw files if needed
        if request.repair_raw and check_results.raw_files.get('missing_days'):
            tasks[task_id]["progress"] = 30
            tasks[task_id]["message"] = "Downloading missing raw files..."
            
            await asyncio.to_thread(
                processor.download_raw_month,
                year=request.year,
                month=request.month,
                region=request.region,
                qc_dir=request.qc_dir
            )
            repair_count += 1
        
        # Repair daily files if needed
        if request.repair_daily and check_results.daily_files.get('missing'):
            tasks[task_id]["progress"] = 60
            tasks[task_id]["message"] = "Creating missing daily combined files..."
            
            await asyncio.to_thread(
                processor.combine_month_days,
                year=request.year,
                month=request.month,
                region=request.region,
                qc_dir=request.qc_dir
            )
            repair_count += 1
        
        # Repair visualizations if needed
        if request.repair_visualizations and not check_results.gif_file.get('exists'):
            tasks[task_id]["progress"] = 80
            tasks[task_id]["message"] = "Generating missing visualizations..."
            
            await asyncio.to_thread(
                processor.render_month_pngs_and_gif,
                year=request.year,
                month=request.month,
                region=request.region,
                lon_range=(request.west_lon, request.east_lon),
                lat_range=(request.south_lat, request.north_lat),
                step=1
            )
            repair_count += 1
        
        # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = f"Repair completed: {repair_count} operations successful"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Repair failed: {str(e)}"
        tasks[task_id]["progress"] = 0

# Helper functions for file checking
def _check_raw_files(request: FileCheckRequest, ndays: int) -> dict:
    """Check existence of raw files."""
    raw_dir = processor.data_dir / "RAW" / request.region / f"{request.year:04d}" / f"{request.month:02d}"
    
    existing_days = 0
    missing_days = []
    total_files = 0
    
    for day in range(1, ndays + 1):
        day_dir = raw_dir / f"{day:02d}"
        if day_dir.exists():
            day_files = list(day_dir.glob("*.nc"))
            if day_files:
                existing_days += 1
                total_files += len(day_files)
            else:
                missing_days.append(day)
        else:
            missing_days.append(day)
    
    return {
        'existing_days': existing_days,
        'missing_days': missing_days,
        'total_files': total_files
    }

def _check_daily_files(request: FileCheckRequest, ndays: int) -> dict:
    """Check existence of daily combined files."""
    daily_dir = processor.data_dir / "DAILY" / request.region / f"{request.year:04d}" / f"{request.month:02d}"
    
    existing = []
    missing = []
    
    for day in range(1, ndays + 1):
        expected_file = daily_dir / f"ACORN_{request.region}_{request.year}{request.month:02d}{day:02d}.nc"
        if expected_file.exists():
            existing.append(day)
        else:
            missing.append(day)
    
    return {
        'existing': existing,
        'missing': missing
    }

def _check_png_files(request: FileCheckRequest) -> dict:
    """Check existence of PNG files."""
    png_dir = processor.png_dir / f"{request.region}_{request.year}_{request.month:02d}"
    
    existing_count = 0
    total_expected = 0  # This would need to be calculated based on available data
    
    if png_dir.exists():
        existing_count = len(list(png_dir.glob("*.png")))
    
    return {
        'existing': existing_count,
        'total_expected': total_expected  # Placeholder - would need actual calculation
    }

def _check_gif_file(request: FileCheckRequest) -> dict:
    """Check existence of GIF file."""
    gif_path = processor.gif_dir / f"HFRadar_{request.region}_{request.year}-{request.month:02d}.gif"
    
    return {
        'exists': gif_path.exists(),
        'path': str(gif_path) if gif_path.exists() else None
    }

def _generate_file_summary(results: dict) -> dict:
    """Generate summary of file check results."""
    return {
        'raw_completion_rate': f"{(results['raw_files']['existing_days']/results['expected_days'])*100:.1f}%" if results['expected_days'] > 0 else "0%",
        'daily_completion_rate': f"{(len(results['daily_files']['existing'])/results['expected_days'])*100:.1f}%" if results['expected_days'] > 0 else "0%",
        'visualizations_complete': results['gif_file']['exists'],
        'total_png_files': results['png_files']['existing']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "aodn_hf_radar_api_example:app", 
        host="0.0.0.0", 
        port=8001,  # Different port from Himawari API
        reload=True,
        log_level="info"
    )
