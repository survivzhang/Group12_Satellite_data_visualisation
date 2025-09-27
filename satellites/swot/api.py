"""
SWOT Satellite API Module

This module provides the SWOT-specific API implementation that integrates
with the swot_processor.py and provides a clean interface for the global API.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
import asyncio

# Add SWOT processor path for imports
swot_path = Path(__file__).parent.parent.parent / "get_data" / "SWOT"
if str(swot_path) not in sys.path:
    sys.path.insert(0, str(swot_path))

from satellites.shared.base_api import BaseSatelliteAPI
from satellites.shared.models import (
    ProcessingRequest, ProcessingStatus, FileInfo, HealthStatus,
    SatelliteSystemStatus, SystemInfo, DataStatus, StorageInfo
)
from satellites.shared.utils import get_system_info, get_file_count

class SwotAPI(BaseSatelliteAPI):
    """SWOT satellite API implementation"""
    
    def __init__(self):
        # Base directory for SWOT data using unified structure
        base_dir = Path(__file__).parent.parent.parent / "get_data" / "data"
        super().__init__("SWOT", str(base_dir))
        
        # Initialize processor, workflow, and file monitor
        self.processor = None
        self.workflow = None
        self.file_monitor = None
        self.tasks = {}  # In-memory task storage
        
        self._initialize_swot_modules()
    
    def _initialize_swot_modules(self):
        """Initialize SWOT processor, workflow, and file monitor"""
        try:
            # Try to import swot_processor
            swot_processor = None
            try:
                import swot_processor
                swot_processor = swot_processor
            except ImportError:
                # If direct import fails, try with sys.path manipulation
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "swot_processor",
                    swot_path / "swot_processor.py"
                )
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load swot_processor from {swot_path / 'swot_processor.py'}")
                swot_processor = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(swot_processor)
            
            # Initialize components with error handling
            if hasattr(swot_processor, 'SwotDataProcessor'):
                self.processor = swot_processor.SwotDataProcessor(str(self.base_dir))
            else:
                raise AttributeError("SwotDataProcessor class not found in swot_processor module")
                
            if hasattr(swot_processor, 'SwotWorkflow'):
                self.workflow = swot_processor.SwotWorkflow(str(self.base_dir))
            else:
                raise AttributeError("SwotWorkflow class not found in swot_processor module")
                
            if hasattr(swot_processor, 'create_file_monitor'):
                self.file_monitor = swot_processor.create_file_monitor(str(self.base_dir))
            else:
                raise AttributeError("create_file_monitor function not found in swot_processor module")
                
            print("✅ SWOT modules initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize SWOT modules: {e}")
            import traceback
            traceback.print_exc()
            self.processor = None
            self.workflow = None
            self.file_monitor = None
    
    async def is_available(self) -> bool:
        """Check if SWOT API is available"""
        if self._available is not None:
            return self._available
        
        # Check if modules are loaded and base directory exists
        self._available = (
            self.processor is not None and
            self.workflow is not None and
            self.base_dir.exists()
        )
        return self._available
    
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        if await self.is_available():
            return HealthStatus(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                message="SWOT API is operational"
            )
        else:
            return HealthStatus(
                status="unhealthy", 
                timestamp=datetime.utcnow().isoformat(),
                message="SWOT modules not available",
                error="Processor, workflow, or file monitor not initialized"
            )
    
    async def get_system_status(self) -> SatelliteSystemStatus:
        """Get detailed system status"""
        system_info = SystemInfo(**get_system_info())
        
        # Count files in SWOT directory structure
        nc_files = 0
        png_files = 0
        
        # SWOT uses: data/swot/ssha/{nc,png}/
        nc_dir = self.base_dir / "swot" / "ssha" / "nc"
        png_dir = self.base_dir / "swot" / "ssha" / "png"
        
        nc_files = get_file_count(nc_dir, "*.nc")
        png_files = get_file_count(png_dir, "*.png")
        
        data_status = DataStatus(
            nc_files=nc_files,
            png_files=png_files,
            authenticated=self.processor is not None and hasattr(self.processor, 'username')
        )
        
        storage_info = StorageInfo(
            base_dir=str(self.base_dir),
            nc_files=nc_files,
            png_files=png_files
        )
        
        return SatelliteSystemStatus(
            system=system_info,
            data_status=data_status,
            storage=storage_info,
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def list_files(self, satellite: str, parameter: str, file_type: str) -> List[FileInfo]:
        """List files for SWOT satellite"""
        files = []
        
        # SWOT directory structure: base_dir/swot/parameter/file_type/
        file_dir = self.base_dir / "swot" / parameter / file_type
        
        if not file_dir.exists():
            return files
        
        pattern = f"*.{file_type}"
        for file_path in file_dir.glob(pattern):
            file_info = self._create_file_info(file_path, satellite, parameter, file_type)
            files.append(file_info)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.modified, reverse=True)
        return files
    
    async def get_nc_file_path(self, satellite: str, parameter: str, filename: str) -> Path:
        """Get NC file path for SWOT"""
        return self.base_dir / "swot" / parameter / "nc" / filename
    
    async def process_data(self, request: ProcessingRequest, background_tasks: BackgroundTasks) -> ProcessingStatus:
        """Process SWOT data"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="SWOT API not available")
        
        if not self._validate_request(request):
            raise HTTPException(status_code=400, detail="Invalid processing request")
        
        import uuid
        task_id = str(uuid.uuid4())
        
        # Store task info
        self.tasks[task_id] = {
            "status": "pending",
            "message": "SWOT processing task queued",
            "progress": 0,
            "request": request,
            "satellite": "swot"
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
            message="SWOT processing task started",
            satellite="swot"
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
            satellite=task_info.get("satellite")
        )
    
    async def handle_get_request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET requests to SWOT endpoints"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="SWOT API not available")
        
        if path == "health":
            health = await self.health_check()
            return {"status": health.status, "timestamp": health.timestamp}
        elif path == "files":
            file_type = params.get("file_type", "nc")
            return await self._list_files_by_type(file_type)
        elif path == "visualizations":
            return await self._list_visualizations()
        elif path == "system-status":
            status = await self.get_system_status()
            return status.dict()
        elif path == "parameters":
            return await self._get_available_parameters()
        elif path == "test-endpoints":
            return await self._get_test_endpoints()
        else:
            raise HTTPException(status_code=404, detail=f"SWOT endpoint '{path}' not found")
    
    async def handle_post_request(self, path: str, data: Dict[str, Any], background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
        """Handle POST requests to SWOT endpoints"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="SWOT API not available")
        
        try:
            if path == "query-data" and data:
                return await self._query_available_data(data)
            elif path == "process-data" and data:
                # Convert data to ProcessingRequest
                processing_request = ProcessingRequest(**data)
                result = await self.process_data(processing_request, background_tasks)
                return result.dict()
            elif path == "check-file" and data:
                return await self._check_file_status(data)
            elif path == "regenerate-pngs" and data:
                return await self._regenerate_png_files(data)
            elif path == "download-data" and data:
                return await self._download_data_direct(data, background_tasks)
            elif path == "check-files" and data:
                return await self._check_file_completeness(data)
            elif path == "repair-files" and data:
                return await self._repair_missing_files(data, background_tasks)
            elif path == "auto-monitor-repair":
                return await self._auto_monitor_and_repair(background_tasks)
            else:
                raise HTTPException(status_code=404, detail=f"SWOT POST endpoint '{path}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SWOT POST request failed: {str(e)}")
    
    # Private helper methods
    
    async def _run_processing_task(self, task_id: str, request: ProcessingRequest):
        """Background task for processing SWOT data"""
        try:
            # Update status
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Processing SWOT data..."
            self.tasks[task_id]["progress"] = 10
            
            # Set up parameters for SWOT processing
            ftp_path = '/swot_products/l3_karin_nadir/l3_lr_ssh/v2_0_1/Expert/'
            level = "L3"
            variant = "Expert"
            cycle_numbers = [29]  # Can be made configurable
            half_orbits = [62]    # Can be made configurable
            variables = ['time', 'ssha_filtered']
            
            # Run the actual processing using the workflow
            result = await asyncio.to_thread(
                self.workflow.run_complete_workflow,
                ftp_path=ftp_path,
                level=level,
                variant=variant,
                cycle_numbers=cycle_numbers,
                half_orbits=half_orbits,
                variables=variables,
                lon_range=(request.west_lon, request.east_lon),
                lat_range=(request.south_lat, request.north_lat),
                username=getattr(request, 'swot_username', None),
                password=getattr(request, 'swot_password', None)
            )
            
            if result.get('success', False):
                # Mark as completed
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["message"] = f"Processing completed successfully. Generated {result.get('total_plots', 0)} plots"
                self.tasks[task_id]["progress"] = 100
                self.tasks[task_id]["result"] = result
            else:
                # Mark as failed
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["message"] = f"Processing failed: {result.get('error', 'Unknown error')}"
                self.tasks[task_id]["progress"] = 0
            
        except Exception as e:
            # Mark as failed
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Processing failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _list_files_by_type(self, file_type: str) -> Dict[str, Any]:
        """List files by type (nc or png)"""
        if file_type == "nc":
            return await self._list_processed_files()
        elif file_type == "png":
            return await self._list_visualizations()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
    
    async def _list_processed_files(self) -> Dict[str, Any]:
        """List all processed NetCDF data files"""
        files = []
        
        # Walk through swot/parameter/nc directories
        nc_pattern = self.base_dir / "swot" / "*" / "nc" / "*.nc"
        for file_path in self.base_dir.glob("swot/*/nc/*.nc"):
            stat = file_path.stat()
            
            # Parse path: base_dir/swot/parameter/nc/filename.nc
            parts = file_path.relative_to(self.base_dir).parts
            if len(parts) >= 3:
                parameter = parts[1]  # ssha
            else:
                parameter = "unknown"
            
            files.append({
                "filename": file_path.name,
                "parameter": parameter,
                "satellite": "swot",
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file_path)
            })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files, "total": len(files)}
    
    async def _list_visualizations(self) -> Dict[str, Any]:
        """List all generated visualization files"""
        images = []
        
        # Walk through swot/parameter/png directories
        for file_path in self.base_dir.glob("swot/*/png/*.png"):
            stat = file_path.stat()
            
            # Parse path: base_dir/swot/parameter/png/filename.png
            parts = file_path.relative_to(self.base_dir).parts
            if len(parts) >= 3:
                parameter = parts[1]  # ssha
            else:
                parameter = "unknown"
            
            # Create relative URL for static file serving
            relative_path = f"swot/{parameter}/png/{file_path.name}"
            
            images.append({
                "filename": file_path.name,
                "parameter": parameter,
                "satellite": "swot",
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/static/{relative_path}"
            })
        
        images.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"images": images, "total": len(images)}
    
    async def _get_available_parameters(self) -> Dict[str, Any]:
        """Get available SWOT parameters"""
        return {
            "parameters": {
                "ssha": {
                    "name": "Sea Surface Height Anomaly",
                    "unit": "meters",
                    "description": "Sea surface height anomaly measurements from SWOT",
                    "variables": ["ssha_filtered", "time"],
                    "levels": ["L2", "L3"],
                    "variants": ["Basic", "Expert", "WindWave", "Unsmoothed"]
                }
            },
            "data_source": {
                "provider": "AVISO",
                "ftp_server": "ftp-access.aviso.altimetry.fr",
                "data_path": "/swot_products/l3_karin_nadir/l3_lr_ssh/"
            }
        }
    
    async def _query_available_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Query available SWOT data capabilities"""
        try:
            # Update authentication if provided
            if data.get("swot_username") and data.get("swot_password"):
                self.processor.authenticate(data["swot_username"], data["swot_password"])
            
            # Get available parameters
            parameters = await self._get_available_parameters()
            
            return {
                "available_parameters": parameters["parameters"],
                "data_source": parameters["data_source"],
                "region": (data.get("west_lon"), data.get("south_lat"), data.get("east_lon"), data.get("north_lat")),
                "time_range": (data.get("start_time"), data.get("end_time")),
                "supported_formats": ["application/x-netcdf", "image/png"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_file_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check NC file status and PNG regeneration needs"""
        try:
            results = self.file_monitor.check_file_status(data["nc_file_path"])
            
            return {
                "nc_exists": results['nc_exists'],
                "nc_modified_time": results['nc_modified_time'],
                "png_count": results['png_count'],
                "needs_regeneration": results['needs_regeneration'],
                "message": results['message'],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _regenerate_png_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate all PNG files from NC file"""
        try:
            variable = data.get("variable", "ssha_filtered")
            results = self.file_monitor.regenerate_all_pngs(data["nc_file_path"], variable)
            
            return {
                "success": results['success'],
                "message": results['message'],
                "png_generated": results['png_generated'],
                "regeneration_performed": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _download_data_direct(self, data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Direct data download endpoint"""
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            # Store download task
            self.tasks[task_id] = {
                "status": "pending",
                "message": "SWOT download task queued",
                "progress": 0,
                "satellite": "swot"
            }
            
            # Add background task for download
            background_tasks.add_task(
                self._run_download_task,
                task_id,
                data
            )
            
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "SWOT download task started"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _run_download_task(self, task_id: str, data: Dict[str, Any]):
        """Background task for downloading SWOT data"""
        try:
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Downloading SWOT data..."
            self.tasks[task_id]["progress"] = 10
            
            # Set up download parameters
            ftp_path = data.get("ftp_path", '/swot_products/l3_karin_nadir/l3_lr_ssh/v2_0_1/Expert/')
            level = data.get("level", "L3")
            variant = data.get("variant", "Expert")
            cycle_numbers = data.get("cycle_numbers", [29])
            half_orbits = data.get("half_orbits", [62])
            
            # Update authentication if provided
            if data.get("swot_username") and data.get("swot_password"):
                self.processor.authenticate(data["swot_username"], data["swot_password"])
            
            # Run download
            downloaded_files = await asyncio.to_thread(
                self.processor.download_data,
                ftp_path=ftp_path,
                level=level,
                variant=variant,
                cycle_numbers=cycle_numbers,
                half_orbits=half_orbits,
                only_last=data.get("only_last", True)
            )
            
            if downloaded_files:
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["message"] = f"Download completed. {len(downloaded_files)} files downloaded"
                self.tasks[task_id]["progress"] = 100
                self.tasks[task_id]["downloaded_files"] = downloaded_files
            else:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["message"] = "No files were downloaded"
                self.tasks[task_id]["progress"] = 0
            
        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Download failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _get_test_endpoints(self) -> Dict[str, Any]:
        """Get test endpoints information"""
        return {
            "message": "SWOT API Test Page",
            "available_endpoints": {
                "GET /": "API information",
                "GET /health": "Health check",
                "GET /files": "List NC files",
                "GET /visualizations": "List PNG files",
                "GET /parameters": "List available parameters",
                "GET /test-endpoints": "This test page",
                "POST /check-file": "Check file status (requires nc_file_path in JSON body)",
                "POST /regenerate-pngs": "Regenerate PNGs (requires nc_file_path in JSON body)",
                "POST /download-data": "Download SWOT data (requires download parameters)",
                "POST /process-data": "Full processing workflow",
                "POST /check-files": "Check file completeness (requires time range parameters)",
                "POST /repair-files": "Repair missing files (requires time range parameters)",
                "POST /auto-monitor-repair": "Auto monitor and repair missing files"
            },
            "example_usage": {
                "check_file": {
                    "method": "POST",
                    "url": "/check-file",
                    "body": {"nc_file_path": "data/swot/ssha/nc/example.nc"}
                },
                "download_data": {
                    "method": "POST",
                    "url": "/download-data",
                    "body": {
                        "ftp_path": "/swot_products/l3_karin_nadir/l3_lr_ssh/v2_0_1/Expert/",
                        "level": "L3",
                        "variant": "Expert",
                        "cycle_numbers": [29],
                        "half_orbits": [62],
                        "swot_username": "your_username",
                        "swot_password": "your_password"
                    }
                },
                "process_data": {
                    "method": "POST",
                    "url": "/process-data", 
                    "body": {
                        "satellite": "swot",
                        "parameter": "ssha",
                        "start_time": "2025-09-12T00:00:00",
                        "end_time": datetime.utcnow().isoformat(),
                        "west_lon": 111.0,
                        "east_lon": 114.0,
                        "south_lat": -25.0,
                        "north_lat": -20.0
                    }
                },
                "check_files": {
                    "method": "POST",
                    "url": "/check-files",
                    "body": {
                        "start_time": "2025-09-12T00:00:00",
                        "end_time": datetime.utcnow().isoformat(),
                        "tstep": 3600
                    }
                },
                "repair_files": {
                    "method": "POST",
                    "url": "/repair-files",
                    "body": {
                        "start_time": "2025-09-12T00:00:00",
                        "end_time": datetime.utcnow().isoformat(),
                        "west_lon": 111.0,
                        "east_lon": 114.0,
                        "south_lat": -25.0,
                        "north_lat": -20.0
                    }
                },
                "auto_monitor_repair": {
                    "method": "POST",
                    "url": "/auto-monitor-repair",
                    "body": {}
                }
            },
            "note": "Use /docs for interactive API documentation"
        }
    
    async def _check_file_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check file completeness for SWOT data"""
        try:
            # Use file monitor to check completeness
            start_time = data.get("start_time", "2025-09-12T00:00:00")
            end_time = data.get("end_time", datetime.utcnow().isoformat())
            tstep = data.get("tstep", 3600)  # 1 hour in seconds
            
            results = self.file_monitor.check_file_completeness(
                timelims=(start_time, end_time),
                tstep=tstep
            )
            
            return {
                "success": True,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _repair_missing_files(self, data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Repair missing SWOT files"""
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            # Store repair task
            self.tasks[task_id] = {
                "status": "pending",
                "message": "SWOT repair task queued",
                "progress": 0,
                "satellite": "swot"
            }
            
            # Add background task for repair
            background_tasks.add_task(
                self._run_repair_task,
                task_id,
                data
            )
            
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "SWOT repair task started"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _run_repair_task(self, task_id: str, data: Dict[str, Any]):
        """Background task for repairing missing SWOT files"""
        try:
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Repairing missing SWOT files..."
            self.tasks[task_id]["progress"] = 10
            
            # Set up repair parameters
            start_time = data.get("start_time", "2025-09-12T00:00:00")
            end_time = data.get("end_time", datetime.utcnow().isoformat())
            west_lon = data.get("west_lon", 111.0)
            east_lon = data.get("east_lon", 114.0)
            south_lat = data.get("south_lat", -25.0)
            north_lat = data.get("north_lat", -20.0)
            
            # Set up SWOT processing parameters
            ftp_path = '/swot_products/l3_karin_nadir/l3_lr_ssh/v2_0_1/Expert/'
            level = "L3"
            variant = "Expert"
            cycle_numbers = [29]  # Can be made configurable
            half_orbits = [62]    # Can be made configurable
            variables = ['time', 'ssha_filtered']
            
            # Run the repair using the workflow
            result = await asyncio.to_thread(
                self.workflow.run_complete_workflow,
                ftp_path=ftp_path,
                level=level,
                variant=variant,
                cycle_numbers=cycle_numbers,
                half_orbits=half_orbits,
                variables=variables,
                lon_range=(west_lon, east_lon),
                lat_range=(south_lat, north_lat),
                username=getattr(data, 'swot_username', None),
                password=getattr(data, 'swot_password', None)
            )
            
            if result.get('success', False):
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["message"] = f"Repair completed successfully. Generated {result.get('total_plots', 0)} plots"
                self.tasks[task_id]["progress"] = 100
                self.tasks[task_id]["result"] = result
            else:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["message"] = f"Repair failed: {result.get('error', 'Unknown error')}"
                self.tasks[task_id]["progress"] = 0
            
        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Repair failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _auto_monitor_and_repair(self, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Auto monitor and repair SWOT data files - Direct update without checking"""
        try:
            print("=== SWOT Auto Monitor and Repair ===")
            print("🚀 SWOT: Direct data update (orbit-based, no pre-check needed)")
            
            # SWOT直接执行更新，不进行预先检查
            # 因为SWOT是轨道卫星，数据按轨道周期更新，不是按固定时间步长
            repair_data = {
                "start_time": "2025-09-12T00:00:00",  # 使用实际SWOT数据时间范围
                "end_time": datetime.utcnow().isoformat(),
                "west_lon": 111.0,
                "east_lon": 114.0,
                "south_lat": -25.0,
                "north_lat": -20.0
            }
            
            print("🔧 Starting SWOT data update...")
            repair_result = await self._repair_missing_files(repair_data, background_tasks)
            print("✅ SWOT update process initiated")
            
            return {
                "status": "update_initiated",
                "message": "SWOT data update started (orbit-based satellite)",
                "repair": repair_result
            }
                
        except Exception as e:
            print(f"❌ SWOT auto monitor and repair failed: {e}")
            return {"error": str(e)}
