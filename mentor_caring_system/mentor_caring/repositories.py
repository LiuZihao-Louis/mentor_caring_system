from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, TypeVar

T = TypeVar("T")


class Table:
    def __init__(self, name: str):
        self.name = name
        self.items: Dict[str, Any] = {}

    def add(self, key: str, value: Any) -> Any:
        self.items[str(key)] = value
        return value

    def get(self, key: Optional[str]) -> Any:
        if key is None:
            return None
        return self.items.get(str(key))

    def require(self, key: str, label: Optional[str] = None) -> Any:
        item = self.get(key)
        if item is None:
            raise LookupError(f"{label or self.name} not found: {key}")
        return item

    def remove(self, key: str) -> None:
        self.items.pop(str(key), None)

    def all(self) -> List[Any]:
        return list(self.items.values())

    def exists(self, key: str) -> bool:
        return str(key) in self.items

    def clear(self) -> None:
        self.items.clear()


class InMemoryStore:
    """Single in-memory store injected into services and routes."""

    def __init__(self) -> None:
        self.users = Table("user")
        self.students = Table("student")
        self.mentors = Table("mentor")
        self.faculty_consultants = Table("faculty_consultant")
        self.coordinators = Table("mcp_coordinator")
        self.supporting_staff = Table("supporting_staff")
        self.faculties = Table("faculty")
        self.departments = Table("department")
        self.majors = Table("major")
        self.groups = Table("mcp_group")
        self.records = Table("record")
        self.messages = Table("message")
        self.appointments = Table("appointment")
        self.logs = Table("log")
        self.feedback = Table("feedback")
        self.notifications = Table("notification")
        self.exports = Table("export")
        self._counters: Dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:04d}"

    def reset(self) -> None:
        for value in self.__dict__.values():
            if isinstance(value, Table):
                value.clear()
        self._counters.clear()

    def find_user_by_account(self, account: str):
        for user in self.users.all():
            if user.account == account:
                return user
        return None

    def find_user_by_email(self, email: str):
        for user in self.users.all():
            if user.email.lower() == email.lower():
                return user
        return None

    def find_mentor_by_email(self, email: str):
        for mentor in self.mentors.all():
            if mentor.email.lower() == email.lower():
                return mentor
        return None

    def find_mentor_by_name(self, name: str):
        for mentor in self.mentors.all():
            if mentor.name.lower() == name.lower():
                return mentor
        return None
