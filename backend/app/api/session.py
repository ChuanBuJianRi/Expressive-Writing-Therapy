"""Session API routes."""
from flask import Blueprint, jsonify
from app.utils.logger import get_logger

log = get_logger(__name__)

session_bp = Blueprint("session", __name__)

# In-memory session store (for MVP; replace with DB for production)
_sessions: dict[str, dict] = {}


def save_session(session_id: str, data: dict):
    _sessions[session_id] = data


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


@session_bp.route("/<session_id>", methods=["GET"])
def get_session_details(session_id: str):
    """Get session details."""
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session": session})


@session_bp.route("/list", methods=["GET"])
def list_sessions():
    """List all sessions."""
    sessions = [
        {"id": sid, "theme": s.get("theme", ""), "status": s.get("status", "unknown")}
        for sid, s in _sessions.items()
    ]
    return jsonify({"sessions": sessions})
