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

from himawari_processor import HimawariDataProcessor

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

# Global processor instance
processor = HimawariDataProcessor()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_example:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
