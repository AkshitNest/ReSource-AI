from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import Listing, Organization, Product, User, product_payload

marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.get("/marketplace")
def marketplace():
    query = (request.args.get("q") or "").lower().strip()
    category = request.args.get("category")
    listings = Listing.query.filter_by(active=True).all()
    if query:
        listings = [row for row in listings if query in row.product.name.lower() or query in row.seller.name.lower() or query in row.product.category.lower()]
    if category:
        listings = [row for row in listings if row.product.category == category]
    return jsonify([product_payload(row) for row in listings])


@marketplace_bp.get("/inventory")
@jwt_required()
def inventory():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.organization.seller_enabled:
        return jsonify({"error": "Seller workspace is not enabled for this organization"}), 403
    return jsonify([product_payload(row) for row in Listing.query.filter_by(seller_id=user.organization_id).all()])


@marketplace_bp.post("/inventory")
@jwt_required()
def create_inventory():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.organization.seller_enabled:
        return jsonify({"error": "Enable seller workspace before listing products"}), 403
    data = request.get_json() or {}
    required = ("name", "sku", "category", "price", "stock")
    if any(data.get(field) in (None, "") for field in required):
        return jsonify({"error": "name, sku, category, price and stock are required"}), 400
    if float(data["price"]) < 0 or int(data["stock"]) < 0:
        return jsonify({"error": "price and stock cannot be negative"}), 400
    product = Product.query.filter_by(sku=data["sku"]).first()
    if product is None:
        product = Product(name=data["name"], sku=data["sku"], category=data["category"], description=data.get("description", ""), image_url=data.get("image", ""), condition=data.get("condition", "new"))
        db.session.add(product)
        db.session.flush()
    elif Listing.query.filter_by(product_id=product.id, seller_id=user.organization_id).first():
        return jsonify({"error": "This SKU is already listed by your organization"}), 409
    listing = Listing(product_id=product.id, seller_id=user.organization_id, unit_price=float(data["price"]), available_quantity=int(data["stock"]), minimum_order_quantity=int(data.get("minimum_order_quantity", 1)), surplus=bool(data.get("surplus", False)), donation_quantity=int(data.get("donation_quantity", 0)), location=user.organization.location, lead_days=int(data.get("lead_days", 5)))
    db.session.add(listing)
    db.session.commit()
    return jsonify(product_payload(listing)), 201
