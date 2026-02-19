  # Report App

## Overview
Report App is a FastAPI-based system for analyzing student results and attendance files, matching records, and generating professional PDF and DOCX academic reports.

## Features
- Upload results and attendance files in CSV or Excel
- Automatic student matching and consolidated profiles
- Individual PDF and DOCX report generation
- Bulk PDF ZIP export for all students
- Web UI and REST API endpoints

## Tech Stack
- FastAPI, Jinja2
- pandas, openpyxl
- WeasyPrint (PDF), python-docx (DOCX)

## Requirements
- Python 3.10+
- Windows: WeasyPrint system dependencies (see Setup)

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install WeasyPrint dependencies on Windows:
   - Install MSYS2 and the mingw64 toolchain.
   - Ensure the DLL directory in [main.py](main.py#L1) and [services/report_generator.py](services/report_generator.py#L1) points to your MSYS2 path (default is `C:\\msys64\\mingw64\\bin`).

## Run
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```
Open the app at http://127.0.0.1:8000.

## API Endpoints
- POST /api/analyze
- GET /api/report/{student_id}/pdf
- GET /api/report/{student_id}/docx
- GET /api/students
- GET /api/student/{student_id}
- POST /api/download-all-reports

## Sample Data
Sample files are available in [sample_data](sample_data). Use them to test uploads.

## Output
- Uploaded files: [uploads](uploads)
- Generated reports: [generated_reports](generated_reports)

## Configuration
Key settings are in [config.py](config.py).
