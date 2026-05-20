from __future__ import annotations

from mentor_caring.models import LogActivity, Notification, now_iso
from mentor_caring.repositories import InMemoryStore
from mentor_caring.services.utils import require_non_blank


class BaseService:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def log(self, user_id: str, function_access: str, data: str, student_id: str | None = None) -> LogActivity:
        log = LogActivity(
            log_id=self.store.next_id("LOG"),
            user_id=user_id,
            student_id=student_id,
            time=now_iso(),
            data=data,
            function_access=function_access,
        )
        self.store.logs.add(log.log_id, log)
        return log

    def notify(self, receiver_id: str, content: str, source_type: str, source_id: str) -> Notification:
        notification = Notification(
            notification_id=self.store.next_id("NTF"),
            receiver_id=receiver_id,
            content=content,
            source_type=source_type,
            source_id=source_id,
        )
        self.store.notifications.add(notification.notification_id, notification)
        return notification

    def require_user_role(self, user_id: str, *roles: str):
        user_id = require_non_blank(user_id, "user_id")
        user = self.store.users.require(user_id, "user")
        if roles and user.role not in roles:
            allowed = ", ".join(roles)
            raise PermissionError(f"user must have one of roles: {allowed}")
        return user

    def public_user(self, user_id: str) -> dict:
        user = self.store.users.require(require_non_blank(user_id, "user_id"), "user")
        return user.public_dict() if hasattr(user, "public_dict") else user.to_dict()
