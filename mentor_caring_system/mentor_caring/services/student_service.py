from __future__ import annotations

from mentor_caring.models import Feedback, Message
from mentor_caring.services.base import BaseService
from mentor_caring.services.feedback_service import FeedbackService
from mentor_caring.services.message_service import MessageService
from mentor_caring.services.utils import require_non_blank


class StudentService(BaseService):
    def get_mentor_info_by_student_id(self, student_id: str) -> dict:
        student_id = require_non_blank(student_id, "student_id")
        student = self.store.students.require(student_id, "student")
        if not student.group_id:
            raise LookupError("student has no group_id")
        group = self.store.groups.require(student.group_id, "MCP group")
        if not group.mentor_id:
            raise LookupError("group has no mentor")
        mentor = self.store.mentors.require(group.mentor_id, "mentor")
        self.log(student_id, "get mentor information", f"Student {student_id} viewed mentor", student_id=student_id)
        return {
            "mentor_id": mentor.mentor_id,
            "name": mentor.name,
            "email": mentor.email,
            "office": mentor.office,
        }

    def submit_feedback(self, student_id: str, content: str) -> Feedback:
        student_id = require_non_blank(student_id, "student_id")
        self.store.students.require(student_id, "student")
        return FeedbackService(self.store).submit_feedback(student_id, content)

    def get_feedback_by_student(self, student_id: str) -> list[Feedback]:
        student_id = require_non_blank(student_id, "student_id")
        self.store.students.require(student_id, "student")
        return [f for f in self.store.feedback.all() if f.student_id == student_id or f.user_id == student_id]

    def get_student_information(self, student_id: str) -> dict:
        student_id = require_non_blank(student_id, "student_id")
        student = self.store.students.require(student_id, "student")
        mentor_info = None
        try:
            mentor_info = self.get_mentor_info_by_student_id(student_id)
        except LookupError:
            mentor_info = None
        records = [r.to_dict() for r in self.store.records.all() if r.student_id == student_id]
        return {
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "status": student.status,
            "group_id": student.group_id,
            "faculty_name": student.faculty_name,
            "department_name": student.department_name,
            "major_name": student.major_name,
            "mentor": mentor_info,
            "interview_records": records,
        }

    def send_message(self, student_id: str, receiver_id: str, content: str) -> Message:
        student_id = require_non_blank(student_id, "student_id")
        self.store.students.require(student_id, "student")
        receiver_id = require_non_blank(receiver_id, "receiver_id")
        content = require_non_blank(content, "content")
        if len(content) > 300:
            raise ValueError("message content cannot exceed 300 characters")
        return MessageService(self.store).send_message(
            sender_id=student_id,
            receiver_ids=[receiver_id],
            content=content,
            related_student_id=student_id,
        )
