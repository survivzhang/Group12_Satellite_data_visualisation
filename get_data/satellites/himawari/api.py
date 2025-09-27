"""
Himawari Satellite API Module

This module provides the Himawari-specific API implementation that integrates
with the existing himawari_processor.py and provides a clean interface for
the global API.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
import asyncio

# Add himawari_test_data to path for imports
himawari_path = Path(__file__).parent.parent.parent / "himawari_test_data"
if str(himawari_path) not in sys.path:
    sys.path.insert(0, str(himawari_path))

from satellites.shared.base_api import BaseSatelliteAPI
from satellites.shared.models import (
    ProcessingRequest, ProcessingStatus, FileInfo, HealthStatus, 
    SatelliteSystemStatus, SystemInfo, DataStatus, StorageInfo
)
from satellites.shared.utils import get_system_info, get_file_count

class HimawariAPI(BaseSatelliteAPI):
    """Himawari satellite API implementation"""
    
    def __init__(self):
        # Use unified directory structure: data/himawari/sst/
        unified_base_dir = Path(__file__).parent.parent.parent / "data" / "himawari" / "sst"
        super().__init__("Himawari-9", str(unified_base_dir))
        
        # Directory paths for unified structure
        self.nc_dir = self.base_dir / "nc"  # renamed from parts_dir
        self.png_dir = self.base_dir / "png"
        self.temp_dir = self.base_dir / "temp"
        
        # Legacy directory paths for backward compatibility
        self.legacy_base_dir = Path(__file__).parent.parent.parent / "himawari_test_data" / "data" / "himawari_l3c"
        self.legacy_parts_dir = self.legacy_base_dir / "parts"
        self.legacy_png_dir = self.legacy_base_dir / "png"
        self.legacy_temp_dir = self.legacy_base_dir / "temp"
        
        # Create unified directories
        self.nc_dir.mkdir(parents=True, exist_ok=True)
        self.png_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to import Himawari modules
        self.processor = None
        self.file_monitor = None
        self.tasks = {}  # In-memory task storage
        
        self._initialize_himawari_modules()
    
    def _initialize_himawari_modules(self):
        """Initialize Himawari processor and file monitor"""
        try:
            # Try to import himawari_processor
            himawari_processor = None
            try:
                import himawari_processor
                himawari_processor = himawari_processor
            except ImportError:
                # If direct import fails, try with sys.path manipulation
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "himawari_processor", 
                    himawari_path / "himawari_processor.py"
                )
                himawari_processor = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(himawari_processor)
            
            self.processor = himawari_processor.HimawariDataProcessor()
            self.file_monitor = himawari_processor.create_file_monitor()
            print("✅ Himawari modules initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize Himawari modules: {e}")
            self.processor = None
            self.file_monitor = None
    
    async def is_available(self) -> bool:
        """Check if Himawari API is available"""
        if self._available is not None:
            return self._available
        
        # Check if modules are loaded and directories exist (either unified or legacy)
        self._available = (
            self.processor is not None and
            (self.nc_dir.exists() or self.legacy_parts_dir.exists()) and
            (self.png_dir.exists() or self.legacy_png_dir.exists())
        )
        return self._available
    
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        if await self.is_available():
            return HealthStatus(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                message="Himawari API is operational"
            )
        else:
            return HealthStatus(
                status="unhealthy",
                timestamp=datetime.utcnow().isoformat(),
                message="Himawari modules not available",
                error="Processor or file monitor not initialized"
            )
    
    async def get_system_status(self) -> SatelliteSystemStatus:
        """Get detailed system status"""
        system_info = SystemInfo(**get_system_info())
        
        # Data status - count files from both unified and legacy directories
        nc_files = get_file_count(self.nc_dir, "*.nc") + get_file_count(self.legacy_parts_dir, "*.nc")
        png_files = get_file_count(self.png_dir, "*.png") + get_file_count(self.legacy_png_dir, "*.png")
        
        data_status = DataStatus(
            nc_files=nc_files,
            png_files=png_files,
            authenticated=self.processor is not None
        )
        
        # Storage info
        storage_info = StorageInfo(
            base_dir=str(self.base_dir),
            nc_files=nc_files,
            png_files=png_files,
            parts_files=nc_files  # Same as nc_files for Himawari
        )
        
        return SatelliteSystemStatus(
            system=system_info,
            data_status=data_status,
            storage=storage_info,
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def list_files(self, satellite: str, parameter: str, file_type: str) -> List[FileInfo]:
        """List files for Himawari satellite from both unified and legacy directories"""
        files = []
        
        # Determine directories to check
        directories = []
        pattern = f"*.{file_type}"
        
        if file_type == "nc":
            directories = [self.nc_dir, self.legacy_parts_dir]
        elif file_type == "png":
            directories = [self.png_dir, self.legacy_png_dir]
        else:
            return files
        
        # Collect files from all directories
        seen_filenames = set()  # Avoid duplicates
        for directory in directories:
            if directory.exists():
                for file_path in directory.glob(pattern):
                    if file_path.name not in seen_filenames:
                        file_info = self._create_file_info(file_path, satellite, parameter, file_type)
                        files.append(file_info)
                        seen_filenames.add(file_path.name)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.modified, reverse=True)
        return files
    
    async def get_nc_file_path(self, satellite: str, parameter: str, filename: str) -> Path:
        """Get NC file path for Himawari - try unified first, then legacy"""
        unified_path = self.nc_dir / filename
        if unified_path.exists():
            return unified_path
        
        legacy_path = self.legacy_parts_dir / filename
        if legacy_path.exists():
            return legacy_path
        
        # Default to unified path for new files
        return unified_path
    
    async def process_data(self, request: ProcessingRequest, background_tasks: BackgroundTasks) -> ProcessingStatus:
        """Process Himawari data"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="Himawari API not available")
        
        if not self._validate_request(request):
            raise HTTPException(status_code=400, detail="Invalid processing request")
        
        import uuid
        task_id = str(uuid.uuid4())
        
        # Store task info
        self.tasks[task_id] = {
            "status": "pending",
            "message": "Task queued for processing",
            "progress": 0,
            "request": request,
            "satellite": "himawari"
        }
        
        # Add background task
        background_tasks.add_task(
            self._run_processing_task,
            task_id,
            request
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="pending",
            message="Himawari processing task started",
            satellite="himawari"
        )
    
    async def get_task_status(self, task_id: str) -> ProcessingStatus:
        """Get processing task status"""
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_info = self.tasks[task_id]
        return ProcessingStatus(
            task_id=task_id,
            status=task_info["status"],
            message=task_info["message"],
            progress=task_info.get("progress"),
            satellite=task_info.get("satellite", "himawari")
        )
    
    async def handle_get_request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET requests to Himawari endpoints"""
        if not await self.is_available():
            if path in ["health", "files", "visualizations", "system-status"]:
                # Provide fallback responses
                return await self._handle_fallback_get(path)
            else:
                raise HTTPException(status_code=503, detail="Himawari API not available")
        
        # Delegate to processor methods
        if path == "health":
            health = await self.health_check()
            return {"status": health.status, "timestamp": health.timestamp}
        elif path == "files":
            return await self._list_processed_files()
        elif path == "files/png":
            result = await self._list_visualizations()
            # Convert images to files format for consistency
            return {
                "files": result.get("images", []),
                "total_count": result.get("total", 0),
                "timestamp": datetime.now().isoformat()
            }
        elif path == "files/nc":
            return await self._list_processed_files()
        elif path == "visualizations":
            return await self._list_visualizations()
        elif path == "system-status":
            status = await self.get_system_status()
            return status.dict()
        else:
            raise HTTPException(status_code=404, detail=f"Himawari endpoint '{path}' not found")
    
    async def handle_post_request(self, path: str, data: Dict[str, Any], background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
        """Handle POST requests to Himawari endpoints"""
        if not await self.is_available():
            return {"error": "Himawari API not available", "status": "module_unavailable"}
        
        try:
            if path == "query-data" and data:
                return await self._query_available_data(data)
            elif path == "process-data" and data:
                result = await self.process_data(ProcessingRequest(**data), background_tasks)
                return result.dict()
            elif path == "check-files" and data:
                return await self._check_file_completeness(data)
            elif path == "repair-files" and data:
                return await self._repair_missing_files(data, background_tasks)
            elif path == "auto-monitor-repair":
                return await self._auto_monitor_and_repair(background_tasks)
            else:
                raise HTTPException(status_code=404, detail=f"Himawari POST endpoint '{path}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Himawari POST request failed: {str(e)}")
    
    # Private helper methods
    
    async def _run_processing_task(self, task_id: str, request: ProcessingRequest):
        """Background task for processing Himawari data"""
        try:
            # Update status
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Processing Himawari data..."
            self.tasks[task_id]["progress"] = 10
            
            # Run the actual processing
            await asyncio.to_thread(
                self.processor.process_time_series,
                timelims=(request.start_time, request.end_time),
                lonlims=(request.west_lon, request.east_lon),
                latlims=(request.south_lat, request.north_lat),
                tstep=request.time_step_hours * 3600,
                    temp_range=(
                        request.temp_min, request.temp_max
                    ) if request.temp_min is not None and request.temp_max is not None else None,
                    units=(request.units or "K")
            )
            
            # Mark as completed
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["message"] = "Processing completed successfully"
            self.tasks[task_id]["progress"] = 100
            
        except Exception as e:
            # Mark as failed
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Processing failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _handle_fallback_get(self, path: str) -> Dict[str, Any]:
        """Handle GET requests when modules are not available"""
        if path == "health":
            return {"status": "module_unavailable", "message": "Himawari module not loaded"}
        elif path == "files":
            return await self._list_files_direct()
        elif path == "visualizations":
            return await self._list_visualizations_direct()
        elif path == "system-status":
            return {"status": "module_unavailable", "file_system": "accessible"}
        else:
            return {"error": f"Endpoint '{path}' not available"}
    
    async def _list_files_direct(self) -> Dict[str, Any]:
        """List NC files directly from filesystem"""
        try:
            files = []
            seen_filenames = set()
            
            # Check unified directory first
            if self.nc_dir.exists():
                for file_path in self.nc_dir.glob("*.nc"):
                    if file_path.name not in seen_filenames:
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": str(file_path),
                            "location": "unified"
                        })
                        seen_filenames.add(file_path.name)
            
            # Check legacy directory for additional files
            if self.legacy_parts_dir.exists():
                for file_path in self.legacy_parts_dir.glob("*.nc"):
                    if file_path.name not in seen_filenames:
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": str(file_path),
                            "location": "legacy"
                        })
                        seen_filenames.add(file_path.name)
            
            files.sort(key=lambda x: x["modified"], reverse=True)
            return {"files": files, "total": len(files)}
        except Exception as e:
            return {"files": [], "total": 0, "error": str(e)}
    
    async def _list_visualizations_direct(self) -> Dict[str, Any]:
        """List PNG files directly from filesystem"""
        try:
            images = []
            seen_filenames = set()
            
            # Check unified directory first
            if self.png_dir.exists():
                for file_path in self.png_dir.glob("*.png"):
                    if file_path.name not in seen_filenames:
                        stat = file_path.stat()
                        images.append({
                            "filename": file_path.name,
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "url": f"/static/himawari/sst/png/{file_path.name}",
                            "location": "unified"
                        })
                        seen_filenames.add(file_path.name)
            
            # Check legacy directory for additional files
            if self.legacy_png_dir.exists():
                for file_path in self.legacy_png_dir.glob("*.png"):
                    if file_path.name not in seen_filenames:
                        stat = file_path.stat()
                        images.append({
                            "filename": file_path.name,
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "url": f"/static/himawari/sst/png/{file_path.name}",
                            "location": "legacy"
                        })
                        seen_filenames.add(file_path.name)
            
            images.sort(key=lambda x: x["modified"], reverse=True)
            return {"images": images, "total": len(images)}
        except Exception as e:
            return {"images": [], "total": 0, "error": str(e)}
    
    async def _list_processed_files(self) -> Dict[str, Any]:
        """List processed files using processor"""
        files = []
        seen_filenames = set()
        
        # Check unified directory first
        if self.nc_dir.exists():
            for file_path in self.nc_dir.glob("*.nc"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(file_path)
                    })
                    seen_filenames.add(file_path.name)
        
        # Check legacy directory for additional files
        if self.legacy_parts_dir.exists():
            for file_path in self.legacy_parts_dir.glob("*.nc"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(file_path)
                    })
                    seen_filenames.add(file_path.name)
        
        files.sort(key=lambda x: x["modified"], reverse=True)
        return {"files": files, "total": len(files)}
    
    async def _list_visualizations(self) -> Dict[str, Any]:
        """List visualizations using processor"""
        images = []
        seen_filenames = set()
        
        # Check unified directory first
        if self.png_dir.exists():
            for file_path in self.png_dir.glob("*.png"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    images.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": f"/static/himawari/sst/png/{file_path.name}"
                    })
                    seen_filenames.add(file_path.name)
        
        # Check legacy directory for additional files
        if self.legacy_png_dir.exists():
            for file_path in self.legacy_png_dir.glob("*.png"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    images.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": f"/static/himawari/sst/png/{file_path.name}"
                    })
                    seen_filenames.add(file_path.name)
        
        images.sort(key=lambda x: x["modified"], reverse=True)
        return {"images": images, "total": len(images)}
    
    async def _query_available_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Query available data using processor"""
        request = ProcessingRequest(**data)
        
        # Query manifest
        manifest_df = self.processor.query_data_manifest(
            timelims=(request.start_time, request.end_time),
            lonlims=(request.west_lon, request.east_lon),
            latlims=(request.south_lat, request.north_lat)
        )
        
        files = manifest_df.to_dict('records') if not manifest_df.empty else []
        
        return {
            "total_files": len(files),
            "time_range": (request.start_time, request.end_time),
            "files": files
        }
    
    async def _check_file_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check file completeness using file monitor"""
        results = self.file_monitor.check_file_completeness(
            timelims=(data["start_time"], data["end_time"]),
            tstep=data.get("time_step_hours", 1) * 3600,
            check_nc=data.get("check_nc", True),
            check_png=data.get("check_png", True)
        )
        
        return {
            "expected_files": results['expected_files'],
            "nc_files": results['nc_files'],
            "png_files": results['png_files'],
            "summary": results['summary'],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _repair_missing_files(self, data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Repair missing files"""
        import uuid
        task_id = str(uuid.uuid4())
        
        # Store repair task
        self.tasks[task_id] = {
            "status": "pending",
            "message": "Repair task queued",
            "progress": 0,
            "satellite": "himawari"
        }
        
        # Add background task
        background_tasks.add_task(
            self._run_repair_task,
            task_id,
            data
        )
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Repair task started"
        }
    
    async def _run_repair_task(self, task_id: str, data: Dict[str, Any]):
        """Background task for repairing files"""
        try:
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Checking file completeness..."
            self.tasks[task_id]["progress"] = 10
            
            # First check which files are missing
            check_results = self.file_monitor.check_file_completeness(
                timelims=(data["start_time"], data["end_time"]),
                tstep=data.get("time_step_hours", 1) * 3600,
                check_nc=data.get("repair_nc", True),
                check_png=data.get("repair_png", True)
            )
            
            self.tasks[task_id]["message"] = "Starting file repair process..."
            self.tasks[task_id]["progress"] = 30
            
            # Run the actual repair using file monitor
            # Use the .netrc file in himawari_test_data directory
            from pathlib import Path
            netrc_path = Path(__file__).parent.parent.parent / "himawari_test_data" / ".netrc"
            
            await asyncio.to_thread(
                self.file_monitor.repair_missing_files,
                check_results=check_results,
                lonlims=(data["west_lon"], data["east_lon"]),
                latlims=(data["south_lat"], data["north_lat"]),
                netrc_path=netrc_path,
                repair_nc=data.get("repair_nc", True),
                repair_png=data.get("repair_png", True)
            )
            
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["message"] = "File repair completed successfully"
            self.tasks[task_id]["progress"] = 100
            
        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Repair failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _auto_monitor_and_repair(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Auto monitor and repair"""
        # Check for missing files and start repair if needed
        check_results = self.file_monitor.check_file_completeness(
            timelims=('2025-09-12T00:00:00', datetime.utcnow().isoformat()),
            tstep=3600
        )
        
        total_missing = (len(check_results['nc_files']['missing']) + 
                        len(check_results['nc_files']['corrupted']) + 
                        len(check_results['png_files']['missing']))
        
        if total_missing == 0:
            return {
                "status": "complete",
                "message": "No missing files detected",
                "missing_files": 0
            }
        else:
            # Start repair task
            repair_data = {
                "start_time": '2025-09-12T00:00:00',
                "end_time": datetime.utcnow().isoformat(),
                "west_lon": 111.0,
                "east_lon": 114.0,
                "south_lat": -25.0,
                "north_lat": -20.0
            }
            
            return await self._repair_missing_files(repair_data, background_tasks)
