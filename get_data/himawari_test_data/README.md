# Himawari Satellite Data Processing

This module provides tools for downloading, processing, and serving Himawari-9 satellite sea surface temperature data with automatic file monitoring and repair capabilities.


## ✨ Main Features

- 🛰️ **Satellite Data Processing**: Automatically download and process Himawari-9 sea surface temperature data
- 🖼️ **Visualization Generation**: Automatically generate PNG images for frontend display
- 🔍 **File Monitoring**: Check data integrity, identify missing and corrupted files
- 🔧 **Automatic Repair**: Intelligently repair missing NC and PNG files
- 🌐 **API Service**: FastAPI backend service, supports frontend integration
- ⚡ **Real-time Updates**: Supports real-time PNG image display for frontend Timeline


## 📁 File Structure

```
himawari_test_data/
├── himawari_processor.py        # Core data processing class
├── api_example.py               # FastAPI backend API
├── data/                        # Data directory
│   └── himawari_l3c/
│       ├── parts/               # Processed NC files
│       ├── png/                 # Generated PNG visualizations
│       └── temp/                # Temporary files
└── README.md                    # This file
```


## 🚀 Quick Start

### 1. Environment Setup

```bash

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate


# Install dependencies
# Minimal dependencies (data processing only)
pip install -r ../requirements-core.txt

# Full dependencies (including backend API and frontend integration)
pip install -r ../requirements.txt
```


### 2. Configure Authentication

Create a `.netrc` file in the project root directory:

```
machine urs.earthdata.nasa.gov
  login YOUR_USERNAME
  password YOUR_PASSWORD
```

> 💡 You need to register an account at [NASA Earthdata](https://urs.earthdata.nasa.gov/)


### 3. Start Backend API

```bash
# Development mode (recommended)
python api_example.py

# Or use uvicorn
uvicorn api_example:app --reload --host 0.0.0.0 --port 8000
```

After the API service starts:
- 🌐 API root: http://localhost:8000
- 📚 Auto docs: http://localhost:8000/docs
- 🖼️ Static images: http://localhost:8000/static/images/



## 📡 API Endpoints

### Basic Info
- `GET /` - API info and endpoint list
- `GET /health` - Health check

### Data Processing
- `POST /query-data` - Query available data list
- `POST /process-data` - Start data processing (background task)
- `GET /status/{task_id}` - Query processing task status

### File Management
- `GET /files` - List processed NC files
- `GET /visualizations` - List generated PNG visualizations
- `GET /static/images/{filename}` - Get PNG image (static file service)

### Monitoring and Repair
- `POST /check-files` - Check file integrity
- `POST /repair-files` - Repair missing files (background task)
- `POST /auto-monitor-repair` - Auto monitor and repair
- `GET /system-status` - Get system status and health info

### Frontend Integration Example

```javascript
// Check file integrity
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

// Display PNG image
const imageUrl = `http://localhost:8000/static/images/20250301080000.png`;
```


## 🛠️ Core Feature Details

### Intelligent File Monitoring System

```python
from himawari_processor import create_file_monitor

# Create file monitor
monitor = create_file_monitor()

# Check file completeness
results = monitor.check_file_completeness(
  timelims=('2025-03-01T00:00:00', '2025-03-01T12:00:00'),
  tstep=3600,  # 1 hour interval
  check_nc=True,
  check_png=True
)

# Automatically repair missing files
monitor.repair_missing_files(
  check_results=results,
  lonlims=(113.0, 115.0),
  latlims=(-24.0, -21.0)
)
```

### Two-step Repair Strategy

1. **Step 1**: Download and process missing NC files (generate PNG at the same time)
2. **Step 2**: Regenerate missing PNGs for existing NC files

### Frontend Timeline Integration

- ⏰ **Time Sync**: Timeline is fully synchronized with backend data timestamps
- 🖼️ **Real-time Display**: Automatically load corresponding PNG image based on selected time
- 🔄 **Smart Cache**: Avoid reloading the same image
- 📍 **Timezone Adaptation**: Automatically convert UTC time to local time for display

### Technical Architecture Advantages

1. **🚀 FastAPI**: Automatic API docs, data validation, high-performance async processing
2. **🔧 Smart Repair**: Separate NC download and PNG generation, improve repair efficiency
3. **📊 Real-time Monitoring**: File completeness check and system status monitoring
4. **🌐 Frontend-backend Separation**: Supports Next.js frontend RESTful API
5. **🛡️ Error Handling**: Robust exception handling and fallback mechanism
6. **📈 Scalability**: Modular design, easy to add new features

## Production Deployment Suggestions

### Database Configuration

```python
# Use PostgreSQL + PostGIS to store metadata
# config.py
DATABASE_URL = "postgresql://user:password@localhost/himawari_db"

# Store file path, processing status, etc.
class ProcessedFile(Base):
  __tablename__ = "processed_files"
    
  id = Column(Integer, primary_key=True)
  filename = Column(String, unique=True)
  timestamp = Column(DateTime)
  bounds = Column(Geometry('POLYGON'))  # PostGIS geometry type
  file_path = Column(String)
  processing_status = Column(String)
```

### Async Task Queue

```python
# Use Celery + Redis to handle long-running tasks
from celery import Celery

celery_app = Celery('himawari_processor')
celery_app.config_from_object('celery_config')

@celery_app.task
def process_satellite_data_task(request_params):
  processor = HimawariDataProcessor()
  return processor.process_time_series(**request_params)
```

### Docker Deployment

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

## Next Development Suggestions

1. **Database Integration** - Store processing history and metadata
2. **Cache Layer** - Use Redis to cache frequently accessed data
3. **Monitoring** - Add logging and monitoring metrics
4. **Testing** - Write unit and integration tests
5. **Security** - Add authentication and authorization
6. **Documentation** - API docs and user guide
