from __future__ import annotations

import json
import os
import secrets
import tempfile
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

frontend_bp = Blueprint("frontend", __name__)

ROLE_DASHBOARDS = {
    "administrator": "frontend.admin_dashboard",
    "faculty_consultant": "frontend.faculty_consultant_dashboard",
    "mentor": "frontend.mentor_dashboard",
    "student": "frontend.student_dashboard",
    "mcp_coordinator": "frontend.coordinator_dashboard",
    "supporting_staff": "frontend.supporting_staff_dashboard",
    "unassigned_staff": "frontend.unassigned_staff_dashboard",
}


def store():
    return current_app.config["store"]


def services():
    return current_app.config["services"]


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return store().users.get(uid)


@frontend_bp.before_app_request
def protect_frontend_forms():
    if request.blueprint == "api" or request.method != "POST":
        return None
    if not current_app.config.get("CSRF_ENABLED", True):
        return None
    token = session.setdefault("csrf_token", secrets.token_urlsafe(32))
    if request.form.get("csrf_token") != token:
        raise PermissionError("Invalid form token")
    return None


@frontend_bp.app_context_processor
def inject_csrf_token():
    def csrf_token():
        return session.setdefault("csrf_token", secrets.token_urlsafe(32))

    return {"csrf_token": csrf_token}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            flash("Please login first.", "error")
            return redirect(url_for("frontend.login_page"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return redirect(url_for("frontend.login_page"))
            if user.role != role:
                flash("You are not allowed to access this page.", "error")
                return redirect(url_for(ROLE_DASHBOARDS.get(user.role, "frontend.login_page")))
            return fn(*args, **kwargs)
        return wrapper
    return deco


def parse_rows_from_form() -> list[dict]:
    text = request.form.get("rows", "").strip()
    if text:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
    return []


def uploaded_xlsx_path():
    file = request.files.get("xlsx_file")
    if not file or not file.filename:
        return None
    if not file.filename.lower().endswith(".xlsx"):
        raise ValueError("only .xlsx files are supported")
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    file.save(path)
    return path


def cleanup_upload(path: str | None) -> None:
    if path and os.path.exists(path):
        os.remove(path)


@frontend_bp.get("/")
def index():
    return redirect(url_for("frontend.login_page"))


@frontend_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        try:
            user = services()["auth"].login(request.form.get("account"), request.form.get("password"))
            session["user_id"] = user.id
            flash("Login successful.", "success")
            return redirect(url_for(ROLE_DASHBOARDS[user.role]))
        except Exception as exc:
            flash(str(exc), "error")
    return render_template("login.html", user=current_user())


@frontend_bp.get("/logout")
def logout_page():
    uid = session.get("user_id")
    if uid:
        services()["auth"].logout(uid)
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("frontend.login_page"))


@frontend_bp.get("/admin/dashboard")
@login_required
@role_required("administrator")
def admin_dashboard():
    s = store()
    stats = {
        "faculties": len(s.faculties.all()),
        "departments": len(s.departments.all()),
        "majors": len(s.majors.all()),
        "students": len(s.students.all()),
        "mentors": len(s.mentors.all()),
        "groups": len(s.groups.all()),
    }
    return render_template(
        "dashboard_admin.html",
        user=current_user(),
        stats=stats,
        faculties=s.faculties.all(),
        departments=s.departments.all(),
        majors=s.majors.all(),
        users=[u.public_dict() for u in s.users.all()],
        consultants=s.faculty_consultants.all(),
        supporting_staff=s.supporting_staff.all(),
    )


@frontend_bp.get("/faculty-consultant/dashboard")
@login_required
@role_required("faculty_consultant")
def faculty_consultant_dashboard():
    user = current_user()
    consultant = store().faculty_consultants.get(user.id)
    faculty_groups = [g for g in store().groups.all() if consultant and g.faculty_name == consultant.faculty_name]
    faculty_students = [s for s in store().students.all() if consultant and s.faculty_name == consultant.faculty_name]
    faculty_mentors = [m for m in store().mentors.all() if consultant and m.faculty_name == consultant.faculty_name]
    faculty_departments = [d for d in store().departments.all() if consultant and d.faculty_name == consultant.faculty_name]
    return render_template(
        "dashboard_faculty_consultant.html",
        user=user,
        consultant=consultant,
        groups=faculty_groups,
        students=faculty_students,
        mentors=faculty_mentors,
        departments=faculty_departments,
        coordinators=store().coordinators.all(),
    )


@frontend_bp.get("/mentor/dashboard")
@login_required
@role_required("mentor")
def mentor_dashboard():
    user = current_user()
    groups = [g for g in store().groups.all() if g.mentor_id == user.id]
    students = [store().students.get(sid) for g in groups for sid in g.student_ids]
    student_ids = {student.student_id for student in students if student}
    records = [record for record in store().records.all() if record.student_id in student_ids]
    return render_template("dashboard_mentor.html", user=user, groups=groups, students=students, records=records)


@frontend_bp.get("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard():
    user = current_user()
    info = services()["student"].get_student_information(user.id)
    return render_template("dashboard_student.html", user=user, info=info)


@frontend_bp.get("/coordinator/dashboard")
@login_required
@role_required("mcp_coordinator")
def coordinator_dashboard():
    user = current_user()
    students = services()["coordinator"].search_students_in_department(user.id)
    mentors = services()["coordinator"].search_mentors_in_department(user.id)
    return render_template("dashboard_coordinator.html", user=user, students=students, mentors=mentors)


@frontend_bp.get("/supporting-staff/dashboard")
@login_required
@role_required("supporting_staff")
def supporting_staff_dashboard():
    user = current_user()
    logs = services()["supporting_staff"].view_all_student_logs(user.id)
    return render_template("dashboard_supporting_staff.html", user=user, logs=logs, feedback_list=store().feedback.all())


@frontend_bp.get("/unassigned/dashboard")
@login_required
@role_required("unassigned_staff")
def unassigned_staff_dashboard():
    return render_template("records.html", user=current_user(), title="No Functional Role Assigned", rows=[{
        "message": "Please ask an administrator to assign Faculty Consultant, Mentor, Coordinator, or Supporting Staff permissions."
    }])


# Student pages
@frontend_bp.get("/student/mentor")
@login_required
@role_required("student")
def student_mentor_page():
    user = current_user()
    mentor = services()["student"].get_mentor_info_by_student_id(user.id)
    return render_template("records.html", user=user, title="My Mentor", rows=[mentor])


@frontend_bp.get("/student/records")
@login_required
@role_required("student")
def student_records_page():
    user = current_user()
    records = [r for r in store().records.all() if r.student_id == user.id]
    return render_template("records.html", user=user, title="My Interview Records", rows=[r.to_dict() for r in records])


@frontend_bp.get("/student/messages")
@login_required
@role_required("student")
def student_messages_page():
    user = current_user()
    return render_template("messages.html", user=user, inbox=services()["message"].get_inbox(user.id), sent=services()["message"].get_sent_messages(user.id), receivers=store().users.all())


@frontend_bp.post("/student/messages/send")
@login_required
@role_required("student")
def student_send_message():
    user = current_user()
    services()["student"].send_message(user.id, request.form.get("receiver_id"), request.form.get("content"))
    flash("Message sent.", "success")
    return redirect(url_for("frontend.student_messages_page"))


@frontend_bp.post("/student/messages/respond")
@login_required
@role_required("student")
def student_respond_message():
    user = current_user()
    services()["message"].respond_message(user.id, request.form.get("message_id"), request.form.get("content"))
    flash("Message responded.", "success")
    return redirect(url_for("frontend.student_messages_page"))


@frontend_bp.get("/student/appointments")
@login_required
@role_required("student")
def student_appointments_page():
    user = current_user()
    appointments = [a for a in store().appointments.all() if a.student_id == user.id]
    return render_template("appointments.html", user=user, appointments=appointments, role="student")


@frontend_bp.post("/student/appointments/book")
@login_required
@role_required("student")
def student_book_appointment():
    user = current_user()
    services()["appointment"].book_appointment(user.id, request.form.get("appointment_id"))
    flash("Appointment booked.", "success")
    return redirect(url_for("frontend.student_appointments_page"))


@frontend_bp.get("/student/feedback")
@login_required
@role_required("student")
def student_feedback_page():
    user = current_user()
    feedback_list = services()["student"].get_feedback_by_student(user.id)
    return render_template("feedback.html", user=user, feedback_list=feedback_list)


@frontend_bp.post("/student/feedback")
@login_required
@role_required("student")
def student_submit_feedback():
    user = current_user()
    services()["feedback"].submit_feedback(user.id, request.form.get("content"))
    flash("Feedback submitted.", "success")
    return redirect(url_for("frontend.student_feedback_page"))


@frontend_bp.get("/feedback")
@login_required
def feedback_page():
    user = current_user()
    feedback_list = services()["feedback"].get_feedback_by_user(user.id)
    return render_template("feedback.html", user=user, feedback_list=feedback_list)


@frontend_bp.post("/feedback")
@login_required
def submit_feedback_page():
    user = current_user()
    services()["feedback"].submit_feedback(user.id, request.form.get("content"))
    flash("Feedback submitted.", "success")
    return redirect(url_for("frontend.feedback_page"))


# Mentor pages
@frontend_bp.get("/mentor/groups")
@login_required
@role_required("mentor")
def mentor_groups_page():
    user = current_user()
    return render_template("records.html", user=user, title="My Groups", rows=[g.to_dict() for g in store().groups.all() if g.mentor_id == user.id])


@frontend_bp.get("/mentor/students")
@login_required
@role_required("mentor")
def mentor_students_page():
    user = current_user()
    groups = [g for g in store().groups.all() if g.mentor_id == user.id]
    rows = [store().students.get(sid).to_dict() for g in groups for sid in g.student_ids]
    return render_template("records.html", user=user, title="My Students", rows=rows)


@frontend_bp.get("/mentor/student-search")
@login_required
@role_required("mentor")
def mentor_student_search_page():
    user = current_user()
    student_id = request.args.get("student_id")
    data = None
    if student_id:
        student = services()["mentor"].search_student_by_id(user.id, student_id)
        records = [record.to_dict() for record in store().records.all() if record.student_id == student_id]
        data = dict(student)
        data["records"] = records
    return render_template("student_info.html", user=user, student_id=student_id, data=data, editable=True)


@frontend_bp.get("/mentor/students/<student_id>")
@login_required
@role_required("mentor")
def mentor_student_detail_page(student_id):
    user = current_user()
    data = services()["mentor"].search_student_by_id(user.id, student_id)
    return render_template("records.html", user=user, title="Student Detail", rows=[data])


@frontend_bp.post("/mentor/records/create")
@login_required
@role_required("mentor")
def mentor_record_create_page():
    user = current_user()
    services()["mentor"].create_interview_record(
        user.id, request.form.get("student_id"), request.form.get("date"), request.form.get("time"),
        request.form.get("problem_statement"), request.form.get("interview_summary"), request.form.get("follow_up_action")
    )
    flash("Record created.", "success")
    return redirect(url_for("frontend.mentor_dashboard"))


@frontend_bp.post("/mentor/records/<record_id>/update")
@login_required
@role_required("mentor")
def mentor_record_update_page(record_id):
    user = current_user()
    fields = {key: value for key, value in dict(request.form).items() if key != "csrf_token" and value.strip()}
    services()["mentor"].update_interview_record(user.id, record_id, fields)
    flash("Record updated.", "success")
    return redirect(url_for("frontend.mentor_dashboard"))


@frontend_bp.post("/mentor/records/<record_id>/delete")
@login_required
@role_required("mentor")
def mentor_record_delete_page(record_id):
    user = current_user()
    services()["mentor"].delete_interview_record(user.id, record_id)
    flash("Record deleted.", "success")
    return redirect(url_for("frontend.mentor_dashboard"))


@frontend_bp.get("/mentor/appointments")
@login_required
@role_required("mentor")
def mentor_appointments_page():
    user = current_user()
    appointments = [a for a in store().appointments.all() if a.mentor_id == user.id]
    return render_template("appointments.html", user=user, appointments=appointments, role="mentor")


@frontend_bp.post("/mentor/appointments/slots")
@login_required
@role_required("mentor")
def mentor_slots_page():
    user = current_user()
    services()["mentor"].create_available_slots(user.id, request.form.get("student_id"), request.form.get("date"), request.form.get("start_time"), request.form.get("end_time"))
    flash("Slots created.", "success")
    return redirect(url_for("frontend.mentor_appointments_page"))


@frontend_bp.post("/mentor/appointments/<appointment_id>/confirm")
@login_required
@role_required("mentor")
def mentor_confirm_page(appointment_id):
    user = current_user()
    services()["mentor"].confirm_appointment(user.id, appointment_id, request.form.get("venue"))
    flash("Appointment confirmed.", "success")
    return redirect(url_for("frontend.mentor_appointments_page"))


@frontend_bp.get("/mentor/messages")
@login_required
@role_required("mentor")
def mentor_messages_page():
    user = current_user()
    return render_template("messages.html", user=user, inbox=services()["message"].get_inbox(user.id), sent=services()["message"].get_sent_messages(user.id), receivers=store().users.all())


@frontend_bp.post("/mentor/messages/send")
@login_required
@role_required("mentor")
def mentor_messages_send_page():
    user = current_user()
    services()["message"].send_message(user.id, [request.form.get("receiver_id")], request.form.get("content"), related_student_id=request.form.get("related_student_id") or None)
    flash("Message sent.", "success")
    return redirect(url_for("frontend.mentor_messages_page"))


@frontend_bp.post("/mentor/messages/respond")
@login_required
@role_required("mentor")
def mentor_messages_respond_page():
    user = current_user()
    services()["message"].respond_message(user.id, request.form.get("message_id"), request.form.get("content"))
    flash("Message responded.", "success")
    return redirect(url_for("frontend.mentor_messages_page"))


@frontend_bp.post("/mentor/special-cases/forward")
@login_required
@role_required("mentor")
def mentor_special_case_page():
    user = current_user()
    services()["mentor"].forward_special_case_to_coordinator(user.id, request.form.get("student_id"), request.form.get("coordinator_id"), request.form.get("description"))
    flash("Special case forwarded.", "success")
    return redirect(url_for("frontend.mentor_dashboard"))


@frontend_bp.get("/mentor/export")
@login_required
@role_required("mentor")
def mentor_export_page():
    user = current_user()
    result = services()["mentor"].export_interview_records(user.id)
    flash(f"Export created: {result.file_path}", "success")
    return render_template("export.html", user=user, result=result.to_dict())


# Faculty consultant pages
@frontend_bp.get("/faculty-consultant/organization")
@login_required
@role_required("faculty_consultant")
def fc_org_page():
    return render_template("export.html", user=current_user(), result={"help": "Use POST form to import organization units."})


@frontend_bp.post("/faculty-consultant/organization/import")
@login_required
@role_required("faculty_consultant")
def fc_org_import_page():
    user = current_user()
    path = uploaded_xlsx_path()
    try:
        result = services()["faculty_consultant"].import_organization_units(rows=parse_rows_from_form(), xlsx_path=path, consultant_id=user.id)
    finally:
        cleanup_upload(path)
    flash(f"Organization imported: {result}", "success")
    return redirect(url_for("frontend.faculty_consultant_dashboard"))


@frontend_bp.get("/faculty-consultant/groups")
@login_required
@role_required("faculty_consultant")
def fc_groups_page():
    user = current_user()
    consultant = store().faculty_consultants.get(user.id)
    rows = [g.to_dict() for g in store().groups.all() if g.faculty_name == consultant.faculty_name]
    return render_template("records.html", user=user, title="Faculty Groups", rows=rows)


@frontend_bp.post("/faculty-consultant/students/import")
@login_required
@role_required("faculty_consultant")
def fc_students_import_page():
    user = current_user()
    path = uploaded_xlsx_path()
    try:
        result = services()["faculty_consultant"].import_students_and_mentors(user.id, rows=parse_rows_from_form(), academic_year=request.form.get("academic_year") or "2024-2025", xlsx_path=path)
    finally:
        cleanup_upload(path)
    flash(f"Students imported: {result}", "success")
    return redirect(url_for("frontend.faculty_consultant_dashboard"))


@frontend_bp.post("/faculty-consultant/coordinators/designate")
@login_required
@role_required("faculty_consultant")
def fc_designate_coordinator_page():
    user = current_user()
    services()["faculty_consultant"].designate_coordinator(user.id, request.form.get("department_name"), request.form.get("coordinator_id"))
    flash("Coordinator designated.", "success")
    return redirect(url_for("frontend.faculty_consultant_dashboard"))


@frontend_bp.post("/faculty-consultant/coordinators/import")
@login_required
@role_required("faculty_consultant")
def fc_import_coordinators_page():
    user = current_user()
    path = uploaded_xlsx_path()
    try:
        result = services()["faculty_consultant"].import_coordinators(user.id, rows=parse_rows_from_form(), xlsx_path=path)
    finally:
        cleanup_upload(path)
    flash(f"Coordinators imported: {result}", "success")
    return redirect(url_for("frontend.faculty_consultant_dashboard"))


@frontend_bp.post("/faculty-consultant/groups/<group_id>/mentor/change")
@login_required
@role_required("faculty_consultant")
def fc_change_mentor_page(group_id):
    user = current_user()
    services()["faculty_consultant"].change_mentor_of_group(user.id, group_id, request.form.get("new_mentor_id"))
    flash("Mentor changed.", "success")
    return redirect(url_for("frontend.fc_groups_page"))


@frontend_bp.post("/faculty-consultant/groups/<group_id>/students/add")
@login_required
@role_required("faculty_consultant")
def fc_group_add_student_page(group_id):
    user = current_user()
    services()["faculty_consultant"].add_student_to_group(user.id, request.form.get("student_id"), group_id)
    flash("Student added.", "success")
    return redirect(url_for("frontend.fc_groups_page"))


@frontend_bp.post("/faculty-consultant/groups/<group_id>/students/<student_id>/remove")
@login_required
@role_required("faculty_consultant")
def fc_group_remove_student_page(group_id, student_id):
    user = current_user()
    services()["faculty_consultant"].remove_student_from_group(user.id, student_id, group_id)
    flash("Student removed but data kept.", "success")
    return redirect(url_for("frontend.fc_groups_page"))


@frontend_bp.get("/faculty-consultant/students/search")
@login_required
@role_required("faculty_consultant")
def fc_student_search_page():
    user = current_user()
    student_id = request.args.get("student_id")
    data = None
    if student_id:
        data = services()["faculty_consultant"].search_student_information(user.id, student_id)
    return render_template("student_info.html", user=user, student_id=student_id, data=data, editable=False)


@frontend_bp.get("/faculty-consultant/mentors/search")
@login_required
@role_required("faculty_consultant")
def fc_mentor_search_page():
    user = current_user()
    rows = services()["faculty_consultant"].search_mentor_information(user.id, keyword=request.args.get("keyword"), email=request.args.get("email"), group_id=request.args.get("group_id"))
    return render_template("records.html", user=user, title="Search Mentors", rows=rows)


@frontend_bp.get("/faculty-consultant/logs")
@login_required
@role_required("faculty_consultant")
def fc_logs_page():
    user = current_user()
    logs = services()["faculty_consultant"].view_student_logs(user.id, request.args.get("student_id"))
    return render_template("logs.html", user=user, logs=logs)


@frontend_bp.get("/faculty-consultant/messages")
@login_required
@role_required("faculty_consultant")
def fc_messages_page():
    user = current_user()
    return render_template("messages.html", user=user, inbox=services()["message"].get_inbox(user.id), sent=services()["message"].get_sent_messages(user.id), receivers=store().users.all())


@frontend_bp.post("/faculty-consultant/messages/send")
@login_required
@role_required("faculty_consultant")
def fc_send_message_page():
    user = current_user()
    services()["message"].send_message(user.id, [request.form.get("receiver_id")], request.form.get("content"), related_student_id=request.form.get("related_student_id") or None)
    flash("Message sent.", "success")
    return redirect(url_for("frontend.fc_messages_page"))


@frontend_bp.post("/faculty-consultant/messages/respond")
@login_required
@role_required("faculty_consultant")
def fc_respond_message_page():
    user = current_user()
    services()["message"].respond_message(user.id, request.form.get("message_id"), request.form.get("content"))
    flash("Message responded.", "success")
    return redirect(url_for("frontend.fc_messages_page"))


@frontend_bp.get("/faculty-consultant/export")
@login_required
@role_required("faculty_consultant")
def fc_export_page():
    return render_template("export.html", user=current_user(), result={"message": "Use the export form on dashboard."})


@frontend_bp.post("/faculty-consultant/export")
@login_required
@role_required("faculty_consultant")
def fc_export_post_page():
    user = current_user()
    result = services()["faculty_consultant"].export_information_to_word(user.id, department_name=request.form.get("department_name") or None, major_name=request.form.get("major_name") or None, student_name=request.form.get("student_name") or None)
    flash("Export created.", "success")
    return render_template("export.html", user=user, result=result)


# Administrator pages
@frontend_bp.get("/admin/organization")
@login_required
@role_required("administrator")
def admin_org_page():
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.post("/admin/organization/import")
@login_required
@role_required("administrator")
def admin_org_import_page():
    user = current_user()
    path = uploaded_xlsx_path()
    try:
        result = services()["admin"].import_organization_units(user.id, rows=parse_rows_from_form(), xlsx_path=path)
    finally:
        cleanup_upload(path)
    flash(f"Organization imported: {result}", "success")
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.post("/admin/organization/faculties/add")
@login_required
@role_required("administrator")
def admin_faculty_add_page():
    services()["admin"].add_faculty(current_user().id, request.form.get("faculty_name"))
    flash("Faculty added.", "success")
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.post("/admin/organization/departments/add")
@login_required
@role_required("administrator")
def admin_department_add_page():
    services()["admin"].add_department(current_user().id, request.form.get("faculty_name"), request.form.get("department_name"))
    flash("Department added.", "success")
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.post("/admin/organization/majors/add")
@login_required
@role_required("administrator")
def admin_major_add_page():
    services()["admin"].add_major(current_user().id, request.form.get("faculty_name"), request.form.get("department_name"), request.form.get("major_name"))
    flash("Major added.", "success")
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.post("/admin/users/create")
@login_required
@role_required("administrator")
def admin_user_create_page():
    user = current_user()
    services()["admin"].create_user(
        user.id,
        request.form.get("user_id"),
        request.form.get("name"),
        request.form.get("account"),
        request.form.get("email"),
        request.form.get("role"),
        request.form.get("password"),
        is_staff=request.form.get("is_staff") == "on",
        faculty_name=request.form.get("faculty_name") or None,
        department_name=request.form.get("department_name") or None,
    )
    flash("User created.", "success")
    return redirect(url_for("frontend.admin_dashboard"))


@frontend_bp.get("/admin/faculty-consultants")
@login_required
@role_required("administrator")
def admin_fc_page():
    return render_template("records.html", user=current_user(), title="Faculty Consultants", rows=[c.to_dict() for c in store().faculty_consultants.all()])


@frontend_bp.post("/admin/faculty-consultants/add")
@login_required
@role_required("administrator")
def admin_fc_add_page():
    user = current_user()
    services()["admin"].add_faculty_consultant(user.id, request.form.get("user_id"), request.form.get("faculty_name"))
    flash("Faculty consultant added.", "success")
    return redirect(url_for("frontend.admin_fc_page"))


@frontend_bp.post("/admin/faculty-consultants/change")
@login_required
@role_required("administrator")
def admin_fc_change_page():
    user = current_user()
    services()["admin"].change_faculty_consultant(user.id, request.form.get("faculty_name"), request.form.get("new_user_id"))
    flash("Faculty consultant changed.", "success")
    return redirect(url_for("frontend.admin_fc_page"))


@frontend_bp.post("/admin/faculty-consultants/delete")
@login_required
@role_required("administrator")
def admin_fc_delete_page():
    user = current_user()
    services()["admin"].delete_faculty_consultant(user.id, request.form.get("faculty_name"), request.form.get("consultant_id"))
    flash("Faculty consultant deleted.", "success")
    return redirect(url_for("frontend.admin_fc_page"))


@frontend_bp.get("/admin/supporting-staff")
@login_required
@role_required("administrator")
def admin_staff_page():
    return render_template("records.html", user=current_user(), title="Supporting Staff", rows=[s.to_dict() for s in store().supporting_staff.all()])


@frontend_bp.post("/admin/supporting-staff/create")
@login_required
@role_required("administrator")
def admin_staff_create_page():
    user = current_user()
    services()["admin"].create_supporting_staff(user.id, request.form.get("user_id"))
    flash("Supporting staff created.", "success")
    return redirect(url_for("frontend.admin_staff_page"))


@frontend_bp.post("/admin/supporting-staff/delete")
@login_required
@role_required("administrator")
def admin_staff_delete_page():
    user = current_user()
    services()["admin"].delete_supporting_staff(user.id, request.form.get("staff_id"))
    flash("Supporting staff deleted.", "success")
    return redirect(url_for("frontend.admin_staff_page"))


# Coordinator pages
@frontend_bp.get("/coordinator/students")
@login_required
@role_required("mcp_coordinator")
def coord_students_page():
    user = current_user()
    return render_template("records.html", user=user, title="Department Students", rows=[s.to_dict() for s in services()["coordinator"].search_students_in_department(user.id, request.args.get("keyword"))])


@frontend_bp.get("/coordinator/student-search")
@login_required
@role_required("mcp_coordinator")
def coord_student_search_page():
    user = current_user()
    student_id = request.args.get("student_id")
    data = None
    if student_id:
        data = services()["coordinator"].search_student_information(user.id, student_id)
    return render_template("student_info.html", user=user, student_id=student_id, data=data, editable=False)


@frontend_bp.get("/coordinator/mentors")
@login_required
@role_required("mcp_coordinator")
def coord_mentors_page():
    user = current_user()
    return render_template("records.html", user=user, title="Department Mentors", rows=[m.to_dict() for m in services()["coordinator"].search_mentors_in_department(user.id, request.args.get("keyword"))])


@frontend_bp.get("/coordinator/messages")
@login_required
@role_required("mcp_coordinator")
def coord_messages_page():
    user = current_user()
    return render_template("messages.html", user=user, inbox=services()["message"].get_inbox(user.id), sent=services()["message"].get_sent_messages(user.id), receivers=store().users.all())


@frontend_bp.post("/coordinator/messages/send")
@login_required
@role_required("mcp_coordinator")
def coord_messages_send_page():
    user = current_user()
    services()["message"].send_message(user.id, [request.form.get("receiver_id")], request.form.get("content"), related_student_id=request.form.get("related_student_id") or None)
    flash("Message sent.", "success")
    return redirect(url_for("frontend.coord_messages_page"))


@frontend_bp.post("/coordinator/messages/respond")
@login_required
@role_required("mcp_coordinator")
def coord_messages_respond_page():
    user = current_user()
    services()["message"].respond_message(user.id, request.form.get("message_id"), request.form.get("content"))
    flash("Message responded.", "success")
    return redirect(url_for("frontend.coord_messages_page"))


@frontend_bp.get("/coordinator/special-cases")
@login_required
@role_required("mcp_coordinator")
def coord_special_cases_page():
    user = current_user()
    msgs = [m for m in services()["message"].get_inbox(user.id) if m.message_type == "special_case"]
    return render_template("messages.html", user=user, inbox=msgs, sent=[], receivers=store().users.all())


@frontend_bp.post("/coordinator/special-cases/forward")
@login_required
@role_required("mcp_coordinator")
def coord_special_forward_page():
    user = current_user()
    services()["coordinator"].forward_special_case_to_faculty_consultant(user.id, request.form.get("student_id"), request.form.get("consultant_id"), request.form.get("description"))
    flash("Special case forwarded.", "success")
    return redirect(url_for("frontend.coord_special_cases_page"))


# Supporting staff pages
@frontend_bp.get("/supporting-staff/logs")
@login_required
@role_required("supporting_staff")
def staff_logs_page():
    user = current_user()
    logs = services()["supporting_staff"].view_all_student_logs(user.id)
    student_id = request.args.get("student_id")
    function_access = request.args.get("function_access")
    if student_id:
        logs = [l for l in logs if l.student_id == student_id]
    if function_access:
        logs = [l for l in logs if function_access.lower() in l.function_access.lower()]
    return render_template("logs.html", user=user, logs=logs)


@frontend_bp.get("/supporting-staff/feedback")
@login_required
@role_required("supporting_staff")
def staff_feedback_page():
    return render_template("feedback.html", user=current_user(), feedback_list=store().feedback.all(), staff_mode=True)


@frontend_bp.post("/supporting-staff/feedback/<feedback_id>/respond")
@login_required
@role_required("supporting_staff")
def staff_feedback_respond_page(feedback_id):
    user = current_user()
    services()["supporting_staff"].respond_feedback(user.id, feedback_id, request.form.get("response"))
    flash("Feedback responded.", "success")
    return redirect(url_for("frontend.staff_feedback_page"))
