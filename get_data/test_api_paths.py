#!/usr/bin/env python3
"""
测试API路径修复

这个脚本验证所有路径引用是否正确修复。
"""

from pathlib import Path
import sys

def test_paths():
    """测试路径配置"""
    print("🔍 测试API路径配置...")
    
    # 测试基本路径
    current_dir = Path(__file__).parent
    print(f"当前目录: {current_dir}")
    
    # 测试Himawari路径
    himawari_path = current_dir / "himawari_test_data"
    himawari_processor_path = himawari_path / "himawari_processor.py"
    himawari_data_path = himawari_path / "data" / "himawari_l3c"
    
    print(f"\n🛰️ Himawari路径:")
    print(f"  模块路径: {himawari_path} {'✅' if himawari_path.exists() else '❌'}")
    print(f"  处理器: {himawari_processor_path} {'✅' if himawari_processor_path.exists() else '❌'}")
    print(f"  数据目录: {himawari_data_path} {'✅' if himawari_data_path.exists() else '❌'}")
    
    # 测试Sentinel-3路径
    sentinel_path = current_dir / "saternal3"
    sentinel_processor_path = sentinel_path / "usingtheEumetview.py"
    sentinel_data_path = sentinel_path / "data" / "eumetview_sentinel3"
    
    print(f"\n🛰️ Sentinel-3路径:")
    print(f"  模块路径: {sentinel_path} {'✅' if sentinel_path.exists() else '❌'}")
    print(f"  处理器: {sentinel_processor_path} {'✅' if sentinel_processor_path.exists() else '❌'}")
    print(f"  数据目录: {sentinel_data_path} {'✅' if sentinel_data_path.exists() else '❌'}")
    
    # 测试satellites模块路径
    satellites_path = current_dir / "satellites"
    shared_path = satellites_path / "shared"
    himawari_api_path = satellites_path / "himawari" / "api.py"
    sentinel_api_path = satellites_path / "sentinel3" / "api.py"
    
    print(f"\n📁 Satellites模块:")
    print(f"  satellites目录: {satellites_path} {'✅' if satellites_path.exists() else '❌'}")
    print(f"  shared模块: {shared_path} {'✅' if shared_path.exists() else '❌'}")
    print(f"  Himawari API: {himawari_api_path} {'✅' if himawari_api_path.exists() else '❌'}")
    print(f"  Sentinel-3 API: {sentinel_api_path} {'✅' if sentinel_api_path.exists() else '❌'}")
    
    return True

def test_imports():
    """测试导入"""
    print("\n🔍 测试模块导入...")
    
    try:
        # 测试共享模块
        from satellites.shared.models import SatelliteInfo
        print("  ✅ 共享模型导入成功")
        
        from satellites.shared.utils import get_system_info
        print("  ✅ 共享工具导入成功")
        
        from satellites.shared.base_api import BaseSatelliteAPI
        print("  ✅ 基础API类导入成功")
        
        # 测试卫星API
        from satellites.himawari.api import HimawariAPI
        print("  ✅ Himawari API导入成功")
        
        from satellites.sentinel3.api import Sentinel3API
        print("  ✅ Sentinel-3 API导入成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始API路径修复验证...")
    
    # 添加当前目录到Python路径
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    paths_ok = test_paths()
    imports_ok = test_imports()
    
    print(f"\n📋 测试结果:")
    print(f"  路径配置: {'✅ 正常' if paths_ok else '❌ 有问题'}")
    print(f"  模块导入: {'✅ 正常' if imports_ok else '❌ 有问题'}")
    
    if paths_ok and imports_ok:
        print("\n🎉 所有测试通过！API路径修复成功。")
        print("现在可以启动API:")
        print("  cd get_data")
        print("  python api.py")
        return 0
    else:
        print("\n⚠️ 有测试失败，请检查路径配置。")
        return 1

if __name__ == "__main__":
    exit(main())
