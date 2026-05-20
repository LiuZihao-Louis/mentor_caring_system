from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash


ROLE_ADMIN = "administrator"
ROLE_FACULTY_CONSULTANT = "faculty_consultant"
ROLE_MENTOR = "mentor"
ROLE_STUDENT = "student"
ROLE_COORDINATOR = "mcp_coordinator"
ROLE_SUPPORTING_STAFF = "supporting_staff"
ROLE_UNASSIGNED_STAFF = "unassigned_staff"

ALL_ROLES = {
    ROLE_ADMIN,
    ROLE_FACULTY_CONSULTANT,
    ROLE_MENTOR,
    ROLE_STUDENT,
    ROLE_COORDINATOR,
    ROLE_SUPPORTING_STAFF,
    ROLE_UNASSIGNED_STAFF,
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_password(raw_password: str) -> str:
    return generate_password_hash(raw_password)


@dataclass
class Serializable:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class User(Serializable):
    id: str
    name: str
    account: str
    password_hash: str
    role: str
    email: str
    is_staff: bool = False
    faculty_name: Optional[str] = None
    department_name: Optional[str] = None

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def public_dict(self) -> Dict[str, Any]:
        data = self.to_dict()
        data.pop("password_hash", None)
        return data


@dataclass
class FacultyMember(Serializable):
    user_id: str
    name: str
    email: str
    faculty_name: Optional[str] = None
    department_name: Optional[str] = None


@dataclass
class Student(Serializable):
    student_id: str
    name: str
    email: str
    status: str = "normal"
    group_id: Optional[str] = None
    faculty_name: str = ""
    department_name: str = ""
    major_name: str = ""
    user_id: Optional[str] = None


@dataclass
class Mentor(Serializable):
    mentor_id: str
    name: str
    email: str
    office: str = ""
    faculty_name: str = ""
    department_name: str = ""
    user_id: Optional[str] = None


@dataclass
class FacultyConsultant(Serializable):
    consultant_id: str
    name: str
    email: str
    faculty_name: str
    user_id: Optional[str] = None


@dataclass
class MCPCoordinator(Serializable):
    coordinator_id: str
    name: str
    email: str
    department_name: str
    user_id: Optional[str] = None


@dataclass
class SupportingStaff(Serializable):
    staff_id: str
    name: str
    email: str
    user_id: Optional[str] = None


@dataclass
class Faculty(Serializable):
    name: str
    departments: List[str] = field(default_factory=list)


@dataclass
class Department(Serializable):
    name: str
    faculty_name: str
    majors: List[str] = field(default_factory=list)
    coordinator_id: Optional[str] = None


@dataclass
class Major(Serializable):
    name: str
    department_name: str
    faculty_name: str


@dataclass
class MCPGroup(Serializable):
    group_id: str
    academic_year: str
    year_label: str
    mentor_id: Optional[str]
    major_name: str
    department_name: str
    faculty_name: str
    student_ids: List[str] = field(default_factory=list)


@dataclass
class Record(Serializable):
    record_id: str
    student_id: str
    mentor_id: str
    group_id: str
    date: str
    time: str
    problem_statement: str
    interview_summary: str
    follow_up_action: str = "None"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def update(self, **fields: Any) -> None:
        allowed = {"date", "time", "problem_statement", "interview_summary", "follow_up_action"}
        for key, value in fields.items():
            if key in allowed and value is not None:
                setattr(self, key, value)
        self.updated_at = now_iso()


@dataclass
class Message(Serializable):
    message_id: str
    sender_id: str
    receiver_ids: List[str]
    content: str
    status: str = "unrespond"
    attachment: Optional[str] = None
    message_type: str = "normal"
    related_student_id: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    responded_at: Optional[str] = None

    def mark_responded(self) -> None:
        self.status = "respond"
        self.responded_at = now_iso()


@dataclass
class Appointment(Serializable):
    appointment_id: str
    mentor_id: str
    student_id: str
    group_id: str
    date: str
    start_time: str
    end_time: str
    venue: str = ""
    status: str = "available"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def update_status(self, status: str, venue: Optional[str] = None) -> None:
        self.status = status
        if venue is not None:
            self.venue = venue
        self.updated_at = now_iso()


@dataclass
class LogActivity(Serializable):
    log_id: str
    user_id: str
    time: str
    data: str
    function_access: str
    student_id: Optional[str] = None


@dataclass
class Feedback(Serializable):
    feedback_id: str
    student_id: Optional[str]
    content: str
    status: str = "unrespond"
    response: str = ""
    created_at: str = field(default_factory=now_iso)
    responded_at: Optional[str] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None

    def respond(self, response: str) -> None:
        self.status = "respond"
        self.response = response
        self.responded_at = now_iso()


@dataclass
class Notification(Serializable):
    notification_id: str
    receiver_id: str
    content: str
    source_type: str
    source_id: str
    created_at: str = field(default_factory=now_iso)


@dataclass
class ExportResult(Serializable):
    file_path: str
    file_name: str
    created_at: str = field(default_factory=now_iso)
