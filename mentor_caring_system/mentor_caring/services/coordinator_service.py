from __future__ import annotations

from mentor_caring.services.base import BaseService
from mentor_caring.services.message_service import MessageService
from mentor_caring.services.utils import require_non_blank


class MCPCoordinatorService(BaseService):
    def _coordinator(self, coordinator_id: str):
        coordinator_id = require_non_blank(coordinator_id, "coordinator_id")
        return self.store.coordinators.require(coordinator_id, "coordinator")

    def search_students_in_department(self, coordinator_id: str, keyword: str | None = None):
        coord = self._coordinator(coordinator_id)
        students = [s for s in self.store.students.all() if s.department_name == coord.department_name]
        if keyword:
            students = [s for s in students if keyword.lower() in s.name.lower() or keyword in s.student_id]
        return students

    def search_mentors_in_department(self, coordinator_id: str, keyword: str | None = None):
        coord = self._coordinator(coordinator_id)
        mentors = [m for m in self.store.mentors.all() if m.department_name == coord.department_name]
        if keyword:
            mentors = [m for m in mentors if keyword.lower() in m.name.lower() or keyword.lower() in m.email.lower()]
        return mentors

    def search_student_information(self, coordinator_id: str, student_id: str):
        coord = self._coordinator(coordinator_id)
        student = self.store.students.require(require_non_blank(student_id, "student_id"), "student")
        if student.department_name != coord.department_name:
            raise PermissionError("coordinator can access only own department students")
        records = [r.to_dict() for r in self.store.records.all() if r.student_id == student.student_id]
        data = student.to_dict()
        data["records"] = records
        self.log(coordinator_id, "search student information", f"Searched {student_id}", student_id=student_id)
        return data

    def search_mentor_information(self, coordinator_id: str, keyword: str | None = None, group_id: str | None = None):
        mentors = self.search_mentors_in_department(coordinator_id, keyword)
        results = []
        for mentor in mentors:
            groups = [g for g in self.store.groups.all() if g.mentor_id == mentor.mentor_id]
            if group_id:
                groups = [g for g in groups if g.group_id == group_id]
            if groups or not group_id:
                results.append({
                    "mentor": mentor.to_dict(),
                    "groups": [{"group_id": group.group_id, "student_ids": group.student_ids} for group in groups],
                })
        return results

    def forward_special_case_to_faculty_consultant(self, coordinator_id: str, student_id: str, consultant_id: str, description: str):
        coord = self._coordinator(coordinator_id)
        student = self.store.students.require(student_id, "student")
        if student.department_name != coord.department_name:
            raise PermissionError("coordinator can forward only own department cases")
        consultant = self.store.faculty_consultants.require(consultant_id, "faculty consultant")
        if consultant.faculty_name != student.faculty_name:
            raise PermissionError("consultant faculty mismatch")
        return MessageService(self.store).send_message(
            sender_id=coordinator_id,
            receiver_ids=[consultant_id],
            content=require_non_blank(description, "description"),
            message_type="special_case",
            related_student_id=student_id,
        )
