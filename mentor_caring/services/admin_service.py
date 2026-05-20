from __future__ import annotations

from mentor_caring.models import (
    Department,
    Faculty,
    FacultyConsultant,
    Major,
    ROLE_ADMIN,
    ROLE_COORDINATOR,
    ROLE_FACULTY_CONSULTANT,
    ROLE_MENTOR,
    ROLE_STUDENT,
    ROLE_SUPPORTING_STAFF,
    ROLE_UNASSIGNED_STAFF,
    SupportingStaff,
    User,
    make_password,
)
from mentor_caring.services.base import BaseService
from mentor_caring.services.faculty_consultant_service import FacultyConsultantService
from mentor_caring.services.utils import require_non_blank


class AdministratorService(BaseService):
    def _assert_admin(self, admin_id: str):
        admin = self.store.users.require(require_non_blank(admin_id, "admin_id"), "admin")
        if admin.role != ROLE_ADMIN:
            raise PermissionError("only administrator can perform this operation")
        return admin

    def _restore_role_after_assignment_removed(self, user: User) -> None:
        if self.store.supporting_staff.exists(user.id):
            user.role = ROLE_SUPPORTING_STAFF
        elif self.store.mentors.exists(user.id):
            user.role = ROLE_MENTOR
        elif self.store.coordinators.exists(user.id):
            user.role = ROLE_COORDINATOR
        elif self.store.students.exists(user.id):
            user.role = ROLE_STUDENT
        elif user.is_staff:
            user.role = ROLE_UNASSIGNED_STAFF
        else:
            user.role = ROLE_STUDENT

    def search_users(self, admin_id: str, keyword: str | None = None, role: str | None = None, staff_only: bool | None = None):
        self._assert_admin(admin_id)
        keyword = (keyword or "").strip().lower()
        users = list(self.store.users.all())
        if keyword:
            users = [
                user for user in users
                if keyword in user.id.lower()
                or keyword in user.name.lower()
                or keyword in user.account.lower()
                or keyword in user.email.lower()
            ]
        if role:
            users = [user for user in users if user.role == role]
        if staff_only is not None:
            users = [user for user in users if user.is_staff is staff_only]
        return [user.public_dict() for user in users]

    def create_user(
        self,
        admin_id: str,
        user_id: str,
        name: str,
        account: str,
        email: str,
        role: str,
        password: str,
        is_staff: bool = False,
        faculty_name: str | None = None,
        department_name: str | None = None,
    ) -> User:
        self._assert_admin(admin_id)
        user_id = require_non_blank(user_id, "user_id")
        if self.store.users.exists(user_id):
            raise ValueError(f"user already exists: {user_id}")
        role = require_non_blank(role, "role")
        user = User(
            id=user_id,
            name=require_non_blank(name, "name"),
            account=require_non_blank(account, "account"),
            password_hash=make_password(require_non_blank(password, "password")),
            role=role,
            email=require_non_blank(email, "email"),
            is_staff=bool(is_staff),
            faculty_name=faculty_name or None,
            department_name=department_name or None,
        )
        self.store.users.add(user.id, user)
        self.log(admin_id, "create user", f"Created user {user.id}")
        return user

    def add_faculty(self, admin_id: str, faculty_name: str) -> Faculty:
        self._assert_admin(admin_id)
        faculty_name = require_non_blank(faculty_name, "faculty_name")
        if self.store.faculties.exists(faculty_name):
            raise ValueError(f"faculty already exists: {faculty_name}")
        faculty = Faculty(name=faculty_name)
        self.store.faculties.add(faculty_name, faculty)
        self.log(admin_id, "add faculty", f"Added {faculty_name}")
        return faculty

    def delete_faculty(self, admin_id: str, faculty_name: str) -> dict:
        self._assert_admin(admin_id)
        faculty_name = require_non_blank(faculty_name, "faculty_name")
        faculty = self.store.faculties.require(faculty_name, "faculty")
        if faculty.departments:
            raise ValueError("cannot delete faculty with departments")
        self.store.faculties.remove(faculty_name)
        self.log(admin_id, "delete faculty", f"Deleted {faculty_name}")
        return {"deleted": faculty_name}

    def add_department(self, admin_id: str, faculty_name: str, department_name: str) -> Department:
        self._assert_admin(admin_id)
        faculty = self.store.faculties.require(require_non_blank(faculty_name, "faculty_name"), "faculty")
        department_name = require_non_blank(department_name, "department_name")
        if self.store.departments.exists(department_name):
            raise ValueError(f"department already exists: {department_name}")
        department = Department(name=department_name, faculty_name=faculty.name)
        self.store.departments.add(department_name, department)
        if department_name not in faculty.departments:
            faculty.departments.append(department_name)
        self.log(admin_id, "add department", f"Added {department_name} to {faculty.name}")
        return department

    def delete_department(self, admin_id: str, department_name: str) -> dict:
        self._assert_admin(admin_id)
        department_name = require_non_blank(department_name, "department_name")
        department = self.store.departments.require(department_name, "department")
        if department.majors:
            raise ValueError("cannot delete department with majors")
        faculty = self.store.faculties.get(department.faculty_name)
        if faculty and department_name in faculty.departments:
            faculty.departments.remove(department_name)
        self.store.departments.remove(department_name)
        self.log(admin_id, "delete department", f"Deleted {department_name}")
        return {"deleted": department_name}

    def add_major(self, admin_id: str, faculty_name: str, department_name: str, major_name: str) -> Major:
        self._assert_admin(admin_id)
        department = self.store.departments.require(require_non_blank(department_name, "department_name"), "department")
        faculty_name = require_non_blank(faculty_name, "faculty_name")
        if department.faculty_name != faculty_name:
            raise PermissionError("department faculty mismatch")
        major_name = require_non_blank(major_name, "major_name")
        if self.store.majors.exists(major_name):
            raise ValueError(f"major already exists: {major_name}")
        major = Major(name=major_name, department_name=department.name, faculty_name=faculty_name)
        self.store.majors.add(major_name, major)
        if major_name not in department.majors:
            department.majors.append(major_name)
        self.log(admin_id, "add major", f"Added {major_name}")
        return major

    def delete_major(self, admin_id: str, major_name: str) -> dict:
        self._assert_admin(admin_id)
        major_name = require_non_blank(major_name, "major_name")
        major = self.store.majors.require(major_name, "major")
        department = self.store.departments.get(major.department_name)
        if department and major_name in department.majors:
            department.majors.remove(major_name)
        self.store.majors.remove(major_name)
        self.log(admin_id, "delete major", f"Deleted {major_name}")
        return {"deleted": major_name}

    def add_faculty_consultant(self, admin_id: str, user_id: str, faculty_name: str):
        self._assert_admin(admin_id)
        user = self.store.users.require(require_non_blank(user_id, "user_id"), "user")
        faculty_name = require_non_blank(faculty_name, "faculty_name")
        self.store.faculties.require(faculty_name, "faculty")
        if not user.is_staff:
            raise ValueError("faculty consultant must be staff")
        if user.role in {ROLE_ADMIN, ROLE_SUPPORTING_STAFF}:
            raise ValueError("administrator and supporting staff cannot become faculty consultant")
        user.role = ROLE_FACULTY_CONSULTANT
        user.faculty_name = faculty_name
        consultant = FacultyConsultant(
            consultant_id=user.id,
            name=user.name,
            email=user.email,
            faculty_name=faculty_name,
            user_id=user.id,
        )
        self.store.faculty_consultants.add(user.id, consultant)
        self.log(admin_id, "add faculty consultant", f"Added {user_id} for {faculty_name}")
        return consultant

    def change_faculty_consultant(self, admin_id: str, faculty_name: str, new_user_id: str):
        self._assert_admin(admin_id)
        faculty_name = require_non_blank(faculty_name, "faculty_name")
        new = self.add_faculty_consultant(admin_id, new_user_id, faculty_name)
        return new

    def delete_faculty_consultant(self, admin_id: str, faculty_name: str, consultant_id: str):
        self._assert_admin(admin_id)
        consultant = self.store.faculty_consultants.require(consultant_id, "faculty consultant")
        if consultant.faculty_name != faculty_name:
            raise PermissionError("faculty mismatch")
        self.store.faculty_consultants.remove(consultant_id)
        user = self.store.users.get(consultant_id)
        if user:
            self._restore_role_after_assignment_removed(user)
        self.log(admin_id, "delete faculty consultant", f"Deleted {consultant_id}")
        return {"deleted": consultant_id}

    def create_supporting_staff(self, admin_id: str, user_id: str):
        self._assert_admin(admin_id)
        user = self.store.users.require(require_non_blank(user_id, "user_id"), "user")
        if not user.is_staff:
            raise ValueError("supporting staff must be staff")
        user.role = ROLE_SUPPORTING_STAFF
        staff = SupportingStaff(staff_id=user.id, name=user.name, email=user.email, user_id=user.id)
        self.store.supporting_staff.add(user.id, staff)
        self.log(admin_id, "create supporting staff", f"Created {user_id}")
        return staff

    def delete_supporting_staff(self, admin_id: str, staff_id: str):
        self._assert_admin(admin_id)
        staff_id = require_non_blank(staff_id, "staff_id")
        self.store.supporting_staff.require(staff_id, "supporting staff")
        self.store.supporting_staff.remove(staff_id)
        user = self.store.users.get(staff_id)
        if user:
            self._restore_role_after_assignment_removed(user)
        self.log(admin_id, "delete supporting staff", f"Deleted {staff_id}")
        return {"deleted": staff_id}

    def import_organization_units(self, admin_id: str, rows: list[dict] | None = None, xlsx_path: str | None = None):
        self._assert_admin(admin_id)
        result = FacultyConsultantService(self.store).import_organization_units(rows=rows, xlsx_path=xlsx_path)
        self.log(admin_id, "import organization", str(result))
        return result
