"""Character API routes."""
from flask import Blueprint, request, jsonify
from app.services.preset_manager import get_preset_characters, get_character_by_id
from app.models.character import Character
import uuid

character_bp = Blueprint("character", __name__)


@character_bp.route("/presets", methods=["POST"])
def list_presets():
    """List available preset characters."""
    return jsonify({"characters": get_preset_characters()})


@character_bp.route("/create", methods=["POST"])
def create_character():
    """Create a custom character."""
    data = request.get_json() or {}

    name = data.get("name", "")
    personality = data.get("personality", "")

    if not name or not personality:
        return jsonify({"error": "name and personality are required"}), 400

    preset_id = data.get("preset_id")
    if preset_id:
        preset = get_character_by_id(preset_id)
        if preset:
            return jsonify({"character": preset})
        return jsonify({"error": f"Preset '{preset_id}' not found"}), 404

    character = Character(
        id=data.get("id", str(uuid.uuid4())[:8]),
        name=name,
        personality=personality,
        background=data.get("background", ""),
        role=data.get("role", "protagonist"),
        color=data.get("color", "#5b8dee"),
    )

    return jsonify({"character": character.to_dict()})
