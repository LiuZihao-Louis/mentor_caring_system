from __future__ import annotations

import os

from flask import Flask

from mentor_caring.exceptions import register_error_handlers
from mentor_caring.repositories import InMemoryStore
from mentor_caring.routes.api import api_bp
from mentor_caring.routes.frontend import frontend_bp
from mentor_caring.seed import seed_data
from mentor_caring.services import build_services


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("MCS_SECRET_KEY", "dev-secret-key-change-in-production"),
        TESTING=testing,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        CSRF_ENABLED=not testing,
    )

    store = InMemoryStore()
    seed_data(store)
    app.config["store"] = store
    app.config["services"] = build_services(store)

    @app.template_filter("to_dicts")
    def to_dicts(values):
        return [v.to_dict() if hasattr(v, "to_dict") else v for v in values]

    register_error_handlers(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(frontend_bp)
    return app


if __name__ == "__main__":
    create_app().run(debug=False)
