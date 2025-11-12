# Deep Doc Analysis with MCP

A powerful web application for analyzing Excel files using AI (LLM) with Model Context Protocol (MCP) integration. Upload Excel files, ask questions, and get intelligent analysis with computational tools.

## Features

### 📊 Data Analysis Tools
- **Statistical Analysis**: Summary statistics, null counts, data types
- **Column Comparison**: Correlation analysis, t-tests, descriptive statistics
- **Data Validation**: Check for nulls, duplicates, outliers
- **Trend Analysis**: Time-series analysis with linear regression
- **Anomaly Detection**: Statistical outlier detection (Z-score, IQR methods)
- **Sheet Comparison**: Compare data between multiple worksheets

### 📝 Excel Manipulation Tools
- **Workbook Operations**: Create, read, update workbooks and worksheets
- **Data Operations**: Write/read data, copy/delete ranges
- **Row/Column Operations**: Insert, delete rows and columns
- **Formatting**: Apply fonts, colors, borders, alignment
- **Formulas**: Apply and validate Excel formulas

### 📈 Pivot Tables & Charts
- **Pivot Tables**: Dynamic pivot tables with multiple aggregation functions
- **Charts**: Line, bar, pie, scatter, area charts
- **Dashboards**: Multi-chart visualizations
- **Excel Tables**: Native Excel table creation with styling

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **FastMCP**: Model Context Protocol server
- **Ollama**: Local LLM runtime (Qwen2.5:1.5b-instruct)
- **openpyxl**: Excel file manipulation
- **pandas**: Data analysis and processing
- **scipy/statsmodels**: Statistical analysis

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Frontend web server

## Prerequisites

- **Docker & Docker Compose** (recommended)
- OR manually install:
  - Python 3.11+
  - Node.js 20+
  - Ollama

## Quick Start with Docker (Recommended)

### 1. Clone the repository

```bash
git clone <repository-url>
cd Deep-Doc-Analysis-with-MCP
```

### 2. Create environment files

```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

### 3. Start all services

```bash
docker-compose up -d
```

This will start:
- **Ollama** on port 11434
- **Backend API** on port 8000
- **Frontend** on port 3000

### 4. Pull the LLM model

First time setup - download the Qwen model:

```bash
docker exec -it deep-doc-ollama ollama pull qwen2.5:1.5b-instruct
```

Or use the API endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/models/pull
```

### 5. Access the application

Open your browser and navigate to:
```
http://localhost:3000
```

## Manual Setup (Without Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Run development server
npm run dev
```

### Ollama Setup

```bash
# Install Ollama (see https://ollama.ai)

# Pull the model
ollama pull qwen2.5:1.5b-instruct

# Ollama will run on http://localhost:11434
```

## Usage

### 1. Upload Excel File

- Click the upload area or drag and drop an Excel file (.xlsx, .xls, .xlsm)
- Maximum file size: 50MB
- File will be uploaded to the server

### 2. Chat with AI

Ask questions about your Excel file:

**Analysis Examples:**
- "Analyze the data in this file"
- "Compare column A and column B statistically"
- "Check for data quality issues"
- "Find outliers in the Sales column"
- "Show me trends in the Revenue column over Time"

**Manipulation Examples:**
- "Create a pivot table showing sales by region"
- "Generate a bar chart for the top 10 products"
- "Add a new column with formula =A1*B1"
- "Format the header row with bold text and blue background"

### 3. View Results

The AI will use the appropriate MCP tools to analyze your data and provide detailed results.

## API Documentation

Once the backend is running, access interactive API docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/upload` - Upload Excel file
- `POST /api/v1/chat` - Chat with AI about Excel files
- `GET /api/v1/status` - System status
- `GET /api/v1/tools` - List available MCP tools
- `GET /api/v1/files` - List uploaded files

## MCP Tools Reference

### Analysis Tools
- `analyze_excel_data` - Comprehensive statistical analysis
- `compare_columns` - Statistical comparison between columns
- `validate_data` - Data validation (nulls, duplicates, outliers)
- `trend_analysis` - Time-series trend analysis
- `detect_anomalies` - Anomaly detection
- `compare_sheets` - Compare data between sheets

