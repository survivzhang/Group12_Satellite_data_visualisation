"""
Himawari File Monitor Example

This script demonstrates how to use the HimawariFileMonitor class
to check file completeness and repair missing files.
"""

from pathlib import Path
import sys
from himawari_processor import (
    HimawariDataProcessor,
    HimawariFileMonitor,
    create_file_monitor
)


def example_check_completeness():
    """示例：检查文件完整性"""
    
    print("=== File Completeness Check Example ===")
    
    # 配置参数
    timelims = ("2025-03-01T00:00:00", "2025-03-01T12:00:00")
    tstep = 3600  # 1小时间隔
    
    # 创建文件监控器
    monitor = create_file_monitor(base_dir="data/himawari_l3c")
    
    # 检查文件完整性
    results = monitor.check_file_completeness(
        timelims=timelims,
        tstep=tstep,
        check_nc=True,
        check_png=True
    )
    
    # 显示详细结果
    print("\n=== Detailed Results ===")
    print(f"Expected files: {results['expected_files']}")
    
    if results['nc_files']['missing']:
        print(f"Missing NC files: {results['nc_files']['missing']}")
    
    if results['nc_files']['corrupted']:
        print(f"Corrupted NC files: {results['nc_files']['corrupted']}")
        
    if results['png_files']['missing']:
        print(f"Missing PNG files: {results['png_files']['missing']}")
    
    return results


def example_repair_files():
    """示例：修复丢失的文件"""
    
    print("=== File Repair Example ===")
    
    # 配置参数
    timelims = ("2025-03-01T00:00:00", "2025-03-01T12:00:00")  # 缩短时间范围
    lonlims = (111, 116)  # 西澳大利亚地区
    latlims = (-24.5, -19.5)
    tstep = 3600
    
    # 创建文件监控器
    monitor = create_file_monitor(base_dir="data/himawari_l3c")
    
    # 1. 首先检查文件完整性
    print("Step 1: Checking file completeness...")
    results = monitor.check_file_completeness(
        timelims=timelims,
        tstep=tstep
    )
    
    # 2. 如果有丢失的文件，进行修复
    missing_count = len(results['nc_files']['missing']) + len(results['nc_files']['corrupted'])
    
    if missing_count > 0:
        print(f"\nStep 2: Found {missing_count} files to repair. Starting repair...")
        
        monitor.repair_missing_files(
            check_results=results,
            lonlims=lonlims,
            latlims=latlims,
            repair_nc=True,
            repair_png=True
        )
        
        # 3. 再次检查修复结果
        print("\nStep 3: Verifying repair results...")
        new_results = monitor.check_file_completeness(
            timelims=timelims,
            tstep=tstep
        )
        
        print("Repair verification complete!")
        
    else:
        print("No files need repair - all files are complete!")


def example_auto_repair_service():
    """示例：自动修复服务"""
    
    print("=== Auto Repair Service Example ===")
    print("This will run continuously. Press Ctrl+C to stop.")
    
    # 配置参数
    timelims = ("2025-03-01T00:00:00", "2025-03-01T12:00:00")
    lonlims = (111, 116)
    latlims = (-24.5, -19.5)
    tstep = 3600
    check_interval = 300  # 5分钟检查一次
    
    # 创建文件监控器
    monitor = create_file_monitor(base_dir="data/himawari_l3c")
    
    # 启动自动修复服务
    monitor.auto_repair_service(
        timelims=timelims,
        lonlims=lonlims,
        latlims=latlims,
        tstep=tstep,
        check_interval=check_interval
    )


def example_custom_regions():
    """示例：多区域文件检查"""
    
    print("=== Multi-Region File Check Example ===")
    
    # 定义多个区域
    regions = {
        "western_australia": {
            "lonlims": (111, 116),
            "latlims": (-24.5, -19.5),
            "base_dir": "data/himawari_western_australia"
        },
        "great_barrier_reef": {
            "lonlims": (145, 150),
            "latlims": (-20, -15),
            "base_dir": "data/himawari_gbr"
        }
    }
    
    timelims = ("2025-03-01T00:00:00", "2025-03-01T06:00:00")
    tstep = 3600
    
    for region_name, config in regions.items():
        print(f"\n=== Checking region: {region_name} ===")
        
        # 为每个区域创建单独的监控器
        monitor = create_file_monitor(base_dir=config["base_dir"])
        
        try:
            # 检查文件完整性
            results = monitor.check_file_completeness(
                timelims=timelims,
                tstep=tstep
            )
            
            # 如果有问题，可以选择修复
            missing_count = len(results['nc_files']['missing']) + len(results['nc_files']['corrupted'])
            
            if missing_count > 0:
                print(f"Region {region_name} has {missing_count} issues.")
                # 可以在这里添加修复逻辑
            else:
                print(f"Region {region_name} is complete!")
                
        except Exception as e:
            print(f"Error checking region {region_name}: {e}")


def example_png_only_repair():
    """示例：仅修复PNG文件"""
    
    print("=== PNG-Only Repair Example ===")
    
    timelims = ("2025-03-01T00:00:00", "2025-03-01T06:00:00")
    tstep = 3600
    
    # 创建文件监控器
    monitor = create_file_monitor(base_dir="data/himawari_l3c")
    
    # 检查文件完整性
    results = monitor.check_file_completeness(
        timelims=timelims,
        tstep=tstep,
        check_nc=True,
        check_png=True
    )
    
    # 仅修复PNG文件（从已存在的NC文件重新生成）
    if results['png_files']['missing']:
        print(f"Found {len(results['png_files']['missing'])} missing PNG files")
        
        monitor.repair_missing_files(
            check_results=results,
            lonlims=(111, 116),  # 这些参数在PNG修复时不会用到
            latlims=(-24.5, -19.5),
            repair_nc=False,  # 不修复NC文件
            repair_png=True   # 只修复PNG文件
        )
    else:
        print("All PNG files are present!")


def main():
    """主函数：选择运行哪个示例"""
    
    if len(sys.argv) > 1:
        example_type = sys.argv[1]
    else:
        print("Available examples:")
        print("1. check - Check file completeness")
        print("2. repair - Repair missing files")
        print("3. auto - Auto repair service (continuous)")
        print("4. regions - Multi-region check")
        print("5. png - PNG-only repair")
        
        example_type = input("Choose example (1-5): ").strip()
    
    try:
        if example_type in ["1", "check"]:
            example_check_completeness()
        elif example_type in ["2", "repair"]:
            example_repair_files()
        elif example_type in ["3", "auto"]:
            example_auto_repair_service()
        elif example_type in ["4", "regions"]:
            example_custom_regions()
        elif example_type in ["5", "png"]:
            example_png_only_repair()
        else:
            print("Invalid choice. Running completeness check...")
            example_check_completeness()
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
