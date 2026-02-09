"""Application configuration."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Upload settings
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

REPORT_DIR = BASE_DIR / "generated_reports"
REPORT_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Attendance thresholds
ATTENDANCE_RED_THRESHOLD = 75.0      # < 75% → Red
ATTENDANCE_YELLOW_THRESHOLD = 80.0   # 75-80% → Yellow
# >= 80% → Green

# University details
UNIVERSITY_NAME = "KL University"
UNIVERSITY_FULL_NAME = "Koneru Lakshmaiah Education Foundation"
DEPARTMENT_NAME = "Department of Artificial Intelligence and Data Science (AI & DS)"
HOD_NAME = "Anubothu Aravind"
REPORT_TITLE = "Student Academic Performance Report"
LOGO_PATH = BASE_DIR / "static" / "images" / "kl_logo.png"

# Telugu attendance notice toggle
ENABLE_TELUGU_NOTICE = True

# Failed grade indicators
FAILED_GRADES = {"F", "FA", "AB", "FAIL", "I", "W"}

# Grade-to-point mapping for CGPA calculation
GRADE_POINT_MAP = {
    "O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6,
    "C": 5, "P": 4, "F": 0, "FA": 0, "AB": 0,
    "FAIL": 0, "I": 0, "W": 0,
}

# Maximum file size (50 MB)
MAX_FILE_SIZE = 50 * 1024 * 1024
