from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import ShoppingPacket, PacketItem, Listing, User

packets_bp = Blueprint("packets", __name__)


def packet_payload(row):
    return {"id": row.reference, "title": row.requirement.title, "items": len(row.items), "sellers": len({item.listing.seller_id for item in row.items}), "total": float(row.approved_total), "status": row.status, "updated": row.updated_at.strftime("Updated %d %b"), "line_items": [{"name": item.listing.product.name, "seller": item.listing.seller.name, "quantity": item.quantity, "unit_price": float(item.unit_price_snapshot), "subtotal": round(float(item.unit_price_snapshot) * item.quantity, 2)} for item in row.items]}


@packets_bp.get("")
@jwt_required()
def list_packets():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 401
    rows = ShoppingPacket.query.join(ShoppingPacket.requirement).filter_by(organization_id=user.organization_id).order_by(ShoppingPacket.updated_at.desc()).all()
    return jsonify([packet_payload(row) for row in rows])


@packets_bp.get("/<reference>")
@jwt_required()
def get_packet(reference):
    user = db.session.get(User, int(get_jwt_identity()))
    packet = ShoppingPacket.query.filter_by(reference=reference).first_or_404()
    if not user or packet.requirement.organization_id != user.organization_id:
        return jsonify({"error": "Packet not found"}), 404
    return jsonify(packet_payload(packet))


@packets_bp.post("/<reference>/approve")
@jwt_required()
def approve_packet(reference):
    user = db.session.get(User, int(get_jwt_identity()))
    packet = ShoppingPacket.query.filter_by(reference=reference).first_or_404()
    if not user or packet.requirement.organization_id != user.organization_id:
        return jsonify({"error": "Packet not found"}), 404
    if packet.status not in ("Ready for review", "Draft"):
        return jsonify({"error": "Packet is not awaiting approval"}), 409
    for item in packet.items:
        listing = db.session.get(Listing, item.listing_id)
        if not listing or not listing.active or listing.sellable_quantity < item.quantity:
            packet.status = "Needs renewed approval"
            db.session.commit()
            return jsonify({"error": "Price or stock changed; renewed approval is required", "status": packet.status}), 409
    packet.status = "Approved"
    db.session.commit()
    return jsonify(packet_payload(packet))
