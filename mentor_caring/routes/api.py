from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session

from mentor_caring.models import (
    ROLE_ADMIN,
    ROLE_COORDINATOR,
    ROLE_FACULTY_CONSULTANT,
    ROLE_MENTOR,
    ROLE_STUDENT,
    ROLE_SUPPORTING_STAFF,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def store():
    return current_app.config["store"]


def services():
    return current_app.config["services"]


def serialize(value):
    if isinstance(value, list):
        return [serialize(v) for v in value]
    if hasattr(value, "public_dict"):
        return value.public_dict()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    return value


def body() -> dict:
    return request.get_json(silent=True) or {}


def current_user():
    uid = session.get("user_id")
    return store().users.get(uid) if uid else None


def require_api_user(*roles: str, expected_id: str | None = None):
    user = current_user()
    if user is None:
        raise PermissionError("login required")
    if roles and user.role not in roles:
        raise PermissionError("current user role is not allowed")
    if expected_id is not None and user.id != expected_id:
        raise PermissionError("current user cannot act as another user")
    return user


@api_bp.get("/me")
def me():
    return jsonify({"user": serialize(require_api_user())})


@api_bp.post("/auth/login")
def login():
    data = body()
    user = services()["auth"].login(data.get("account"), data.get("password"))
    session["user_id"] = user.id
    return jsonify({"user": user.public_dict()}), 200


@api_bp.post("/auth/logout")
def logout():
    user = require_api_user()
    result = services()["auth"].logout(user.id)
    session.clear()
    return jsonify(result), 200


@api_bp.get("/students/<student_id>/mentor")
def student_mentor(student_id):
    require_api_user(ROLE_STUDENT, expected_id=student_id)
    return jsonify(services()["student"].get_mentor_info_by_student_id(student_id)), 200


@api_bp.get("/students/<student_id>")
def student_info(student_id):
    require_api_user(ROLE_STUDENT, expected_id=student_id)
    return jsonify(services()["student"].get_student_information(student_id)), 200


@api_bp.post("/students/<student_id>/feedback")
def student_feedback(student_id):
    require_api_user(ROLE_STUDENT, expected_id=student_id)
    feedback = services()["feedback"].submit_feedback(student_id, body().get("content"))
    return jsonify(feedback.to_dict()), 201


@api_bp.post("/feedback")
def submit_feedback():
    user = require_api_user(ROLE_STUDENT, ROLE_MENTOR, ROLE_COORDINATOR, ROLE_FACULTY_CONSULTANT, ROLE_ADMIN)
    feedback = services()["feedback"].submit_feedback(user.id, body().get("content"))
    return jsonify(feedback.to_dict()), 201


@api_bp.post("/students/<student_id>/appointments/<appointment_id>/book")
def book_appointment(student_id, appointment_id):
    require_api_user(ROLE_STUDENT, expected_id=student_id)
    appt = services()["appointment"].book_appointment(student_id, appointment_id)
    return jsonify(appt.to_dict()), 200


@api_bp.get("/students/<student_id>/messages")
def student_messages(student_id):
    require_api_user(ROLE_STUDENT, expected_id=student_id)
    return jsonify({
        "inbox": serialize(services()["message"].get_inbox(student_id)),
        "sent": serialize(services()["message"].get_sent_messages(student_id)),
    })


@api_bp.get("/mentors/<mentor_id>/students/<student_id>")
def mentor_search_student(mentor_id, student_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    return jsonify(services()["mentor"].search_student_by_id(mentor_id, student_id))


@api_bp.post("/mentors/<mentor_id>/records")
def mentor_create_record(mentor_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    data = body()
    record = services()["mentor"].create_interview_record(
        mentor_id=mentor_id,
        student_id=data.get("student_id"),
        date=data.get("date"),
        time=data.get("time"),
        problem_statement=data.get("problem_statement"),
        interview_summary=data.get("interview_summary"),
        follow_up_action=data.get("follow_up_action"),
    )
    return jsonify(record.to_dict()), 201


@api_bp.patch("/mentors/<mentor_id>/records/<record_id>")
def mentor_update_record(mentor_id, record_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    record = services()["mentor"].update_interview_record(mentor_id, record_id, body())
    return jsonify(record.to_dict())


@api_bp.delete("/mentors/<mentor_id>/records/<record_id>")
def mentor_delete_record(mentor_id, record_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    return jsonify(services()["mentor"].delete_interview_record(mentor_id, record_id))


@api_bp.post("/mentors/<mentor_id>/appointments/slots")
def mentor_create_slots(mentor_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    data = body()
    appts = services()["mentor"].create_available_slots(
        mentor_id=mentor_id,
        student_id=data.get("student_id"),
        date=data.get("date"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
    )
    return jsonify(serialize(appts)), 201


@api_bp.post("/mentors/<mentor_id>/appointments/<appointment_id>/confirm")
def mentor_confirm_appt(mentor_id, appointment_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    appt = services()["mentor"].confirm_appointment(mentor_id, appointment_id, body().get("venue"))
    return jsonify(appt.to_dict())


@api_bp.post("/mentors/<mentor_id>/special-cases")
def mentor_special_case(mentor_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    data = body()
    msg = services()["mentor"].forward_special_case_to_coordinator(
        mentor_id, data.get("student_id"), data.get("coordinator_id"), data.get("description")
    )
    return jsonify(msg.to_dict()), 201


@api_bp.get("/mentors/<mentor_id>/export")
def mentor_export(mentor_id):
    require_api_user(ROLE_MENTOR, expected_id=mentor_id)
    result = services()["mentor"].export_interview_records(mentor_id)
    return jsonify(result.to_dict())


@api_bp.post("/messages")
def send_message():
    user = require_api_user()
    data = body()
    msg = services()["message"].send_message(
        user.id, data.get("receiver_ids"), data.get("content"),
        data.get("message_type", "normal"), data.get("attachment"), data.get("related_student_id")
    )
    return jsonify(msg.to_dict()), 201


@api_bp.get("/messages/recipients")
def search_recipients():
    user = require_api_user()
    return jsonify(services()["message"].search_recipients(user.id, request.args.get("keyword")))


@api_bp.post("/messages/<message_id>/respond")
def respond_message(message_id):
    user = require_api_user()
    msg = services()["message"].respond_message(user.id, message_id, body().get("content"))
    return jsonify(msg.to_dict()), 201


@api_bp.get("/users/<user_id>/messages/inbox")
def inbox(user_id):
    require_api_user(expected_id=user_id)
    return jsonify(serialize(services()["message"].get_inbox(user_id)))


@api_bp.get("/users/<user_id>/messages/sent")
def sent(user_id):
    require_api_user(expected_id=user_id)
    return jsonify(serialize(services()["message"].get_sent_messages(user_id)))


@api_bp.post("/faculty-consultants/<consultant_id>/organization/import")
def fc_import_org(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    result = services()["faculty_consultant"].import_organization_units(rows=body().get("rows", []), consultant_id=consultant_id)
    return jsonify(result), 201


@api_bp.post("/faculty-consultants/<consultant_id>/students/import")
def fc_import_students(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    data = body()
    result = services()["faculty_consultant"].import_students_and_mentors(
        consultant_id, rows=data.get("rows", []), academic_year=data.get("academic_year", "2024-2025")
    )
    return jsonify(result), 201


@api_bp.patch("/faculty-consultants/<consultant_id>/groups/<group_id>/mentor")
def fc_change_mentor(consultant_id, group_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    group = services()["faculty_consultant"].change_mentor_of_group(consultant_id, group_id, body().get("new_mentor_id"))
    return jsonify(group.to_dict())


@api_bp.post("/faculty-consultants/<consultant_id>/coordinators")
def fc_designate_coord(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    data = body()
    dept = services()["faculty_consultant"].designate_coordinator(consultant_id, data.get("department_name"), data.get("coordinator_id"))
    return jsonify(dept.to_dict())


@api_bp.post("/faculty-consultants/<consultant_id>/coordinators/import")
def fc_import_coords(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    result = services()["faculty_consultant"].import_coordinators(consultant_id, rows=body().get("rows", []))
    return jsonify(result), 201


@api_bp.post("/faculty-consultants/<consultant_id>/groups/<group_id>/students")
def fc_add_student_group(consultant_id, group_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    group = services()["faculty_consultant"].add_student_to_group(consultant_id, body().get("student_id"), group_id)
    return jsonify(group.to_dict())


@api_bp.delete("/faculty-consultants/<consultant_id>/groups/<group_id>/students/<student_id>")
def fc_remove_student_group(consultant_id, group_id, student_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    group = services()["faculty_consultant"].remove_student_from_group(consultant_id, student_id, group_id)
    return jsonify(group.to_dict())


@api_bp.get("/faculty-consultants/<consultant_id>/students/<student_id>")
def fc_student_info(consultant_id, student_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    return jsonify(services()["faculty_consultant"].search_student_information(consultant_id, student_id))


@api_bp.get("/faculty-consultants/<consultant_id>/mentors/search")
def fc_mentor_search(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    data = services()["faculty_consultant"].search_mentor_information(
        consultant_id, request.args.get("keyword"), request.args.get("email"), request.args.get("group_id")
    )
    return jsonify(serialize(data))


@api_bp.get("/faculty-consultants/<consultant_id>/logs")
def fc_logs(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    return jsonify(serialize(services()["faculty_consultant"].view_student_logs(consultant_id, request.args.get("student_id"))))


@api_bp.post("/faculty-consultants/<consultant_id>/export")
def fc_export(consultant_id):
    require_api_user(ROLE_FACULTY_CONSULTANT, expected_id=consultant_id)
    data = body()
    result = services()["faculty_consultant"].export_information_to_word(
        consultant_id,
        academic_years=data.get("academic_years"),
        department_name=data.get("department_name"),
        major_name=data.get("major_name"),
        mentor_name=data.get("mentor_name"),
        student_name=data.get("student_name"),
    )
    return jsonify(result)


@api_bp.get("/coordinators/<coordinator_id>/students")
def coord_students(coordinator_id):
    require_api_user(ROLE_COORDINATOR, expected_id=coordinator_id)
    return jsonify(serialize(services()["coordinator"].search_students_in_department(coordinator_id, request.args.get("keyword"))))


@api_bp.get("/coordinators/<coordinator_id>/students/<student_id>")
def coord_student(coordinator_id, student_id):
    require_api_user(ROLE_COORDINATOR, expected_id=coordinator_id)
    return jsonify(services()["coordinator"].search_student_information(coordinator_id, student_id))


@api_bp.get("/coordinators/<coordinator_id>/mentors")
def coord_mentors(coordinator_id):
    require_api_user(ROLE_COORDINATOR, expected_id=coordinator_id)
    return jsonify(serialize(services()["coordinator"].search_mentors_in_department(coordinator_id, request.args.get("keyword"))))


@api_bp.post("/coordinators/<coordinator_id>/special-cases/forward")
def coord_forward(coordinator_id):
    require_api_user(ROLE_COORDINATOR, expected_id=coordinator_id)
    data = body()
    msg = services()["coordinator"].forward_special_case_to_faculty_consultant(
        coordinator_id, data.get("student_id"), data.get("consultant_id"), data.get("description")
    )
    return jsonify(msg.to_dict()), 201


@api_bp.post("/admin/<admin_id>/faculty-consultants")
def admin_add_fc(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    data = body()
    result = services()["admin"].add_faculty_consultant(admin_id, data.get("user_id"), data.get("faculty_name"))
    return jsonify(result.to_dict()), 201


@api_bp.patch("/admin/<admin_id>/faculty-consultants")
def admin_change_fc(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    data = body()
    result = services()["admin"].change_faculty_consultant(admin_id, data.get("faculty_name"), data.get("new_user_id"))
    return jsonify(result.to_dict())


@api_bp.delete("/admin/<admin_id>/faculty-consultants/<consultant_id>")
def admin_delete_fc(admin_id, consultant_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    return jsonify(services()["admin"].delete_faculty_consultant(admin_id, request.args.get("faculty_name", "FST"), consultant_id))


@api_bp.post("/admin/<admin_id>/supporting-staff")
def admin_staff(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    result = services()["admin"].create_supporting_staff(admin_id, body().get("user_id"))
    return jsonify(result.to_dict()), 201


@api_bp.delete("/admin/<admin_id>/supporting-staff/<staff_id>")
def admin_delete_staff(admin_id, staff_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    return jsonify(services()["admin"].delete_supporting_staff(admin_id, staff_id))


@api_bp.post("/admin/<admin_id>/organization/import")
def admin_org(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    return jsonify(services()["admin"].import_organization_units(admin_id, rows=body().get("rows", []))), 201


@api_bp.post("/admin/<admin_id>/organization/faculties")
def admin_add_faculty(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    result = services()["admin"].add_faculty(admin_id, body().get("faculty_name"))
    return jsonify(result.to_dict()), 201


@api_bp.post("/admin/<admin_id>/organization/departments")
def admin_add_department(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    data = body()
    result = services()["admin"].add_department(admin_id, data.get("faculty_name"), data.get("department_name"))
    return jsonify(result.to_dict()), 201


@api_bp.post("/admin/<admin_id>/organization/majors")
def admin_add_major(admin_id):
    require_api_user(ROLE_ADMIN, expected_id=admin_id)
    data = body()
    result = services()["admin"].add_major(admin_id, data.get("faculty_name"), data.get("department_name"), data.get("major_name"))
    return jsonify(result.to_dict()), 201


@api_bp.get("/supporting-staff/<staff_id>/logs")
def staff_logs(staff_id):
    require_api_user(ROLE_SUPPORTING_STAFF, expected_id=staff_id)
    return jsonify(serialize(services()["supporting_staff"].view_all_student_logs(staff_id)))


@api_bp.get("/supporting-staff/<staff_id>/feedback")
def staff_feedback(staff_id):
    require_api_user(ROLE_SUPPORTING_STAFF, expected_id=staff_id)
    return jsonify(serialize(services()["feedback"].list_feedback(request.args.get("status"))))


@api_bp.post("/supporting-staff/<staff_id>/feedback/<feedback_id>/respond")
def staff_respond_feedback(staff_id, feedback_id):
    require_api_user(ROLE_SUPPORTING_STAFF, expected_id=staff_id)
    feedback = services()["supporting_staff"].respond_feedback(staff_id, feedback_id, body().get("response"))
    return jsonify(feedback.to_dict())
