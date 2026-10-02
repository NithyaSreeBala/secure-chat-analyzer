import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # General Flask secret (used for sessions)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # JWT auth secret
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///chat_analyzer.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Symmetric key used to encrypt/decrypt message content at rest.
    # Generate your own with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # and put it in a .env file as ENCRYPTION_KEY=...
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    # Risk thresholds used by the AI analyzer
    TOXICITY_FLAG_THRESHOLD = 0.4   # 0.0 - 1.0
    NEGATIVE_SENTIMENT_THRESHOLD = -0.4  # -1.0 - 1.0
