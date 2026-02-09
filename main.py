"""
KL University — Student Academic Performance Analysis System
FastAPI Application Entry Point
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Dict, List

# Set DLL path for WeasyPrint on Windows (must be before any WeasyPrint import)
os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", r"C:\msys64\mingw64\bin")

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import BASE_DIR, UPLOAD_DIR, REPORT_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from services.file_parser import parse_results_file, parse_attendance_file, FileParserError
from services.student_matcher import match_students, build_attendance_only, build_results_only
from services.report_generator import generate_pdf, generate_docx, generate_all_pdfs_zip
from models.student import StudentProfile

from typing import Optional

# ───── Logging ─────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ───── App Setup ─────
app = FastAPI(
    title="KL University — Student Academic Analysis",
    description="Upload results & attendance files to generate professional academic reports.",
    version="1.0.0",
)

# Static files & templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ───── In-Memory Session Store ─────
# Maps session_id → list[StudentProfile]
_sessions: Dict[str, List[StudentProfile]] = {}
# Maps student_id → StudentProfile for quick lookup (latest upload)
_latest_students: Dict[str, StudentProfile] = {}


# ───── Routes ─────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main upload page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/analyze")
async def analyze_files(
    results_file: Optional[UploadFile] = File(None, description="Previous semester results (CSV/XLSX)"),
    attendance_file: Optional[UploadFile] = File(None, description="Current semester attendance (CSV/XLSX)"),
):
    """Analyze uploaded files and return student data. Accepts one or both files."""

    # ── Check at least one file provided ──
    has_results = results_file is not None and results_file.filename
    has_attendance = attendance_file is not None and attendance_file.filename

    if not has_results and not has_attendance:
        raise HTTPException(status_code=400, detail="Please upload at least one file (results or attendance).")

    # ── Validate file extensions ──
    if has_results:
        ext = Path(results_file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Results file must be CSV or Excel. Got: {ext}")
    if has_attendance:
        ext = Path(attendance_file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Attendance file must be CSV or Excel. Got: {ext}")

    session_id = str(uuid.uuid4())
    results_path = None
    attendance_path = None

    try:
        # ── Save uploaded files ──
        if has_results:
            results_path = UPLOAD_DIR / f"{session_id}_results{Path(results_file.filename).suffix}"
            results_data = await results_file.read()
            if len(results_data) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Results file too large. Maximum 50 MB.")
            results_path.write_bytes(results_data)

        if has_attendance:
            attendance_path = UPLOAD_DIR / f"{session_id}_attendance{Path(attendance_file.filename).suffix}"
            attendance_data = await attendance_file.read()
            if len(attendance_data) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Attendance file too large. Maximum 50 MB.")
            attendance_path.write_bytes(attendance_data)

        logger.info(f"Session {session_id}: Files — results={'yes' if has_results else 'no'}, attendance={'yes' if has_attendance else 'no'}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {e}")

    # ── Parse & match ──
    try:
        if has_results and has_attendance:
            results_df, r_id_col, r_name_col = parse_results_file(results_path)
            attendance_df, a_id_col, a_name_col = parse_attendance_file(attendance_path)
            logger.info(f"Session {session_id}: Parsed results ({len(results_df)} rows), attendance ({len(attendance_df)} rows)")
            students = match_students(results_df, r_id_col, r_name_col, attendance_df, a_id_col, a_name_col)
        elif has_attendance:
            attendance_df, a_id_col, a_name_col = parse_attendance_file(attendance_path)
            logger.info(f"Session {session_id}: Parsed attendance-only ({len(attendance_df)} rows)")
            students = build_attendance_only(attendance_df, a_id_col, a_name_col)
        else:
            results_df, r_id_col, r_name_col = parse_results_file(results_path)
            logger.info(f"Session {session_id}: Parsed results-only ({len(results_df)} rows)")
            students = build_results_only(results_df, r_id_col, r_name_col)

        logger.info(f"Session {session_id}: Built {len(students)} student profiles")
    except FileParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Parse/match error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing files: {e}")

    # ── Store in session ──
    _sessions[session_id] = students
    for s in students:
        _latest_students[s.student_id] = s

    # ── Build response ──
    summary = {
        "total_students": len(students),
        "low_attendance_count": sum(1 for s in students if s.has_low_attendance),
        "warning_attendance_count": sum(
            1 for s in students
            if any(a.status == "Yellow" for a in s.attendance_records) and not s.has_low_attendance
        ),
        "good_attendance_count": sum(
            1 for s in students
            if all(a.status == "Green" for a in s.attendance_records) and s.attendance_records
        ),
        "students_with_backlogs": sum(1 for s in students if s.backlog_count > 0),
    }

    student_list = [
        {
            "student_id": s.student_id,
            "student_name": s.student_name,
            "section": s.section,
            "year": s.year,
            "semester": s.semester,
            "branch": s.branch,
            "overall_attendance": s.overall_attendance,
            "backlog_count": s.backlog_count,
            "needs_counseling": s.needs_counseling,
            "has_low_attendance": s.has_low_attendance,
        }
        for s in students
    ]

    # ── Cleanup temp files ──
    try:
        if results_path:
            results_path.unlink(missing_ok=True)
        if attendance_path:
            attendance_path.unlink(missing_ok=True)
    except Exception:
        pass

    return {"session_id": session_id, "summary": summary, "students": student_list}


@app.get("/api/report/{student_id}/pdf")
async def download_pdf(student_id: str):
    """Generate and download PDF report for a student."""
    student_id = student_id.strip().upper()
    student = _latest_students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found. Please upload files first.")

    try:
        pdf_bytes = generate_pdf(student)
    except Exception as e:
        logger.error(f"PDF generation error for {student_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")

    filename = f"{student.student_id}_{student.student_name.replace(' ', '_')}_Report.pdf"
    filepath = REPORT_DIR / filename
    filepath.write_bytes(pdf_bytes)

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/pdf",
    )


@app.get("/api/report/{student_id}/docx")
async def download_docx(student_id: str):
    """Generate and download DOCX report for a student."""
    student_id = student_id.strip().upper()
    student = _latest_students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found. Please upload files first.")

    try:
        docx_bytes = generate_docx(student)
    except Exception as e:
        logger.error(f"DOCX generation error for {student_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate DOCX: {e}")

    filename = f"{student.student_id}_{student.student_name.replace(' ', '_')}_Report.docx"
    filepath = REPORT_DIR / filename
    filepath.write_bytes(docx_bytes)

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/students")
async def list_students():
    """List all currently loaded students."""
    if not _latest_students:
        return {"students": [], "message": "No data loaded. Upload files first."}
    return {
        "students": [
            {
                "student_id": s.student_id,
                "student_name": s.student_name,
                "overall_attendance": s.overall_attendance,
                "backlog_count": s.backlog_count,
                "needs_counseling": s.needs_counseling,
            }
            for s in sorted(_latest_students.values(), key=lambda x: x.student_id)
        ]
    }


@app.get("/api/student/{student_id}")
async def get_student_detail(student_id: str):
    """Get detailed profile for a specific student."""
    student_id = student_id.strip().upper()
    student = _latest_students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found.")

    return {
        "student_id": student.student_id,
        "student_name": student.student_name,
        "section": student.section,
        "year": student.year,
        "semester": student.semester,
        "branch": student.branch,
        "email": student.email,
        "phone": student.phone,
        "counselor_name": student.counselor_name,
        "counselor_id": student.counselor_id,
        "overall_attendance": student.overall_attendance,
        "backlog_count": student.backlog_count,
        "backlog_subjects": student.backlog_subjects,
        "has_low_attendance": student.has_low_attendance,
        "low_attendance_subjects": student.low_attendance_subjects,
        "needs_counseling": student.needs_counseling,
        "concern_reasons": student.concern_reasons,
        "attendance_records": [
            {
                "subject_code": a.subject_code,
                "subject_name": a.subject_name,
                "classes_held": a.classes_held,
                "classes_attended": a.classes_attended,
                "attendance_percentage": a.attendance_percentage,
                "status": a.status,
            }
            for a in student.attendance_records
        ],
        "previous_results": [
            {
                "subject_code": r.subject_code,
                "subject_name": r.subject_name,
                "grade": r.grade,
                "credits": r.credits,
                "is_backlog": r.is_backlog,
            }
            for r in student.previous_results
        ],
    }


@app.post("/api/download-all-reports")
async def download_all_reports_zip():
    """Generate PDFs for all loaded students and return as a single ZIP file."""
    if not _latest_students:
        raise HTTPException(status_code=400, detail="No student data loaded. Upload files first.")

    students = sorted(_latest_students.values(), key=lambda s: s.student_id)
    try:
        zip_bytes = generate_all_pdfs_zip(students)
    except Exception as e:
        logger.error(f"Bulk ZIP generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ZIP: {e}")

    # Save and serve
    zip_path = REPORT_DIR / "all_student_reports.zip"
    zip_path.write_bytes(zip_bytes)

    return FileResponse(
        path=str(zip_path),
        filename="all_student_reports.zip",
        media_type="application/zip",
    )


# ───── Entry Point ─────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
