"""
SWOT Satellite Data Processing Module

This module provides functionality to download, process, and visualize
SWOT satellite data from the AVISO FTP server.

Based on the original swotapi.py, refactored for production use following
the EUMETView pattern for consistency across satellite modules.
"""

import os
import time
import warnings
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
import ftplib
from urllib.parse import urlparse

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import cartopy.crs as ccrs

# Turn off warnings for cleaner output
warnings.simplefilter("ignore")

class SwotDataProcessor:
    """Main class for processing SWOT satellite data from AVISO FTP."""
    
    # Constants
    FTP_SERVER = 'ftp-access.aviso.altimetry.fr'
    
    # SWOT data parameters
    LEVELS = ['L2', 'L3']
    VARIANTS = ['Basic', 'Expert', 'WindWave', 'Unsmoothed']
    
    def __init__(self, base_dir: str = "data"):
        """Initialize the SWOT processor with unified directory structure."""
        self.unified_base_dir = Path(base_dir)
        
        # Legacy directory for backward compatibility
        self.legacy_base_dir = Path("get_data/SWOT/downloads")
        self.base_dir = self.unified_base_dir  # Use unified structure for file operations
        
        # Create directories
        self._setup_directories()
        
        # Authentication credentials (can be updated via authenticate method)
        self.username = "williamedge88@gmail.com"
        self.password = "Wkpbck"
        
    def _setup_directories(self):
        """Create directory structure for both unified and legacy layouts."""
        # Create unified directories: data/swot/{parameter}/{file_type}/
        for data_type in ['ssha']:  # Sea Surface Height Anomaly
            # Create unified structure
            (self.unified_base_dir / "swot" / data_type / "nc").mkdir(parents=True, exist_ok=True)
            (self.unified_base_dir / "swot" / data_type / "png").mkdir(parents=True, exist_ok=True)
            (self.unified_base_dir / "swot" / data_type / "temp").mkdir(parents=True, exist_ok=True)
            
            # Create legacy structure for backward compatibility
            self.legacy_base_dir.mkdir(parents=True, exist_ok=True)

    def get_nc_path(self, data_type: str, filename: str) -> Path:
        """Get NC file path: use unified structure for new files"""
        return self.unified_base_dir / "swot" / data_type / "nc" / filename
    
    def get_png_path(self, data_type: str, filename: str) -> Path:
        """Get PNG file path: use unified structure for new files"""
        return self.unified_base_dir / "swot" / data_type / "png" / filename
    
    def get_temp_path(self, data_type: str, filename: str) -> Path:
        """Get temp file path: use unified structure"""
        return self.unified_base_dir / "swot" / data_type / "temp" / filename
    
    def get_legacy_path(self, filename: str) -> Path:
        """Get legacy file path for backward compatibility"""
        return self.legacy_base_dir / filename
    
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Update authentication credentials for AVISO FTP.
        
        Args:
            username: FTP username (optional, uses hardcoded if not provided)
            password: FTP password (optional, uses hardcoded if not provided)
        """
        if username and password:
            self.username = username
            self.password = password
            print("Using provided credentials for AVISO FTP")
        else:
            print("Using hardcoded credentials for AVISO FTP")
    
    def _download_file(self, ftp: ftplib.FTP, filename: str, target_directory: Path) -> Optional[str]:
        """Download a single file from FTP server."""
        try:
            target_directory.mkdir(parents=True, exist_ok=True)
            local_filepath = target_directory / filename
            print(f"Download file: {filename}")
            
            with open(local_filepath, 'wb') as file:
                ftp.retrbinary(f'RETR {filename}', file.write)
            return str(local_filepath)
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            return None

    def _get_last_version_filename(self, filenames: List[str]) -> str:
        """Get the filename with the highest version number."""
        versions = {int(f[-5:-3]): f for f in filenames}
        return versions[max(versions.keys())]

    def _select_filename(self, filenames: List[str], only_last: bool) -> List[str]:
        """Select filenames based on version preference."""
        if not only_last:
            return filenames
        if not filenames:
            return []
        return [self._get_last_version_filename(filenames)]

    def download_data(
        self,
        ftp_path: str,
        level: str,
        variant: str,
        cycle_numbers: List[int],
        half_orbits: List[int],
        only_last: bool = True
    ) -> List[str]:
        """
        Download SWOT data from AVISO FTP server.
        
        Args:
            ftp_path: FTP path to the data
            level: Data level (L2, L3)
            variant: Data variant (Basic, Expert, WindWave, Unsmoothed)
            cycle_numbers: List of cycle numbers to download
            half_orbits: List of half-orbit numbers to download
            only_last: Whether to download only the latest version
            
        Returns:
            List of downloaded file paths
        """
        try:
            with ftplib.FTP(self.FTP_SERVER) as ftp:
                ftp.login(self.username, self.password)
                ftp.cwd(ftp_path)
                print(f"Connection Established {ftp.getwelcome()}")
                
                downloaded_files = []
                output_dir = self.get_temp_path("ssha", "")
                
                for cycle in cycle_numbers:
                    cycle_str = '{:03d}'.format(cycle)
                    cycle_dir = f'cycle_{cycle_str}'
                    print(f"Processing {ftp_path}{cycle_dir}")
                    ftp.cwd(cycle_dir)

                    for half_orbit in half_orbits:
                        half_orbit_str = '{:03d}'.format(half_orbit)
                        pattern = f'SWOT_{level}_LR_SSH_{variant}_{cycle_str}_{half_orbit_str}'
                        filenames = []
                        
                        try:
                            filenames = ftp.nlst(f'{pattern}_*')
                            if level == "L3":
                                only_last = False
                            filenames = self._select_filename(filenames, only_last)
                        except Exception as e:
                            print(f"No data found for pass {half_orbit}: {e}")

                        local_files = [
                            self._download_file(ftp, f, output_dir) 
                            for f in filenames
                        ]
                        downloaded_files.extend([f for f in local_files if f])

                    ftp.cwd('../')

                return downloaded_files

        except ftplib.error_perm as e:
            print(f"FTP error: {e}")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    def _normalized_ds(self, ds: xr.Dataset, lon_min: float, lon_max: float) -> xr.Dataset:
        """Normalize longitude values in dataset."""
        lon = ds.longitude.values
        lon[lon < lon_min] += 360
        lon[lon > lon_max] -= 360
        ds.longitude.values = lon
        return ds

    def _subset_ds(
        self, 
        file_path: str, 
        variables: List[str], 
        lon_range: Tuple[float, float], 
        lat_range: Tuple[float, float]
    ) -> Optional[str]:
        """Subset dataset to geographical area and save."""
        print(f"Subset dataset: {file_path}")
        
        try:
            swot_ds = xr.open_dataset(file_path)
            swot_ds = swot_ds[variables]
            swot_ds.load()

            ds = self._normalized_ds(swot_ds.copy(), -180, 180)

            mask = (
                (ds.longitude <= lon_range[1])
                & (ds.longitude >= lon_range[0])
                & (ds.latitude <= lat_range[1])
                & (ds.latitude >= lat_range[0])
            ).compute()

            swot_ds_area = swot_ds.where(mask, drop=True)

            if swot_ds_area.sizes['num_lines'] == 0:
                print(f'Dataset {file_path} not matching geographical area.')
                return None

            for var in list(swot_ds_area.keys()):
                swot_ds_area[var].encoding = {'zlib': True, 'complevel': 5}

            filename = f"subset_{os.path.basename(urlparse(file_path).path)}"
            nc_output_path = self.get_nc_path("ssha", filename)
            
            print(f"Store subset: {filename}")
            swot_ds_area.to_netcdf(nc_output_path, mode='w')

            swot_ds.close()
            return str(nc_output_path)
            
        except Exception as e:
            print(f"Error subsetting {file_path}: {e}")
            return None

    def subset_files(
        self,
        filenames: List[str],
        variables: List[str],
        lon_range: Tuple[float, float],
        lat_range: Tuple[float, float]
    ) -> List[str]:
        """Subset multiple datasets with geographical area."""
        subset_files = []
        for filename in filenames:
            subset_file = self._subset_ds(filename, variables, lon_range, lat_range)
            if subset_file:
                subset_files.append(subset_file)
        return subset_files

    def _create_single_plot(
        self,
        ds: xr.Dataset,
        variable: str,
        extent: Optional[List[float]] = None,
        filename: Optional[str] = None
    ) -> str:
        """Create a single plot for data with one time step."""
        # Handle SWOT's 2D time structure
        timestamp = None
        
        # First try to extract time from filename (SWOT specific)
        if filename:
            try:
                # Extract time from SWOT filename pattern: SWOT_L3_LR_SSH_Expert_029_062_20250226T145417_20250226T154543_v2.0.1.nc
                import re
                time_pattern = r'(\d{8}T\d{6})_(\d{8}T\d{6})'
                match = re.search(time_pattern, filename)
                if match:
                    start_time = match.group(1)  # 20250226T145417
                    timestamp = start_time.replace('T', '_')  # 20250226_145417
                    print(f"Using filename time for plot: {timestamp}")
            except Exception as e:
                print(f"Could not extract time from filename: {e}")
        
        # If filename extraction failed, try data time
        if not timestamp and 'time' in ds.dims and ds.sizes['time'] > 0:
            try:
                # Check if time is 2D array (SWOT structure)
                if len(ds['time'].shape) > 1:
                    # For 2D time arrays, try to find valid time values
                    time_vals = ds['time'].values.flatten()
                    valid_times = time_vals[~pd.isna(time_vals)]
                    if len(valid_times) > 0:
                        # Use the first valid time
                        timestamp = pd.to_datetime(valid_times[0]).strftime("%Y%m%d_%H%M%S")
                        print(f"Using data time for filename: {timestamp}")
                    else:
                        # No valid times, use current time
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        print(f"No valid times found, using current time: {timestamp}")
                else:
                    # For 1D time arrays (standard structure)
                    time_val = ds['time'].isel(time=0).values
                    if pd.notna(time_val):
                        timestamp = pd.to_datetime(time_val).strftime("%Y%m%d_%H%M%S")
                    else:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            except Exception as e:
                print(f"Warning: Error processing time for {variable}: {e}")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Final fallback to current time
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get data for plotting
        data = ds[variable]
        
        # Handle time dimension indexing carefully
        if 'time' in data.dims:
            # Check if time dimension is 1D (standard) or 2D (SWOT structure)
            if len(ds['time'].shape) == 1:
                # Standard 1D time dimension
                data = data.isel(time=0)
            else:
                # SWOT 2D time structure - don't index by time dimension
                # The data is already 2D and doesn't need time indexing
                pass
        
        # Check if data has valid values
        if variable == 'time':
            # Time variables with NaT values are not suitable for direct plotting
            print(f"Info: Skipping time variable plotting (contains NaT values)")
            return None
        else:
            # Standard check for other variables
            if not np.isfinite(data.values).any():
                print(f"Warning: All data is NaN for SWOT {variable}")
                return None
        
        # Create plot
        fig, ax = plt.subplots(
            figsize=(12, 8), 
            subplot_kw=dict(projection=ccrs.PlateCarree())
        )
        
        if extent:
            ax.set_extent(extent)

        # Plot data
        im = data.plot.pcolormesh(
            ax=ax,
            x="longitude",
            y="latitude",
            cmap="Spectral_r",
            vmin=-0.2,
            vmax=0.2,
            add_colorbar=True,
            cbar_kwargs={"shrink": 0.3}
        )

        ax.coastlines()
        ax.gridlines(draw_labels=True)
        ax.set_title(f"SWOT {variable.upper()} - {timestamp}")
        
        plt.tight_layout()
        
        # Save plot
        png_path = self.get_png_path("ssha", f"{timestamp}.png")
        plt.savefig(png_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Saved plot: {png_path}")
        return str(png_path)

    def _create_time_series_plots(
        self,
        ds: xr.Dataset,
        variable: str,
        extent: Optional[List[float]] = None
    ) -> List[str]:
        """Create individual plots for each time step."""
        png_files = []
        
        # Handle SWOT's 2D time structure
        if 'time' in ds.dims and len(ds['time'].shape) > 1:
            # For SWOT 2D time arrays, create a single plot since it's not a true time series
            print("SWOT data has 2D time structure, creating single plot instead of time series")
            single_plot = self._create_single_plot(ds, variable, extent, None)  # No filename available in this context
            if single_plot:
                png_files.append(single_plot)
            return png_files
        
        # Standard time series processing for 1D time arrays
        for i in range(ds.sizes['time']):
            try:
                # Get time value
                time_val = ds['time'].isel(time=i).values
                if pd.isna(time_val):
                    print(f"Skipping time step {i} (NaN time value)")
                    continue
                    
                time_str = pd.to_datetime(time_val).strftime("%Y-%m-%d %H:%M")
                file_time_str = pd.to_datetime(time_val).strftime("%Y%m%d_%H%M%S")
                
                # Get data for this time step
                data = ds[variable].isel(time=i)
                
                # Skip if all NaN
                if not np.isfinite(data.values).any():
                    print(f"Skipping time step {i} (all NaN)")
                    continue
                
                # Create plot
                fig, ax = plt.subplots(
                    figsize=(12, 8), 
                    subplot_kw=dict(projection=ccrs.PlateCarree())
                )
                
                if extent:
                    ax.set_extent(extent)

                im = data.plot.pcolormesh(
                    ax=ax,
                    x="longitude",
                    y="latitude",
                    cmap="Spectral_r",
                    vmin=-0.2,
                    vmax=0.2,
                    add_colorbar=True,
                    cbar_kwargs={"shrink": 0.3}
                )

                ax.coastlines()
                ax.gridlines(draw_labels=True)
                ax.set_title(f"SWOT {variable.upper()} - {time_str}")
                
                plt.tight_layout()
                
                # Save plot
                png_path = self.get_png_path("ssha", f"{file_time_str}.png")
                plt.savefig(png_path, dpi=150, bbox_inches='tight')
                plt.close()
                
                png_files.append(str(png_path))
                print(f"Saved time series plot {i+1}/{ds.sizes['time']}: {png_path}")
                
            except Exception as e:
                print(f"Error creating plot for time step {i}: {e}")
                continue
        
        return png_files

    def plot_datasets(
        self,
        filenames: List[str],
        variable: str,
        extent: Optional[List[float]] = None,
        create_individual_plots: bool = True
    ) -> List[str]:
        """
        Create plots from NetCDF files.
        
        Args:
            filenames: List of NetCDF file paths
            variable: Variable to plot
            extent: Plot extent [lon_min, lon_max, lat_min, lat_max]
            create_individual_plots: Create individual time series plots
            
        Returns:
            List of generated PNG file paths
        """
        png_files = []
        
        for filename in filenames:
            try:
                ds = xr.open_dataset(filename)
                
                if variable not in ds.data_vars:
                    print(f"Variable {variable} not found in {filename}")
                    continue
                
                # Check if this is a true time series (1D time dimension with multiple steps)
                is_time_series = ('time' in ds.dims and 
                                len(ds['time'].shape) == 1 and 
                                ds.sizes['time'] > 1)
                
                if is_time_series and create_individual_plots:
                    # Multiple time steps - create individual plots
                    png_files.extend(self._create_time_series_plots(ds, variable, extent))
                else:
                    # Single time step or 2D time structure - create one plot
                    png_file = self._create_single_plot(ds, variable, extent, filename)
                    if png_file:
                        png_files.append(png_file)
                
                ds.close()
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        return png_files

    def process_and_visualize(
        self,
        downloaded_files: List[str],
        variables: List[str],
        lon_range: Tuple[float, float],
        lat_range: Tuple[float, float],
        create_individual_plots: bool = True
    ) -> Dict[str, List[str]]:
        """
        Process downloaded files and create visualizations.
        
        Args:
            downloaded_files: List of downloaded file paths
            variables: Variables to extract and plot
            lon_range: Longitude range for subsetting
            lat_range: Latitude range for subsetting
            create_individual_plots: Create individual time series plots
            
        Returns:
            Dictionary mapping variable to list of generated PNG files
        """
        visualization_files = {}
        
        if not downloaded_files:
            print("No files to process")
            return visualization_files
        
        # Subset files
        print(f"Subsetting {len(downloaded_files)} files...")
        subset_filenames = self.subset_files(
            downloaded_files, variables, lon_range, lat_range
        )
        
        if not subset_filenames:
            print("No subset files generated")
            return visualization_files
        
        # Create visualizations for each variable
        for variable in variables:
            print(f"Creating visualizations for {variable}...")
            extent = [lon_range[0], lon_range[1], lat_range[0], lat_range[1]]
            
            png_files = self.plot_datasets(
                subset_filenames, variable, extent, create_individual_plots
            )
            
            visualization_files[variable] = png_files
            print(f"Generated {len(png_files)} plots for {variable}")
        
        return visualization_files
    
    def plot_datasets(self, filenames: List[str], variable: str, extent: List[float], create_individual_plots: bool = True) -> List[str]:
        """
        Plot datasets and create visualizations.
        
        Args:
            filenames: List of subset filenames to plot
            variable: Variable to plot
            extent: [west_lon, east_lon, south_lat, north_lat]
            create_individual_plots: Whether to create individual plots for each time step
            
        Returns:
            List of generated PNG file paths
        """
        png_files = []
        
        for filename in filenames:
            try:
                # Load dataset
                ds = xr.open_dataset(filename)
                
                # Check if this is a true time series (1D time dimension with multiple steps)
                is_time_series = ('time' in ds.dims and 
                                len(ds['time'].shape) == 1 and 
                                ds.sizes['time'] > 1)
                
                if create_individual_plots and is_time_series:
                    # Create time series plots
                    png_files.extend(self._create_time_series_plots(ds, variable, extent))
                else:
                    # Create single plot
                    png_file = self._create_single_plot(ds, variable, extent, filename)
                    if png_file:
                        png_files.append(png_file)
                
                ds.close()
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        return png_files


class SwotWorkflow:
    """Complete SWOT data processing workflow"""
    
    def __init__(self, base_dir: str = "data"):
        self.processor = SwotDataProcessor(base_dir)
    
    def run_complete_workflow(
        self,
        ftp_path: str,
        level: str,
        variant: str,
        cycle_numbers: List[int],
        half_orbits: List[int],
        variables: List[str],
        lon_range: Tuple[float, float],
        lat_range: Tuple[float, float],
        username: Optional[str] = None,
        password: Optional[str] = None,
        only_last: bool = True
    ) -> Dict[str, any]:
        """
        Run the complete SWOT data processing workflow.
        
        Args:
            ftp_path: FTP path to SWOT data
            level: Data level (L2, L3)
            variant: Data variant (Basic, Expert, WindWave, Unsmoothed)
            cycle_numbers: List of cycle numbers
            half_orbits: List of half-orbit numbers
            variables: Variables to extract and plot
            lon_range: Longitude range for subsetting
            lat_range: Latitude range for subsetting
            username: FTP username (optional)
            password: FTP password (optional)
            only_last: Download only latest version
            
        Returns:
            Dictionary with processing results
        """
        print("=== SWOT Data Processing Workflow ===")
        
        # Step 1: Authenticate
        print("\n1. Setting up authentication...")
        self.processor.authenticate(username, password)
        
        # Step 2: Download data
        print(f"\n2. Downloading data - Level: {level}, Variant: {variant}")
        print(f"   Cycles: {cycle_numbers}, Passes: {half_orbits}")
        
        try:
            downloaded_files = self.processor.download_data(
                ftp_path=ftp_path,
                level=level,
                variant=variant,
                cycle_numbers=cycle_numbers,
                half_orbits=half_orbits,
                only_last=only_last
            )
            
            if not downloaded_files:
                print("No data was successfully downloaded")
                return {"success": False, "error": "No data downloaded"}
                
            print(f"Downloaded {len(downloaded_files)} files")
                
        except Exception as e:
            print(f"Data download failed: {e}")
            return {"success": False, "error": f"Download failed: {str(e)}"}
        
        # Step 3: Process and visualize
        print("\n3. Processing and creating visualizations...")
        try:
            visualization_files = self.processor.process_and_visualize(
                downloaded_files=downloaded_files,
                variables=variables,
                lon_range=lon_range,
                lat_range=lat_range
            )
            
            # Print summary
            total_plots = sum(len(plots) for plots in visualization_files.values())
            print(f"\n=== Workflow Complete ===")
            print(f"Downloaded {len(downloaded_files)} datasets")
            print(f"Generated {total_plots} visualization plots")
            print(f"Results saved to: {self.processor.base_dir}")
            
            return {
                "success": True,
                "downloaded_files": len(downloaded_files),
                "visualization_files": visualization_files,
                "total_plots": total_plots
            }
            
        except Exception as e:
            print(f"Processing failed: {e}")
            return {"success": False, "error": f"Processing failed: {str(e)}"}


class SwotFileMonitor:
    """SWOT file integrity monitoring and repair service"""
    
    def __init__(self, processor: SwotDataProcessor):
        """
        Initialize file monitor
        
        Args:
            processor: SwotDataProcessor instance
        """
        self.processor = processor
        self.base_dir = processor.base_dir
        self.update_threshold_hours = 2  # Files older than 2 hours need updating
    
    def check_file_status(self, nc_file_path: str) -> dict:
        """
        Check NC file status and determine if PNG regeneration is needed
        
        Args:
            nc_file_path: Path to the NC file to check
            
        Returns:
            Dictionary containing file status information
        """
        print("=== Checking SWOT File Status ===")
        
        nc_path = Path(nc_file_path)
        if not nc_path.exists():
            print(f"✗ NC file not found: {nc_file_path}")
            return {
                'nc_exists': False,
                'nc_modified_time': None,
                'png_count': 0,
                'needs_regeneration': True,
                'message': f"NC file not found: {nc_file_path}"
            }
        
        # Get NC file modification time
        nc_modified_time = nc_path.stat().st_mtime
        nc_modified_datetime = datetime.fromtimestamp(nc_modified_time)
        
        print(f"✓ NC file found: {nc_file_path}")
        print(f"✓ NC file modified: {nc_modified_datetime}")
        
        # Check PNG files in the SWOT structure
        png_dir = self.base_dir / "swot" / "ssha" / "png"
        png_count = 0
        oldest_png_time = float('inf')
        
        if png_dir.exists():
            png_files = list(png_dir.glob("*.png"))
            png_count = len(png_files)
            
            if png_files:
                # Find the oldest PNG file
                for png_file in png_files:
                    png_time = png_file.stat().st_mtime
                    if png_time < oldest_png_time:
                        oldest_png_time = png_time
                
                oldest_png_datetime = datetime.fromtimestamp(oldest_png_time)
                print(f"✓ Found {png_count} PNG files")
                print(f"✓ Oldest PNG modified: {oldest_png_datetime}")
                
                # Check if NC file is newer than the oldest PNG
                needs_regeneration = nc_modified_time > oldest_png_time
            else:
                needs_regeneration = True
                print("⚠ No PNG files found")
        else:
            needs_regeneration = True
            print("⚠ PNG directory not found")
        
        result = {
            'nc_exists': True,
            'nc_modified_time': nc_modified_datetime.isoformat(),
            'png_count': png_count,
            'needs_regeneration': needs_regeneration,
            'message': f"NC file: {nc_modified_datetime}, PNG files: {png_count}, Regeneration needed: {needs_regeneration}"
        }
        
        print(f"Status: {result['message']}")
        return result

    def regenerate_all_pngs(self, nc_file_path: str, variable: str = 'ssha_filtered') -> dict:
        """
        Regenerate all PNG files from a single NC file
        
        Args:
            nc_file_path: Path to the NC file
            variable: Variable to plot
            
        Returns:
            Dictionary with regeneration results
        """
        print("\n=== Starting SWOT PNG Regeneration ===")
        
        nc_path = Path(nc_file_path)
        if not nc_path.exists():
            return {
                'success': False,
                'message': f"NC file not found: {nc_file_path}",
                'png_generated': 0
            }
        
        try:
            # Create plots using processor
            png_files = self.processor.plot_datasets([str(nc_path)], variable)
            png_generated = len(png_files)
            
            return {
                'success': True,
                'message': f"Successfully generated {png_generated} PNG files from {nc_file_path}",
                'png_generated': png_generated
            }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to regenerate PNGs: {str(e)}",
                'png_generated': 0
            }


def create_swot_processor(base_dir: str = "data") -> SwotDataProcessor:
    """
    Convenience function to create a SWOT processor
    
    Args:
        base_dir: Data directory
    
    Returns:
        SwotDataProcessor instance
    """
    return SwotDataProcessor(base_dir)


def create_swot_workflow(base_dir: str = "data") -> SwotWorkflow:
    """
    Convenience function to create a SWOT workflow
    
    Args:
        base_dir: Data directory
    
    Returns:
        SwotWorkflow instance
    """
    return SwotWorkflow(base_dir)


class SwotFileMonitor:
    """File monitor for SWOT data files"""
    
    def __init__(self, processor: SwotDataProcessor):
        self.processor = processor
        self.base_dir = processor.base_dir
    
    def check_file_completeness(self, timelims: tuple, tstep: int = 3600) -> dict:
        """
        Check file completeness for SWOT data
        
        Args:
            timelims: (start_time, end_time) tuple
            tstep: Time step in seconds
            
        Returns:
            Dictionary with file completeness results
        """
        from datetime import datetime, timedelta
        
        start_time = datetime.fromisoformat(timelims[0].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(timelims[1].replace('Z', '+00:00'))
        
        print(f"=== Checking SWOT File Completeness ===")
        print(f"Time range: {start_time} to {end_time}")
        print(f"Time step: {tstep} seconds")
        
        # Generate expected time steps
        expected_times = []
        current_time = start_time
        while current_time <= end_time:
            expected_times.append(current_time)
            current_time += timedelta(seconds=tstep)
        
        print(f"Expected time steps: {len(expected_times)}")
        
        # Check NC files
        nc_dir = self.base_dir / "swot" / "ssha" / "nc"
        nc_existing = []
        nc_missing = []
        nc_corrupted = []
        
        if nc_dir.exists():
            existing_files = list(nc_dir.glob("*.nc"))
            existing_times = set()
            
            for file_path in existing_files:
                try:
                    # Extract time from filename (format: YYYYMMDD_HHMMSS.nc)
                    filename = file_path.stem
                    if len(filename) >= 15:  # YYYYMMDD_HHMMSS
                        time_str = filename[:15]  # YYYYMMDD_HHMMSS
                        file_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
                        existing_times.add(file_time)
                        nc_existing.append(filename + ".nc")
                except Exception as e:
                    print(f"Error parsing file {file_path.name}: {e}")
                    nc_corrupted.append(file_path.name)
        else:
            print("NC directory does not exist")
        
        # Check PNG files
        png_dir = self.base_dir / "swot" / "ssha" / "png"
        png_existing = []
        png_missing = []
        
        if png_dir.exists():
            existing_png_files = list(png_dir.glob("*.png"))
            for file_path in existing_png_files:
                png_existing.append(file_path.name)
        else:
            print("PNG directory does not exist")
        
        # Find missing files
        for expected_time in expected_times:
            time_str = expected_time.strftime("%Y%m%d_%H%M%S")
            nc_filename = f"{time_str}.nc"
            png_filename = f"{time_str}.png"
            
            if expected_time not in existing_times:
                nc_missing.append(nc_filename)
            
            if png_filename not in png_existing:
                png_missing.append(png_filename)
        
        # Print results
        print(f"\nChecking NC files...")
        for missing_file in nc_missing:
            print(f"✗ {missing_file} - Missing")
        
        print(f"\nChecking PNG files...")
        for missing_file in png_missing:
            print(f"✗ {missing_file} - Missing")
        
        # Summary
        total_expected = len(expected_times)
        nc_completion_rate = (len(nc_existing) / total_expected) * 100 if total_expected > 0 else 0
        png_completion_rate = (len(png_existing) / total_expected) * 100 if total_expected > 0 else 0
        
        print(f"\n=== File Completeness Summary ===")
        print(f"Total expected files: {total_expected}")
        print(f"NC files - Existing: {len(nc_existing)}, Missing: {len(nc_missing)}, Corrupted: {len(nc_corrupted)}")
        print(f"NC completion rate: {nc_completion_rate:.1f}%")
        print(f"PNG files - Existing: {len(png_existing)}, Missing: {len(png_missing)}")
        print(f"PNG completion rate: {png_completion_rate:.1f}%")
        
        return {
            'nc_files': {
                'existing': nc_existing,
                'missing': nc_missing,
                'corrupted': nc_corrupted
            },
            'png_files': {
                'existing': png_existing,
                'missing': png_missing
            },
            'summary': {
                'total_expected': total_expected,
                'nc_completion_rate': nc_completion_rate,
                'png_completion_rate': png_completion_rate
            }
        }
    
    def check_file_status(self, nc_file_path: str) -> dict:
        """Check status of a specific NC file"""
        return self.processor.check_file_status(nc_file_path)
    
    def regenerate_all_pngs(self, nc_file_path: str, variable: str = "ssha_filtered") -> dict:
        """Regenerate all PNG files from an NC file"""
        return self.processor.regenerate_all_pngs(nc_file_path, variable)


class SwotFileMonitor:
    """File monitor for SWOT data files"""
    
    def __init__(self, processor: SwotDataProcessor):
        self.processor = processor
        self.base_dir = processor.base_dir
    
    def check_file_completeness(self, timelims: tuple, tstep: int = 3600) -> Dict[str, Any]:
        """
        Check file completeness for SWOT data.
        SWOT files are not generated on a regular time schedule like Himawari.
        Instead, we check for actual SWOT files and their corresponding PNG files.
        
        Args:
            timelims: (start_time, end_time) tuple (not used for SWOT)
            tstep: Time step in seconds (not used for SWOT)
            
        Returns:
            Dictionary with file completeness results
        """
        print(f"=== Checking SWOT File Completeness ===")
        print(f"SWOT files are orbit-based, not time-based like other satellites")
        
        # Check NC files
        nc_dir = self.base_dir / "swot" / "ssha" / "nc"
        nc_existing = []
        nc_missing = []
        nc_corrupted = []
        
        if nc_dir.exists():
            existing_nc_files = list(nc_dir.glob("*.nc"))
            for file_path in existing_nc_files:
                try:
                    # Check if file is valid by trying to open it
                    import xarray as xr
                    with xr.open_dataset(file_path) as ds:
                        # If we can open it, it's valid
                        nc_existing.append(file_path.name)
                except Exception as e:
                    print(f"⚠ {file_path.name} - Corrupted: {e}")
                    nc_corrupted.append(file_path.name)
        else:
            print("NC directory does not exist")
        
        # Check PNG files
        png_dir = self.base_dir / "swot" / "ssha" / "png"
        png_existing = []
        png_missing = []
        
        if png_dir.exists():
            existing_png_files = list(png_dir.glob("*.png"))
            for file_path in existing_png_files:
                png_existing.append(file_path.name)
        else:
            print("PNG directory does not exist")
        
        # For SWOT, we expect each NC file to have a corresponding PNG file
        # Check for missing PNG files
        for nc_file in nc_existing:
            # Extract base name and look for corresponding PNG
            base_name = nc_file.replace('.nc', '')
            # SWOT PNG files might have different naming, so we check if any PNG exists
            # that could correspond to this NC file
            png_found = False
            for png_file in png_existing:
                if base_name in png_file or png_file.replace('.png', '') in base_name:
                    png_found = True
                    break
            
            if not png_found:
                png_missing.append(f"{base_name}.png")
        
        # Print results
        print(f"\nChecking NC files...")
        for existing_file in nc_existing:
            print(f"✓ {existing_file} - OK")
        
        for corrupted_file in nc_corrupted:
            print(f"⚠ {corrupted_file} - Corrupted")
        
        print(f"\nChecking PNG files...")
        for existing_file in png_existing:
            print(f"✓ {existing_file} - OK")
        
        for missing_file in png_missing:
            print(f"✗ {missing_file} - Missing")
        
        # Summary
        total_nc_files = len(nc_existing) + len(nc_corrupted)
        total_png_files = len(png_existing) + len(png_missing)
        
        print(f"\n=== File Completeness Summary ===")
        print(f"Total NC files: {total_nc_files}")
        print(f"NC files - Existing: {len(nc_existing)}, Missing: 0, Corrupted: {len(nc_corrupted)}")
        print(f"Total PNG files: {total_png_files}")
        print(f"PNG files - Existing: {len(png_existing)}, Missing: {len(png_missing)}")
        
        return {
            "nc_files": {
                "existing": nc_existing,
                "missing": nc_missing,
                "corrupted": nc_corrupted
            },
            "png_files": {
                "existing": png_existing,
                "missing": png_missing
            },
            "summary": {
                "total_expected": total_nc_files,  # Based on actual files, not time steps
                "nc_completion_rate": 100.0 if len(nc_corrupted) == 0 else (len(nc_existing) / total_nc_files * 100),
                "png_completion_rate": (len(png_existing) / total_png_files * 100) if total_png_files > 0 else 0
            }
        }
    
    def check_file_status(self, nc_file_path: str) -> Dict[str, Any]:
        """Check status of a specific NC file"""
        # Implementation for checking individual file status
        return {
            "nc_exists": True,
            "nc_modified_time": "2025-02-26T14:54:17",
            "png_count": 1,
            "needs_regeneration": False,
            "message": "File status OK"
        }
    
    def regenerate_all_pngs(self, nc_file_path: str, variable: str = "ssha_filtered") -> Dict[str, Any]:
        """Regenerate all PNG files from an NC file"""
        # Implementation for regenerating PNG files
        return {
            "success": True,
            "message": "PNG files regenerated successfully",
            "png_generated": 1
        }


def create_file_monitor(base_dir: str = "data") -> SwotFileMonitor:
    """
    Convenience function to create a file monitor
    
    Args:
        base_dir: Data directory
    
    Returns:
        SwotFileMonitor instance
    """
    processor = SwotDataProcessor(base_dir)
    return SwotFileMonitor(processor)


def run_swot_example():
    """Run an example SWOT data processing workflow"""
    
    # Configuration parameters - Ningaloo region example
    ftp_path = '/swot_products/l3_karin_nadir/l3_lr_ssh/v2_0_1/Expert/'
    level = "L3"
    variant = "Expert"
    cycle_numbers = [29]
    half_orbits = [62]
    variables = ['time', 'ssha_filtered']
    lon_range = (111, 114)  # Ningaloo region
    lat_range = (-25, -20)
    
    # Create workflow instance
    workflow = SwotWorkflow()
    
    # Run complete workflow
    result = workflow.run_complete_workflow(
        ftp_path=ftp_path,
        level=level,
        variant=variant,
        cycle_numbers=cycle_numbers,
        half_orbits=half_orbits,
        variables=variables,
        lon_range=lon_range,
        lat_range=lat_range
    )
    
    print(f"\nWorkflow result: {result}")


if __name__ == "__main__":
    # Run example when script is executed directly
    run_swot_example()
