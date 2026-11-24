"""
History Routes — CRUD for user action history.
Tracks generated sketches, edits, and recognitions.
"""
import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, History

history_bp = Blueprint("history", __name__, url_prefix="/api/history")


# ══════════════════════════════════════════════════════════════════════
# LIST HISTORY
# ══════════════════════════════════════════════════════════════════════

@history_bp.route("", methods=["GET"])
@login_required
def list_history():
    """
    List history entries for the current user.

    Query params:
        type:   str|None  — filter by action_type (generate, edit, recognize)
        page:   int       — page number (default 1)
        limit:  int       — items per page (default 20)
    """
    action_type = request.args.get("type", None)
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    limit = min(limit, 50)  # Cap at 50

    query = History.query.filter_by(user_id=current_user.id)

    if action_type and action_type in ("generate", "edit", "recognize"):
        query = query.filter_by(action_type=action_type)

    query = query.order_by(History.created_at.desc())
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        "success": True,
        "items": [item.to_dict() for item in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


# ══════════════════════════════════════════════════════════════════════
# GET SINGLE ENTRY
# ══════════════════════════════════════════════════════════════════════

@history_bp.route("/<int:entry_id>", methods=["GET"])
@login_required
def get_entry(entry_id):
    """Get a single history entry (must belong to current user)."""
    entry = History.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        return jsonify({"error": "Entry not found."}), 404
    return jsonify({"success": True, "item": entry.to_dict()})


# ══════════════════════════════════════════════════════════════════════
# DELETE ENTRY
# ══════════════════════════════════════════════════════════════════════

@history_bp.route("/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id):
    """Delete a history entry (must belong to current user)."""
    entry = History.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        return jsonify({"error": "Entry not found."}), 404

    db.session.delete(entry)
    db.session.commit()
    return jsonify({"success": True, "message": "Entry deleted."})


# ══════════════════════════════════════════════════════════════════════
# HELPER — Save to history (called from app.py endpoints)
# ══════════════════════════════════════════════════════════════════════

def save_to_history(
    user_id: int,
    action_type: str,
    prompt: str = "",
    image_filename: str = "",
    thumbnail: str = "",
    metadata: dict | None = None,
):
    """
    Save an action to the user's history.

    Parameters
    ----------
    user_id : int
    action_type : str — 'generate', 'edit', or 'recognize'
    prompt : str
    image_filename : str
    thumbnail : str — small base64 thumbnail (first ~100x100px)
    metadata : dict — extra info (similarity score, region, etc.)
    """
    entry = History(
        user_id=user_id,
        action_type=action_type,
        prompt=prompt,
        image_filename=image_filename,
        thumbnail=thumbnail,
        metadata_json=json.dumps(metadata or {}),
    )
    db.session.add(entry)
    db.session.commit()
    return entry
