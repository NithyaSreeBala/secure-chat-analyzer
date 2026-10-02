"""
app.py
------
Entry point for the Secure Chat Analyser backend.

Provides:
  - REST auth endpoints: /api/register, /api/login
  - REST history/analytics endpoints: /api/messages/<room>, /api/analytics/<room>
  - Real-time chat over Socket.IO: connect, join, send_message, disconnect
  - AI-based message risk analysis
  - HIGH-risk message blocking before storage and delivery

Run with:  python app.py
"""

import os
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, emit
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    decode_token,
)
from flask_bcrypt import Bcrypt
from cryptography.fernet import Fernet

from config import Config
from models import db, User, Message
from ai_analyzer import ChatAnalyzer
from encryption import MessageEncryptor


# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(Config)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)


# ---------------------------------------------------------------------------
# Encryption key
# ---------------------------------------------------------------------------

# If no ENCRYPTION_KEY was set in .env, auto-generate one for local development.
if not app.config.get("ENCRYPTION_KEY"):
    generated = Fernet.generate_key().decode()

    app.config["ENCRYPTION_KEY"] = generated

    print("=" * 70)
    print("No ENCRYPTION_KEY found in .env - generated a temporary one:")
    print(generated)
    print("Add this to backend/.env as ENCRYPTION_KEY=...")
    print("to keep messages decryptable across server restarts.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

CORS(app)

db.init_app(app)

bcrypt = Bcrypt(app)

jwt = JWTManager(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


# ---------------------------------------------------------------------------
# AI Analyzer
# ---------------------------------------------------------------------------

analyzer = ChatAnalyzer(
    toxicity_threshold=Config.TOXICITY_FLAG_THRESHOLD,
    negative_sentiment_threshold=Config.NEGATIVE_SENTIMENT_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Message Encryption
# ---------------------------------------------------------------------------

encryptor = MessageEncryptor(
    app.config["ENCRYPTION_KEY"]
)


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()


# ===========================================================================
# REST API - AUTHENTICATION
# ===========================================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({
            "error": "username and password are required"
        }), 400

    if User.query.filter_by(username=username).first():

        return jsonify({
            "error": "username already taken"
        }), 409

    pw_hash = bcrypt.generate_password_hash(
        password
    ).decode("utf-8")

    user = User(
        username=username,
        password_hash=pw_hash
    )

    db.session.add(user)

    db.session.commit()

    token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "token": token,
        "user": user.to_dict()
    }), 201


@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(
        username=username
    ).first()

    if not user or not bcrypt.check_password_hash(
        user.password_hash,
        password
    ):

        return jsonify({
            "error": "invalid username or password"
        }), 401

    token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }), 200


# ===========================================================================
# REST API - MESSAGE HISTORY
# ===========================================================================

@app.route("/api/messages/<room>", methods=["GET"])
@jwt_required()
def get_messages(room):

    msgs = (
        Message.query
        .filter_by(room=room)
        .order_by(Message.timestamp.asc())
        .limit(200)
        .all()
    )

    out = [
        m.to_dict(
            encryptor.decrypt(
                m.encrypted_content
            )
        )
        for m in msgs
    ]

    return jsonify(out), 200


# ===========================================================================
# REST API - ANALYTICS
# ===========================================================================

@app.route("/api/analytics/<room>", methods=["GET"])
@jwt_required()
def get_analytics(room):

    msgs = Message.query.filter_by(room=room).all()

    total = len(msgs)

    if total == 0:
        return jsonify({
            "total_messages": 0
        }), 200

    risk_counts = {
        "SAFE": 0,
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0
    }

    sentiment_counts = {
        "positive": 0,
        "neutral": 0,
        "negative": 0
    }

    flagged_users = {}

    for m in msgs:

        risk_counts[m.risk_level] = (
            risk_counts.get(m.risk_level, 0) + 1
        )

        sentiment_counts[m.sentiment_label] = (
            sentiment_counts.get(m.sentiment_label, 0) + 1
        )

        if m.risk_level in ("MEDIUM", "HIGH"):

            flagged_users[m.sender_username] = (
                flagged_users.get(
                    m.sender_username,
                    0
                ) + 1
            )

    return jsonify({

        "total_messages": total,

        "risk_distribution": risk_counts,

        "sentiment_distribution": sentiment_counts,

        "flagged_by_user": flagged_users

    }), 200


