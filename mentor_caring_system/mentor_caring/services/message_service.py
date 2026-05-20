from __future__ import annotations

from mentor_caring.models import Message
from mentor_caring.services.base import BaseService
from mentor_caring.services.utils import require_non_blank


class MessageService(BaseService):
    def send_message(
        self,
        sender_id: str,
        receiver_ids: list[str],
        content: str,
        message_type: str = "normal",
        attachment: str | None = None,
        related_student_id: str | None = None,
    ) -> Message:
        sender_id = require_non_blank(sender_id, "sender_id")
        self.store.users.require(sender_id, "sender")
        if not receiver_ids:
            raise ValueError("receiver_ids is required")
        clean_receivers = [require_non_blank(rid, "receiver_id") for rid in receiver_ids]
        for receiver_id in clean_receivers:
            self.store.users.require(receiver_id, "receiver")
        content = require_non_blank(content, "content")
        if len(content) > 1000:
            raise ValueError("message content cannot exceed 1000 characters")
        message = Message(
            message_id=self.store.next_id("MSG"),
            sender_id=sender_id,
            receiver_ids=clean_receivers,
            content=content,
            message_type=message_type or "normal",
            attachment=attachment,
            related_student_id=related_student_id,
        )
        self.store.messages.add(message.message_id, message)
        for receiver_id in clean_receivers:
            self.notify(receiver_id, f"New message from {sender_id}", "message", message.message_id)
        self.log(sender_id, "send message", f"Sent message {message.message_id}", student_id=related_student_id)
        return message

    def respond_message(self, receiver_id: str, message_id: str, content: str) -> Message:
        receiver_id = require_non_blank(receiver_id, "receiver_id")
        self.store.users.require(receiver_id, "receiver")
        message_id = require_non_blank(message_id, "message_id")
        original = self.store.messages.require(message_id, "message")
        if receiver_id not in original.receiver_ids:
            raise PermissionError("receiver is not allowed to respond to this message")
        content = require_non_blank(content, "content")
        original.mark_responded()
        reply = Message(
            message_id=self.store.next_id("MSG"),
            sender_id=receiver_id,
            receiver_ids=[original.sender_id],
            content=content,
            message_type="normal",
            related_student_id=original.related_student_id,
        )
        self.store.messages.add(reply.message_id, reply)
        self.notify(original.sender_id, f"Reply from {receiver_id}", "message", reply.message_id)
        self.log(receiver_id, "respond message", f"Responded to {message_id}", student_id=original.related_student_id)
        return reply

    def get_inbox(self, user_id: str) -> list[Message]:
        user_id = require_non_blank(user_id, "user_id")
        self.store.users.require(user_id, "user")
        return [m for m in self.store.messages.all() if user_id in m.receiver_ids]

    def get_sent_messages(self, user_id: str) -> list[Message]:
        user_id = require_non_blank(user_id, "user_id")
        self.store.users.require(user_id, "user")
        return [m for m in self.store.messages.all() if m.sender_id == user_id]

    def search_recipients(self, sender_id: str, keyword: str | None = None) -> list[dict]:
        sender = self.store.users.require(require_non_blank(sender_id, "sender_id"), "sender")
        keyword = (keyword or "").strip().lower()
        users = []
        for user in self.store.users.all():
            if user.id == sender.id:
                continue
            if keyword and keyword not in user.name.lower() and keyword not in user.account.lower() and keyword not in user.email.lower():
                continue
            users.append(user.public_dict() if hasattr(user, "public_dict") else user.to_dict())
        return users
