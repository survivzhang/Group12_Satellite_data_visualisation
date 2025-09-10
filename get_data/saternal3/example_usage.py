"""
Example usage of the refactored EUMETView data processing module.

This script demonstrates how to use the new class-based API for downloading
and processing Sentinel-3 satellite data from EUMETView.
"""

from usingtheEumetview import EUMETViewDataProcessor, EUMETViewWorkflow, create_file_monitor

def example_basic_usage():
    """Basic usage example."""
    print("=== Basic EUMETView Usage Example ===")
    
    # Initialize processor
    processor = EUMETViewDataProcessor(base_dir="data/eumetview_example")
    
    # Authenticate (will try to read credentials from file or use defaults)
    try:
        processor.authenticate()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return
    
    # Define parameters
    layer_keys = ['sentinel3a_sst', 'sentinel3a_chl']
    region = (111, -25, 114, -20)  # Western Australia region (lon1, lat1, lon2, lat2)
    time_range = ('2025-03-01T00:00:00.000Z', '2025-03-01T12:00:00.000Z')
    
    # Download data
    print(f"\nDownloading data for layers: {layer_keys}")
    try:
        downloaded_files = processor.download_data(
            layer_keys=layer_keys,
            region=region,
            time_range=time_range
        )
        print(f"✓ Downloaded {len(downloaded_files)} datasets")
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return
    
    # Process and visualize
    print("\nProcessing and creating visualizations...")
    try:
        visualization_files = processor.process_and_visualize(downloaded_files)
        total_plots = sum(len(plots) for plots in visualization_files.values())
        print(f"✓ Generated {total_plots} visualization plots")
    except Exception as e:
        print(f"✗ Visualization failed: {e}")
    
    print(f"\n✓ Results saved to: {processor.base_dir}")

def example_workflow_usage():
    """Example using the high-level workflow class."""
    print("\n=== Workflow Usage Example ===")
    
    # Configuration
    layer_keys = ['sentinel3a_sst', 'sentinel3b_chl']
    region = (111, -25, 114, -20)  # Western Australia region
    time_range = ('2025-03-01T00:00:00.000Z', '2025-03-01T12:00:00.000Z')
    
    # Create workflow instance
    workflow = EUMETViewWorkflow(base_dir="data/eumetview_workflow")
    
    # Run complete workflow
    workflow.run_complete_workflow(
        layer_keys=layer_keys,
        region=region,
        time_range=time_range
    )

def example_layer_information():
    """Example showing how to get information about available layers."""
    print("\n=== Layer Information Example ===")
    
    processor = EUMETViewDataProcessor()
    
    print("Available layer configurations:")
    for key, layer_id in processor.LAYER_CONFIGS.items():
        satellite, data_type = processor._parse_layer_key(key)
        print(f"  {key}: {layer_id}")
        print(f"    Satellite: {satellite}, Data Type: {data_type}")
    
    # Try to authenticate and get supported formats
    try:
        processor.authenticate()
        print("\nSupported formats for sentinel3a_sst:")
        formats = processor.get_supported_formats('sentinel3a_sst')
        for fmt in formats:
            print(f"  - {fmt}")
    except Exception as e:
        print(f"Could not get format information: {e}")

def example_file_monitoring():
    """Example showing simplified file monitoring functionality."""
    print("\n=== File Monitoring Example ===")
    
    # Create file monitor
    monitor = create_file_monitor()
    
    print("Simplified file monitoring capabilities:")
    print("- Check NC file modification time")
    print("- Compare with PNG file timestamps")
    print("- Automatically regenerate all PNGs if NC file is newer")
    print("- Simple one-step operation")
    
    # Example usage (commented out as it requires actual data)
    print("\nExample usage:")
    print("# Check file status")
    print("status = monitor.check_file_status('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')")
    print("")
    print("# Regenerate all PNGs from NC file")
    print("result = monitor.regenerate_all_pngs('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')")
    print("")
    print("# Auto check and regenerate if needed")
    print("result = monitor.check_and_regenerate_if_needed('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')")
    print("")
    print("Key benefits:")
    print("- ✅ Simple: Only one NC file to monitor")
    print("- ⚡ Fast: Direct file timestamp comparison")
    print("- 🔄 Automatic: Regenerates all PNGs when NC file updates")
    print("- 📊 Comprehensive: Uses original plotting logic for all visualizations")

def example_api_server():
    """Example of running the API server."""
    print("\n=== API Server Example ===")
    print("To run the API server, execute:")
    print("python api_example.py")
    print("\nOr use uvicorn directly:")
    print("uvicorn api_example:app --host 0.0.0.0 --port 8000 --reload")
    print("\nAPI will be available at: http://localhost:8000")
    print("Interactive documentation at: http://localhost:8000/docs")

if __name__ == "__main__":
    print("EUMETView Data Processing Examples")
    print("=" * 40)
    
    # Show layer information first
    example_layer_information()
    
    # Show file monitoring capabilities
    example_file_monitoring()
    
    # Show API server info
    example_api_server()
    
    # Uncomment to run actual data processing examples
    # NOTE: These require valid EUMETView credentials
    
    print("\n" + "=" * 40)
    print("To run data processing examples, uncomment the lines below")
    print("and ensure you have valid EUMETView API credentials")
    print("=" * 40)
    
    # example_basic_usage()
    # example_workflow_usage()
