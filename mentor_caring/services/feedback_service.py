from __future__ import annotations

from mentor_caring.models import Feedback, ROLE_STUDENT
from mentor_caring.services.base import BaseService
from mentor_caring.services.utils import require_non_blank


class FeedbackService(BaseService):
    def submit_feedback(self, user_id: str, content: str) -> Feedback:
        user_id = require_non_blank(user_id, "user_id")
        user = self.store.users.require(user_id, "user")
        content = require_non_blank(content, "content")
        if len(content) > 500:
            raise ValueError("feedback content cannot exceed 500 characters")
        feedback = Feedback(
            feedback_id=self.store.next_id("FDB"),
            student_id=user.id if user.role == ROLE_STUDENT else None,
            user_id=user.id,
            user_role=user.role,
            content=content,
        )
        self.store.feedback.add(feedback.feedback_id, feedback)
        self.log(user.id, "submit feedback", f"Submitted feedback {feedback.feedback_id}", student_id=feedback.student_id)
        return feedback

    def get_feedback_by_user(self, user_id: str) -> list[Feedback]:
        user_id = require_non_blank(user_id, "user_id")
        self.store.users.require(user_id, "user")
        return [item for item in self.store.feedback.all() if item.user_id == user_id or item.student_id == user_id]

    def list_feedback(self, status: str | None = None) -> list[Feedback]:
        feedback = list(self.store.feedback.all())
        if status:
            feedback = [item for item in feedback if item.status == status]
        return feedback
