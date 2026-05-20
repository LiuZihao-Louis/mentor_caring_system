from __future__ import annotations

from mentor_caring.services.base import BaseService
from mentor_caring.services.utils import require_non_blank


class AuthService(BaseService):
    def login(self, account: str, password: str):
        account = require_non_blank(account, "account")
        password = require_non_blank(password, "password")
        user = self.store.find_user_by_account(account)
        if user is None or not user.check_password(password):
            raise PermissionError("Invalid account or password")
        self.log(user.id, "login", f"User {user.account} logged in")
        return user

    def logout(self, user_id: str):
        user_id = require_non_blank(user_id, "user_id")
        self.store.users.require(user_id, "user")
        self.log(user_id, "logout", f"User {user_id} logged out")
        return {"message": "logged out"}
