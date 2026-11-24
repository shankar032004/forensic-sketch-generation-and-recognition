"""
Database Models — SQLAlchemy ORM for Users and History.
Uses SQLite for lightweight persistent storage.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ── Shared instances ──────────────────────────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "serve_login"


# ══════════════════════════════════════════════════════════════════════
# USER MODEL
# ══════════════════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    history = db.relationship("History", backref="user", lazy="dynamic",
                              cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ══════════════════════════════════════════════════════════════════════
# HISTORY MODEL
# ══════════════════════════════════════════════════════════════════════

class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action_type = db.Column(db.String(20), nullable=False, index=True)  # generate, edit, recognize
    prompt = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="")
    thumbnail = db.Column(db.Text, default="")  # small base64 thumbnail
    metadata_json = db.Column(db.Text, default="{}")  # extra info as JSON string
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "prompt": self.prompt,
            "image_filename": self.image_filename,
            "thumbnail": self.thumbnail,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ══════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ══════════════════════════════════════════════════════════════════════

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def init_db(app):
    """Initialize database and login manager with the Flask app."""
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        print("[Database] OK SQLite database initialized")
