from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Organization, User, organization_payload

auth_bp = Blueprint("auth", __name__)


def user_payload(user):
    return {"id": user.id, "name": user.name, "email": user.email, "organization": user.organization.name, "organization_id": user.organization_id, "verified": user.verified, "roles": {"buyer": user.organization.buyer_enabled, "seller": user.organization.seller_enabled}}


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    required = ("name", "email", "password", "organization", "organization_type", "location")
    if any(not data.get(field) for field in required):
        return jsonify({"error": "name, email, password, organization, organization_type and location are required"}), 400
    org = Organization(name=data["organization"], organization_type=data["organization_type"], location=data["location"], buyer_enabled=data.get("role", "buyer") == "buyer", seller_enabled=data.get("role") == "seller")
    user = User(name=data["name"], email=data["email"].lower().strip(), organization=org)
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An account with this email already exists"}), 409
    return jsonify({"user": user_payload(user), "access_token": create_access_token(identity=str(user.id))}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=(data.get("email") or "").lower().strip()).first()
    if not user or not user.check_password(data.get("password", "")):
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"user": user_payload(user), "access_token": create_access_token(identity=str(user.id))})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    return jsonify(user_payload(user)) if user else (jsonify({"error": "User not found"}), 404)


@auth_bp.post("/roles")
@jwt_required()
def enable_role():
    user = db.session.get(User, int(get_jwt_identity()))
    role = (request.get_json() or {}).get("role")
    if not user or role not in ("buyer", "seller"):
        return jsonify({"error": "role must be buyer or seller"}), 400
    if role == "buyer":
        user.organization.buyer_enabled = True
    else:
        user.organization.seller_enabled = True
    db.session.commit()
    return jsonify(user_payload(user))
