#!/usr/bin/env python3
"""
Sentinel-3 远程数据下载测试脚本
直接测试从EUMETView网站下载NC数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加路径
sys.path.append('get_data/saternal3')

def test_sentinel3_download():
    """直接测试Sentinel-3数据下载"""
    print("=== Sentinel-3 远程数据下载测试 ===")
    print(f"测试时间: {datetime.now()}")
    print()
    
    try:
        # 导入Sentinel-3模块
        from usingtheEumetview import EUMETViewDataProcessor, EUMETViewWorkflow
        print("✅ 成功导入Sentinel-3模块")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    # 1. 初始化处理器
    print("1. 初始化数据处理器...")
    try:
        processor = EUMETViewDataProcessor("data")
        print("✅ 数据处理器初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    # 2. 认证
    print("2. 认证EUMETView API...")
    try:
        processor.authenticate()
        print("✅ 认证成功")
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        return
    
    # 3. 检查可用图层
    print("3. 检查可用图层...")
    try:
        layers = processor.get_available_layers()
        print(f"✅ 可用图层: {len(layers)} 个")
        for layer in layers:
            print(f"   - {layer}")
    except Exception as e:
        print(f"❌ 获取图层失败: {e}")
        return
    
    # 4. 测试数据下载 - 使用从9月12日开始的完整时间范围
    print("4. 测试数据下载...")
    
    # 计算时间范围：从9月12日开始到现在
    end_time = datetime.now()
    start_time = datetime(2025, 9, 12, 0, 0, 0)  # 9月12日 00:00:00
    
    # 格式化时间为EUMETView API期望的格式（不包含微秒）
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    print(f"   时间范围: {start_time_str} 到 {end_time_str}")
    print(f"   区域: 西澳大利亚 (111°E, -25°N 到 114°E, -20°N)")
    
    # 测试所有四个参数
    layer_keys = ["sentinel3a_sst", "sentinel3a_chl", "sentinel3b_sst", "sentinel3b_chl"]
    region = (111.0, -25.0, 114.0, -20.0)  # (west_lon, south_lat, east_lon, north_lat)
    time_range = (start_time_str, end_time_str)
    
    try:
        print("   开始下载数据...")
        downloaded_files = processor.download_data(
            layer_keys=layer_keys,
            region=region,
            time_range=time_range
        )
        
        if downloaded_files:
            print(f"✅ 下载成功: {len(downloaded_files)} 个文件")
            for layer_key, file_path in downloaded_files.items():
                print(f"   - {layer_key}: {file_path}")
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    print(f"     文件大小: {file_size:,} 字节")
                else:
                    print(f"     ⚠️ 文件不存在")
        else:
            print("❌ 没有下载到任何文件")
            
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
    
    # 5. 检查下载的文件
    print("5. 检查下载的文件...")
    try:
        base_dir = Path("data")
        for satellite in ["sentinel3a", "sentinel3b"]:
            for data_type in ["sst", "chl"]:
                nc_dir = base_dir / satellite / data_type / "nc"
                if nc_dir.exists():
                    nc_files = list(nc_dir.glob("*.nc"))
                    print(f"   {satellite}/{data_type}: {len(nc_files)} 个NC文件")
                    for nc_file in nc_files[-3:]:  # 显示最新的3个文件
                        file_size = nc_file.stat().st_size
                        mod_time = datetime.fromtimestamp(nc_file.stat().st_mtime)
                        print(f"     - {nc_file.name} ({file_size:,} 字节, {mod_time})")
                else:
                    print(f"   {satellite}/{data_type}: 目录不存在")
    except Exception as e:
        print(f"❌ 检查文件失败: {e}")

def test_workflow():
    """测试完整工作流程"""
    print("\n=== 测试完整工作流程 ===")
    
    try:
        from usingtheEumetview import EUMETViewWorkflow
        
        # 计算时间范围：从9月12日开始到现在
        end_time = datetime.now()
        start_time = datetime(2025, 9, 12, 0, 0, 0)  # 9月12日 00:00:00
        
        print(f"时间范围: {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')} 到 {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        
        # 创建工作流
        workflow = EUMETViewWorkflow("data")
        
        # 运行工作流 - 测试所有四个参数
        workflow.run_complete_workflow(
            layer_keys=["sentinel3a_sst", "sentinel3a_chl", "sentinel3b_sst", "sentinel3b_chl"],
            region=(111.0, -25.0, 114.0, -20.0),
            time_range=(start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        
        print("✅ 工作流程完成")
        
    except Exception as e:
        print(f"❌ 工作流程失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    test_sentinel3_download()
    
    # 询问是否测试完整工作流程
    print("\n是否测试完整工作流程（包括可视化）？(y/n): ", end="")
    try:
        response = input().lower().strip()
        if response in ['y', 'yes', '是']:
            test_workflow()
    except KeyboardInterrupt:
        print("\n测试中断")
