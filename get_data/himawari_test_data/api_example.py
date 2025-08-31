"""
FastAPI Backend Example for Himawari Satellite Data

This demonstrates how to create a REST API for your satellite data processing.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    """检查文件完整性"""
    try:
        # 执行文件完整性检查
        results = file_monitor.check_file_completeness(
            timelims=(request.start_time, request.end_time),
            tstep=request.time_step_hours * 3600,  # 转换为秒
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
    """修复丢失的文件"""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # 先检查文件完整性
    try:
        check_results = file_monitor.check_file_completeness(
            timelims=(request.start_time, request.end_time),
            tstep=request.time_step_hours * 3600
        )
        
        # 统计需要修复的文件数量
        files_to_repair = len(check_results['nc_files']['missing']) + len(check_results['nc_files']['corrupted'])
        
        if files_to_repair == 0:
            return ProcessingStatus(
                task_id=task_id,
                status="completed",
                message="No files need repair - all files are complete",
                progress=100
            )
        
        # 存储任务信息
        tasks[task_id] = {
            "status": "pending",
            "message": f"Queued repair for {files_to_repair} files",
            "progress": 0,
            "request": request,
            "check_results": check_results
        }
        
        # 添加后台任务
        background_tasks.add_task(
            run_repair_task,
            task_id,
            request,
            check_results
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="pending",
            message=f"Repair task started for {files_to_repair} files"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair initialization failed: {str(e)}")

@app.get("/system-status")
async def get_system_status():
    """获取系统状态和健康检查"""
    try:
        # 检查最近7天的数据完整性
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        recent_check = file_monitor.check_file_completeness(
            timelims=(start_time.isoformat(), end_time.isoformat()),
            tstep=3600  # 每小时检查
        )
        
        # 系统信息
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
        
        # Run the actual repair
        await asyncio.to_thread(
            file_monitor.repair_missing_files,
            check_results=check_results,
            lonlims=(request.west_lon, request.east_lon),
            latlims=(request.south_lat, request.north_lat),
            repair_nc=request.repair_nc,
            repair_png=request.repair_png
        )
        
        # Mark as completed
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "File repair completed successfully"
        tasks[task_id]["progress"] = 100
        
    except Exception as e:
        # Mark as failed
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"File repair failed: {str(e)}"
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
