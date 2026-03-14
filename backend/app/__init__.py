"""Flask application factory."""
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    from app.api.story import story_bp
    from app.api.character import character_bp
    from app.api.world import world_bp
    from app.api.session import session_bp

    app.register_blueprint(story_bp, url_prefix="/api/story")
    app.register_blueprint(character_bp, url_prefix="/api/character")
    app.register_blueprint(world_bp, url_prefix="/api/world")
    app.register_blueprint(session_bp, url_prefix="/api/session")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
