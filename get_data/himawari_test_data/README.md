# Himawari Satellite Data Processing

This module provides tools for downloading, processing, and serving Himawari-9 satellite sea surface temperature data.

## 文件结构

```
himawari_test_data/
├── himawari_processor.py     # 重构后的数据处理类
├── example_usage.py          # 使用示例
├── api_example.py           # FastAPI后端示例
├── test.py                  # 原始测试文件（已废弃）
└── README.md               # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 最小依赖（仅数据处理）
pip install -r ./requirements-core.txt

# 完整依赖（包括后端API）
pip install -r ./requirements.txt
```

### 2. 配置认证

创建 `.netrc` 文件用于NASA Earthdata认证：

```bash
# 在项目根目录创建 .netrc 文件
cat > .netrc << EOF
machine urs.earthdata.nasa.gov
  login YOUR_USERNAME
  password YOUR_PASSWORD
EOF

chmod 600 .netrc
```

### 3. 数据处理示例

```python
from himawari_processor import HimawariDataProcessor

# 初始化处理器
processor = HimawariDataProcessor(base_dir="data/himawari_l3c")

# 查询可用数据
manifest = processor.query_data_manifest(
    timelims=("2025-03-01T00:00:00", "2025-03-01T12:00:00"),
    lonlims=(111, 116),
    latlims=(-24.5, -19.5)
)

# 处理时间序列数据
processor.process_time_series(
    timelims=("2025-03-01T00:00:00", "2025-03-01T12:00:00"),
    lonlims=(111, 116),
    latlims=(-24.5, -19.5),
    tstep=3600  # 1小时间隔
)
```

### 4. 启动API服务器

```bash
# 开发模式
python api_example.py

# 或使用uvicorn
uvicorn api_example:app --reload --host 0.0.0.0 --port 8000
```

API将在 http://localhost:8000 启动，访问 http://localhost:8000/docs 查看自动生成的API文档。

## API端点

- `GET /` - API信息
- `GET /health` - 健康检查
- `POST /query-data` - 查询可用数据
- `POST /process-data` - 开始数据处理（后台任务）
- `GET /status/{task_id}` - 查询处理状态
- `GET /files` - 列出已处理的文件
- `GET /visualizations` - 列出生成的可视化图像

## 主要改进

### 相比原始 `test.py` 文件：

1. **模块化设计** - 将功能拆分为清晰的类和方法
2. **错误处理** - 更好的异常处理和错误信息
3. **类型提示** - 完整的类型注解提高代码可读性
4. **配置分离** - 将配置参数从代码中分离
5. **可重用性** - 创建可重用的组件而不是脚本
6. **文档完善** - 详细的文档字符串和注释

### 后端技术栈优势：

1. **FastAPI** - 自动API文档、数据验证、高性能
2. **异步处理** - 后台任务处理耗时的数据下载
3. **类型安全** - Pydantic模型确保数据类型正确
4. **CORS支持** - 与前端Next.js应用无缝集成
5. **可扩展性** - 易于添加新功能和端点

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