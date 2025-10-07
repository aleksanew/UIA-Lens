# Creates the Flask app and registers all blueprints.

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from .config import Config

def create_app(config_obj: type[Config]=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_obj)

    # --- Logging
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    # --- Blueprints
    from .routes.files import bp as files_bp
    from .routes.layers import bp as layers_bp
    from .routes.select import bp as select_bp
    from .routes.filters import bp as filters_bp
    from .routes.tools import bp as tools_bp
    from .routes.ui import bp as ui_bp

    app.register_blueprint(files_bp, url_prefix="/api/v1/files")
    app.register_blueprint(layers_bp, url_prefix="/api/v1/layers")
    app.register_blueprint(select_bp, url_prefix="/api/v1/select")
    app.register_blueprint(filters_bp, url_prefix="/api/v1/filters")
    app.register_blueprint(tools_bp, url_prefix="/api/v1/tools")
    app.register_blueprint(ui_bp, url_prefix="/api/v1")

    # --- Error handler
    @app.errorhandler(Exception)
    def handle_errors(e):
        if isinstance(e, HTTPException):
            payload = {"error": e.name, "message": e.description}
            return jsonify(payload), e.code
        app.logger.exception("Unhandled error")
        return jsonify({"error": "InternalServerError", "message": "Unexpected Error"}), 500
    return app
