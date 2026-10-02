from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # User role: "user" or "admin"
    role = db.Column(
        db.String(20),
        default="user",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role
        }


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    room = db.Column(
        db.String(120),
        nullable=False,
        index=True
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    sender_username = db.Column(
        db.String(80),
        nullable=False
    )

    # Message content is NEVER stored in plaintext.
    # Only the Fernet-encrypted token is stored.
    encrypted_content = db.Column(
        db.Text,
        nullable=False
    )

    # AI analysis results
    sentiment_label = db.Column(
        db.String(20)
    )

    sentiment_polarity = db.Column(
        db.Float
    )

    toxicity_score = db.Column(
        db.Float
    )

    risk_level = db.Column(
        db.String(10)
    )

    has_sensitive_info = db.Column(
        db.Boolean,
        default=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def to_dict(self, plaintext_content: str):
        return {
            "id": self.id,
            "room": self.room,
            "sender": self.sender_username,
            "content": plaintext_content,
            "sentiment": {
                "label": self.sentiment_label,
                "polarity": self.sentiment_polarity
            },
            "toxicity_score": self.toxicity_score,
            "risk_level": self.risk_level,
            "has_sensitive_info": self.has_sensitive_info,
            "timestamp": self.timestamp.isoformat()
        }