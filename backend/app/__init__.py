from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from .config import Config
from .extensions import cors, db, jwt, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})

    from .blueprints.auth import auth_bp
    from .blueprints.marketplace import marketplace_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.requirements import requirements_bp
    from .blueprints.packets import packets_bp
    from .blueprints.payments import payments_bp
    from .blueprints.agent_security import security_bp
    from .blueprints.liquidity import liquidity_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(marketplace_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(requirements_bp, url_prefix="/api/requirements")
    app.register_blueprint(packets_bp, url_prefix="/api/packets")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(security_bp, url_prefix="/api/guardrail")
    app.register_blueprint(liquidity_bp, url_prefix="/api/liquidity")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "resource-ai-api"})

    with app.app_context():
        db.create_all()
    return app
