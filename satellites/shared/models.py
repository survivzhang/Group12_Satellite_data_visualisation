"""
Shared Pydantic models for all satellite APIs

This module contains common data models used across all satellite APIs
to ensure consistency and reduce duplication.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Base satellite information models
class SatelliteInfo(BaseModel):
    """Information about a satellite"""
    name: str
    description: str
    available: bool
    parameters: Dict[str, Dict[str, str]]

class ParameterInfo(BaseModel):
    """Information about a satellite parameter"""
    name: str
    unit: str
    description: str
    file_types: List[str]

class FileInfo(BaseModel):
    """Information about a data file"""
    filename: str
    size_bytes: int
    modified: str
    url: str
    layer: Optional[str] = None
    satellite: Optional[str] = None
    data_type: Optional[str] = None

# Request models
class DataRequest(BaseModel):
    """Base data request"""
    satellite: str
    parameter: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    region: Optional[Dict[str, float]] = None

class ProcessingRequest(BaseModel):
    """Unified processing request"""
    satellite: str
    parameter: str
    start_time: str
    end_time: str
    west_lon: float
    east_lon: float
    south_lat: float
    north_lat: float
    time_step_hours: int = 1
    # Optional satellite-specific parameters
    layer_keys: Optional[List[str]] = None  # For Sentinel-3
    consumer_key: Optional[str] = None      # For EUMETView
    consumer_secret: Optional[str] = None   # For EUMETView

class ProcessingStatus(BaseModel):
    """Processing task status"""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str
    progress: Optional[int] = None
    satellite: Optional[str] = None

# File management models
class FileCheckRequest(BaseModel):
    """File integrity check request"""
    start_time: str
    end_time: str
    time_step_hours: int = 1
    check_nc: bool = True
    check_png: bool = True
    # Satellite-specific fields
    nc_file_path: Optional[str] = None  # For Sentinel-3 single file check

class FileCheckResponse(BaseModel):
    """File integrity check response"""
    expected_files: Optional[int] = None
    nc_files: Optional[Dict] = None
    png_files: Optional[Dict] = None
    summary: Optional[Dict] = None
    # Sentinel-3 specific fields
    nc_exists: Optional[bool] = None
    nc_modified_time: Optional[str] = None
    png_count: Optional[int] = None
    needs_regeneration: Optional[bool] = None
    message: str
    timestamp: str

class RepairRequest(BaseModel):
    """File repair request"""
    start_time: str
    end_time: str
    west_lon: float
    east_lon: float
    south_lat: float
    north_lat: float
    time_step_hours: int = 1
    repair_nc: bool = True
    repair_png: bool = True
    # Sentinel-3 specific
    nc_file_path: Optional[str] = None

# System status models
class SystemInfo(BaseModel):
    """System information"""
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    uptime: float

class StorageInfo(BaseModel):
    """Storage information"""
    base_dir: str
    nc_files: Optional[int] = None
    png_files: Optional[int] = None
    parts_files: Optional[int] = None

class DataStatus(BaseModel):
    """Data status information"""
    nc_files: Optional[int] = None
    png_files: Optional[int] = None
    authenticated: Optional[bool] = None
    # Additional status fields can be added as needed

class SatelliteSystemStatus(BaseModel):
    """Individual satellite system status"""
    system: SystemInfo
    data_status: DataStatus
    storage: StorageInfo
    timestamp: str

class UnifiedSystemStatus(BaseModel):
    """Unified system status across all satellites"""
    global_api: Dict[str, Any]
    satellites: Dict[str, Dict[str, Any]]

# Data manifest models
class LayerInfo(BaseModel):
    """Information about a data layer (for Sentinel-3)"""
    key: str
    name: str
    description: str
    data_type: str
    satellite: str

class DataManifest(BaseModel):
    """Data availability manifest"""
    # For Himawari
    total_files: Optional[int] = None
    time_range: Optional[Tuple[str, str]] = None
    files: Optional[List[dict]] = None
    # For Sentinel-3
    available_layers: Optional[List[LayerInfo]] = None
    supported_formats: Optional[List[str]] = None
    region: Optional[Tuple[float, float, float, float]] = None

# Response models
class FileListResponse(BaseModel):
    """File list response"""
    files: List[dict]
    total: int
    by_layer: Optional[Dict[str, int]] = None

class VisualizationListResponse(BaseModel):
    """Visualization list response"""
    images: List[dict]
    total: int
    by_layer: Optional[Dict[str, int]] = None

# Health check models
class HealthStatus(BaseModel):
    """Health check status"""
    status: str
    timestamp: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
