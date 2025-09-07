"""
Shared utilities for satellite APIs

This module contains common utility functions used across all satellite APIs.
"""

import psutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def setup_satellite_static_files(app: FastAPI, satellites: Dict[str, Any]):
    """
    Setup static file serving for all satellites
    
    Args:
        app: FastAPI application instance
        satellites: Dictionary of satellite configurations
    """
    base_path = Path(__file__).parent.parent.parent  # Go up to get_data directory
    
    for satellite_id, config in satellites.items():
        try:
            # Setup static file serving based on satellite type
            if satellite_id == "himawari":
                # Himawari structure: himawari_test_data/data/himawari_l3c/png/
                png_dir = base_path / "himawari_test_data" / "data" / "himawari_l3c" / "png"
                if png_dir.exists():
                    mount_path = f"/static/{satellite_id}/sst/png"
                    app.mount(mount_path, StaticFiles(directory=str(png_dir)), name=f"{satellite_id}_sst_png")
                    print(f"✅ Mounted static files: {mount_path} -> {png_dir}")
                else:
                    print(f"⚠️ PNG directory not found: {png_dir}")
                    
            else:
                # Sentinel structure: saternal3/data/eumetview_sentinel3/satellite/parameter/png/
                for param_id in config.get("parameters", {}):
                    png_dir = base_path / "saternal3" / "data" / "eumetview_sentinel3" / satellite_id / param_id / "png"
                    if png_dir.exists():
                        mount_path = f"/static/{satellite_id}/{param_id}/png"
                        app.mount(mount_path, StaticFiles(directory=str(png_dir)), name=f"{satellite_id}_{param_id}_png")
                        print(f"✅ Mounted static files: {mount_path} -> {png_dir}")
                    else:
                        print(f"⚠️ PNG directory not found: {png_dir}")
                        
        except Exception as e:
            print(f"⚠️ Failed to mount static files for {satellite_id}: {e}")

def get_system_info() -> Dict[str, Any]:
    """
    Get system information (CPU, memory, disk usage)
    
    Returns:
        Dictionary with system information
    """
    try:
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "uptime": time.time() - psutil.boot_time()
        }
    except Exception as e:
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_usage": 0.0,
            "uptime": 0.0,
            "error": str(e)
        }

def get_file_count(directory: Path, pattern: str = "*") -> int:
    """
    Count files in a directory
    
    Args:
        directory: Directory path
        pattern: File pattern to match
        
    Returns:
        Number of matching files
    """
    try:
        if not directory.exists():
            return 0
        return len(list(directory.glob(pattern)))
    except Exception:
        return 0

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_coordinates(west_lon: float, east_lon: float, south_lat: float, north_lat: float) -> bool:
    """
    Validate coordinate bounds
    
    Args:
        west_lon: Western longitude
        east_lon: Eastern longitude  
        south_lat: Southern latitude
        north_lat: Northern latitude
        
    Returns:
        True if coordinates are valid
    """
    return (
        -180 <= west_lon <= 180 and
        -180 <= east_lon <= 180 and
        -90 <= south_lat <= 90 and
        -90 <= north_lat <= 90 and
        west_lon < east_lon and
        south_lat < north_lat
    )

def validate_time_range(start_time: str, end_time: str) -> bool:
    """
    Validate time range format and order
    
    Args:
        start_time: Start time in ISO format
        end_time: End time in ISO format
        
    Returns:
        True if time range is valid
    """
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        return start_dt < end_dt
    except Exception:
        return False

def create_error_response(error: str, details: str = None) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error: Error message
        details: Additional error details
        
    Returns:
        Error response dictionary
    """
    response = {
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        response["details"] = details
        
    return response

def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """
    Create standardized success response
    
    Args:
        message: Success message
        data: Response data
        
    Returns:
        Success response dictionary
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
        
    return response
