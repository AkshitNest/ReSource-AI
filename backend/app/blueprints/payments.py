from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import ShoppingPacket, User
from ..payments.paypal import PayPalClient, PayPalConfigurationError

payments_bp = Blueprint("payments", __name__)


@payments_bp.post("/paypal/order")
@jwt_required()
def create_paypal_order():
    data = request.get_json() or {}
    user = db.session.get(User, int(get_jwt_identity()))
    packet = ShoppingPacket.query.filter_by(reference=data.get("packet_reference")).first()
    if not packet or not user or packet.requirement.organization_id != user.organization_id or packet.status != "Approved":
        return jsonify({"error": "Only an approved shopping packet can start checkout"}), 409
    try:
        result = PayPalClient().create_order(float(packet.approved_total), packet.requirement.currency, packet.reference)
    except PayPalConfigurationError as error:
        return jsonify({"error": str(error), "mode": "sandbox_configuration_required"}), 503
    return jsonify({"provider": "paypal", "order": result})


@payments_bp.post("/paypal/capture/<paypal_order_id>")
@jwt_required()
def capture_paypal_order(paypal_order_id):
    try:
        result = PayPalClient().capture_order(paypal_order_id)
    except PayPalConfigurationError as error:
        return jsonify({"error": str(error), "mode": "sandbox_configuration_required"}), 503
    status = result.get("status")
    if status != "COMPLETED":
        return jsonify({"error": "PayPal did not confirm capture", "provider_status": status}), 502
    return jsonify({"provider": "paypal", "status": "COMPLETED", "capture": result})
