import secrets
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import LiquidityLeg, LiquidityRoute, User
from ..payments.paypal import PayPalClient, PayPalConfigurationError
from ..services.router import calculate_route, leg_from_model, route_payload

liquidity_bp = Blueprint("liquidity", __name__)


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


@liquidity_bp.post("/routes")
@jwt_required()
def create_route():
    user = current_user()
    data = request.get_json() or {}
    legs = data.get("legs") or []
    try:
        normalized, total = calculate_route(legs, data.get("base_currency", "INR"), data.get("fx_rates") or {data.get("base_currency", "INR"): 1}, int(data.get("partner_fee_bps", 0)))
    except (TypeError, ValueError, ArithmeticError) as error:
        return jsonify({"error": str(error)}), 400
    route = LiquidityRoute(reference=f"ROUTE-{secrets.token_hex(6).upper()}", organization_id=user.organization_id, intent=str(data.get("intent", "")), base_currency=data.get("base_currency", "INR"), partner_fee_bps=int(data.get("partner_fee_bps", 0)), fx_rates=data.get("fx_rates") or {data.get("base_currency", "INR"): 1}, total_base_amount=total, status="DRAFT")
    db.session.add(route)
    db.session.flush()
    for item in normalized:
        db.session.add(LiquidityLeg(route_id=route.id, leg_key=item["key"], seller_name=item["seller"], description=item["description"], amount=item["amount"], currency=item["currency"], converted_amount=item["converted"], partner_fee=item["fee"], depends_on=item["depends_on"]))
    db.session.commit()
    return jsonify(route_payload(route)), 201


@liquidity_bp.get("/routes")
@jwt_required()
def list_routes():
    user = current_user()
    rows = LiquidityRoute.query.filter_by(organization_id=user.organization_id).order_by(LiquidityRoute.created_at.desc()).all()
    return jsonify([route_payload(row) for row in rows])


@liquidity_bp.get("/routes/<reference>")
@jwt_required()
def get_route(reference):
    user = current_user()
    route = LiquidityRoute.query.filter_by(reference=reference, organization_id=user.organization_id).first_or_404()
    return jsonify(route_payload(route))


@liquidity_bp.post("/routes/<reference>/execute")
@jwt_required()
def execute_route(reference):
    user = current_user()
    route = LiquidityRoute.query.filter_by(reference=reference, organization_id=user.organization_id).first_or_404()
    if route.status not in ("DRAFT", "FAILED", "ROLLED_BACK"):
        return jsonify({"error": f"Route cannot execute from {route.status}"}), 409
    data = request.get_json() or {}
    failure_key = data.get("simulate_failure_key")
    route.status = "EXECUTING"
    completed = []
    adapter = PayPalClient()
    for leg in route.legs:
        if any(next((candidate.status for candidate in route.legs if candidate.leg_key == dep), "PENDING") != "CAPTURED" for dep in (leg.depends_on or [])):
            leg.status = "SKIPPED_DEPENDENCY"
            continue
        if failure_key and leg.leg_key == failure_key:
            leg.status = "FAILED"
            break
        try:
            if adapter.configured:
                provider_order = adapter.create_order(float(leg.converted_amount + leg.partner_fee), route.base_currency, f"{route.reference}-{leg.leg_key}")
                leg.provider_order_id = provider_order.get("id")
                leg.status = "ORDER_CREATED"
                # Capture is deliberately separated; the provider response is the authority.
                if data.get("capture", False):
                    captured = adapter.capture_order(leg.provider_order_id)
                    if captured.get("status") != "COMPLETED":
                        raise RuntimeError("PayPal did not confirm leg capture")
                    leg.provider_capture_id = captured.get("id") or leg.provider_order_id
                    leg.status = "CAPTURED"
                else:
                    leg.status = "AUTHORIZED"
            else:
                leg.status = "CAPTURED"
            completed.append(leg)
        except (PayPalConfigurationError, RuntimeError, OSError) as error:
            leg.status = "FAILED"
            failure_key = leg.leg_key
            break
    failed = next((leg for leg in route.legs if leg.status == "FAILED"), None)
    if failed:
        route.status = "ROLLING_BACK"
        for leg in completed:
            if leg.status in ("CAPTURED", "AUTHORIZED", "ORDER_CREATED"):
                if adapter.configured and leg.provider_capture_id:
                    try:
                        adapter.refund_capture(leg.provider_capture_id)
                    except Exception:
                        leg.status = "REFUND_PENDING"
                        continue
                leg.status = "COMPENSATED"
        route.status = "ROLLED_BACK"
        db.session.commit()
        return jsonify({"route": route_payload(route), "atomic": False, "rolled_back": True, "failed_leg": failed.leg_key}), 409
    route.status = "COMPLETED" if all(leg.status == "CAPTURED" for leg in route.legs) else "AUTHORIZED"
    db.session.commit()
    return jsonify({"route": route_payload(route), "atomic": True, "rolled_back": False})
