from datetime import date
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..agents import demand_agent
from ..extensions import db
from ..models import Requirement, User

requirements_bp = Blueprint("requirements", __name__)


def requirement_payload(row):
    return {"id": row.reference, "title": row.title, "beneficiaries": row.beneficiaries, "budget": float(row.budget), "created": row.created_at.strftime("%d %b %Y"), "status": row.status, "location": row.location, "spec": row.extracted_spec}


@requirements_bp.get("")
@jwt_required()
def list_requirements():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 401
    return jsonify([requirement_payload(row) for row in Requirement.query.filter_by(organization_id=user.organization_id).order_by(Requirement.created_at.desc()).all()])


@requirements_bp.post("")
@jwt_required()
def create_requirement():
    data = request.get_json() or {}
    if not all(data.get(key) for key in ("title", "description", "beneficiaries", "budget", "location")):
        return jsonify({"error": "title, description, beneficiaries, budget and location are required"}), 400
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.organization.buyer_enabled:
        return jsonify({"error": "Buyer workspace is not enabled for this organization"}), 403
    organization_id = user.organization_id
    spec = demand_agent(data["description"], int(data["beneficiaries"]))
    row = Requirement(reference=f"REQ-{1000 + Requirement.query.count() + 1}", organization_id=organization_id, title=data["title"], description=data["description"], beneficiaries=int(data["beneficiaries"]), budget=float(data["budget"]), deadline=date.fromisoformat(data["deadline"]) if data.get("deadline") else None, location=data["location"], status="Processing", extracted_spec=spec.model_dump())
    db.session.add(row)
    db.session.commit()
    return jsonify(requirement_payload(row)), 201
