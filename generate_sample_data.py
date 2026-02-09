"""
Generate sample test data files for the Student Academic Analysis System.
Creates:
  - sample_results.csv   (previous semester results)
  - sample_attendance.csv (current semester attendance)
"""

import csv
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "sample_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Student pool ──
STUDENTS = []
for i in range(1, 51):
    STUDENTS.append({
        "Student_ID": f"2300{i:03d}",
        "Student_Name": f"Student_{i:03d}",
        "Section": random.choice(["A", "B", "C"]),
        "Year": "2",
        "Semester": "3",
        "Branch": "Computer Science and Engineering",
        "Email": f"student{i:03d}@kluniversity.in",
        "Counselor_Name": random.choice(["Dr. Ramesh Kumar", "Dr. Priya Sharma", "Dr. Anil Reddy"]),
        "Counselor_ID": random.choice(["FAC001", "FAC002", "FAC003"]),
    })

# ── Subjects ──
PREV_SUBJECTS = [
    ("CS201", "Data Structures", 4),
    ("CS202", "Digital Logic Design", 3),
    ("MA201", "Probability and Statistics", 3),
    ("CS203", "Object Oriented Programming", 4),
    ("HS201", "Professional Communication", 2),
]

CURR_SUBJECTS = [
    ("CS301", "Database Management Systems"),
    ("CS302", "Computer Networks"),
    ("CS303", "Operating Systems"),
    ("CS304", "Software Engineering"),
    ("MA301", "Discrete Mathematics"),
]

GRADES = ["O", "A+", "A", "B+", "B", "C", "P", "F"]
GRADE_WEIGHTS = [5, 10, 20, 20, 15, 10, 10, 10]


def generate_results():
    """Generate previous semester results CSV."""
    filepath = OUTPUT_DIR / "sample_results.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Student_ID", "Student_Name", "Section", "Year", "Semester",
            "Branch", "Email", "Counselor_Name", "Counselor_ID",
            "Subject_Code", "Subject_Name", "Grade", "Credits"
        ])
        for student in STUDENTS:
            for code, name, credits in PREV_SUBJECTS:
                grade = random.choices(GRADES, weights=GRADE_WEIGHTS, k=1)[0]
                writer.writerow([
                    student["Student_ID"],
                    student["Student_Name"],
                    student["Section"],
                    student["Year"],
                    student["Semester"],
                    student["Branch"],
                    student["Email"],
                    student["Counselor_Name"],
                    student["Counselor_ID"],
                    code, name, grade, credits,
                ])
    print(f"Results file: {filepath} ({len(STUDENTS) * len(PREV_SUBJECTS)} rows)")


def generate_attendance():
    """Generate current semester attendance CSV."""
    filepath = OUTPUT_DIR / "sample_attendance.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Student_ID", "Student_Name", "Section", "Year", "Semester",
            "Branch", "Email", "Counselor_Name", "Counselor_ID",
            "Subject_Code", "Subject_Name", "Classes_Held", "Classes_Attended"
        ])
        for student in STUDENTS:
            for code, name in CURR_SUBJECTS:
                classes_held = random.randint(35, 50)
                # Vary attendance: some students have low attendance
                if random.random() < 0.15:
                    # Low attendance
                    classes_attended = random.randint(
                        int(classes_held * 0.50), int(classes_held * 0.74)
                    )
                elif random.random() < 0.2:
                    # Warning zone
                    classes_attended = random.randint(
                        int(classes_held * 0.75), int(classes_held * 0.79)
                    )
                else:
                    # Good attendance
                    classes_attended = random.randint(
                        int(classes_held * 0.80), classes_held
                    )
                writer.writerow([
                    student["Student_ID"],
                    student["Student_Name"],
                    student["Section"],
                    student["Year"],
                    student["Semester"],
                    student["Branch"],
                    student["Email"],
                    student["Counselor_Name"],
                    student["Counselor_ID"],
                    code, name, classes_held, classes_attended,
                ])
    print(f"Attendance file: {filepath} ({len(STUDENTS) * len(CURR_SUBJECTS)} rows)")


if __name__ == "__main__":
    generate_results()
    generate_attendance()
    print("Sample data generation complete!")
