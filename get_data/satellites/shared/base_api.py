"""
Base API class for satellite-specific APIs

This module provides a base class that defines the common interface
all satellite APIs must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks
from datetime import datetime

from .models import (
    ProcessingRequest, ProcessingStatus, FileInfo, 
    HealthStatus, SatelliteSystemStatus
)

class BaseSatelliteAPI(ABC):
    """
    Base class for satellite-specific APIs
    
    This abstract base class defines the interface that all satellite APIs
    must implement to ensure consistency across different satellite data sources.
    """
    
    def __init__(self, name: str, base_dir: str):
        """
        Initialize the satellite API
        
        Args:
            name: Satellite name
            base_dir: Base data directory
        """
        self.name = name
        self.base_dir = Path(base_dir)
        self._available = None  # Cache availability status
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the satellite API is available and operational
        
        Returns:
            True if the API is available
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Perform health check
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def get_system_status(self) -> SatelliteSystemStatus:
        """
        Get detailed system status
        
        Returns:
            System status information
        """
        pass
    
    @abstractmethod
    async def list_files(self, satellite: str, parameter: str, file_type: str) -> List[FileInfo]:
        """
        List files for a specific satellite/parameter/file_type combination
        
        Args:
            satellite: Satellite identifier
            parameter: Parameter name (e.g., 'sst', 'chl')
            file_type: File type ('nc' or 'png')
            
        Returns:
            List of file information
        """
        pass
    
    @abstractmethod
    async def get_nc_file_path(self, satellite: str, parameter: str, filename: str) -> Path:
        """
        Get the file system path for an NC file
        
        Args:
            satellite: Satellite identifier
            parameter: Parameter name
            filename: File name
            
        Returns:
            Path to the NC file
        """
        pass
    
    @abstractmethod
    async def process_data(self, request: ProcessingRequest, background_tasks: BackgroundTasks) -> ProcessingStatus:
        """
        Process satellite data
        
        Args:
            request: Processing request
            background_tasks: FastAPI background tasks
            
        Returns:
            Processing status
        """
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> ProcessingStatus:
        """
        Get the status of a processing task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Processing status
        """
        pass
    
    @abstractmethod
    async def handle_get_request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GET requests to satellite-specific endpoints
        
        Args:
            path: Request path
            params: Query parameters
            
        Returns:
            Response data
        """
        pass
    
    @abstractmethod
    async def handle_post_request(self, path: str, data: Dict[str, Any], background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
        """
        Handle POST requests to satellite-specific endpoints
        
        Args:
            path: Request path
            data: Request data
            background_tasks: FastAPI background tasks
            
        Returns:
            Response data
        """
        pass
    
    # Common utility methods (can be overridden)
    
    def _get_data_directories(self) -> Dict[str, Path]:
        """
        Get data directory paths
        
        Returns:
            Dictionary of directory paths
        """
        return {
            "base": self.base_dir,
            "nc": self.base_dir,
            "png": self.base_dir
        }
    
    def _validate_request(self, request: ProcessingRequest) -> bool:
        """
        Validate processing request
        
        Args:
            request: Processing request to validate
            
        Returns:
            True if request is valid
        """
        # Basic validation - can be extended by subclasses
        return (
            request.satellite and
            request.parameter and
            request.start_time and
            request.end_time and
            isinstance(request.west_lon, (int, float)) and
            isinstance(request.east_lon, (int, float)) and
            isinstance(request.south_lat, (int, float)) and
            isinstance(request.north_lat, (int, float))
        )
    
    def _create_file_info(self, file_path: Path, satellite: str, parameter: str, file_type: str) -> FileInfo:
        """
        Create FileInfo object from file path
        
        Args:
            file_path: Path to the file
            satellite: Satellite identifier
            parameter: Parameter name
            file_type: File type
            
        Returns:
            FileInfo object
        """
        stat = file_path.stat()
        
        # Generate appropriate URL
        if file_type == "png":
            url = f"/static/{satellite}/{parameter}/png/{file_path.name}"
        else:
            url = f"/api/v1/satellites/{satellite}/{parameter}/nc/{file_path.name}"
        
        return FileInfo(
            filename=file_path.name,
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            url=url,
            satellite=satellite,
            data_type=parameter
        )
