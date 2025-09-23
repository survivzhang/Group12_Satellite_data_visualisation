#!/usr/bin/env python3
"""
测试新的网格数据API端点
"""

import requests
import json

def test_grid_api():
    """测试网格数据API"""
    url = "http://localhost:8000/api/v1/satellites/himawari/sst/grid-data/20250301000000.nc"
    params = {
        "target_time": "2025-03-01T00:00:00Z",
        "max_grid_size": 50  # 小一点用于测试
    }
    
    try:
        print("测试网格数据API...")
        print(f"URL: {url}")
        print(f"参数: {params}")
        
        response = requests.get(url, params=params, timeout=30)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API调用成功!")
            print(f"网格形状: {data['shape']}")
            print(f"数据类型: {data['metadata']['grid_type']}")
            print(f"有效像素: {data['statistics']['valid_pixels']}")
            print(f"总像素: {data['statistics']['total_pixels']}")
            print(f"边界: {data['bounds']}")
            return True
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

if __name__ == "__main__":
    test_grid_api()

