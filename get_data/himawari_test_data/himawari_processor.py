"""
Himawari Satellite Data Processing Module

This module provides functionality to download, process, and visualize
Himawari-9 satellite sea surface temperature data.
"""

import os
import time
import re
from pathlib import Path
from typing import Tuple, Optional, List

import earthaccess
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend, only generate files without displaying windows
import matplotlib.pyplot as plt
from pyproj import Proj


class HimawariDataProcessor:
    """Main class for processing Himawari satellite data."""
    
    # Constants
    COLLECTION_SHORT_NAME = "H09-AHI-L3C-ACSPO-v2.90"
    FILENAME_TIME_RE = re.compile(r"(\d{14})-STAR-L3C_")
    LONG_NAME = "STAR-L3C_GHRSST-SSTsubskin-AHI_H09-ACSPO_V2.90-v02.0-fv01.0"
    
    def __init__(self, base_dir: str = "data/himawari_l3c"):
        """Initialize the processor with directory structure."""
        self.base_dir = Path(base_dir)
        self.temp_dir = self.base_dir / "temp"
        self.parts_dir = self.base_dir / "parts"
        self.png_dir = self.base_dir / "png"
        
        # Create directories
        self._setup_directories()
        
    def _setup_directories(self):
        """Create necessary directories."""
        for directory in [self.base_dir, self.temp_dir, self.parts_dir, self.png_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def ensure_earthdata_login(self, netrc_path: Path = Path(".netrc")):
        """Login to Earthdata using .netrc file."""
        if not netrc_path.exists():
            raise FileNotFoundError(
                f".netrc not found at {netrc_path}\n"
                "Create a .netrc file with:\n"
                "machine urs.earthdata.nasa.gov\n  login YOUR_USERNAME\n  password YOUR_PASSWORD\n"
            )
        
        os.environ["NETRC"] = str(netrc_path.resolve())
        
        # Remove proxy settings that might interfere
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            os.environ.pop(key, None)
            
        auth = earthaccess.login(strategy="netrc", persist=True)
        if not auth.authenticated:
            raise RuntimeError("Earthdata login failed. Check .netrc credentials")
        
        print("✓ Successfully authenticated with Earthdata")
    
    def query_data_manifest(
        self,
        timelims: Tuple[str, str],
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        delay_hours: int = 4,
        max_results: Optional[int] = None,
        netrc_path: Path = Path(".netrc")
    ) -> pd.DataFrame:
        """
        Query available Himawari-9 L3C data.
        
        Args:
            timelims: Time range as (start, end) ISO strings
            lonlims: Longitude range as (west, east)
            latlims: Latitude range as (south, north)
            delay_hours: Hours to subtract from end time to account for processing delay
            max_results: Maximum number of results to return
            netrc_path: Path to .netrc file
            
        Returns:
            DataFrame with available data information
        """
        self.ensure_earthdata_login(netrc_path)
        
        t0_iso, t1_iso = timelims
        t0_cap, t1_cap = self._cap_temporal_by_delay(t0_iso, t1_iso, delay_hours)
        bbox = self._create_bbox(lonlims, latlims)
        
        print(f"Querying data from {t0_cap} to {t1_cap}")
        print(f"Bounding box: {bbox}")
        
        # Search for granules
        results = earthaccess.search_data(
            short_name=self.COLLECTION_SHORT_NAME,
            temporal=(t0_cap, t1_cap),
            bounding_box=bbox,
            count=max_results if max_results else 2000,
        )
        
        rows = []
        for gran in results:
            links = [u.get("href") if isinstance(u, dict) else str(u) for u in gran.data_links()]
            https_links = [u for u in links if u.startswith("https://")]
            
            if not https_links:
                continue
                
            url = https_links[0]
            file = url.split("/")[-1]
            
            # Extract timestamp from filename
            match = self.FILENAME_TIME_RE.search(file)
            timestamp = pd.NaT
            if match:
                timestamp = pd.to_datetime(match.group(1), format="%Y%m%d%H%M%S", utc=True)
            
            # Get file size
            size_MB = None
            try:
                size_MB = float(gran.size()) / (1024 * 1024)
            except Exception:
                pass
            
            rows.append({
                "time_utc": timestamp,
                "file": file,
                "size_MB": size_MB,
                "url": url,
                "bbox": bbox,
            })
        
        df = pd.DataFrame(rows).sort_values("time_utc").reset_index(drop=True)
        print(f"Found {len(df)} data files")
        return df
    
    def process_time_series(
        self,
        timelims: Tuple[str, str],
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        tstep: int = 3600,
        netrc_path: Path = Path(".netrc")
    ):
        """
        Process a time series of Himawari data.
        
        Args:
            timelims: Time range as (start, end) ISO strings
            lonlims: Longitude range as (west, east)
            latlims: Latitude range as (south, north)
            tstep: Time step in seconds
            netrc_path: Path to .netrc file
        """
        self.ensure_earthdata_login(netrc_path)
        
        # Generate time range
        dtlims = (np.datetime64(timelims[0]), np.datetime64(timelims[1]))
        dtrange = np.arange(dtlims[0], dtlims[1], np.timedelta64(tstep, 's'))
        
        # Account for processing delay
        now_utc = np.datetime64(pd.Timestamp.utcnow().to_pydatetime())
        safe_latest = now_utc - np.timedelta64(4, 'h')
        dtrange = dtrange[dtrange <= safe_latest]
        
        print(f"Processing {len(dtrange)} time steps")
        print(f"Time range: {timelims[0]} to {pd.Timestamp(safe_latest)} UTC")
        
        for dt in dtrange:
            self._process_single_timestamp(dt, lonlims, latlims)
    
    def _process_single_timestamp(
        self,
        dt: np.datetime64,
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float]
    ):
        """Process data for a single timestamp."""
        dt_pd = pd.Timestamp(dt)
        time_str = dt_pd.strftime("%Y%m%d%H%M%S")
        file_name = f"{time_str}-{self.LONG_NAME}.nc"
        
        file_path = self.temp_dir / file_name
        output_path = self.parts_dir / f"{time_str}.nc"
        
        if output_path.exists():
            print(f"Already processed: {output_path}")
            return
        
        # Download file
        link = f"https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/{self.COLLECTION_SHORT_NAME}/{file_name}"
        
        if not file_path.exists():
            print(f"Downloading: {file_name}")
            paths = earthaccess.download(link, str(self.temp_dir))
            if not paths:
                print(f"Download failed or not available yet: {file_name}")
                return
            file_on_disk = Path(paths[0])
        else:
            print(f"Using cached file: {file_path}")
            file_on_disk = file_path
        
        try:
            self._process_netcdf_file(file_on_disk, output_path, lonlims, latlims, time_str)
        finally:
            # Clean up temporary file
            if file_on_disk.exists():
                try:
                    os.remove(file_on_disk)
                    print(f"Removed temp file: {file_on_disk}")
                except PermissionError:
                    print(f"Could not remove temp file (still in use): {file_on_disk}")
    
    def _process_netcdf_file(
        self,
        file_path: Path,
        output_path: Path,
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        time_str: str
    ):
        """Process a single NetCDF file."""
        with xr.open_dataset(file_path, engine="netcdf4") as ds:
            # Identify coordinate names
            lon_name = self._pick_coord_name(ds, ["lon", "longitude"])
            lat_name = self._pick_coord_name(ds, ["lat", "latitude"])
            time_name = self._pick_coord_name(ds, ["time", "t"])
            
            # Ensure latitude is in ascending order for slicing
            if np.asarray(ds[lat_name]).ndim == 1:
                if float(ds[lat_name].values[0]) > float(ds[lat_name].values[-1]):
                    ds = ds.sortby(lat_name)
            
            # Crop to region of interest
            lon_slice = slice(min(lonlims), max(lonlims))
            lat_slice = slice(min(latlims), max(latlims))
            ds_cropped = ds.sel({lon_name: lon_slice, lat_name: lat_slice})
            
            # Find SST variable
            sst_name = self._find_sst_variable(ds_cropped)
            
            # Find quality variable (optional)
            quality_name = self._find_quality_variable(ds_cropped)
            
            # Keep only necessary variables
            keep_vars = [sst_name] + ([quality_name] if quality_name else [])
            ds_cropped = ds_cropped[keep_vars].copy()
            ds_cropped.attrs = {}  # Remove global attributes to reduce file size
            
            # Save processed data
            ds_cropped.to_netcdf(output_path)
            print(f"Saved cropped dataset to {output_path}")
            
            # Generate visualization
            self._create_visualization(ds_cropped, sst_name, time_name, time_str)
    
    def _create_visualization(self, ds: xr.Dataset, sst_name: str, time_name: str, time_str: str):
        """Create PNG visualization of SST data."""
        sst = ds[sst_name]
        
        # Handle time dimension
        if time_name in sst.dims and sst.sizes[time_name] >= 1:
            sst0 = sst.isel({time_name: 0})
        else:
            sst0 = sst
        
        # Check for valid data
        if not np.isfinite(sst0.values).any():
            print(f"SST all-NaN for {time_str}, skipping PNG.")
            return
        
        vmin = float(np.nanmin(sst0.values))
        vmax = float(np.nanmax(sst0.values))
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(sst0.values, origin="lower", cmap="turbo", vmin=vmin, vmax=vmax)
        plt.colorbar(im, ax=ax, label="Sea Surface Temperature (K)")
        ax.set_title(f"Himawari-9 SST {time_str}")
        plt.tight_layout()
        
        png_path = self.png_dir / f"{time_str}.png"
        plt.savefig(png_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Saved PNG: {png_path}")
    
    @staticmethod
    def _cap_temporal_by_delay(t0: str, t1: str, delay_hours: int = 4) -> Tuple[str, str]:
        """Cap end time to account for processing delay."""
        end = np.datetime64(t1)
        now_safe = np.datetime64(pd.Timestamp.utcnow().to_pydatetime()) - np.timedelta64(delay_hours, "h")
        if end > now_safe:
            end = now_safe
        return t0, str(end.astype("datetime64[s]"))
    
    @staticmethod
    def _create_bbox(lonlims: Tuple[float, float], latlims: Tuple[float, float]) -> Tuple[float, float, float, float]:
        """Create bounding box in (west, south, east, north) format."""
        west, east = min(lonlims), max(lonlims)
        south, north = min(latlims), max(latlims)
        return (west, south, east, north)
    
    @staticmethod
    def _pick_coord_name(ds: xr.Dataset, candidates: List[str]) -> str:
        """Pick coordinate name from candidates."""
        for name in candidates:
            if name in ds.coords or name in ds.variables:
                return name
        raise KeyError(f"None of {candidates} found in dataset")
    
    @staticmethod
    def _find_sst_variable(ds: xr.Dataset) -> str:
        """Find SST variable name."""
        candidates = ["sea_surface_temperature", "sst", "sea_surface_temperature_skin"]
        for var in candidates:
            if var in ds.data_vars:
                return var
        raise KeyError(f"No SST variable found. Available: {list(ds.data_vars)}")
    
    @staticmethod
    def _find_quality_variable(ds: xr.Dataset) -> Optional[str]:
        """Find quality variable name."""
        candidates = ["quality_level", "l2p_flags", "quality_level_sst"]
        for var in candidates:
            if var in ds.data_vars:
                return var
        return None


# Utility functions for coordinate transformations (kept for L2P data if needed)
def retry_operation(func, retries: int = 20, wait_seconds: int = 60, *args, **kwargs):
    """Retry a function call with specified retries and wait time."""
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[Retry] Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(wait_seconds)
            else:
                raise RuntimeError(f"Function '{func.__name__}' failed after {retries} retries.")


def calculate_latlon_from_geostationary(ds: xr.Dataset) -> Tuple[np.ndarray, ...]:
    """
    Calculate latitude and longitude from geostationary projection.
    Only needed for L2P datasets with geostationary coordinates.
    """
    x = ds['ni'].values
    y = ds['nj'].values
    
    geo_var = ds['geostationary']
    lon_0 = float(geo_var.longitude_of_projection_origin)
    h = float(geo_var.perspective_point_height)
    sweep = str(geo_var.sweep_angle_axis)
    
    p = Proj(proj='geos', h=h, lon_0=lon_0, sweep=sweep, datum='WGS84')
    
    X, Y = np.meshgrid(x * h, y * h)
    lon, lat = p(X, Y, inverse=True)
    
    # Fill space pixels with NaNs
    lon[np.abs(lon) > 360.0] = np.nan
    lat[np.abs(lat) > 90.0] = np.nan
    
    return X, Y, lat, lon, x, y


def create_coordinates_dataset(ds: xr.Dataset) -> xr.Dataset:
    """Create coordinate dataset for geostationary data."""
    X, Y, lat, lon, x, y = calculate_latlon_from_geostationary(ds)
    
    ds_coords = xr.Dataset(
        coords={
            'ni': ('ni', x),
            'nj': ('nj', y),
            'lat': (('nj', 'ni'), lat),
            'lon': (('nj', 'ni'), lon),
            'X': (('nj', 'ni'), X),
            'Y': (('nj', 'ni'), Y),
        }
    )
    
    # Set attributes
    ds_coords['lat'].attrs.update(long_name='latitude', units='degrees_north')
    ds_coords['lon'].attrs.update(long_name='longitude', units='degrees_east')
    ds_coords['X'].attrs.update(long_name='geostationary X', units='m')
    ds_coords['Y'].attrs.update(long_name='geostationary Y', units='m')
    
    return ds_coords


def get_crop_indices(lon: np.ndarray, lat: np.ndarray, 
                    lonlims: Tuple[float, float], 
                    latlims: Tuple[float, float]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Get i and j indices for cropping based on lon/lat limits."""
    def find_nearest(x_grid, y_grid, x_point, y_point):
        """Find nearest grid point ignoring NaNs."""
        valid_mask = ~np.isnan(x_grid) & ~np.isnan(y_grid)
        distances = np.full_like(x_grid, np.inf, dtype=float)
        distances[valid_mask] = np.hypot(x_grid[valid_mask] - x_point,
                                        y_grid[valid_mask] - y_point)
        return np.unravel_index(np.argmin(distances), distances.shape)
    
    # Find grid indices for corner points
    j1, i1 = find_nearest(lon, lat, lonlims[0], latlims[0])
    j2, i2 = find_nearest(lon, lat, lonlims[1], latlims[0])
    j3, i3 = find_nearest(lon, lat, lonlims[0], latlims[1])
    j4, i4 = find_nearest(lon, lat, lonlims[1], latlims[1])
    
    ilims = (min(i1, i2, i3, i4), max(i1, i2, i3, i4) + 1)
    jlims = (min(j1, j2, j3, j4), max(j1, j2, j3, j4) + 1)
    
    return ilims, jlims


def merge_parts_to_single_nc(parts_dir: Path, merged_path: Path):
    """
    Merge all cropped nc files in the parts/ directory into a single file
    
    Args:
        parts_dir: Directory containing split nc files
        merged_path: Path to save the merged file
    """
    import pandas as pd
    
    # Find all cropped nc files
    nc_files = sorted(parts_dir.glob("*.nc"))
    if not nc_files:
        print(f"[WARN] No files found in {parts_dir}")
        return
    
    print(f"Found {len(nc_files)} files, merging...")

    # Read all nc files
    datasets = []
    for f in nc_files:
        try:
            ds = xr.open_dataset(f)
            # Ensure time is datetime64
            if 'time' in ds:
                ds['time'] = pd.to_datetime(ds['time'].values)
            datasets.append(ds)
        except Exception as e:
            print(f"Warning: Could not open {f}: {e}")
            continue
    
    if not datasets:
        print("[ERROR] No valid datasets found to merge")
        return
    
    # Concatenate along time dimension
    try:
        merged_ds = xr.concat(datasets, dim="time")
        
    # Save as a new large nc file
        merged_ds.to_netcdf(merged_path)
        print(f"[OK] Merged dataset saved to {merged_path}")
        
    # Close all small files, free memory
        for ds in datasets:
            ds.close()
        merged_ds.close()
        
    except Exception as e:
        print(f"[ERROR] Failed to merge datasets: {e}")
    # Clean up opened datasets
        for ds in datasets:
            try:
                ds.close()
            except:
                pass


def analyze_merged_dataset(merged_path: Path):
    """
    Analyze the merged dataset
    
    Args:
        merged_path: Path to the merged dataset
    """
    if not merged_path.exists():
        print(f"[ERROR] Merged file not found: {merged_path}")
        return
    
    try:
    # Read the merged file
        ds = xr.open_dataset(merged_path)
        
        print("=== Dataset Analysis ===")
        print(f"Data variables: {list(ds.data_vars.keys())}")
        
    # Get sea surface temperature data
        if "sea_surface_temperature" in ds.data_vars:
            sst = ds["sea_surface_temperature"]
            print(f"SST shape: {sst.shape}")
            print(f"SST dimensions: {sst.dims}")
            print(f"SST data type: {sst.dtype}")
            
            # Statistics
            valid_data = sst.values[~np.isnan(sst.values)]
            if len(valid_data) > 0:
                print(f"Valid data points: {len(valid_data)}")
                print(f"SST range: {np.min(valid_data):.2f} - {np.max(valid_data):.2f} K")
                print(f"SST mean: {np.mean(valid_data):.2f} K")
            else:
                print("No valid SST data found")
        
    # Get time coordinate
        if "time" in ds.coords:
            print(f"Time coordinate: {ds['time'].values}")
            print(f"Time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
        
    # Get spatial coordinates
        if "lon" in ds.coords and "lat" in ds.coords:
            lon_range = (float(ds['lon'].min()), float(ds['lon'].max()))
            lat_range = (float(ds['lat'].min()), float(ds['lat'].max()))
            print(f"Longitude range: {lon_range[0]:.2f} - {lon_range[1]:.2f}")
            print(f"Latitude range: {lat_range[0]:.2f} - {lat_range[1]:.2f}")
        
        ds.close()
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze dataset: {e}")


# Add a convenient utility class to handle the complete workflow
class HimawariWorkflow:
    """Complete Himawari data processing workflow"""
    
    def __init__(self, base_dir: str = "data/himawari_l3c"):
        self.processor = HimawariDataProcessor(base_dir)
        self.merged_path = self.processor.base_dir / "merged_sst.nc"
    
    def run_complete_workflow(
        self,
        timelims: Tuple[str, str],
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        tstep: int = 3600,
        netrc_path: Path = Path(".netrc")
    ):
        """
        Run the complete data processing workflow: query -> download -> process -> merge -> analyze
        
        Args:
            timelims: Time range
            lonlims: Longitude range  
            latlims: Latitude range
            tstep: Time step (seconds)
            netrc_path: Path to .netrc file
        """
        print("=== Himawari Data Processing Workflow ===")
        
        # Step 1: Query available data
        print("\n1. Querying available data...")
        try:
            manifest = self.processor.query_data_manifest(
                timelims=timelims,
                lonlims=lonlims,
                latlims=latlims,
                netrc_path=netrc_path
            )
            if len(manifest) == 0:
                print("No data available for the specified time range and region")
                return
            # Save manifest
            manifest_path = self.processor.base_dir / "data_manifest.csv"
            manifest.to_csv(manifest_path, index=False)
            print(f"Saved data manifest to: {manifest_path}")
        except Exception as e:
            print(f"Failed to query data: {e}")
            return
        
        # Step 2: Process time series data
        print("\n2. Processing time series data...")
        try:
            self.processor.process_time_series(
                timelims=timelims,
                lonlims=lonlims,
                latlims=latlims,
                tstep=tstep,
                netrc_path=netrc_path
            )
        except Exception as e:
            print(f"Failed to process time series: {e}")
            return
        
        # Step 3: Merge all processed files
        print("\n3. Merging processed files...")
        try:
            merge_parts_to_single_nc(self.processor.parts_dir, self.merged_path)
        except Exception as e:
            print(f"Failed to merge files: {e}")
            return
        
        # Step 4: Analyze merged dataset
        print("\n4. Analyzing merged dataset...")
        try:
            analyze_merged_dataset(self.merged_path)
        except Exception as e:
            print(f"Failed to analyze dataset: {e}")
        
        print(f"\n=== Workflow Complete ===")
        print(f"Results saved to: {self.processor.base_dir}")
        print(f"- Processed files: {self.processor.parts_dir}")
        print(f"- Visualizations: {self.processor.png_dir}")
        print(f"- Merged dataset: {self.merged_path}")
    
    def quick_analysis(self):
        """Quickly analyze the existing merged dataset"""
        if self.merged_path.exists():
            analyze_merged_dataset(self.merged_path)
        else:
            print(f"Merged dataset not found at: {self.merged_path}")
            print("Run the complete workflow first.")



# Convenience function
def run_himawari_workflow_example():
    """Run an example Himawari data processing workflow"""
    
    # Configuration parameters
    timelims = ("2025-03-01T00:00:00", "2025-03-01T12:00:00")
    lonlims = (111, 116)  # Western Australia region
    latlims = (-24.5, -19.5)
    tstep = 3600  # 1 hour interval
    
    # Create workflow instance
    workflow = HimawariWorkflow()
    
    # Run complete workflow
    workflow.run_complete_workflow(
        timelims=timelims,
        lonlims=lonlims,
        latlims=latlims,
        tstep=tstep
    )


class HimawariFileMonitor:
    """Himawari file integrity monitoring and repair service"""
    
    def __init__(self, processor: HimawariDataProcessor):
        """
        Initialize file monitor
        
        Args:
            processor: HimawariDataProcessor instance
        """
        self.processor = processor
        self.base_dir = processor.base_dir
        self.parts_dir = processor.parts_dir
        self.png_dir = processor.png_dir
        
    def check_file_completeness(
        self,
        timelims: Tuple[str, str],
        tstep: int = 3600,
        check_nc: bool = True,
        check_png: bool = True
    ) -> dict:
        """
        Check file integrity within the specified time range
        
        Args:
            timelims: Time range (start, end)
            tstep: Time step (seconds)
            check_nc: Whether to check nc files
            check_png: Whether to check png files
        
        Returns:
            Dictionary containing check results
        """
        print("=== Checking File Completeness ===")
        
    # Generate expected time series
        dtlims = (np.datetime64(timelims[0]), np.datetime64(timelims[1]))
        dtrange = np.arange(dtlims[0], dtlims[1], np.timedelta64(tstep, 's'))
        
    # Consider processing delay
        now_utc = np.datetime64(pd.Timestamp.utcnow().to_pydatetime())
        safe_latest = now_utc - np.timedelta64(4, 'h')
        dtrange = dtrange[dtrange <= safe_latest]
        
        expected_times = [pd.Timestamp(dt).strftime("%Y%m%d%H%M%S") for dt in dtrange]
        
        print(f"Expected time steps: {len(expected_times)}")
        print(f"Time range: {timelims[0]} to {pd.Timestamp(safe_latest)} UTC")
        
        results = {
            'expected_files': len(expected_times),
            'expected_times': expected_times,
            'nc_files': {
                'existing': [],
                'missing': [],
                'corrupted': []
            },
            'png_files': {
                'existing': [],
                'missing': []
            },
            'summary': {}
        }
        
    # Check nc files
        if check_nc:
            print("\nChecking NC files...")
            results['nc_files'] = self._check_nc_files(expected_times)
            
    # Check png files
        if check_png:
            print("\nChecking PNG files...")
            results['png_files'] = self._check_png_files(expected_times)
            
    # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _check_nc_files(self, expected_times: List[str]) -> dict:
        """Check existence and integrity of nc files"""
        nc_results = {
            'existing': [],
            'missing': [],
            'corrupted': []
        }
        
        for time_str in expected_times:
            nc_path = self.parts_dir / f"{time_str}.nc"
            
            if nc_path.exists():
                # Check if file can be opened normally
                try:
                    with xr.open_dataset(nc_path) as ds:
                        # Basic integrity check
                        if 'sea_surface_temperature' in ds.data_vars:
                            nc_results['existing'].append(time_str)
                            print(f"✓ {time_str}.nc - OK")
                        else:
                            nc_results['corrupted'].append(time_str)
                            print(f"⚠ {time_str}.nc - Missing SST variable")
                except Exception as e:
                    nc_results['corrupted'].append(time_str)
                    print(f"✗ {time_str}.nc - Corrupted: {e}")
            else:
                nc_results['missing'].append(time_str)
                print(f"✗ {time_str}.nc - Missing")
                
        return nc_results
    
    def _check_png_files(self, expected_times: List[str]) -> dict:
        """Check existence of png files"""
        png_results = {
            'existing': [],
            'missing': []
        }
        
        for time_str in expected_times:
            png_path = self.png_dir / f"{time_str}.png"
            
            if png_path.exists() and png_path.stat().st_size > 0:
                png_results['existing'].append(time_str)
                print(f"✓ {time_str}.png - OK")
            else:
                png_results['missing'].append(time_str)
                print(f"✗ {time_str}.png - Missing")
                
        return png_results
    
    def _generate_summary(self, results: dict) -> dict:
        """Generate summary of check results"""
        total_expected = results['expected_files']
        
    # NC file statistics
        nc_existing = len(results['nc_files']['existing'])
        nc_missing = len(results['nc_files']['missing'])
        nc_corrupted = len(results['nc_files']['corrupted'])
        
    # PNG file statistics
        png_existing = len(results['png_files']['existing'])
        png_missing = len(results['png_files']['missing'])
        
        summary = {
            'total_expected': total_expected,
            'nc_files': {
                'existing': nc_existing,
                'missing': nc_missing,
                'corrupted': nc_corrupted,
                'completion_rate': f"{(nc_existing/total_expected)*100:.1f}%" if total_expected > 0 else "0%"
            },
            'png_files': {
                'existing': png_existing,
                'missing': png_missing,
                'completion_rate': f"{(png_existing/total_expected)*100:.1f}%" if total_expected > 0 else "0%"
            }
        }
        
        print(f"\n=== File Completeness Summary ===")
        print(f"Total expected files: {total_expected}")
        print(f"NC files - Existing: {nc_existing}, Missing: {nc_missing}, Corrupted: {nc_corrupted}")
        print(f"NC completion rate: {summary['nc_files']['completion_rate']}")
        print(f"PNG files - Existing: {png_existing}, Missing: {png_missing}")
        print(f"PNG completion rate: {summary['png_files']['completion_rate']}")
        
        return summary
    
    def repair_missing_files(
        self,
        check_results: dict,
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        netrc_path: Path = Path(".netrc"),
        repair_nc: bool = True,
        repair_png: bool = True,
        max_concurrent: int = 3
    ):
        """
        Repair missing and corrupted files
        
        Args:
            check_results: Result from check_file_completeness
            lonlims: Longitude range
            latlims: Latitude range
            netrc_path: Path to .netrc file
            repair_nc: Whether to repair nc files
            repair_png: Whether to repair png files
            max_concurrent: Maximum concurrent downloads
        """
        print("\n=== Starting File Repair ===")
        
        nc_repaired_count = 0
        nc_failed_count = 0
        png_repaired_count = 0
        png_failed_count = 0
        
    # Step 1: Repair NC files (download and process)
        if repair_nc:
            nc_files_to_repair = []
            nc_files_to_repair.extend(check_results['nc_files']['missing'])
            nc_files_to_repair.extend(check_results['nc_files']['corrupted'])
            nc_files_to_repair = sorted(list(set(nc_files_to_repair)))
            
            if nc_files_to_repair:
                print(f"\n--- Step 1: Repairing {len(nc_files_to_repair)} NC files ---")
                
                # Ensure login
                self.processor.ensure_earthdata_login(netrc_path)
                
                for i, time_str in enumerate(nc_files_to_repair, 1):
                    print(f"[{i}/{len(nc_files_to_repair)}] Downloading and processing {time_str}...")
                    
                    try:
                        # Convert time string to datetime64
                        dt = np.datetime64(pd.to_datetime(time_str, format="%Y%m%d%H%M%S"))
                        
                        # Process single time step (will download NC and generate PNG)
                        self.processor._process_single_timestamp(dt, lonlims, latlims)
                        
                        nc_repaired_count += 1
                        print(f"✓ Successfully repaired NC and PNG for {time_str}")
                        
                    except Exception as e:
                        nc_failed_count += 1
                        print(f"✗ Failed to repair {time_str}: {e}")
            else:
                print("--- Step 1: No NC files need repair ---")
        
    # Step 2: Repair PNG files (based on existing NC files)
        if repair_png:
            # Find time points missing PNG but with existing NC file
            png_only_repairs = [t for t in check_results['png_files']['missing'] 
                             if t in check_results['nc_files']['existing']]
            
            if png_only_repairs:
                print(f"\n--- Step 2: Regenerating {len(png_only_repairs)} PNG files from existing NC files ---")
                
                for i, time_str in enumerate(png_only_repairs, 1):
                    print(f"[{i}/{len(png_only_repairs)}] Regenerating PNG for {time_str}...")
                    try:
                        self._regenerate_png(time_str)
                        png_repaired_count += 1
                        print(f"✓ Regenerated PNG for {time_str}")
                    except Exception as e:
                        png_failed_count += 1
                        print(f"✗ Failed to regenerate PNG for {time_str}: {e}")
            else:
                print("--- Step 2: No PNG-only repairs needed ---")
                
        print(f"\n=== Repair Complete ===")
        print(f"NC files - Successfully repaired: {nc_repaired_count}, Failed: {nc_failed_count}")
        print(f"PNG files - Successfully regenerated: {png_repaired_count}, Failed: {png_failed_count}")
        print(f"Total operations: {nc_repaired_count + png_repaired_count} successful, {nc_failed_count + png_failed_count} failed")
    
    def _regenerate_png(self, time_str: str):
        """Regenerate PNG from existing nc file"""
        nc_path = self.parts_dir / f"{time_str}.nc"
        if not nc_path.exists():
            raise FileNotFoundError(f"NC file not found: {nc_path}")
        # Read nc file and generate visualization
        with xr.open_dataset(nc_path) as ds:
            sst_name = self.processor._find_sst_variable(ds)
            time_name = self.processor._pick_coord_name(ds, ["time", "t"])
            self.processor._create_visualization(ds, sst_name, time_name, time_str)
    
    def auto_repair_service(
        self,
        timelims: Tuple[str, str],
        lonlims: Tuple[float, float],
        latlims: Tuple[float, float],
        tstep: int = 3600,
        netrc_path: Path = Path(".netrc"),
        check_interval: int = 3600  # Check interval (seconds)
    ):
        """
        Auto repair service - periodically check and repair missing files
        
        Args:
            timelims: Time range
            lonlims: Longitude range
            latlims: Latitude range
            tstep: Time step
            netrc_path: Path to .netrc file
            check_interval: Check interval (seconds)
        """
        print("=== Starting Auto Repair Service ===")
        print(f"Check interval: {check_interval} seconds")
        print("Press Ctrl+C to stop the service")
        
        try:
            while True:
                print(f"\n[{pd.Timestamp.now()}] Running file completeness check...")
                
                # Check file integrity
                results = self.check_file_completeness(
                    timelims=timelims,
                    tstep=tstep
                )
                
                # If there are missing files, repair them
                missing_nc = len(results['nc_files']['missing'])
                corrupted_nc = len(results['nc_files']['corrupted'])
                missing_png = len(results['png_files']['missing'])
                
                if missing_nc > 0 or corrupted_nc > 0 or missing_png > 0:
                    print(f"Found issues: {missing_nc} missing NC, {corrupted_nc} corrupted NC, {missing_png} missing PNG")
                    
                    self.repair_missing_files(
                        check_results=results,
                        lonlims=lonlims,
                        latlims=latlims,
                        netrc_path=netrc_path
                    )
                else:
                    print("All files are complete and healthy.")
                
                print(f"Next check in {check_interval} seconds...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n=== Auto Repair Service Stopped ===")


def create_file_monitor(base_dir
                        : str = "data/himawari_l3c") -> HimawariFileMonitor:
    """
    Convenience function to create a file monitor
    
    Args:
        base_dir: Data directory
    
    Returns:
        HimawariFileMonitor instance
    """
    processor = HimawariDataProcessor(base_dir)
    return HimawariFileMonitor(processor)
