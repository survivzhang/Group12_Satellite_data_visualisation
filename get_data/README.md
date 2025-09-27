# Satellite Data API

## Quick Start

### 1. Environment Setup

```bash
# Activate virtual environment
source venv/bin/activate
#For windows
#create virtual enviroment
python -m venv venv
#Then activate it
venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
```

### 2. Start the API

```bash
# Run in the get_data directory
python api.py

# Or use uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the API

- **API Overview**: http://localhost:8000
- **Interactive Documentation**: http://localhost:8000/docs  
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
