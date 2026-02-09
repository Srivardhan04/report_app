"""File parser service – reads CSV/Excel files into normalized DataFrames."""

import pandas as pd
from pathlib import Path
from typing import Tuple

from config import ALLOWED_EXTENSIONS


class FileParserError(Exception):
    """Raised when file parsing fails."""
    pass


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names: strip, lowercase, replace spaces/hyphens with underscores."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df


def _detect_id_column(df: pd.DataFrame) -> str:
    """Detect the student ID column from common variations."""
    candidates = [
        "student_id", "studentid", "sid", "roll_no", "rollno",
        "roll_number", "rollnumber", "id", "reg_no", "regno",
        "registration_no", "registrationno", "htno", "hall_ticket_no",
    ]
    for col in df.columns:
        if col in candidates:
            return col
    # Fallback: first column containing 'id' or 'roll' or 'reg'
    for col in df.columns:
        if any(k in col for k in ("id", "roll", "reg", "htno")):
            return col
    raise FileParserError(
        f"Could not detect Student ID column. Found columns: {list(df.columns)}"
    )


def _detect_name_column(df: pd.DataFrame) -> str:
    """Detect the student name column."""
    candidates = [
        "student_name", "studentname", "name", "full_name", "fullname",
        "student_full_name",
    ]
    for col in df.columns:
        if col in candidates:
            return col
    for col in df.columns:
        if "name" in col:
            return col
    raise FileParserError(
        f"Could not detect Student Name column. Found columns: {list(df.columns)}"
    )


def parse_file(file_path: Path) -> pd.DataFrame:
    """Parse a CSV or Excel file into a pandas DataFrame."""
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise FileParserError(f"Unsupported file format: {suffix}")

    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        raise FileParserError(f"Failed to read file {file_path.name}: {e}")

    if df.empty:
        raise FileParserError(f"File {file_path.name} is empty.")

    df = _normalize_columns(df)
    return df


def parse_results_file(file_path: Path) -> Tuple[pd.DataFrame, str, str]:
    """
    Parse previous semester results file.
    Returns: (DataFrame, id_column_name, name_column_name)
    Expected columns: Student_ID, Student_Name, Subject_Code, Subject_Name, Grade, Credits
    """
    df = parse_file(file_path)
    id_col = _detect_id_column(df)
    name_col = _detect_name_column(df)

    # Normalize Student ID to string
    df[id_col] = df[id_col].astype(str).str.strip().str.upper()
    df[name_col] = df[name_col].astype(str).str.strip().str.title()

    return df, id_col, name_col


def parse_attendance_file(file_path: Path) -> Tuple[pd.DataFrame, str, str]:
    """
    Parse current semester attendance file.
    Returns: (DataFrame, id_column_name, name_column_name)
    Expected columns: Student_ID, Student_Name, Subject_Code, Subject_Name,
                      Classes_Held, Classes_Attended (or Attendance_Percentage)
    """
    df = parse_file(file_path)
    id_col = _detect_id_column(df)
    name_col = _detect_name_column(df)

    # Normalize Student ID to string
    df[id_col] = df[id_col].astype(str).str.strip().str.upper()
    df[name_col] = df[name_col].astype(str).str.strip().str.title()

    return df, id_col, name_col
