"""
EUMETView Sentinel-3 Data Processing Module

This module provides functionality to download, process, and visualize
Sentinel-3 satellite data from the EUMETView WCS API.

Based on the original EUMETView WCS API tutorial, refactored for production use.
Copyright (c) 2020 EUMETSAT, License: MIT
Modified for CSSE satellite group
"""

import os
import time
import warnings
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime

import requests
from xml.etree import ElementTree
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import ssl

from owslib.wcs import WebCoverageService
from owslib.util import Authentication
import eumdac

# Turn off SSL certificate verification warnings
ssl._create_default_https_context = ssl._create_unverified_context
warnings.simplefilter("ignore")

class EUMETViewDataProcessor:
    """Main class for processing Sentinel-3 data from EUMETView WCS API."""
    
    # Constants
    SERVICE_URL = 'https://view.eumetsat.int/geoserver/wcs?'
    
    # Available data layers
    LAYER_CONFIGS = {
        'sentinel3a_sst': 'copernicus__sentinel3a_slstr_l2p_sst_fullres',
        'sentinel3b_sst': 'copernicus__sentinel3b_slstr_l2p_sst_fullres',
        'sentinel3a_chl': 'copernicus__sentinel3a_olci_l2_chl_fullres',
        'sentinel3b_chl': 'copernicus__sentinel3b_olci_l2_chl_fullres'
    }
    
    def __init__(self, base_dir: str = "data"):
        """Initialize the processor with unified directory structure."""
        self.unified_base_dir = Path(base_dir)
        
        # Legacy directory for backward compatibility
        self.legacy_base_dir = Path("saternal3/data/eumetview_sentinel3")
        self.base_dir = self.legacy_base_dir  # Keep for backward compatibility
        
        # Create directories
        self._setup_directories()
        
        # Initialize WCS connection
        self.wcs = None
        self.token = None
        
    def _setup_directories(self):
        """Create directory structure for both unified and legacy layouts."""
        # Create unified directories: data/{satellite}/{parameter}/{file_type}/
        for satellite in ['sentinel3a', 'sentinel3b']:
            for data_type in ['sst', 'chl']:
                # Create unified structure
                (self.unified_base_dir / satellite / data_type / "nc").mkdir(parents=True, exist_ok=True)
                (self.unified_base_dir / satellite / data_type / "png").mkdir(parents=True, exist_ok=True)
                
                # Create legacy structure for backward compatibility
                (self.legacy_base_dir / satellite / data_type / "nc").mkdir(parents=True, exist_ok=True)
                (self.legacy_base_dir / satellite / data_type / "png").mkdir(parents=True, exist_ok=True)

    def get_nc_path(self, satellite: str, data_type: str, filename: str) -> Path:
        """Get NC file path: use unified structure for new files"""
        return self.unified_base_dir / satellite / data_type / "nc" / filename
    
    def get_png_path(self, satellite: str, data_type: str, filename: str) -> Path:
        """Get PNG file path: use unified structure for new files"""
        return self.unified_base_dir / satellite / data_type / "png" / filename
    
    def get_legacy_nc_path(self, satellite: str, data_type: str, filename: str) -> Path:
        """Get legacy NC file path for backward compatibility"""
        return self.legacy_base_dir / satellite / data_type / "nc" / filename
    
    def get_legacy_png_path(self, satellite: str, data_type: str, filename: str) -> Path:
        """Get legacy PNG file path for backward compatibility"""
        return self.legacy_base_dir / satellite / data_type / "png" / filename
    
    
    def authenticate(self, consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None):
        """
        Authenticate with EUMETView API and establish WCS connection.
        
        Args:
            consumer_key: Consumer key (optional, uses hardcoded if not provided)
            consumer_secret: Consumer secret (optional, uses hardcoded if not provided)
        """
        # Use provided credentials or fallback to hardcoded ones
        if not consumer_key or not consumer_secret:
            print("Using hardcoded credentials for EUMETView API")
            consumer_key = 'NuIve4rLXKqpMG6X7UoCI_8fVb8a'
            consumer_secret = 'XGmZwA6bxOGH50iSbjlFibLprmUa'
        else:
            print("Using provided credentials")
        
        # Create token
        credentials = (consumer_key, consumer_secret)
        self.token = eumdac.AccessToken(credentials)
        
        print(f"Token expires: {self.token.expiration}")
        
        # Initialize WCS connection
        self.wcs = WebCoverageService(
            self.SERVICE_URL,
            auth=Authentication(verify=False),
            version='2.0.1',
            timeout=120
        )
        
        print("✓ Successfully authenticated with EUMETView API")
    
    def get_available_layers(self) -> List[str]:
        """Get list of available data layers."""
        if not self.wcs:
            raise RuntimeError("WCS not initialized. Call authenticate() first.")
        
        return list(self.LAYER_CONFIGS.values())
    
    def describe_coverage(self, layer_key: str) -> str:
        """Get coverage description for a data layer."""
        if not self.wcs or not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        layer_id = self.LAYER_CONFIGS.get(layer_key)
        if not layer_id:
            raise ValueError(f"Unknown layer: {layer_key}. Available: {list(self.LAYER_CONFIGS.keys())}")
        
        payload = {
            'service': 'WCS',
            'access_token': self.token,
            'request': 'DescribeCoverage',
            'version': '2.0.1',
            'coverageID': [layer_id]
        }
        
        response = requests.get(self.SERVICE_URL, params=payload, verify=False)
        return response.text

    
    def get_supported_formats(self, layer_key: str) -> List[str]:
        """Get supported output formats for a data layer."""
        if not self.wcs:
            raise RuntimeError("WCS not initialized. Call authenticate() first.")
        
        layer_id = self.LAYER_CONFIGS.get(layer_key)
        if not layer_id:
            raise ValueError(f"Unknown layer: {layer_key}")
        
        if layer_id in self.wcs.contents:
            return list(self.wcs.contents[layer_id].supportedFormats)
        else:
            return ['application/x-netcdf']  # Default format

    
    def download_data(
        self,
        layer_keys: List[str],
        region: Tuple[float, float, float, float],  # (lon1, lat1, lon2, lat2)
        time_range: Tuple[str, str],  # (start_time, end_time)
        format_option: str = 'application/x-netcdf'
    ) -> Dict[str, Path]:
        """
        Download satellite data for specified layers and parameters.
        
        Args:
            layer_keys: List of layer keys to download
            region: Bounding box (lon1, lat1, lon2, lat2)
            time_range: Time range (start_time, end_time) in ISO format
            format_option: Output format
            
        Returns:
            Dictionary mapping layer_key to downloaded file path
        """
        if not self.wcs or not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        downloaded_files = {}
        
        for layer_key in layer_keys:
            try:
                file_path = self._download_single_layer(
                    layer_key, region, time_range, format_option
                )
                downloaded_files[layer_key] = file_path
                print(f"✓ Downloaded {layer_key}: {file_path}")
                
            except Exception as e:
                print(f"✗ Failed to download {layer_key}: {e}")
                continue
        
        return downloaded_files

    
    def _download_single_layer(
        self,
        layer_key: str,
        region: Tuple[float, float, float, float],
        time_range: Tuple[str, str],
        format_option: str
    ) -> Path:
        """Download a single data layer."""
        layer_id = self.LAYER_CONFIGS.get(layer_key)
        if not layer_id:
            raise ValueError(f"Unknown layer: {layer_key}")
        
        # Prepare payload for WCS request
        payload = {
            'identifier': [layer_id],
            'format': format_option,
            'crs': 'EPSG:4326',
            'subsets': [
                ('Lat', region[1], region[3]),
                ('Long', region[0], region[2]),
                ('Time', time_range[0], time_range[1])
            ],
            'access_token': self.token
        }
        
        # Make WCS request
        output = self.wcs.getCoverage(**payload)
        
        # Determine output file path using satellite/datatype/nc structure
        satellite, data_type = self._parse_layer_key(layer_key)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.nc"
        file_path = self.get_nc_path(satellite, data_type, filename)
        
        # Save data
        with open(file_path, 'wb') as f:
            f.write(output.read())
        
        return file_path
    
    def _parse_layer_key(self, layer_key: str) -> Tuple[str, str]:
        """Parse layer key to extract satellite and data type."""
        if 'sentinel3a' in layer_key:
            satellite = 'sentinel3a'
        elif 'sentinel3b' in layer_key:
            satellite = 'sentinel3b'
        else:
            satellite = 'unknown'
        
        if 'sst' in layer_key:
            data_type = 'sst'
        elif 'chl' in layer_key:
            data_type = 'chl'
        else:
            data_type = 'unknown'
        
        return satellite, data_type

    
    def process_and_visualize(
        self,
        downloaded_files: Dict[str, Path],
        create_individual_plots: bool = True,
        create_combined_plot: bool = True
    ) -> Dict[str, List[Path]]:
        """
        Process downloaded NetCDF files and create visualizations.
        
        Args:
            downloaded_files: Dictionary of layer_key -> file_path
            create_individual_plots: Create individual time series plots
            create_combined_plot: Create combined overview plot
            
        Returns:
            Dictionary mapping layer_key to list of generated PNG files
        """
        visualization_files = {}
        
        for layer_key, nc_file in downloaded_files.items():
            try:
                png_files = self._process_single_file(
                    layer_key, nc_file, create_individual_plots
                )
                visualization_files[layer_key] = png_files
                
            except Exception as e:
                print(f"Failed to process {layer_key}: {e}")
                visualization_files[layer_key] = []
        
        return visualization_files
    
    def _process_single_file(
        self,
        layer_key: str,
        nc_file: Path,
        create_individual_plots: bool = True
    ) -> List[Path]:
        """Process a single NetCDF file and create visualizations."""
        try:
            # Open dataset with xarray
            ds = xr.open_dataset(nc_file)
            
            # Find the main data variable
            data_var = self._find_data_variable(ds, layer_key)
            if not data_var:
                print(f"No data variable found in {nc_file}")
                return []
            
            # Get satellite and data type for file naming
            satellite, data_type = self._parse_layer_key(layer_key)
            
            png_files = []
            
            if 'time' in ds.dims and ds.sizes['time'] > 1:
                # Multiple time steps - create individual plots
                if create_individual_plots:
                    png_files.extend(self._create_time_series_plots(
                        ds, data_var, satellite, data_type
                    ))
            else:
                # Single time step - create one plot
                png_files.append(self._create_single_plot(
                    ds, data_var, satellite, data_type
                ))
            
            ds.close()
            return png_files
            
        except Exception as e:
            print(f"Error processing {nc_file}: {e}")
            return []
    
    def _find_data_variable(self, ds: xr.Dataset, layer_key: str) -> Optional[str]:
        """Find the main data variable in the dataset."""
        # Try to find the variable based on the layer name pattern
        layer_id = self.LAYER_CONFIGS.get(layer_key, '')
        
        # Convert layer ID to expected variable name
        var_name = layer_id.replace('__', '_')
        if var_name in ds.data_vars:
            return var_name
        
        # Fallback: look for common patterns
        for var in ds.data_vars:
            if any(keyword in var.lower() for keyword in ['sst', 'temperature', 'chl', 'chlorophyll']):
                return var
        
        # Last resort: return first data variable
        if ds.data_vars:
            return list(ds.data_vars)[0]
        
        return None
    
    def _create_single_plot(
        self,
        ds: xr.Dataset,
        data_var: str,
        satellite: str,
        data_type: str
    ) -> Path:
        """Create a single plot for data with one time step."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get data for plotting
        data = ds[data_var]
        if 'time' in data.dims:
            data = data.isel(time=0)
        
        # Check if data has valid values
        if not np.isfinite(data.values).any():
            print(f"Warning: All data is NaN for {satellite}_{data_type}")
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Set colormap based on data type
        cmap = 'viridis' if data_type == 'chl' else 'turbo'
        
        im = ax.pcolormesh(ds['lon'], ds['lat'], data, cmap=cmap)
        plt.colorbar(im, ax=ax, label=self._get_data_label(data_type))
        
        ax.set_title(f"{satellite.upper()} {data_type.upper()} - {timestamp}")
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        
        plt.tight_layout()
        
        # Save plot using satellite/datatype/png structure
        png_path = self.get_png_path(satellite, data_type, f"{timestamp}.png")
        plt.savefig(png_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Saved plot: {png_path}")
        return png_path
    
    def _create_time_series_plots(
        self,
        ds: xr.Dataset,
        data_var: str,
        satellite: str,
        data_type: str
    ) -> List[Path]:
        """Create individual plots for each time step."""
        png_files = []
        
        for i in range(ds.sizes['time']):
            try:
                # Get time value
                time_val = ds['time'].isel(time=i).values
                time_str = pd.to_datetime(time_val).strftime("%Y-%m-%d %H:%M")
                file_time_str = pd.to_datetime(time_val).strftime("%Y%m%d_%H%M%S")
                
                # Get data for this time step
                data = ds[data_var].isel(time=i)
                
                # Skip if all NaN
                if not np.isfinite(data.values).any():
                    print(f"Skipping time step {i} (all NaN)")
                    continue
                
                # Create plot
                fig, ax = plt.subplots(figsize=(10, 8))
                
                cmap = 'viridis' if data_type == 'chl' else 'turbo'
                im = ax.pcolormesh(ds['lon'], ds['lat'], data, cmap=cmap)
                plt.colorbar(im, ax=ax, label=self._get_data_label(data_type))
                
                ax.set_title(f"{satellite.upper()} {data_type.upper()} - {time_str}")
                ax.set_xlabel('Longitude')
                ax.set_ylabel('Latitude')
                
                plt.tight_layout()
                
                # Save plot using satellite/datatype/png structure
                png_path = self.get_png_path(satellite, data_type, f"{file_time_str}.png")
                plt.savefig(png_path, dpi=150, bbox_inches='tight')
                plt.close()
                
                png_files.append(png_path)
                print(f"Saved time series plot {i+1}/{ds.sizes['time']}: {png_path}")
                
            except Exception as e:
                print(f"Error creating plot for time step {i}: {e}")
                continue
        
        return png_files
    
    def _get_data_label(self, data_type: str) -> str:
        """Get appropriate label for data type."""
        labels = {
            'sst': 'Sea Surface Temperature (K)',
            'chl': 'Chlorophyll Concentration (mg/m³)'
        }
        return labels.get(data_type, 'Value')


class EUMETViewWorkflow:
    """Complete EUMETView data processing workflow"""
    
    def __init__(self, base_dir: str = "data/eumetview_sentinel3"):
        self.processor = EUMETViewDataProcessor(base_dir)
    
    def run_complete_workflow(
        self,
        layer_keys: List[str],
        region: Tuple[float, float, float, float],
        time_range: Tuple[str, str],
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None
    ):
        """
        Run the complete data processing workflow.
        
        Args:
            layer_keys: List of layer keys to process
            region: Bounding box (lon1, lat1, lon2, lat2)
            time_range: Time range (start_time, end_time)
            consumer_key: Consumer key (optional, uses hardcoded if not provided)
            consumer_secret: Consumer secret (optional, uses hardcoded if not provided)
        """
        print("=== EUMETView Data Processing Workflow ===")
        
        # Step 1: Authenticate
        print("\n1. Authenticating...")
        try:
            self.processor.authenticate(consumer_key, consumer_secret)
        except Exception as e:
            print(f"Authentication failed: {e}")
            return
        
        # Step 2: Download data
        print(f"\n2. Downloading data for layers: {layer_keys}")
        try:
            downloaded_files = self.processor.download_data(
                layer_keys=layer_keys,
                region=region,
                time_range=time_range
            )
            
            if not downloaded_files:
                print("No data was successfully downloaded")
                return
                
        except Exception as e:
            print(f"Data download failed: {e}")
            return
        
        # Step 3: Process and visualize
        print("\n3. Processing and creating visualizations...")
        try:
            visualization_files = self.processor.process_and_visualize(
                downloaded_files=downloaded_files
            )
            
            # Print summary
            total_plots = sum(len(plots) for plots in visualization_files.values())
            print(f"\n=== Workflow Complete ===")
            print(f"Downloaded {len(downloaded_files)} datasets")
            print(f"Generated {total_plots} visualization plots")
            print(f"Results saved to: {self.processor.base_dir}")
            
        except Exception as e:
            print(f"Visualization failed: {e}")


# Convenience function for example usage
def run_eumetview_example():
    """Run an example EUMETView data processing workflow"""
    
    # Configuration parameters
    layer_keys = ['sentinel3a_sst', 'sentinel3a_chl']
    region = (111, -25, 114, -20)  # Western Australia region
    time_range = ('2025-03-01T00:00:00.000Z', '2025-03-01T12:00:00.000Z')
    
    # Create workflow instance
    workflow = EUMETViewWorkflow()
    
    # Run complete workflow
    workflow.run_complete_workflow(
        layer_keys=layer_keys,
        region=region,
        time_range=time_range
    )


class EUMETViewFileMonitor:
    """EUMETView file integrity monitoring and repair service"""
    
    def __init__(self, processor: EUMETViewDataProcessor):
        """
        Initialize file monitor
        
        Args:
            processor: EUMETViewDataProcessor instance
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
        print("=== Checking File Status ===")
        
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
        
        # Check PNG files in the same satellite/datatype structure
        # nc_path format: base_dir/satellite/datatype/nc/filename.nc
        # png_dir format: base_dir/satellite/datatype/png/
        satellite = nc_path.parent.parent.parent.name  # satellite name
        data_type = nc_path.parent.parent.name         # datatype name
        png_dir = self.base_dir / satellite / data_type / "png"
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
    
    def check_data_freshness(self, satellite: str, data_type: str) -> dict:
        """
        Check if data needs updating based on file age (Sentinel-3 specific)
        
        Args:
            satellite: Satellite name (sentinel3a, sentinel3b)
            data_type: Data type (sst, chl)
            
        Returns:
            Dictionary containing freshness check results
        """
        print(f"=== Checking Data Freshness for {satellite}/{data_type} ===")
        
        # Get the NC directory for this satellite/data_type
        nc_dir = self.base_dir / satellite / data_type / "nc"
        
        if not nc_dir.exists():
            return {
                'needs_update': True,
                'reason': 'NC directory does not exist',
                'latest_file': None,
                'file_age_hours': None,
                'threshold_hours': self.update_threshold_hours
            }
        
        # Find the most recent NC file
        nc_files = list(nc_dir.glob("*.nc"))
        if not nc_files:
            return {
                'needs_update': True,
                'reason': 'No NC files found',
                'latest_file': None,
                'file_age_hours': None,
                'threshold_hours': self.update_threshold_hours
            }
        
        # Get the newest file
        latest_file = max(nc_files, key=lambda f: f.stat().st_mtime)
        file_modified_time = latest_file.stat().st_mtime
        current_time = datetime.now().timestamp()
        
        # Calculate file age in hours
        file_age_hours = (current_time - file_modified_time) / 3600
        
        # Check if file is older than threshold
        needs_update = file_age_hours > self.update_threshold_hours
        
        latest_file_datetime = datetime.fromtimestamp(file_modified_time)
        
        print(f"✓ Latest file: {latest_file.name}")
        print(f"✓ File modified: {latest_file_datetime}")
        print(f"✓ File age: {file_age_hours:.2f} hours")
        print(f"✓ Threshold: {self.update_threshold_hours} hours")
        print(f"✓ Needs update: {needs_update}")
        
        return {
            'needs_update': needs_update,
            'reason': f'File is {file_age_hours:.2f} hours old' if needs_update else 'File is fresh',
            'latest_file': str(latest_file),
            'latest_file_name': latest_file.name,
            'file_age_hours': file_age_hours,
            'threshold_hours': self.update_threshold_hours,
            'file_modified': latest_file_datetime.isoformat()
        }
    
    def check_all_data_freshness(self) -> dict:
        """
        Check freshness for all satellite/data_type combinations
        
        Returns:
            Dictionary with freshness results for all combinations
        """
        print("=== Checking All Data Freshness ===")
        
        results = {}
        needs_update_count = 0
        
        for satellite in ['sentinel3a', 'sentinel3b']:
            for data_type in ['sst', 'chl']:
                key = f"{satellite}_{data_type}"
                result = self.check_data_freshness(satellite, data_type)
                results[key] = result
                
                if result['needs_update']:
                    needs_update_count += 1
        
        return {
            'results': results,
            'total_checked': len(results),
            'needs_update_count': needs_update_count,
            'all_fresh': needs_update_count == 0,
            'timestamp': datetime.now().isoformat()
        }
    def check_and_regenerate_if_needed(self, nc_file_path: str) -> dict:
        """
        Check NC file status and regenerate PNGs if needed
        
        Args:
            nc_file_path: Path to the NC file to check
            
        Returns:
            Dictionary with operation results
        """
        print("=== Auto Check and Regenerate ===")
        
        # Check file status
        status = self.check_file_status(nc_file_path)
        
        if not status['nc_exists']:
            return status
        
        if status['needs_regeneration']:
            print("\n🔄 NC file is newer than PNG files, regenerating...")
            regen_result = self.regenerate_all_pngs(nc_file_path)
            
            return {
                **status,
                'regeneration_performed': True,
                'regeneration_success': regen_result['success'],
                'png_generated': regen_result['png_generated'],
                'final_message': f"Regenerated {regen_result['png_generated']} PNG files"
            }
        else:
            print("\n✅ PNG files are up to date, no regeneration needed")
            return {
                **status,
                'regeneration_performed': False,
                'final_message': "PNG files are up to date"
            }
    
    def regenerate_all_pngs(self, nc_file_path: str) -> dict:
        """
        Regenerate all PNG files from a single NC file
        
        Args:
            nc_file_path: Path to the NC file
            
        Returns:
            Dictionary with regeneration results
        """
        print("\n=== Starting PNG Regeneration ===")
        
        nc_path = Path(nc_file_path)
        if not nc_path.exists():
            return {
                'success': False,
                'message': f"NC file not found: {nc_file_path}",
                'png_generated': 0
            }
        
        try:
            # Open the NC file
            with xr.open_dataset(nc_path) as ds:
                # Find the main data variable
                data_var = self.processor._find_data_variable(ds, "")
                if not data_var:
                    return {
                        'success': False,
                        'message': f"No data variable found in {nc_file_path}",
                        'png_generated': 0
                    }
                
                # Parse satellite and data type from file path
                # nc_path format: base_dir/satellite/datatype/nc/filename.nc
                satellite = nc_path.parent.parent.parent.name  # satellite name
                data_type = nc_path.parent.parent.name         # datatype name
                
                png_generated = 0
                
                # Check if data has time dimension
                if 'time' in ds.dims and ds.sizes['time'] > 1:
                    print(f"Generating {ds.sizes['time']} individual PNG files...")
                    
                    # Generate individual plots for each time step
                    png_files = self.processor._create_time_series_plots(
                        ds, data_var, satellite, data_type
                    )
                    png_generated = len(png_files)
                    
                else:
                    print("Generating single PNG file...")
                    
                    # Generate single plot
                    png_file = self.processor._create_single_plot(
                        ds, data_var, satellite, data_type
                    )
                    png_generated = 1 if png_file else 0
                
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


