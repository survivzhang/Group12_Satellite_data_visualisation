import requests
import json

# 测试简单数据端点
url = "http://localhost:8000/api/v1/satellites/himawari/sst/simple-data/20250301020000.nc?target_time=2025-03-01T02%3A16%3A34%48.000Z"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        print("数据结构:")
        print(f"- data shape: {len(data['data'])} x {len(data['data'][0])}")
        print(f"- lons length: {len(data['lons'])}")
        print(f"- lats length: {len(data['lats'])}")
        print(f"- min_value: {data['min_value']}")
        print(f"- max_value: {data['max_value']}")
        print(f"- shape: {data['shape']}")
        
        print("\n前几个数据点:")
        print(f"- data[0][0:5]: {data['data'][0][:5]}")
        print(f"- lons[0:5]: {data['lons'][:5]}")
        print(f"- lats[0:5]: {data['lats'][:5]}")
        
        # 检查坐标范围
        print(f"\n坐标范围:")
        print(f"- lon range: {min(data['lons'])} to {max(data['lons'])}")
        print(f"- lat range: {min(data['lats'])} to {max(data['lats'])}")
        
    else:
        print(f"错误: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"异常: {e}")