# ===========================================================================
# SOCKET.IO - USER AUTHENTICATION
# ===========================================================================

def _user_from_token(token):
    """
    Resolve a JWT into a User row for Socket.IO events.
    """

    try:

        decoded = decode_token(token)

        user_id = decoded["sub"]

        return User.query.get(
            int(user_id)
        )

    except Exception:

        return None


# ===========================================================================
# SOCKET.IO - CONNECT
# ===========================================================================

@socketio.on("connect")
def handle_connect(auth):

    token = (auth or {}).get("token")

    user = _user_from_token(token)

    if not user:

        return False

    print(
        f"[connect] {user.username} connected"
    )


# ===========================================================================
# SOCKET.IO - JOIN ROOM
# ===========================================================================

@socketio.on("join")
def handle_join(data):

    room = data.get(
        "room",
        "general"
    )

    token = data.get("token")

    user = _user_from_token(token)

    if not user:

        return

    join_room(room)

    emit(
        "system",
        {
            "message":
            f"{user.username} joined {room}"
        },
        room=room
    )


# ===========================================================================
# SOCKET.IO - SEND MESSAGE
# ===========================================================================

@socketio.on("send_message")
def handle_send_message(data):

    token = data.get("token")

    room = data.get(
        "room",
        "general"
    )

    content = (
        data.get("content") or ""
    ).strip()

    # -------------------------------------------------------
    # Authenticate the user
    # -------------------------------------------------------

    user = _user_from_token(token)

    if not user or not content:

        return

    # -------------------------------------------------------
    # STEP 1: AI ANALYSIS
    # -------------------------------------------------------

    result = analyzer.analyze(content)

    # -------------------------------------------------------
    # STEP 2: SECURITY INTERVENTION
    #
    # HIGH-risk messages are blocked BEFORE:
    #
    #   1. Encryption
    #   2. Database storage
    #   3. Broadcasting to chat users
    #
    # This makes the system prevention-oriented.
    # -------------------------------------------------------

    if result["risk_level"] == "HIGH":

        # Get detected toxic terms safely
        toxic_terms = result.get(
            "toxicity",
            {}
        ).get(
            "matched_terms",
            []
        )

        # Get sensitive-information details safely
        sensitive_details = result.get(
            "sensitive_info",
            {}
        ).get(
            "details",
            {}
        )

        # Send security notification ONLY
        # to the user who attempted the message.
        emit(
            "message_blocked",
            {
                "risk_level": "HIGH",

                "message":
                "Your message was blocked because high-risk content was detected.",

                "reason": {
                    "toxic_terms": toxic_terms,

                    "sensitive_info":
                    sensitive_details
                }
            }
        )

        # Print security event in backend terminal
        print(
            f"[SECURITY] BLOCKED HIGH-risk message "
            f"from {user.username}: {content}"
        )

        # IMPORTANT:
        # Stop here.
        #
        # The message will NOT:
        # - be encrypted
        # - be stored
        # - be broadcast
        #
        return

    # -------------------------------------------------------
    # STEP 3: ENCRYPT ONLY ALLOWED MESSAGES
    # -------------------------------------------------------

    encrypted = encryptor.encrypt(
        content
    )

    # -------------------------------------------------------
    # STEP 4: CREATE DATABASE MESSAGE
    # -------------------------------------------------------

    msg = Message(

        room=room,

        sender_id=user.id,

        sender_username=user.username,

        encrypted_content=encrypted,

        sentiment_label=
        result["sentiment"]["label"],

        sentiment_polarity=
        result["sentiment"]["polarity"],

        toxicity_score=
        result["toxicity"]["score"],

        risk_level=
        result["risk_level"],

        has_sensitive_info=
        result["sensitive_info"]["has_sensitive_info"],
    )

    # -------------------------------------------------------
    # STEP 5: SAVE MESSAGE
    # -------------------------------------------------------

    db.session.add(msg)

    db.session.commit()

    # -------------------------------------------------------
    # STEP 6: PREPARE MESSAGE FOR CHAT
    # -------------------------------------------------------

    payload = msg.to_dict(
        content
    )

    # Include complete AI analysis
    # for the frontend risk badge/tooltip.
    payload["analysis"] = result

    # -------------------------------------------------------
    # STEP 7: SEND MESSAGE TO CHAT
    # -------------------------------------------------------

    emit(
        "new_message",
        payload,
        room=room
    )

    # -------------------------------------------------------
    # STEP 8: SEND RISK ALERT
    #
    # MEDIUM messages are allowed but flagged.
    # HIGH messages never reach this section because
    # they were already blocked above.
    # -------------------------------------------------------

    if result["risk_level"] == "MEDIUM":

        emit(
            "risk_alert",
            {
                "sender":
                user.username,

                "risk_level":
                result["risk_level"],

                "reason": {

                    "toxic_terms":
                    result["toxicity"]["matched_terms"],

                    "sensitive_info":
                    result["sensitive_info"]["details"],
                },
            },
            room=room
        )


