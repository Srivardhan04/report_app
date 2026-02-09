"""Student matcher service – matches students across two datasets."""

import pandas as pd
from difflib import SequenceMatcher
from typing import Dict, Set, Tuple

from models.student import StudentProfile, SubjectResult, SubjectAttendance


class StudentMatcherError(Exception):
    pass


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    return " ".join(name.strip().lower().split())


def _name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity ratio between two names."""
    n1 = _normalize_name(name1)
    n2 = _normalize_name(name2)
    return SequenceMatcher(None, n1, n2).ratio()


def _detect_column(df: pd.DataFrame, keywords: list[str], label: str) -> str:
    """Try to find a column by keyword matching."""
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                return col
    return ""


def match_students(
    results_df: pd.DataFrame,
    results_id_col: str,
    results_name_col: str,
    attendance_df: pd.DataFrame,
    attendance_id_col: str,
    attendance_name_col: str,
) -> list[StudentProfile]:
    """
    Match students from results and attendance files.
    Primary key: Student_ID
    Fallback: Student_Name (fuzzy match with threshold 0.85)
    """
    profiles: Dict[str, StudentProfile] = {}
    unmatched_attendance: list = []

    # --- Step 1: Build profiles from results data ---
    results_grouped = results_df.groupby(results_id_col)
    id_to_name: Dict[str, str] = {}

    # Detect CGPA column (read directly if present)
    cgpa_col = _detect_column(results_df, ["cgpa", "cg", "cgpa_value"], "CGPA")

    for student_id, group in results_grouped:
        sid = str(student_id).strip().upper()
        name = group[results_name_col].iloc[0]
        id_to_name[sid] = name

        profile = StudentProfile(student_id=sid, student_name=name)

        # Extract optional fields
        for col in group.columns:
            if "section" in col:
                profile.section = str(group[col].iloc[0]).strip()
            elif "year" in col:
                profile.year = str(group[col].iloc[0]).strip()
            elif col in ("semester", "sem"):
                profile.semester = str(group[col].iloc[0]).strip()
            elif "branch" in col or "department" in col or "dept" in col:
                profile.branch = str(group[col].iloc[0]).strip()
            elif "email" in col:
                profile.email = str(group[col].iloc[0]).strip()
            elif "phone" in col or "mobile" in col:
                profile.phone = str(group[col].iloc[0]).strip()
            elif "counselor" in col or "counsellor" in col or "mentor" in col:
                if "id" in col:
                    profile.counselor_id = str(group[col].iloc[0]).strip()
                elif "email" in col:
                    profile.counselor_email = str(group[col].iloc[0]).strip()
                elif "phone" in col or "mobile" in col:
                    profile.counselor_phone = str(group[col].iloc[0]).strip()
                else:
                    profile.counselor_name = str(group[col].iloc[0]).strip()

        # Read CGPA from CSV if column exists
        if cgpa_col:
            try:
                raw = group[cgpa_col].iloc[0]
                val = float(raw)
                if val > 0:
                    profile.cgpa = round(val, 2)
                    profile.cgpa_source = "csv"
            except (ValueError, TypeError):
                pass

        # Extract subject results
        subj_code_col = _detect_column(group, ["subject_code", "subjectcode", "course_code", "coursecode", "sub_code"], "Subject Code")
        subj_name_col = _detect_column(group, ["subject_name", "subjectname", "course_name", "coursename", "sub_name"], "Subject Name")
        grade_col = _detect_column(group, ["grade", "result", "status"], "Grade")
        credits_col = _detect_column(group, ["credit", "credits"], "Credits")

        for _, row in group.iterrows():
            s_code = str(row.get(subj_code_col, "")).strip() if subj_code_col else ""
            s_name = str(row.get(subj_name_col, "")).strip() if subj_name_col else ""
            grade = str(row.get(grade_col, "")).strip() if grade_col else ""
            credits = 0.0
            if credits_col:
                try:
                    credits = float(row.get(credits_col, 0))
                except (ValueError, TypeError):
                    credits = 0.0

            if grade:  # Only add if there's a grade
                profile.previous_results.append(
                    SubjectResult(
                        subject_code=s_code,
                        subject_name=s_name,
                        grade=grade,
                        credits=credits,
                    )
                )

        profiles[sid] = profile

    # --- Step 2: Match attendance data to profiles ---
    attendance_grouped = attendance_df.groupby(attendance_id_col)

    for student_id, group in attendance_grouped:
        sid = str(student_id).strip().upper()
        name = group[attendance_name_col].iloc[0]
        matched_profile = None

        # Primary match: Student ID
        if sid in profiles:
            matched_profile = profiles[sid]
        else:
            # Fallback: Name matching
            best_match_id = None
            best_score = 0.0
            for existing_id, existing_name in id_to_name.items():
                score = _name_similarity(name, existing_name)
                if score > best_score:
                    best_score = score
                    best_match_id = existing_id

            if best_score >= 0.85 and best_match_id:
                matched_profile = profiles[best_match_id]
            else:
                # Create new profile for attendance-only student
                matched_profile = StudentProfile(student_id=sid, student_name=name)
                profiles[sid] = matched_profile

        # Extract optional fields from attendance if not already set
        for col in group.columns:
            if "section" in col and not matched_profile.section:
                matched_profile.section = str(group[col].iloc[0]).strip()
            elif "year" in col and not matched_profile.year:
                matched_profile.year = str(group[col].iloc[0]).strip()
            elif col in ("semester", "sem") and not matched_profile.semester:
                matched_profile.semester = str(group[col].iloc[0]).strip()
            elif ("branch" in col or "department" in col or "dept" in col) and not matched_profile.branch:
                matched_profile.branch = str(group[col].iloc[0]).strip()
            elif "email" in col and not matched_profile.email:
                matched_profile.email = str(group[col].iloc[0]).strip()
            elif ("phone" in col or "mobile" in col) and not matched_profile.phone:
                matched_profile.phone = str(group[col].iloc[0]).strip()
            elif ("counselor" in col or "counsellor" in col or "mentor" in col):
                if "id" in col and not matched_profile.counselor_id:
                    matched_profile.counselor_id = str(group[col].iloc[0]).strip()
                elif "email" in col and not matched_profile.counselor_email:
                    matched_profile.counselor_email = str(group[col].iloc[0]).strip()
                elif ("phone" in col or "mobile" in col) and not matched_profile.counselor_phone:
                    matched_profile.counselor_phone = str(group[col].iloc[0]).strip()
                elif not matched_profile.counselor_name:
                    matched_profile.counselor_name = str(group[col].iloc[0]).strip()

        # Extract attendance records
        subj_code_col = _detect_column(group, ["subject_code", "subjectcode", "course_code", "coursecode", "sub_code"], "Subject Code")
        subj_name_col = _detect_column(group, ["subject_name", "subjectname", "course_name", "coursename", "sub_name"], "Subject Name")
        held_col = _detect_column(group, ["classes_held", "classheld", "total_classes", "totalclasses", "held"], "Classes Held")
        attended_col = _detect_column(group, ["classes_attended", "classattended", "attended", "present"], "Classes Attended")
        pct_col = _detect_column(group, ["attendance_percentage", "attendancepercentage", "attendance_pct", "attendance", "percentage"], "Attendance %")

        for _, row in group.iterrows():
            s_code = str(row.get(subj_code_col, "")).strip() if subj_code_col else ""
            s_name = str(row.get(subj_name_col, "")).strip() if subj_name_col else ""

            classes_held = 0
            classes_attended = 0

            if held_col and attended_col:
                try:
                    classes_held = int(float(row.get(held_col, 0)))
                    classes_attended = int(float(row.get(attended_col, 0)))
                except (ValueError, TypeError):
                    classes_held = 0
                    classes_attended = 0
            elif pct_col:
                # If only percentage is available, use it with assumed total of 100
                try:
                    pct = float(row.get(pct_col, 0))
                    classes_held = 100
                    classes_attended = int(pct)
                except (ValueError, TypeError):
                    pass

            if s_code or s_name:
                matched_profile.attendance_records.append(
                    SubjectAttendance(
                        subject_code=s_code,
                        subject_name=s_name,
                        classes_held=classes_held,
                        classes_attended=classes_attended,
                    )
                )

    # --- Step 3: Compute analytics for all profiles ---
    for profile in profiles.values():
        profile.compute_analytics()

    # Sort by student ID
    return sorted(profiles.values(), key=lambda p: p.student_id)


# ═══════════════════════════════════════════════
#  Single-file builders
# ═══════════════════════════════════════════════

def build_attendance_only(
    attendance_df: pd.DataFrame,
    attendance_id_col: str,
    attendance_name_col: str,
) -> list[StudentProfile]:
    """Build student profiles from attendance data only (no results)."""
    profiles: Dict[str, StudentProfile] = {}
    attendance_grouped = attendance_df.groupby(attendance_id_col)

    for student_id, group in attendance_grouped:
        sid = str(student_id).strip().upper()
        name = group[attendance_name_col].iloc[0]
        profile = StudentProfile(student_id=sid, student_name=name)

        # Extract optional fields
        for col in group.columns:
            if "section" in col and not profile.section:
                profile.section = str(group[col].iloc[0]).strip()
            elif "year" in col and not profile.year:
                profile.year = str(group[col].iloc[0]).strip()
            elif col in ("semester", "sem") and not profile.semester:
                profile.semester = str(group[col].iloc[0]).strip()
            elif ("branch" in col or "department" in col or "dept" in col) and not profile.branch:
                profile.branch = str(group[col].iloc[0]).strip()
            elif "email" in col and not profile.email:
                profile.email = str(group[col].iloc[0]).strip()
            elif ("phone" in col or "mobile" in col) and not profile.phone:
                profile.phone = str(group[col].iloc[0]).strip()
            elif ("counselor" in col or "counsellor" in col or "mentor" in col):
                if "id" in col and not profile.counselor_id:
                    profile.counselor_id = str(group[col].iloc[0]).strip()
                elif "email" in col and not profile.counselor_email:
                    profile.counselor_email = str(group[col].iloc[0]).strip()
                elif ("phone" in col or "mobile" in col) and not profile.counselor_phone:
                    profile.counselor_phone = str(group[col].iloc[0]).strip()
                elif not profile.counselor_name:
                    profile.counselor_name = str(group[col].iloc[0]).strip()

        # Extract attendance records
        subj_code_col = _detect_column(group, ["subject_code", "subjectcode", "course_code", "coursecode", "sub_code"], "Subject Code")
        subj_name_col = _detect_column(group, ["subject_name", "subjectname", "course_name", "coursename", "sub_name"], "Subject Name")
        held_col = _detect_column(group, ["classes_held", "classheld", "total_classes", "totalclasses", "held"], "Classes Held")
        attended_col = _detect_column(group, ["classes_attended", "classattended", "attended", "present"], "Classes Attended")
        pct_col = _detect_column(group, ["attendance_percentage", "attendancepercentage", "attendance_pct", "attendance", "percentage"], "Attendance %")

        for _, row in group.iterrows():
            s_code = str(row.get(subj_code_col, "")).strip() if subj_code_col else ""
            s_name = str(row.get(subj_name_col, "")).strip() if subj_name_col else ""
            classes_held = 0
            classes_attended = 0
            if held_col and attended_col:
                try:
                    classes_held = int(float(row.get(held_col, 0)))
                    classes_attended = int(float(row.get(attended_col, 0)))
                except (ValueError, TypeError):
                    pass
            elif pct_col:
                try:
                    pct = float(row.get(pct_col, 0))
                    classes_held = 100
                    classes_attended = int(pct)
                except (ValueError, TypeError):
                    pass
            if s_code or s_name:
                profile.attendance_records.append(
                    SubjectAttendance(subject_code=s_code, subject_name=s_name,
                                     classes_held=classes_held, classes_attended=classes_attended)
                )

        profiles[sid] = profile

    for profile in profiles.values():
        profile.compute_analytics()
    return sorted(profiles.values(), key=lambda p: p.student_id)


def build_results_only(
    results_df: pd.DataFrame,
    results_id_col: str,
    results_name_col: str,
) -> list[StudentProfile]:
    """Build student profiles from results data only (no attendance)."""
    profiles: Dict[str, StudentProfile] = {}
    results_grouped = results_df.groupby(results_id_col)

    # Detect CGPA column (read directly if present)
    cgpa_col = _detect_column(results_df, ["cgpa", "cg", "cgpa_value"], "CGPA")

    for student_id, group in results_grouped:
        sid = str(student_id).strip().upper()
        name = group[results_name_col].iloc[0]
        profile = StudentProfile(student_id=sid, student_name=name)

        for col in group.columns:
            if "section" in col:
                profile.section = str(group[col].iloc[0]).strip()
            elif "year" in col:
                profile.year = str(group[col].iloc[0]).strip()
            elif col in ("semester", "sem"):
                profile.semester = str(group[col].iloc[0]).strip()
            elif "branch" in col or "department" in col or "dept" in col:
                profile.branch = str(group[col].iloc[0]).strip()
            elif "email" in col:
                profile.email = str(group[col].iloc[0]).strip()
            elif "phone" in col or "mobile" in col:
                profile.phone = str(group[col].iloc[0]).strip()
            elif "counselor" in col or "counsellor" in col or "mentor" in col:
                if "id" in col:
                    profile.counselor_id = str(group[col].iloc[0]).strip()
                elif "email" in col:
                    profile.counselor_email = str(group[col].iloc[0]).strip()
                elif "phone" in col or "mobile" in col:
                    profile.counselor_phone = str(group[col].iloc[0]).strip()
                else:
                    profile.counselor_name = str(group[col].iloc[0]).strip()

        # Read CGPA from CSV if column exists
        if cgpa_col:
            try:
                raw = group[cgpa_col].iloc[0]
                val = float(raw)
                if val > 0:
                    profile.cgpa = round(val, 2)
                    profile.cgpa_source = "csv"
            except (ValueError, TypeError):
                pass

        subj_code_col = _detect_column(group, ["subject_code", "subjectcode", "course_code", "coursecode", "sub_code"], "Subject Code")
        subj_name_col = _detect_column(group, ["subject_name", "subjectname", "course_name", "coursename", "sub_name"], "Subject Name")
        grade_col = _detect_column(group, ["grade", "result", "status"], "Grade")
        credits_col = _detect_column(group, ["credit", "credits"], "Credits")

        for _, row in group.iterrows():
            s_code = str(row.get(subj_code_col, "")).strip() if subj_code_col else ""
            s_name = str(row.get(subj_name_col, "")).strip() if subj_name_col else ""
            grade = str(row.get(grade_col, "")).strip() if grade_col else ""
            credits = 0.0
            if credits_col:
                try:
                    credits = float(row.get(credits_col, 0))
                except (ValueError, TypeError):
                    credits = 0.0
            if grade:
                profile.previous_results.append(
                    SubjectResult(subject_code=s_code, subject_name=s_name, grade=grade, credits=credits)
                )

        profiles[sid] = profile

    for profile in profiles.values():
        profile.compute_analytics()
    return sorted(profiles.values(), key=lambda p: p.student_id)
