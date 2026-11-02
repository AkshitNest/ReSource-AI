import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-before-deploy-123456")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "local-development-jwt-secret-change-before-deploy-123456")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///resource_ai.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
    PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_COOKIE_SECURE = False
