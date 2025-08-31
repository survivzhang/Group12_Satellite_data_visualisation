# Himawari Satellite Data Processing

This module provides tools for downloading, processing, and serving Himawari-9 satellite sea surface temperature data with automatic file monitoring and repair capabilities.

## ✨ 主要功能

- 🛰️ **卫星数据处理**: 自动下载和处理Himawari-9海表温度数据
- 🖼️ **可视化生成**: 自动生成PNG图像用于前端显示
- 🔍 **文件监控**: 检查数据完整性，识别缺失和损坏的文件
- 🔧 **自动修复**: 智能修复缺失的NC和PNG文件
- 🌐 **API服务**: FastAPI后端服务，支持前端集成
- ⚡ **实时更新**: 支持前端Timeline的实时PNG图像显示

## 📁 文件结构

```
himawari_test_data/
├── himawari_processor.py        # 核心数据处理类
├── api_example.py              # FastAPI后端API
├── file_monitor_example.py     # 文件监控示例
├── example_usage.py            # 基础使用示例
├── test_api.py                 # API测试脚本
├── data/                       # 数据目录
│   └── himawari_l3c/
│       ├── parts/              # 处理后的NC文件
│       ├── png/                # 生成的PNG可视化
│       └── temp/               # 临时文件
└── README.md                   # 本文件
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
# 最小依赖（仅数据处理）
pip install -r ../requirements-core.txt

# 完整依赖（包括后端API和前端集成）
pip install -r ../requirements.txt
```

### 2. 配置认证

创建 `.netrc` 文件在项目根目录：

```
machine urs.earthdata.nasa.gov
  login YOUR_USERNAME
  password YOUR_PASSWORD
```

> 💡 需要在 [NASA Earthdata](https://urs.earthdata.nasa.gov/) 注册账号

### 3. 启动后端API

```bash
# 开发模式（推荐）
python api_example.py

# 或使用uvicorn
uvicorn api_example:app --reload --host 0.0.0.0 --port 8000
```

API服务启动后：
- 🌐 API根路径: http://localhost:8000
- 📚 自动文档: http://localhost:8000/docs
- 🖼️ 静态图片: http://localhost:8000/static/images/

### 4. 测试系统

```bash
# 检查文件完整性
python file_monitor_example.py check

# 自动修复缺失文件
python file_monitor_example.py repair

# 测试API功能
python test_api.py
```

## 📡 API端点

### 基础信息
- `GET /` - API信息和端点列表
- `GET /health` - 健康检查

### 数据处理
- `POST /query-data` - 查询可用数据清单
- `POST /process-data` - 开始数据处理（后台任务）
- `GET /status/{task_id}` - 查询处理任务状态

### 文件管理
- `GET /files` - 列出已处理的NC文件
- `GET /visualizations` - 列出生成的PNG可视化
- `GET /static/images/{filename}` - 获取PNG图片（静态文件服务）

### 监控和修复
- `POST /check-files` - 检查文件完整性
- `POST /repair-files` - 修复缺失文件（后台任务）
- `POST /auto-monitor-repair` - 自动监控并修复
- `GET /system-status` - 获取系统状态和健康信息

### 前端集成示例

```javascript
// 检查文件完整性
const checkFiles = async () => {
  const response = await fetch('http://localhost:8000/check-files', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_time: '2025-03-01T00:00:00',
      end_time: '2025-03-01T12:00:00',
      time_step_hours: 1
    })
  });
  return await response.json();
};

// 显示PNG图片
const imageUrl = `http://localhost:8000/static/images/20250301080000.png`;
```

## 🛠️ 核心功能详解

### 智能文件监控系统

```python
from himawari_processor import create_file_monitor

# 创建文件监控器
monitor = create_file_monitor()

# 检查文件完整性
results = monitor.check_file_completeness(
    timelims=('2025-03-01T00:00:00', '2025-03-01T12:00:00'),
    tstep=3600,  # 1小时间隔
    check_nc=True,
    check_png=True
)

# 自动修复缺失文件
monitor.repair_missing_files(
    check_results=results,
    lonlims=(113.0, 115.0),
    latlims=(-24.0, -21.0)
)
```

### 两步修复策略

1. **Step 1**: 下载并处理缺失的NC文件（同时生成PNG）
2. **Step 2**: 为现有NC文件重新生成缺失的PNG

### 前端Timeline集成

- ⏰ **时间同步**: Timeline与后端数据时间戳完全一致
- 🖼️ **实时显示**: 根据选择时间自动加载对应PNG图片
- 🔄 **智能缓存**: 避免重复加载相同图片
- 📍 **时区适配**: 自动转换UTC时间到本地时间显示

### 技术架构优势

1. **🚀 FastAPI**: 自动API文档、数据验证、高性能异步处理
2. **🔧 智能修复**: 分离NC下载和PNG生成，提高修复效率
3. **📊 实时监控**: 文件完整性检查和系统状态监控
4. **🌐 前后端分离**: 支持Next.js前端的RESTful API
5. **🛡️ 错误处理**: 完善的异常处理和回退机制
6. **📈 可扩展性**: 模块化设计，易于添加新功能

## 生产部署建议

### 数据库配置

```python
# 使用PostgreSQL + PostGIS存储元数据
# config.py
DATABASE_URL = "postgresql://user:password@localhost/himawari_db"

# 存储文件路径、处理状态等
class ProcessedFile(Base):
    __tablename__ = "processed_files"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True)
    timestamp = Column(DateTime)
    bounds = Column(Geometry('POLYGON'))  # PostGIS几何类型
    file_path = Column(String)
    processing_status = Column(String)
```

### 异步任务队列

```python
# 使用Celery + Redis处理长时间运行的任务
from celery import Celery

celery_app = Celery('himawari_processor')
celery_app.config_from_object('celery_config')

@celery_app.task
def process_satellite_data_task(request_params):
    processor = HimawariDataProcessor()
    return processor.process_time_series(**request_params)
```

### Docker部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api_example:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 下一步开发建议

1. **数据库集成** - 存储处理历史和元数据
2. **缓存层** - Redis缓存频繁访问的数据
3. **监控** - 添加日志和监控指标
4. **测试** - 编写单元测试和集成测试
5. **安全性** - 添加认证和授权
6. **文档** - API文档和用户指南


# 运行示例脚本
python file_monitor_example.py check    # 检查文件完整性
python file_monitor_example.py repair   # 修复丢失文件
python file_monitor_example.py auto     # 启动自动服务
python file_monitor_example.py regions  # 多区域检查
python file_monitor_example.py png      # 仅修复PNG