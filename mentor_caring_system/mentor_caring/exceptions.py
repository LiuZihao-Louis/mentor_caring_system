from __future__ import annotations

from flask import flash, jsonify, redirect, request


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


def register_error_handlers(app):
    def wants_json() -> bool:
        return request.path.startswith("/api/")

    def handle_frontend_error(error):
        flash(str(error), "error")
        return redirect(request.referrer or "/")

    def handle_error(error, status_code: int, error_type: str):
        if wants_json():
            return jsonify({"error": str(error), "type": error_type}), status_code
        return handle_frontend_error(error)

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return handle_error(error, 400, "ValueError")

    @app.errorhandler(LookupError)
    def handle_lookup_error(error):
        return handle_error(error, 404, "LookupError")

    @app.errorhandler(PermissionError)
    def handle_permission_error(error):
        return handle_error(error, 403, "PermissionError")

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return handle_error(error, error.status_code, error.__class__.__name__)
