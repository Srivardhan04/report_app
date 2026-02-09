"""Data models for the student academic analysis system."""

from dataclasses import dataclass, field
from typing import Optional

from config import GRADE_POINT_MAP


@dataclass
class SubjectResult:
    """Represents a single subject result from previous semester."""
    subject_code: str
    subject_name: str
    grade: str
    credits: float = 0.0
    is_backlog: bool = False

    def __post_init__(self):
        self.grade = self.grade.strip().upper()
        self.is_backlog = self.grade in {"F", "FA", "AB", "FAIL", "I", "W"}


@dataclass
class SubjectAttendance:
    """Represents attendance for a single subject in current semester."""
    subject_code: str
    subject_name: str
    classes_held: int
    classes_attended: int
    attendance_percentage: float = 0.0
    status: str = "Green"   # Red / Yellow / Green

    def __post_init__(self):
        if self.classes_held > 0:
            self.attendance_percentage = round(
                (self.classes_attended / self.classes_held) * 100, 2
            )
        self._compute_status()

    def _compute_status(self):
        if self.attendance_percentage < 75.0:
            self.status = "Red"
        elif self.attendance_percentage < 80.0:
            self.status = "Yellow"
        else:
            self.status = "Green"

    @property
    def attendance_class(self) -> str:
        """CSS class for attendance color-coding in PDF."""
        if self.attendance_percentage < 75.0:
            return "att-red"
        elif self.attendance_percentage < 80.0:
            return "att-yellow"
        return "att-green"


@dataclass
class StudentProfile:
    """Unified student profile merging results and attendance."""
    student_id: str
    student_name: str
    section: str = ""
    year: str = ""
    semester: str = ""
    branch: str = ""
    email: str = ""
    phone: str = ""
    counselor_name: str = ""
    counselor_id: str = ""
    counselor_email: str = ""
    counselor_phone: str = ""

    # CGPA — from CSV column or computed
    cgpa: Optional[float] = None
    cgpa_source: str = ""  # "csv" if read from file, "computed" if calculated

    # Academic data
    previous_results: list[SubjectResult] = field(default_factory=list)
    attendance_records: list[SubjectAttendance] = field(default_factory=list)

    # Computed fields
    backlog_count: int = 0
    backlog_subjects: list[str] = field(default_factory=list)
    has_low_attendance: bool = False
    low_attendance_subjects: list[str] = field(default_factory=list)
    overall_attendance: float = 0.0

    def compute_cgpa(self):
        """Calculate CGPA from previous results if not already set from CSV."""
        if self.cgpa is not None:
            return  # Already set from CSV — do not recompute
        if not self.previous_results:
            return  # No results — nothing to compute

        total_weighted = 0.0
        total_credits = 0.0
        for r in self.previous_results:
            if r.credits <= 0:
                continue
            gp = GRADE_POINT_MAP.get(r.grade, None)
            if gp is None:
                continue  # Unknown grade — skip
            total_weighted += gp * r.credits
            total_credits += r.credits

        if total_credits > 0:
            self.cgpa = round(total_weighted / total_credits, 2)
            self.cgpa_source = "computed"

    def compute_analytics(self):
        """Calculate backlog count, attendance alerts, CGPA, etc."""
        # CGPA
        self.compute_cgpa()

        # Backlogs
        self.backlog_subjects = [
            r.subject_name for r in self.previous_results if r.is_backlog
        ]
        self.backlog_count = len(self.backlog_subjects)

        # Attendance
        self.low_attendance_subjects = [
            a.subject_name for a in self.attendance_records
            if a.status in ("Red", "Yellow")
        ]
        self.has_low_attendance = any(
            a.status == "Red" for a in self.attendance_records
        )

        # Overall attendance
        total_held = sum(a.classes_held for a in self.attendance_records)
        total_attended = sum(a.classes_attended for a in self.attendance_records)
        if total_held > 0:
            self.overall_attendance = round(
                (total_attended / total_held) * 100, 2
            )

    @property
    def needs_counseling(self) -> bool:
        return self.has_low_attendance or self.backlog_count > 0

    @property
    def concern_reasons(self) -> list[str]:
        """Generate professional concern statements."""
        reasons = []
        if self.has_low_attendance:
            red_subjects = [
                a.subject_name for a in self.attendance_records if a.status == "Red"
            ]
            reasons.append(
                f"the student has attendance below 75% in the following subject(s): "
                f"{', '.join(red_subjects)}, which may lead to detention as per university regulations"
            )
        yellow_subjects = [
            a.subject_name for a in self.attendance_records if a.status == "Yellow"
        ]
        if yellow_subjects:
            reasons.append(
                f"the student's attendance is between 75%–80% in {', '.join(yellow_subjects)}, "
                f"requiring immediate improvement to avoid falling below the minimum threshold"
            )
        if self.backlog_count > 0:
            reasons.append(
                f"the student has {self.backlog_count} backlog(s) in the previous semester "
                f"({', '.join(self.backlog_subjects)}), which requires dedicated effort to clear"
            )
        return reasons

    @property
    def footer_message(self) -> str:
        """Generate professional footer with concern reasons."""
        if not self.needs_counseling:
            return (
                "The student's academic performance and attendance are satisfactory. "
                "We encourage the student to continue maintaining this standard.\n\n"
                "Sincerely,\nHead of the Department"
            )
        reasons = self.concern_reasons
        reason_text = "; and ".join(reasons)
        return (
            f"This is to bring to your kind attention that {reason_text}. "
            f"We kindly request the parent/guardian to counsel the student and ensure "
            f"regular attendance and focused academic effort. The department will continue "
            f"to monitor the student's progress and provide necessary academic support.\n\n"
            f"Sincerely,\nHead of the Department\n"
            f"{self.branch or 'Department of Artificial Intelligence and Data Science (AI & DS)'}"
        )
