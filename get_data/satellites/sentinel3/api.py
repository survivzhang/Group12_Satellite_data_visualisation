"""
Sentinel-3 Satellite API Module

This module provides the Sentinel-3 specific API implementation that integrates
with the existing usingtheEumetview.py and provides a clean interface for
the global API.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
import asyncio

# Add saternal3 to path for imports
sentinel_path = Path(__file__).parent.parent.parent / "saternal3"
if str(sentinel_path) not in sys.path:
    sys.path.insert(0, str(sentinel_path))

from satellites.shared.base_api import BaseSatelliteAPI
from satellites.shared.models import (
    ProcessingRequest, ProcessingStatus, FileInfo, HealthStatus,
    SatelliteSystemStatus, SystemInfo, DataStatus, StorageInfo,
    LayerInfo
)
from satellites.shared.utils import get_system_info, get_file_count

class Sentinel3API(BaseSatelliteAPI):
    """Sentinel-3 satellite API implementation"""
    
    # Parameter configuration for Sentinel-3
    PARAMETER_CONFIGS = {
        "sst": {
            "var_names": [
                "copernicus_sentinel3a_slstr_l2p_sst_fullres",
                "copernicus_sentinel3b_slstr_l2p_sst_fullres"
            ],
            "unit": "K",
            "colormap": "turbo",
            "description": "Sea Surface Temperature"
        },
        "chl": {
            "var_names": [
                "copernicus_sentinel3a_olci_l2_chl_fullres",
                "copernicus_sentinel3b_olci_l2_chl_fullres"
            ],
            "unit": "mg/m³",
            "colormap": "viridis",
            "description": "Chlorophyll-a Concentration"
        }
    }
    
    def __init__(self):
        # Use unified directory structure: data/
        unified_base_dir = Path(__file__).parent.parent.parent / "data"
        super().__init__("Sentinel-3", str(unified_base_dir))
        
        # Legacy directory for backward compatibility
        self.legacy_base_dir = Path(__file__).parent.parent.parent / "saternal3" / "data" / "eumetview_sentinel3"
        
        # Initialize processor and workflow
        self.processor = None
        self.workflow = None
        self.file_monitor = None
        self.tasks = {}  # In-memory task storage
        
        self._initialize_sentinel_modules()
    
    def _initialize_sentinel_modules(self):
        """Initialize Sentinel-3 processor, workflow, and file monitor"""
        try:
            # Try to import usingtheEumetview
            eumetview_module = None
            try:
                import usingtheEumetview
                eumetview_module = usingtheEumetview
            except ImportError:
                # If direct import fails, try with sys.path manipulation
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "usingtheEumetview",
                    sentinel_path / "usingtheEumetview.py"
                )
                eumetview_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(eumetview_module)
            
            # Initialize processor with unified base directory
            self.processor = eumetview_module.EUMETViewDataProcessor(str(self.base_dir))
            self.workflow = eumetview_module.EUMETViewWorkflow(str(self.base_dir))
            self.file_monitor = eumetview_module.create_file_monitor(str(self.base_dir))
            print("✅ Sentinel-3 modules initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize Sentinel-3 modules: {e}")
            self.processor = None
            self.workflow = None
            self.file_monitor = None
    
    async def is_available(self) -> bool:
        """Check if Sentinel-3 API is available"""
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
                message="Sentinel-3 API is operational"
            )
        else:
            return HealthStatus(
                status="unhealthy", 
                timestamp=datetime.utcnow().isoformat(),
                message="Sentinel-3 modules not available",
                error="Processor, workflow, or file monitor not initialized"
            )
    
    async def get_system_status(self) -> SatelliteSystemStatus:
        """Get detailed system status"""
        system_info = SystemInfo(**get_system_info())
        
        # Count files across all satellites and parameters from both unified and legacy directories
        nc_files = 0
        png_files = 0
        
        for satellite in ['sentinel3a', 'sentinel3b']:
            for param in ['sst', 'chl']:
                # Count from unified directories
                unified_nc_dir = self.base_dir / satellite / param / "nc"
                unified_png_dir = self.base_dir / satellite / param / "png"
                nc_files += get_file_count(unified_nc_dir, "*.nc")
                png_files += get_file_count(unified_png_dir, "*.png")
                
                # Count from legacy directories
                legacy_nc_dir = self.legacy_base_dir / satellite / param / "nc"
                legacy_png_dir = self.legacy_base_dir / satellite / param / "png"
                nc_files += get_file_count(legacy_nc_dir, "*.nc")
                png_files += get_file_count(legacy_png_dir, "*.png")
        
        data_status = DataStatus(
            nc_files=nc_files,
            png_files=png_files,
            authenticated=self.processor is not None and hasattr(self.processor, 'wcs') and self.processor.wcs is not None
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
        """List files for Sentinel-3 satellites from both unified and legacy directories"""
        files = []
        seen_filenames = set()  # Avoid duplicates
        
        # Check unified directory first
        unified_file_dir = self.base_dir / satellite / parameter / file_type
        legacy_file_dir = self.legacy_base_dir / satellite / parameter / file_type
        
        pattern = f"*.{file_type}"
        
        # Collect files from unified directory
        if unified_file_dir.exists():
            for file_path in unified_file_dir.glob(pattern):
                if file_path.name not in seen_filenames:
                    file_info = self._create_file_info(file_path, satellite, parameter, file_type)
                    files.append(file_info)
                    seen_filenames.add(file_path.name)
        
        # Collect files from legacy directory
        if legacy_file_dir.exists():
            for file_path in legacy_file_dir.glob(pattern):
                if file_path.name not in seen_filenames:
                    file_info = self._create_file_info(file_path, satellite, parameter, file_type)
                    files.append(file_info)
                    seen_filenames.add(file_path.name)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.modified, reverse=True)
        return files
    
    async def get_nc_file_path(self, satellite: str, parameter: str, filename: str) -> Path:
        """Get NC file path for Sentinel-3 - try unified first, then legacy"""
        unified_path = self.base_dir / satellite / parameter / "nc" / filename
        if unified_path.exists():
            return unified_path
        
        legacy_path = self.legacy_base_dir / satellite / parameter / "nc" / filename
        if legacy_path.exists():
            return legacy_path
        
        # Default to unified path for new files
        return unified_path
    
    async def process_data(self, request: ProcessingRequest, background_tasks: BackgroundTasks) -> ProcessingStatus:
        """Process Sentinel-3 data"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="Sentinel-3 API not available")
        
        if not self._validate_request(request):
            raise HTTPException(status_code=400, detail="Invalid processing request")
        
        import uuid
        task_id = str(uuid.uuid4())
        
        # Determine layer keys based on satellite and parameter
        layer_keys = request.layer_keys or [f"{request.satellite}_{request.parameter}"]
        
        # Store task info
        self.tasks[task_id] = {
            "status": "pending",
            "message": f"Task queued for processing {len(layer_keys)} layers",
            "progress": 0,
            "request": request,
            "satellite": request.satellite,
            "layer_keys": layer_keys
        }
        
        # Add background task
        background_tasks.add_task(
            self._run_processing_task,
            task_id,
            request,
            layer_keys
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="pending",
            message=f"Sentinel-3 processing task started for {len(layer_keys)} layers",
            satellite=request.satellite
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
        """Handle GET requests to Sentinel-3 endpoints"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="Sentinel-3 API not available")
        
        if path == "health":
            health = await self.health_check()
            return {"status": health.status, "timestamp": health.timestamp}
        elif path == "layers":
            return await self._get_available_layers()
        elif path == "files":
            return await self._list_processed_files()
        elif path.startswith("files/"):
            # Handle files/{satellite}/{parameter}/{file_type} requests
            path_parts = path.split("/")
            if len(path_parts) == 4:  # files/{satellite}/{parameter}/{file_type}
                satellite = path_parts[1]
                parameter = path_parts[2]
                file_type = path_parts[3]
                return await self._list_specific_files(satellite, parameter, file_type)
            else:
                raise HTTPException(status_code=400, detail="Invalid files path format. Expected: files/{satellite}/{parameter}/{file_type}")
        elif path == "visualizations":
            return await self._list_visualizations()
        elif path == "system-status":
            status = await self.get_system_status()
            return status.dict()
        elif path == "test-endpoints":
            return await self._get_test_endpoints()
        elif path.startswith("status/"):
            # Handle status/{task_id} requests
            task_id = path.split("/", 1)[1]
            return await self.get_task_status(task_id)
        else:
            raise HTTPException(status_code=404, detail=f"Sentinel-3 endpoint '{path}' not found")
    
    async def handle_post_request(self, path: str, data: Dict[str, Any], background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
        """Handle POST requests to Sentinel-3 endpoints"""
        if not await self.is_available():
            raise HTTPException(status_code=503, detail="Sentinel-3 API not available")
        
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
            elif path == "auto-check-regenerate" and data:
                return await self._auto_check_and_regenerate(data)
            elif path == "check-freshness" and data:
                return await self._check_data_freshness(data)
            elif path == "incremental-update" and data:
                return await self._run_incremental_update(data, background_tasks)
            elif path.startswith("describe-coverage/"):
                layer_key = path.split("/", 1)[1]
                return await self._describe_coverage(layer_key)
            else:
                raise HTTPException(status_code=404, detail=f"Sentinel-3 POST endpoint '{path}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sentinel-3 POST request failed: {str(e)}")
    
    # Private helper methods
    
    async def _run_processing_task(self, task_id: str, request: ProcessingRequest, layer_keys: List[str]):
        """Background task for processing Sentinel-3 data"""
        try:
            # Update status
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Processing Sentinel-3 data..."
            self.tasks[task_id]["progress"] = 10
            
            # Format time strings for EUMETView API (remove microseconds)
            from datetime import datetime
            
            # Parse and reformat start_time
            try:
                start_dt = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
                formatted_start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except:
                formatted_start_time = request.start_time
            
            # Parse and reformat end_time
            try:
                end_dt = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
                formatted_end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except:
                formatted_end_time = request.end_time
            
            # Run the actual processing using the workflow with incremental download
            await asyncio.to_thread(
                self.workflow.run_complete_workflow,
                layer_keys=layer_keys,
                region=(request.west_lon, request.south_lat, request.east_lon, request.north_lat),
                time_range=(formatted_start_time, formatted_end_time),
                consumer_key=request.consumer_key,
                consumer_secret=request.consumer_secret
            )
            
            # Mark as completed
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["message"] = f"Processing completed successfully for {len(layer_keys)} layers"
            self.tasks[task_id]["progress"] = 100
            
        except Exception as e:
            # Mark as failed
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Processing failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _get_available_layers(self) -> Dict[str, Any]:
        """Get available data layers"""
        try:
            # Initialize processor if not already done
            if not self.processor.wcs:
                self.processor.authenticate()
            
            layer_info = []
            for key, layer_id in self.processor.LAYER_CONFIGS.items():
                satellite, data_type = self.processor._parse_layer_key(key)
                
                layer_info.append(LayerInfo(
                    key=key,
                    name=layer_id,
                    description=f"{satellite.upper()} {data_type.upper()} data",
                    data_type=data_type,
                    satellite=satellite
                ).dict())
            
            return {
                "layers": layer_info,
                "total": len(layer_info)
            }
        except Exception as e:
            return {
                "layers": [],
                "total": 0,
                "error": str(e)
            }
    
    async def _list_processed_files(self) -> Dict[str, Any]:
        """List all processed NetCDF data files"""
        files = []
        by_layer = {}
        
        # Walk through satellite/datatype/nc directories
        for file_path in self.base_dir.rglob("*/*/nc/*.nc"):
            stat = file_path.stat()
            
            # Parse path: base_dir/satellite/datatype/nc/filename.nc
            parts = file_path.relative_to(self.base_dir).parts
            if len(parts) >= 3:
                satellite = parts[0]      # sentinel3a, sentinel3b
                data_type = parts[1]      # sst, chl
                layer_key = f"{satellite}_{data_type}"
            else:
                layer_key = "unknown"
            
            files.append({
                "filename": file_path.name,
                "layer": layer_key,
                "satellite": satellite if len(parts) >= 3 else "unknown",
                "data_type": data_type if len(parts) >= 3 else "unknown",
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(file_path)
            })
            
            by_layer[layer_key] = by_layer.get(layer_key, 0) + 1
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files, "total": len(files), "by_layer": by_layer}
    
    async def _list_visualizations(self) -> Dict[str, Any]:
        """List all generated visualization files"""
        images = []
        by_layer = {}
        
        # Walk through satellite/datatype/png directories
        for file_path in self.base_dir.rglob("*/*/png/*.png"):
            stat = file_path.stat()
            
            # Parse path: base_dir/satellite/datatype/png/filename.png
            parts = file_path.relative_to(self.base_dir).parts
            if len(parts) >= 3:
                satellite = parts[0]      # sentinel3a, sentinel3b
                data_type = parts[1]      # sst, chl
                layer_key = f"{satellite}_{data_type}"
            else:
                layer_key = "unknown"
            
            # Create relative URL for static file serving
            relative_path = f"{satellite}/{data_type}/png/{file_path.name}"
            
            images.append({
                "filename": file_path.name,
                "layer": layer_key,
                "satellite": satellite if len(parts) >= 3 else "unknown",
                "data_type": data_type if len(parts) >= 3 else "unknown",
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/static/{relative_path}"
            })
            
            by_layer[layer_key] = by_layer.get(layer_key, 0) + 1
        
        images.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"images": images, "total": len(images), "by_layer": by_layer}
    
    async def _list_specific_files(self, satellite: str, parameter: str, file_type: str) -> Dict[str, Any]:
        """List files for a specific satellite, parameter, and file type"""
        files = []
        seen_filenames = set()
        
        # Validate satellite and parameter
        if satellite not in ['sentinel3a', 'sentinel3b']:
            raise HTTPException(status_code=400, detail=f"Invalid satellite: {satellite}")
        if parameter not in ['sst', 'chl']:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {parameter}")
        if file_type not in ['nc', 'png']:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")
        
        # Check unified directory first
        unified_dir = self.base_dir / satellite / parameter / file_type
        if unified_dir.exists():
            for file_path in unified_dir.glob(f"*.{file_type}"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    # Create URL for static file serving
                    if file_type == 'png':
                        url = f"/static/{satellite}/{parameter}/png/{file_path.name}"
                    else:
                        url = f"/api/v1/satellites/{satellite}/{parameter}/{file_type}/{file_path.name}"
                    
                    files.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(file_path),
                        "url": url
                    })
                    seen_filenames.add(file_path.name)
        
        # Check legacy directory for additional files
        legacy_dir = self.legacy_base_dir / satellite / parameter / file_type
        if legacy_dir.exists():
            for file_path in legacy_dir.glob(f"*.{file_type}"):
                if file_path.name not in seen_filenames:
                    stat = file_path.stat()
                    # Create URL for static file serving
                    if file_type == 'png':
                        url = f"/static/{satellite}/{parameter}/png/{file_path.name}"
                    else:
                        url = f"/api/v1/satellites/{satellite}/{parameter}/{file_type}/{file_path.name}"
                    
                    files.append({
                        "filename": file_path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": str(file_path),
                        "url": url
                    })
                    seen_filenames.add(file_path.name)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "files": files,
            "total_count": len(files),
            "satellite": satellite,
            "parameter": parameter,
            "file_type": file_type,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _query_available_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Query available satellite data capabilities"""
        try:
            # Initialize processor if not already done
            if not self.processor.wcs:
                self.processor.authenticate(data.get("consumer_key"), data.get("consumer_secret"))
            
            # Get available layers info
            layer_keys = data.get("layer_keys", [])
            layer_info = []
            
            for key in layer_keys:
                if key in self.processor.LAYER_CONFIGS:
                    satellite, data_type = self.processor._parse_layer_key(key)
                    layer_info.append(LayerInfo(
                        key=key,
                        name=self.processor.LAYER_CONFIGS[key],
                        description=f"{satellite.upper()} {data_type.upper()} data",
                        data_type=data_type,
                        satellite=satellite
                    ).dict())
            
            # Get supported formats for first layer
            supported_formats = ['application/x-netcdf']
            if layer_keys:
                try:
                    supported_formats = self.processor.get_supported_formats(layer_keys[0])
                except Exception:
                    pass
            
            return {
                "available_layers": layer_info,
                "supported_formats": supported_formats,
                "region": (data.get("west_lon"), data.get("south_lat"), data.get("east_lon"), data.get("north_lat")),
                "time_range": (data.get("start_time"), data.get("end_time"))
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _describe_coverage(self, layer_key: str) -> Dict[str, Any]:
        """Get detailed coverage description for a layer"""
        try:
            if not self.processor.wcs:
                self.processor.authenticate()
            
            description = self.processor.describe_coverage(layer_key)
            
            return {
                "layer_key": layer_key,
                "layer_id": self.processor.LAYER_CONFIGS.get(layer_key),
                "description": description
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
            results = self.file_monitor.regenerate_all_pngs(data["nc_file_path"])
            
            return {
                "success": results['success'],
                "message": results['message'],
                "png_generated": results['png_generated'],
                "regeneration_performed": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _auto_check_and_regenerate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically check file status and regenerate PNGs if needed"""
        try:
            results = self.file_monitor.check_and_regenerate_if_needed(data["nc_file_path"])
            
            return {
                "success": results.get('regeneration_success', True),
                "message": results['final_message'],
                "png_generated": results.get('png_generated', 0),
                "regeneration_performed": results['regeneration_performed'],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _check_data_freshness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data freshness using the file monitor"""
        try:
            satellite = data.get("satellite")
            threshold_hours = data.get("threshold_hours", 2)
            
            if satellite:
                # Check specific satellite
                results = {}
                for data_type in ['sst', 'chl']:
                    result = self.file_monitor.check_data_freshness(satellite, data_type)
                    results[f"{satellite}_{data_type}"] = result
                
                return {
                    "results": results,
                    "satellite": satellite,
                    "threshold_hours": threshold_hours,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Check all satellites
                results = self.file_monitor.check_all_data_freshness()
                return results
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _run_incremental_update(self, data: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """Run incremental update for all Sentinel-3 parameters"""
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            # Store task info
            self.tasks[task_id] = {
                "status": "pending",
                "message": "Incremental update task queued",
                "progress": 0,
                "satellite": "sentinel3",
                "layer_keys": ['sentinel3a_sst', 'sentinel3a_chl', 'sentinel3b_sst', 'sentinel3b_chl']
            }
            
            # Add background task
            background_tasks.add_task(
                self._run_incremental_update_task,
                task_id,
                data
            )
            
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Incremental update started for all Sentinel-3 parameters",
                "satellite": "sentinel3"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _run_incremental_update_task(self, task_id: str, data: Dict[str, Any]):
        """Background task for incremental update"""
        try:
            # Update status
            self.tasks[task_id]["status"] = "processing"
            self.tasks[task_id]["message"] = "Running incremental update..."
            self.tasks[task_id]["progress"] = 10
            
            # Get region from data or use default
            region = (
                data.get("west_lon", 111.0),
                data.get("south_lat", -25.0),
                data.get("east_lon", 114.0),
                data.get("north_lat", -20.0)
            )
            
            # Run incremental update
            await asyncio.to_thread(
                self.workflow.run_incremental_update,
                region=region,
                consumer_key=data.get("consumer_key"),
                consumer_secret=data.get("consumer_secret")
            )
            
            # Mark as completed
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["message"] = "Incremental update completed successfully"
            self.tasks[task_id]["progress"] = 100
            
        except Exception as e:
            # Mark as failed
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["message"] = f"Incremental update failed: {str(e)}"
            self.tasks[task_id]["progress"] = 0
    
    async def _get_test_endpoints(self) -> Dict[str, Any]:
        """Get test endpoints information"""
        return {
            "message": "Sentinel-3 API Test Page",
            "available_endpoints": {
                "GET /": "API information",
                "GET /health": "Health check",
                "GET /layers": "List available layers",
                "GET /files": "List NC files",
                "GET /visualizations": "List PNG files",
                "GET /test-endpoints": "This test page",
                "POST /check-file": "Check file status (requires nc_file_path in JSON body)",
                "POST /regenerate-pngs": "Regenerate PNGs (requires nc_file_path in JSON body)",
                "POST /auto-check-regenerate": "Auto check and regenerate (requires nc_file_path in JSON body)",
                "POST /incremental-update": "Run incremental update for all Sentinel-3 parameters"
            },
            "example_usage": {
                "check_file": {
                    "method": "POST",
                    "url": "/check-file",
                    "body": {"nc_file_path": "data/eumetview_sentinel3/sentinel3a/sst/nc/example.nc"}
                },
                "auto_regenerate": {
                    "method": "POST",
                    "url": "/auto-check-regenerate",
                    "body": {"nc_file_path": "data/eumetview_sentinel3/sentinel3a/sst/nc/example.nc"}
                }
            },
            "note": "Use /docs for interactive API documentation"
        }
    
    def find_first_valid_timepoint(self, data_var):
        """Find the first time point with valid data for Sentinel-3"""
        import numpy as np
        
        # Handle both xarray and numpy array inputs
        if hasattr(data_var, 'values'):
            data_array = data_var.values
        else:
            data_array = data_var
            
        if len(data_array.shape) <= 2:
            return data_array
        
        for i in range(data_array.shape[0]):
            time_data = data_array[i]
            valid_data = time_data[~np.isnan(time_data)]
            if len(valid_data) > 0:
                return time_data
        
        # If no valid data found, return first time point
        return data_array[0]
    
    def get_parameter_config(self, parameter: str) -> dict:
        """Get parameter configuration for Sentinel-3"""
        return self.PARAMETER_CONFIGS.get(parameter, {})
    
    def get_parameter_var_names(self, parameter: str) -> list:
        """Get variable names for a specific parameter"""
        config = self.get_parameter_config(parameter)
        return config.get("var_names", [])
    
    def get_parameter_unit(self, parameter: str) -> str:
        """Get unit for a specific parameter"""
        config = self.get_parameter_config(parameter)
        return config.get("unit", "unknown")
    
    def get_parameter_colormap(self, parameter: str) -> str:
        """Get colormap for a specific parameter"""
        config = self.get_parameter_config(parameter)
        return config.get("colormap", "viridis")
    
    def find_data_variable(self, ds, parameter: str):
        """Find the data variable for a specific parameter in the dataset"""
        var_names = self.get_parameter_var_names(parameter)
        
        for var_name in var_names:
            if var_name in ds.data_vars:
                return ds[var_name]
        
        return None

    def get_sentinel3_data(self, data_var, target_time=None, time_coords=None):
        """Get data for Sentinel-3 with proper time point selection logic"""
        import numpy as np
        
        # Handle both xarray and numpy array inputs
        if hasattr(data_var, 'values'):
            data_array = data_var.values
        else:
            data_array = data_var
        
        # Handle multi-time data (like Sentinel-3)
        if len(data_array.shape) > 2:  # Multi-time data
            if target_time and time_coords is not None:
                # Try to find the closest time point to target_time
                from datetime import datetime
                try:
                    target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                    time_diffs = np.abs([(np.datetime64(t) - np.datetime64(target_dt)).astype('timedelta64[s]').astype(float) for t in time_coords])
                    closest_time_idx = np.argmin(time_diffs)
                    data = data_array[closest_time_idx]
                    
                    # Check if the closest time point has valid data
                    valid_data = data[~np.isnan(data)]
                    if len(valid_data) == 0:
                        # If closest time point has no valid data, use first valid time point
                        print(f"Closest time point has no valid data, using first valid time point...")
                        return self.find_first_valid_timepoint(data_var)
                    else:
                        return data
                except Exception as e:
                    print(f"Error parsing target_time {target_time}: {e}")
                    # Fallback to first valid time point
                    return self.find_first_valid_timepoint(data_var)
            else:
                # No target_time specified, use first valid time point
                return self.find_first_valid_timepoint(data_var)
        else:
            # Single time data
            return data_array
    
    def _find_closest_time_data(self, data_var, target_dt):
        """Find the closest time point data for Sentinel-3"""
        import numpy as np
        
        # This is a simplified version - in practice, we'd need access to the time coordinates
        # For now, we'll use the first time point as fallback
        # TODO: Implement proper time matching when we have access to time coordinates
        data = data_var.values[0]
        
        # Check if the first time point has valid data
        valid_data = data[~np.isnan(data)]
        if len(valid_data) == 0:
            # If first time point has no valid data, try other time points
            print(f"First time point has no valid data, trying other time points...")
            data = self.find_first_valid_timepoint(data_var)
        
        return data