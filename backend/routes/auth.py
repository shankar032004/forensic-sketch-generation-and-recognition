"""
Auth Routes — signup, login, logout, current user.
Session-based auth with Flask-Login.
"""
import re
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from models.database import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ══════════════════════════════════════════════════════════════════════
# SIGNUP
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Create a new user account.

    Body (JSON):
        username: str (3-80 chars, alphanumeric + underscore)
        email:    str (valid email format)
        password: str (min 6 chars)
    """
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # ── Validation ────────────────────────────────────────────────────
    errors = []

    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif not re.match(r"^[a-zA-Z0-9_]+$", username):
        errors.append("Username can only contain letters, numbers, and underscores.")

    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        errors.append("Please provide a valid email address.")

    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    # ── Check uniqueness ──────────────────────────────────────────────
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    # ── Create user ───────────────────────────────────────────────────
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    print(f"[Auth] ✓ New user registered: {username}")
    return jsonify({"success": True, "message": "Account created successfully."}), 201


# ══════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login with username + password.

    Body (JSON):
        username: str
        password: str
    """
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password."}), 401

    login_user(user, remember=True)
    print(f"[Auth] ✓ User logged in: {username}")
    return jsonify({"success": True, "user": user.to_dict()})


# ══════════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log out the current user."""
    username = current_user.username
    logout_user()
    print(f"[Auth] ✓ User logged out: {username}")
    return jsonify({"success": True, "message": "Logged out successfully."})


# ══════════════════════════════════════════════════════════════════════
# CURRENT USER
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/me", methods=["GET"])
def me():
    """Get the currently logged-in user info, or 401 if not logged in."""
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": current_user.to_dict()})
    return jsonify({"authenticated": False}), 401
