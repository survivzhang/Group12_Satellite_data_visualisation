# Unified Satellite Data API

这是一个统一的卫星数据API系统，整合了多个卫星数据源，提供标准化的RESTful接口。

## 🛰️ 支持的卫星

| 卫星 | 状态 | 参数 | 描述 |
|------|------|------|------|
| **Himawari-9** | ✅ | SST | 日本静止气象卫星，海表温度数据 |
| **Sentinel-3A** | ✅ | SST, CHL | 欧洲海洋陆地监测卫星，海表温度和叶绿素数据 |
| **Sentinel-3B** | ✅ | SST, CHL | 欧洲海洋陆地监测卫星，海表温度和叶绿素数据 |

## 📁 API架构

### 三层结构设计

```
/api/v1/{satellite}/{parameter}/{file_type}
```

1. **第一层 - 卫星名称**: `himawari`, `sentinel3a`, `sentinel3b`
2. **第二层 - 参数名称**: `sst`, `chl`, `ndvi`, `cloud` 等
3. **第三层 - 文件类型**: `nc` (NetCDF数据), `png` (可视化图片)

### 示例URL

```
# Himawari海表温度数据
GET /api/v1/satellites/himawari/sst/nc          # NetCDF文件列表
GET /api/v1/satellites/himawari/sst/png         # PNG图片列表
GET /static/himawari/sst/png/20250301120000.png # 直接访问图片

# Sentinel-3A叶绿素数据  
GET /api/v1/satellites/sentinel3a/chl/nc        # NetCDF文件列表
GET /api/v1/satellites/sentinel3a/chl/png       # PNG图片列表
GET /static/sentinel3a/chl/png/20250301120000.png # 直接访问图片
```

## 🚀 快速开始

### 1. 环境设置

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动统一API

```bash
# 在 get_data 目录下运行
python api_example.py

# 或使用 uvicorn
uvicorn api_example:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问API

- **API根页面**: http://localhost:8000
- **交互式文档**: http://localhost:8000/docs  
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 📡 API端点详解

### 基础信息

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API概览和卫星状态 |
| `/health` | GET | 系统健康检查 |
| `/api/v1/satellites` | GET | 列出所有卫星 |

### 卫星信息

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/satellites/{satellite}` | GET | 获取卫星详细信息 |
| `/api/v1/satellites/{satellite}/{parameter}` | GET | 获取参数详细信息 |

### 文件管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/satellites/{satellite}/{parameter}/{file_type}` | GET | 列出文件 |
| `/api/v1/satellites/{satellite}/{parameter}/nc/{filename}` | GET | 下载NC文件 |
| `/static/{satellite}/{parameter}/png/{filename}` | GET | 访问PNG图片 |

### 数据处理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/process` | POST | 启动数据处理任务 |

## 💡 使用示例

### 1. 获取卫星列表

```bash
curl http://localhost:8000/api/v1/satellites
```

```json
{
  "satellites": {
    "himawari": {
      "name": "Himawari-9",
      "description": "Japanese geostationary weather satellite",
      "available": true,
      "parameters": {
        "sst": {
          "name": "Sea Surface Temperature",
          "unit": "Kelvin",
          "description": "Ocean surface temperature data"
        }
      }
    },
    "sentinel3a": {
      "name": "Sentinel-3A", 
      "description": "European ocean and land monitoring satellite",
      "available": true,
      "parameters": {
        "sst": {...},
        "chl": {...}
      }
    }
  }
}
```

### 2. 获取特定卫星的文件列表

```bash
# 获取Himawari SST的PNG文件
curl http://localhost:8000/api/v1/satellites/himawari/sst/png
```

```json
{
  "satellite": "himawari",
  "parameter": "sst", 
  "file_type": "png",
  "files": [
    {
      "filename": "20250301120000.png",
      "size_bytes": 245760,
      "modified": "2025-01-08T12:00:00",
      "url": "/static/himawari/sst/png/20250301120000.png"
    }
  ],
  "total": 1
}
```

### 3. 启动数据处理

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "satellite": "himawari",
    "parameter": "sst",
    "start_time": "2025-03-01T00:00:00",
    "end_time": "2025-03-01T12:00:00",
    "west_lon": 113.0,
    "east_lon": 115.0,
    "south_lat": -25.0,
    "north_lat": -20.0
  }'