def create_file_monitor(base_dir: str = "data/eumetview_sentinel3") -> EUMETViewFileMonitor:
    """
    Convenience function to create a file monitor
    
    Args:
        base_dir: Data directory
    
    Returns:
        EUMETViewFileMonitor instance
    """
    processor = EUMETViewDataProcessor(base_dir)
    return EUMETViewFileMonitor(processor)


def run_freshness_check_example():
    """Run an example of the freshness checking system"""
    print("=== EUMETView Data Freshness Check Example ===")
    
    # Create file monitor
    monitor = create_file_monitor()
    
    # Check freshness for all data
    results = monitor.check_all_data_freshness()
    
    print(f"\n=== Summary ===")
    print(f"Total combinations checked: {results['total_checked']}")
    print(f"Need updates: {results['needs_update_count']}")
    print(f"All fresh: {results['all_fresh']}")
    
    # Show details for each combination
    for key, result in results['results'].items():
        print(f"\n{key}:")
        print(f"  Needs update: {result['needs_update']}")
        print(f"  Reason: {result['reason']}")
        if result['latest_file']:
            print(f"  Latest file: {result['latest_file_name']}")
            print(f"  File age: {result['file_age_hours']:.2f} hours")

if __name__ == "__main__":
    # Run example when script is executed directly
    run_eumetview_example()
    
    # Uncomment to test freshness checking
    # run_freshness_check_example()