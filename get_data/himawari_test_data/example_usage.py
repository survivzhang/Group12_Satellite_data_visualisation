"""
Example usage of the HimawariDataProcessor

This script demonstrates how to use the HimawariDataProcessor class
and HimawariWorkflow to download and process Himawari satellite data.
"""

from pathlib import Path
from himawari_processor import (
    HimawariDataProcessor, 
    HimawariWorkflow, 
    merge_parts_to_single_nc, 
    analyze_merged_dataset,
    run_himawari_workflow_example
)


def example_basic_usage():
    """基本用法示例：逐步处理"""
    
    print("=== Basic Usage Example ===")
    
    # Configuration
    timelims = ("2025-03-01T00:00:00", "2025-03-01T12:00:00")
    lonlims = (111, 116)  # Western Australia region
    latlims = (-24.5, -19.5)
    tstep = 3600  # 1 hour intervals
    
    # Initialize processor
    processor = HimawariDataProcessor(base_dir="data/himawari_l3c")
    
    # Example 1: Query available data
    print("\n1. Querying available data...")
    manifest = processor.query_data_manifest(
        timelims=timelims,
        lonlims=lonlims,
        latlims=latlims,
        delay_hours=4
    )
    
    print(f"Found {len(manifest)} available files")
    if len(manifest) > 0:
        print(manifest.head())
        
        # Save manifest for reference
        manifest.to_csv("himawari_manifest.csv", index=False)
        print("Saved manifest to himawari_manifest.csv")
    
    # Example 2: Process time series
    print("\n2. Processing time series...")
    processor.process_time_series(
        timelims=timelims,
        lonlims=lonlims,
        latlims=latlims,
        tstep=tstep
    )
    
    print("Processing complete!")
    print(f"Processed files saved to: {processor.parts_dir}")
    print(f"Visualizations saved to: {processor.png_dir}")
    
    # Example 3: Merge processed files
    print("\n3. Merging processed files...")
    merged_path = processor.base_dir / "merged_sst.nc"
    merge_parts_to_single_nc(processor.parts_dir, merged_path)
    
    # Example 4: Analyze merged dataset
    print("\n4. Analyzing merged dataset...")
    analyze_merged_dataset(merged_path)


def example_workflow_usage():
    """工作流用法示例：一键处理"""
    
    print("=== Workflow Usage Example ===")
    
    # Configuration
    timelims = ("2025-03-01T00:00:00", "2025-03-01T06:00:00")  # 缩短时间范围
    lonlims = (111, 116)  # Western Australia region
    latlims = (-24.5, -19.5)
    tstep = 3600  # 1 hour intervals
    
    # 使用工作流类进行一键处理
    workflow = HimawariWorkflow(base_dir="data/himawari_workflow")
    
    workflow.run_complete_workflow(
        timelims=timelims,
        lonlims=lonlims,
        latlims=latlims,
        tstep=tstep
    )


def example_analysis_only():
    """仅分析已有数据的示例"""
    
    print("=== Analysis Only Example ===")
    
    # 假设你已经有了合并的数据集
    merged_path = Path("data/himawari_l3c/merged_sst.nc")
    
    if merged_path.exists():
        analyze_merged_dataset(merged_path)
    else:
        print(f"No merged dataset found at {merged_path}")
        print("Run the complete workflow first to generate data.")


def example_custom_regions():
    """自定义区域处理示例"""
    
    print("=== Custom Region Example ===")
    
    # 定义多个感兴趣的区域
    regions = {
        "western_australia": {
            "lonlims": (111, 116),
            "latlims": (-24.5, -19.5)
        },
        "great_barrier_reef": {
            "lonlims": (145, 150),
            "latlims": (-20, -15)
        },
        "tasmania": {
            "lonlims": (144, 149),
            "latlims": (-44, -39)
        }
    }
    
    timelims = ("2025-03-01T00:00:00", "2025-03-01T06:00:00")
    
    for region_name, coords in regions.items():
        print(f"\nProcessing region: {region_name}")
        
        # 为每个区域创建单独的工作流
        workflow = HimawariWorkflow(base_dir=f"data/himawari_{region_name}")
        
        try:
            workflow.run_complete_workflow(
                timelims=timelims,
                lonlims=coords["lonlims"],
                latlims=coords["latlims"],
                tstep=3600
            )
        except Exception as e:
            print(f"Failed to process {region_name}: {e}")


def main():
    """主函数：选择运行哪个示例"""
    
    import sys
    
    if len(sys.argv) > 1:
        example_type = sys.argv[1]
    else:
        print("Available examples:")
        print("1. basic - Basic step-by-step usage")
        print("2. workflow - One-step workflow usage") 
        print("3. analysis - Analysis only")
        print("4. regions - Multiple custom regions")
        print("5. simple - Simple example using convenience function")
        
        example_type = input("Choose example (1-5): ").strip()
    
    if example_type in ["1", "basic"]:
        example_basic_usage()
    elif example_type in ["2", "workflow"]:
        example_workflow_usage()
    elif example_type in ["3", "analysis"]:
        example_analysis_only()
    elif example_type in ["4", "regions"]:
        example_custom_regions()
    elif example_type in ["5", "simple"]:
        run_himawari_workflow_example()
    else:
        print("Invalid choice. Running basic example...")
        example_basic_usage()


if __name__ == "__main__":
    main()
