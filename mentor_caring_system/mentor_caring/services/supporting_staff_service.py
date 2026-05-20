from __future__ import annotations

from mentor_caring.services.base import BaseService
from mentor_caring.services.utils import require_non_blank
from mentor_caring.models import ROLE_SUPPORTING_STAFF


class SupportingStaffService(BaseService):
    def _staff(self, staff_id: str):
        staff_id = require_non_blank(staff_id, "staff_id")
        staff = self.store.supporting_staff.require(staff_id, "supporting staff")
        user = self.store.users.require(staff.user_id or staff.staff_id, "user")
        if user.role != ROLE_SUPPORTING_STAFF:
            raise PermissionError("only supporting staff can perform this operation")
        return staff

    def view_all_student_logs(self, staff_id: str):
        self._staff(staff_id)
        return list(self.store.logs.all())

    def respond_feedback(self, staff_id: str, feedback_id: str, response: str):
        self._staff(staff_id)
        feedback = self.store.feedback.require(require_non_blank(feedback_id, "feedback_id"), "feedback")
        response = require_non_blank(response, "response")
        feedback.respond(response)
        self.log(staff_id, "respond feedback", f"Responded {feedback_id}", student_id=feedback.student_id)
        return feedback