# ===========================================================================
# SOCKET.IO - TYPING
# ===========================================================================

@socketio.on("typing")
def handle_typing(data):

    room = data.get(
        "room",
        "general"
    )

    username = data.get(
        "username",
        "Someone"
    )

    emit(
        "user_typing",
        {
            "username": username
        },
        room=room,
        include_self=False
    )


# ===========================================================================
# SOCKET.IO - STOP TYPING
# ===========================================================================

@socketio.on("stop_typing")
def handle_stop_typing(data):

    room = data.get(
        "room",
        "general"
    )

    username = data.get(
        "username",
        "Someone"
    )

    emit(
        "user_stopped_typing",
        {
            "username": username
        },
        room=room,
        include_self=False
    )


# ===========================================================================
# SOCKET.IO - DISCONNECT
# ===========================================================================

@socketio.on("disconnect")
def handle_disconnect():

    print(
        "[disconnect] a client disconnected"
    )


# ===========================================================================
# START SERVER
# ===========================================================================

@app.route("/api/threat-monitor", methods=["GET"])
def threat_monitor():

    messages = Message.query.order_by(
        Message.timestamp.desc()
    ).limit(50).all()

    threats = []

    for message in messages:

        if message.risk_level in ["MEDIUM", "HIGH"]:

            threats.append({
                "username": message.sender_username,
                "risk_level": message.risk_level,
                "toxicity_score": message.toxicity_score,
                "has_sensitive_info": message.has_sensitive_info,
                "timestamp": message.timestamp.isoformat()
            })

    return jsonify(threats)


@app.route("/api/risk-analytics", methods=["GET"])
def risk_analytics():

    messages = Message.query.all()

    total = len(messages)

    safe = sum(
        1 for m in messages
        if m.risk_level == "SAFE"
    )

    low = sum(
        1 for m in messages
        if m.risk_level == "LOW"
    )

    medium = sum(
        1 for m in messages
        if m.risk_level == "MEDIUM"
    )

    high = sum(
        1 for m in messages
        if m.risk_level == "HIGH"
    )

    flagged = medium + high

    return jsonify({
        "total_messages": total,
        "safe": safe,
        "low": low,
        "medium": medium,
        "high": high,
        "flagged": flagged
    })


if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )

    @app.route("/api/user-profiles", methods=["GET"])
    def user_profiles():
        users = User.query.all()

        profiles = []

        for user in users:

            messages = Message.query.filter_by(
                sender_id=user.id
            ).all()

            total_messages = len(messages)

            flagged_messages = sum(
                1 for m in messages
                if m.risk_level in ["MEDIUM", "HIGH"]
            )

            high_messages = sum(
                1 for m in messages
                if m.risk_level == "HIGH"
            )

            medium_messages = sum(
                1 for m in messages
                if m.risk_level == "MEDIUM"
            )

            # Calculate risk score
            risk_points = (
                high_messages * 10
                + medium_messages * 5
            )

            # Keep score between 0 and 100
            risk_score = min(risk_points, 100)

            profiles.append({
                "username": user.username,
                "messages": total_messages,
                "flagged": flagged_messages,
                "high": high_messages,
                "medium": medium_messages,
                "score": risk_score
            })

        return jsonify(profiles)

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True
    )