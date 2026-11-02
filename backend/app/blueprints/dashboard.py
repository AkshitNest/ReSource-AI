from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import Organization, Requirement, ShoppingPacket, Listing, User

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard/<role>")
@jwt_required()
def dashboard(role):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or (role == "seller" and not user.organization.seller_enabled) or (role == "buyer" and not user.organization.buyer_enabled):
        return jsonify({"error": "Role is not enabled for this organization"}), 403
    if role == "seller":
        listings = Listing.query.filter_by(seller_id=user.organization_id).all()
        metrics = [
            {"label": "Active listings", "value": str(sum(1 for row in listings if row.active)), "meta": "Current catalog", "tone": "sage", "icon": "boxes"},
            {"label": "Current stock", "value": f"{sum(row.sellable_quantity for row in listings):,}", "meta": "Available units", "tone": "peach", "icon": "wallet"},
            {"label": "Open requests", "value": str(Requirement.query.filter(Requirement.status.in_(["Processing", "Sourcing"])).count()), "meta": "Visible opportunities", "tone": "lavender", "icon": "message"},
            {"label": "Payouts", "value": "₹0", "meta": "No confirmed payouts", "tone": "blue", "icon": "arrow"},
        ]
    else:
        requirements = Requirement.query.filter_by(organization_id=user.organization_id).all()
        packets = ShoppingPacket.query.join(ShoppingPacket.requirement).filter_by(organization_id=user.organization_id).all()
        metrics = [
            {"label": "Active requirements", "value": str(sum(1 for row in requirements if row.status not in ["Completed", "Cancelled"])), "meta": "Your open needs", "tone": "sage", "icon": "list"},
            {"label": "Awaiting approval", "value": str(sum(1 for row in packets if row.status == "Ready for review")), "meta": "Human review required", "tone": "peach", "icon": "clock"},
            {"label": "Orders in progress", "value": "0", "meta": "No confirmed orders yet", "tone": "lavender", "icon": "truck"},
            {"label": "Budget tracked", "value": f"₹{sum(float(row.budget) for row in requirements):,.0f}", "meta": "Across your requirements", "tone": "blue", "icon": "wallet"},
        ]
    return jsonify({"role": role, "chart": [], "metrics": metrics, "counts": {"requirements": Requirement.query.count(), "packets": ShoppingPacket.query.count()}, "organizations": Organization.query.count()})


@dashboard_bp.get("/demand")
@jwt_required()
def buyer_demand():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.organization.seller_enabled:
        return jsonify({"error": "Seller workspace is not enabled for this organization"}), 403
    rows = Requirement.query.filter(Requirement.organization_id != user.organization_id, Requirement.status.in_(["Processing", "Sourcing", "Packet ready"])).all()
    return jsonify([{"id": row.reference, "title": row.title, "organization": row.organization.name, "location": row.location, "beneficiaries": row.beneficiaries, "budget": float(row.budget), "deadline": row.deadline.isoformat() if row.deadline else None, "status": row.status} for row in rows])
