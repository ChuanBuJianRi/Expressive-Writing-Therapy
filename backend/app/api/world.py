"""World API routes."""
from flask import Blueprint, request, jsonify
from app.services.preset_manager import get_preset_worlds, get_world_by_id
from app.services.world_builder import build_world

world_bp = Blueprint("world", __name__)


@world_bp.route("/presets", methods=["POST"])
def list_presets():
    """List available preset worlds."""
    return jsonify({"worlds": get_preset_worlds()})


@world_bp.route("/generate", methods=["POST"])
def generate_world():
    """Generate a custom world from user input."""
    data = request.get_json() or {}
    theme = data.get("theme", "")
    tags = data.get("tags", [])
    custom_setting = data.get("custom_setting", "")
    preset_id = data.get("preset_id")

    if preset_id:
        world = get_world_by_id(preset_id)
        if world:
            return jsonify({"world": world})
        return jsonify({"error": f"Preset '{preset_id}' not found"}), 404

    if not theme:
        return jsonify({"error": "theme is required"}), 400

    world = build_world(theme, tags=tags, custom_setting=custom_setting)
    return jsonify({"world": world})
