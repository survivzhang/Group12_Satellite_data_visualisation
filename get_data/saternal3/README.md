# EUMETView Sentinel-3 Data Processing

This module provides tools for downloading, processing, and serving Sentinel-3 satellite data from the EUMETView WCS API with automatic file monitoring and repair capabilities.

## ✨ Main Features

- 🛰️ **Satellite Data Processing**: Automatically download and process Sentinel-3 SST and Chlorophyll data
- 🖼️ **Visualization Generation**: Automatically generate PNG images for frontend display
- 🔍 **File Monitoring**: Check data integrity, identify missing and corrupted files
- 🔧 **Automatic Repair**: Intelligently repair missing NC and PNG files
- 🌐 **API Service**: FastAPI backend service, supports frontend integration
- ⚡ **Real-time Updates**: Supports real-time PNG image display for frontend Timeline

## 📁 File Structure

```
saternal3/
├── usingtheEumetview.py         # Core data processing class
├── api_example.py               # FastAPI backend API
├── example_usage.py             # Usage examples
├── data/                        # Data directory
│   └── eumetview_sentinel3/
│       ├── nc/                  # Processed NC files
│       ├── png/                 # Generated PNG visualizations
│       └── temp/                # Temporary files
└── README.md                    # This file

../                              # Project root
├── requirements.txt             # Full dependencies (shared with Himawari)
├── requirements-core.txt        # Core dependencies only (shared)
└── venv/                        # Shared virtual environment
```

## Available Data Layers

| Layer Key | Description | Satellite | Data Type |
|-----------|-------------|-----------|-----------|
| `sentinel3a_sst` | Sentinel-3A Sea Surface Temperature | Sentinel-3A | SST |
| `sentinel3b_sst` | Sentinel-3B Sea Surface Temperature | Sentinel-3B | SST |
| `sentinel3a_chl` | Sentinel-3A Chlorophyll | Sentinel-3A | CHL |
| `sentinel3b_chl` | Sentinel-3B Chlorophyll | Sentinel-3B | CHL |
| `daily_sst` | Daily composite SST | Combined | SST |
| `daily_chl` | Daily composite Chlorophyll | Combined | CHL |

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


# Install dependencies (from project root directory)
cd ..  # Go to project root

# Minimal dependencies (data processing only)
pip install -r requirements-core.txt

# Full dependencies (including backend API and frontend integration)
pip install -r requirements.txt
```

### 2. Configure Authentication

Create a file named `eumetsat_api_credentials.txt` in the project root directory:

```
consumer_key=YOUR_CONSUMER_KEY
consumer_secret=YOUR_CONSUMER_SECRET
```

> 💡 You need to register an account at [EUMETView](https://view.eumetsat.int/)

To get API credentials:
1. Log in to EUMETView (https://view.eumetsat.int/)
2. Click on your username in the top right corner
3. Select 'API Key'
4. Copy your consumer key and secret

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

## Usage Examples

### Basic Usage

```python
from usingtheEumetview import EUMETViewDataProcessor

# Initialize processor
processor = EUMETViewDataProcessor(base_dir="data/sentinel3")

# Authenticate
processor.authenticate()

# Download data
downloaded_files = processor.download_data(
    layer_keys=['sentinel3a_sst', 'sentinel3a_chl'],
    region=(111, -25, 114, -20),  # Western Australia
    time_range=('2025-03-01T00:00:00.000Z', '2025-03-01T12:00:00.000Z')
)

# Create visualizations
visualization_files = processor.process_and_visualize(downloaded_files)
```

### Workflow Usage

```python
from usingtheEumetview import EUMETViewWorkflow

# Create workflow
workflow = EUMETViewWorkflow(base_dir="data/sentinel3")

# Run complete processing pipeline
workflow.run_complete_workflow(
    layer_keys=['sentinel3a_sst', 'sentinel3a_chl'],
    region=(111, -25, 114, -20),
    time_range=('2025-03-01T00:00:00.000Z', '2025-03-01T12:00:00.000Z')
)
```

### Running the API Server

```bash
python api_example.py
```

Or with uvicorn:

```bash
uvicorn api_example:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at:
- Main API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

### File Monitoring (Simplified)
- `POST /check-file` - Check NC file status and PNG regeneration needs
- `POST /regenerate-pngs` - Regenerate all PNG files from NC file
- `POST /auto-check-regenerate` - Auto check and regenerate if needed
- `GET /system-status` - Get system status and health info

### Frontend Integration Example

```javascript
// Check if NC file needs PNG regeneration
const checkFile = async (ncFilePath) => {
  const response = await fetch('http://localhost:8000/check-file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nc_file_path: ncFilePath
    })
  });
  return await response.json();
};

// Auto check and regenerate PNGs if needed
const autoRegenerate = async (ncFilePath) => {
  const response = await fetch('http://localhost:8000/auto-check-regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nc_file_path: ncFilePath
    })
  });
  return await response.json();
};

// Display PNG image
const imageUrl = `http://localhost:8000/static/images/20250301080000.png`;
```

## Directory Structure

The processor creates the following directory structure:

```
data/eumetview_sentinel3/
├── sentinel3a/            # Sentinel-3A satellite data
│   ├── sst/              # Sea Surface Temperature
│   │   ├── nc/           # NetCDF data files
│   │   └── png/          # PNG visualizations
│   └── chl/              # Chlorophyll concentration
│       ├── nc/           # NetCDF data files
│       └── png/          # PNG visualizations
└── sentinel3b/            # Sentinel-3B satellite data
    ├── sst/              # Sea Surface Temperature
    │   ├── nc/           # NetCDF data files
    │   └── png/          # PNG visualizations
    └── chl/              # Chlorophyll concentration
        ├── nc/           # NetCDF data files
        └── png/          # PNG visualizations
```

## Error Handling

The module includes comprehensive error handling:

- **Authentication Errors**: Clear messages for credential issues
- **Network Errors**: Retry logic and timeout handling
- **Data Errors**: Graceful handling of missing or corrupt data
- **File System Errors**: Automatic directory creation and permission handling

## Visualization Features

- **Automatic Colormap Selection**: Different colormaps for SST (turbo) and CHL (viridis)
- **Time Series Support**: Individual plots for each time step
- **Data Quality Checks**: Skip plots for all-NaN data
- **Customizable Output**: PNG files with timestamps and metadata

## Integration with Frontend

The API is designed to work with Next.js frontends:

- **CORS Support**: Pre-configured for localhost:3000
- **Static File Serving**: Direct access to generated visualizations
- **Async Processing**: Background tasks with status monitoring
- **JSON Responses**: Structured data for easy frontend consumption

## 🛠️ Core Feature Details

### Simplified File Monitoring System

```python
from usingtheEumetview import create_file_monitor

# Create file monitor
monitor = create_file_monitor()

# Check if NC file needs PNG regeneration
status = monitor.check_file_status('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')

# Regenerate all PNGs from NC file
result = monitor.regenerate_all_pngs('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')

# Auto check and regenerate if needed (recommended)
result = monitor.check_and_regenerate_if_needed('data/eumetview_sentinel3/nc/sentinel3a/sst/data.nc')
```

### Simple One-Step Strategy

1. **Check**: Compare NC file modification time with PNG files
2. **Regenerate**: If NC is newer, regenerate all PNG files using original logic
3. **Complete**: All visualizations updated automatically

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
DATABASE_URL = "postgresql://user:password@localhost/eumetview_db"

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

celery_app = Celery('eumetview_processor')
celery_app.config_from_object('celery_config')

@celery_app.task
def process_satellite_data_task(request_params):
  processor = EUMETViewDataProcessor()
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