```

### 4. JavaScript前端集成

```javascript
// 获取卫星列表
const getSatellites = async () => {
  const response = await fetch('http://localhost:8000/api/v1/satellites');
  return await response.json();
};

// 获取文件列表
const getFiles = async (satellite, parameter, fileType) => {
  const url = `http://localhost:8000/api/v1/satellites/${satellite}/${parameter}/${fileType}`;
  const response = await fetch(url);
  return await response.json();
};

// 显示图片
const showImage = (satellite, parameter, filename) => {
  const imageUrl = `http://localhost:8000/static/${satellite}/${parameter}/png/${filename}`;
  document.getElementById('image').src = imageUrl;
};

// 处理数据
const processData = async (satellite, parameter, timeRange, region) => {
  const response = await fetch('http://localhost:8000/api/v1/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      satellite,
      parameter,
      start_time: timeRange.start,
      end_time: timeRange.end,
      ...region
    })
  });
  return await response.json();
};
```

## 🔧 扩展新卫星

### 1. 添加卫星配置

在 `api_example.py` 中的 `SATELLITE_CONFIG` 添加新卫星：

```python
SATELLITE_CONFIG = {
    # ... 现有卫星 ...
    "landsat8": {
        "name": "Landsat-8",
        "description": "American Earth observation satellite",
        "available": True,
        "base_port": 8004,
        "parameters": {
            "ndvi": {
                "name": "Normalized Difference Vegetation Index",
                "unit": "index",
                "description": "Vegetation health indicator"
            },
            "lst": {
                "name": "Land Surface Temperature", 
                "unit": "Kelvin",
                "description": "Land surface temperature data"
            }
        },
        "data_dir": "landsat8/data"
    }
}
```

### 2. 创建卫星模块

创建 `landsat8/` 目录和相应的处理模块：

```
get_data/
├── landsat8/
│   ├── landsat_processor.py    # 数据处理逻辑
│   ├── api_example.py          # 卫星专用API
│   └── data/
│       ├── ndvi/
│       │   ├── nc/
│       │   └── png/
│       └── lst/
│           ├── nc/
│           └── png/
```

### 3. 实现处理接口

新卫星模块需要实现标准接口：

```python
# landsat8/api_example.py
class ProcessingRequest(BaseModel):
    start_time: str
    end_time: str
    west_lon: float
    east_lon: float  
    south_lat: float
    north_lat: float
    # 其他卫星特定参数

async def process_satellite_data(request: ProcessingRequest, background_tasks: BackgroundTasks):
    # 实现数据处理逻辑
    pass
```

## 📊 目录结构

```
get_data/
├── api_example.py              # 统一API入口
├── README.md                   # 本文档
├── requirements.txt            # 依赖包
├── himawari_test_data/         # Himawari卫星模块
│   ├── api_example.py
│   ├── himawari_processor.py
│   └── data/himawari_l3c/
│       ├── parts/              # NC文件
│       └── png/                # PNG文件
├── saternal3/                  # Sentinel-3卫星模块
│   ├── api_example.py
│   ├── usingtheEumetview.py
│   └── data/eumetview_sentinel3/
│       ├── sentinel3a/
│       │   ├── sst/
│       │   │   ├── nc/
│       │   │   └── png/
│       │   └── chl/
│       │       ├── nc/
│       │       └── png/
│       └── sentinel3b/
│           ├── sst/
│           └── chl/
└── venv/                       # 虚拟环境
```

## 🔍 监控和调试

### 健康检查

```bash
curl http://localhost:8000/health
```

### 查看日志

```bash
# 启动时查看详细日志
uvicorn api_example:app --host 0.0.0.0 --port 8000 --log-level debug
```

### 系统状态

访问 http://localhost:8000 查看：
- 各卫星可用状态
- 参数支持情况  
- API端点列表

## 🚀 生产部署

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api_example:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 负载均衡

```nginx
upstream satellite_api {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://satellite_api;
    }
}
```

## 📈 性能优化

1. **缓存策略**: 使用Redis缓存文件列表
2. **CDN加速**: 静态文件使用CDN分发
3. **数据库**: 使用PostgreSQL存储元数据
4. **异步处理**: 大数据处理使用Celery队列

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

MIT License - 详见LICENSE文件
