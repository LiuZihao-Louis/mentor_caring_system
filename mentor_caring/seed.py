from __future__ import annotations

from mentor_caring.models import (
    Department,
    Faculty,
    FacultyConsultant,
    Major,
    MCPGroup,
    MCPCoordinator,
    Mentor,
    Record,
    Message,
    Student,
    SupportingStaff,
    User,
    make_password,
    ROLE_ADMIN,
    ROLE_FACULTY_CONSULTANT,
    ROLE_MENTOR,
    ROLE_STUDENT,
    ROLE_COORDINATOR,
    ROLE_SUPPORTING_STAFF,
)
from mentor_caring.repositories import InMemoryStore


def seed_data(store: InMemoryStore) -> InMemoryStore:
    store.reset()

    for faculty in ["FST", "FHSS", "FSM", "DCC"]:
        store.faculties.add(faculty, Faculty(name=faculty))

    store.departments.add("DCS", Department(name="DCS", faculty_name="FST", majors=["CST", "AI"], coordinator_id="COR001"))
    store.faculties.get("FST").departments.append("DCS")
    store.majors.add("CST", Major(name="CST", department_name="DCS", faculty_name="FST"))
    store.majors.add("AI", Major(name="AI", department_name="DCS", faculty_name="FST"))

    # Users use domain ids where possible. This makes API calls simple in tests and demos.
    admin = User("admin", "System Admin", "admin", make_password("admin123"), ROLE_ADMIN, "admin@bnbu.edu.cn", True)
    consultant_user = User("FC001", "Alice Consultant", "alice", make_password("consultant123"), ROLE_FACULTY_CONSULTANT, "alice.consultant@bnbu.edu.cn", True, "FST")
    mentor_user = User("MTR001", "Mary Lee", "mary", make_password("mentor123"), ROLE_MENTOR, "marylee@bnbu.edu.cn", True, "FST", "DCS")
    coord_user = User("COR001", "Ruth Mo", "ruth", make_password("coord123"), ROLE_COORDINATOR, "ruthmo@bnbu.edu.cn", True, "FST", "DCS")
    staff_user = User("STF001", "Sam Staff", "sam", make_password("staff123"), ROLE_SUPPORTING_STAFF, "sam.staff@bnbu.edu.cn", True)
    student_user = User("123456789", "Bnbuer", "123456789", make_password("student123"), ROLE_STUDENT, "123456789@mail.bnbu.edu.cn", False, "FST", "DCS")
    student2_user = User("987654321", "Other Student", "987654321", make_password("student123"), ROLE_STUDENT, "987654321@mail.bnbu.edu.cn", False, "FHSS", "OTHER")

    for user in [admin, consultant_user, mentor_user, coord_user, staff_user, student_user, student2_user]:
        store.users.add(user.id, user)

    consultant = FacultyConsultant("FC001", "Alice Consultant", "alice.consultant@bnbu.edu.cn", "FST", "FC001")
    mentor = Mentor("MTR001", "Mary Lee", "marylee@bnbu.edu.cn", "T1-102", "FST", "DCS", "MTR001")
    coordinator = MCPCoordinator("COR001", "Ruth Mo", "ruthmo@bnbu.edu.cn", "DCS", "COR001")
    staff = SupportingStaff("STF001", "Sam Staff", "sam.staff@bnbu.edu.cn", "STF001")
    student = Student("123456789", "Bnbuer", "123456789@mail.bnbu.edu.cn", "normal", "2024-2025-Y2", "FST", "DCS", "CST", "123456789")
    student2 = Student("987654321", "Other Student", "987654321@mail.bnbu.edu.cn", "normal", None, "FHSS", "OTHER", "OTHER", "987654321")

    store.faculty_consultants.add(consultant.consultant_id, consultant)
    store.mentors.add(mentor.mentor_id, mentor)
    store.coordinators.add(coordinator.coordinator_id, coordinator)
    store.supporting_staff.add(staff.staff_id, staff)
    store.students.add(student.student_id, student)
    store.students.add(student2.student_id, student2)

    group = MCPGroup(
        group_id="2024-2025-Y2",
        academic_year="2024-2025",
        year_label="Y2",
        mentor_id="MTR001",
        major_name="CST",
        department_name="DCS",
        faculty_name="FST",
        student_ids=["123456789"],
    )
    store.groups.add(group.group_id, group)

    record = Record(
        record_id="RECSEED1",
        student_id="123456789",
        mentor_id="MTR001",
        group_id="2024-2025-Y2",
        date="2026-01-01",
        time="10:00",
        problem_statement="Study difficulty.",
        interview_summary="Give students advice on study method.",
        follow_up_action="Fix the next interview time to check the study progress.",
    )
    store.records.add(record.record_id, record)

    message = Message(
        message_id="MSGSEED1",
        sender_id="MTR001",
        receiver_ids=["123456789"],
        content="Welcome to the Mentor Caring Programme.",
        related_student_id="123456789",
    )
    store.messages.add(message.message_id, message)
    return store