### Manipulation Tools
- `create_workbook` - Create new workbook
- `create_worksheet` - Add new worksheet
- `write_data_to_excel` - Write data to worksheet
- `read_data_from_excel` - Read data from worksheet
- `format_range` - Apply formatting
- `apply_formula` - Apply Excel formula
- And 15+ more tools...

### Pivot & Chart Tools
- `create_pivot_table` - Create pivot table
- `analyze_pivot_data` - Analyze pivot results
- `create_chart` - Generate charts
- `create_dashboard` - Multi-chart dashboard
- `create_table` - Create Excel table

## Architecture

```
┌─────────────────┐
│  React Frontend │
│   (Port 3000)   │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI Server │
│   (Port 8000)   │
└────┬───────┬────┘
     │       │
     │       └──────► ┌──────────────┐
     │                │  MCP Server  │
     │                │ Excel Tools  │
     │                └──────────────┘
     ▼
┌─────────────────┐
│     Ollama      │
│  Qwen2.5:1.5B   │
│  (Port 11434)   │
└─────────────────┘
```

## Configuration

### Backend Configuration (`backend/.env`)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b-instruct
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800  # 50MB
```

### Frontend Configuration (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Development

### Backend Development

```bash
cd backend

# Run with auto-reload
uvicorn app.main:app --reload

# Run tests (if implemented)
pytest

# Format code
black app/
```

### Frontend Development

```bash
cd frontend

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Switching LLM Models

The system uses Qwen2.5:1.5b-instruct by default (lightweight, ~1GB RAM).

To use a different model:

1. Update `backend/.env`:
   ```env
   OLLAMA_MODEL=mistral:7b  # or any other Ollama model
   ```

2. Pull the new model:
   ```bash
   docker exec -it deep-doc-ollama ollama pull mistral:7b
   ```

3. Restart the backend:
   ```bash
   docker-compose restart backend
   ```

### Recommended Models

- **Qwen2.5:1.5b-instruct** - Fastest, lowest RAM (~2GB)
- **Phi-3:mini** - Good balance (~4GB)
- **Mistral:7b** - Better quality (~8GB)
- **Llama3.2:3b** - Latest Meta model (~4GB)

## Troubleshooting

### Ollama Connection Issues

```bash
# Check Ollama status
docker logs deep-doc-ollama

# Restart Ollama
docker-compose restart ollama
```

### Backend Issues

```bash
# Check logs
docker logs deep-doc-backend

# Restart backend
docker-compose restart backend
```

### Model Not Found

```bash
# Pull the model manually
docker exec -it deep-doc-ollama ollama pull qwen2.5:1.5b-instruct

# Or use the API
curl -X POST http://localhost:8000/api/v1/models/pull
```

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "3001:80"      # Frontend (instead of 3000)
  - "8001:8000"    # Backend (instead of 8000)
  - "11435:11434"  # Ollama (instead of 11434)
```

## Project Structure

```
Deep-Doc-Analysis-with-MCP/
├── backend/
│   ├── app/
│   │   ├── mcp_server/
│   │   │   ├── analysis_tools.py
│   │   │   ├── manipulation_tools.py
│   │   │   ├── pivot_chart_tools.py
│   │   │   ├── server.py
│   │   │   └── utils.py
│   │   ├── main.py
│   │   ├── llm_service.py
│   │   ├── models.py
│   │   └── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   ├── MessageList.jsx
│   │   │   └── StatusBar.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Performance Optimization

### For Better Performance

1. **Use GPU acceleration** (if available):
   ```yaml
   # In docker-compose.yml for ollama service
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

2. **Increase model size** for better quality:
   - Use Mistral:7b or Llama3.2:3b

3. **Adjust worker count** for FastAPI:
   ```bash
   uvicorn app.main:app --workers 4
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation

## Roadmap

- [ ] Add support for CSV files
- [ ] Implement streaming responses
- [ ] Add user authentication
- [ ] Support for multiple file uploads
- [ ] Export analysis results
- [ ] Custom chart styling
- [ ] Advanced statistical tests
- [ ] Data visualization improvements

---

**Built with ❤️ using FastAPI, React, and Ollama**
