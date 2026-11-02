from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    organization_type = db.Column(db.String(80), nullable=False, default="nonprofit")
    country = db.Column(db.String(80), nullable=False, default="India")
    location = db.Column(db.String(160), nullable=False, default="Pune, Maharashtra")
    verified = db.Column(db.Boolean, default=False, nullable=False)
    buyer_enabled = db.Column(db.Boolean, default=True, nullable=False)
    seller_enabled = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    organization = db.relationship("Organization", backref="users")
    verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, default="")
    image_url = db.Column(db.String(500), default="")
    condition = db.Column(db.String(40), default="new")
    unit = db.Column(db.String(40), default="unit")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Listing(db.Model):
    __tablename__ = "listings"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    available_quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_order_quantity = db.Column(db.Integer, nullable=False, default=1)
    surplus = db.Column(db.Boolean, default=False, nullable=False)
    donation_quantity = db.Column(db.Integer, default=0, nullable=False)
    location = db.Column(db.String(160), nullable=False, default="Pune, Maharashtra")
    lead_days = db.Column(db.Integer, default=5, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    product = db.relationship("Product", backref="listings")
    seller = db.relationship("Organization", backref="listings")

    @property
    def sellable_quantity(self):
        return max(self.available_quantity - self.reserved_quantity, 0)


class Requirement(db.Model):
    __tablename__ = "requirements"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    beneficiaries = db.Column(db.Integer, nullable=False)
    budget = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(5), default="INR", nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(160), nullable=False)
    status = db.Column(db.String(50), default="Processing", nullable=False)
    extracted_spec = db.Column(db.JSON, default=dict, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    organization = db.relationship("Organization", backref="requirements")


class ShoppingPacket(db.Model):
    __tablename__ = "shopping_packets"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    requirement_id = db.Column(db.Integer, db.ForeignKey("requirements.id"), nullable=False)
    status = db.Column(db.String(50), default="Draft", nullable=False)
    approved_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    estimated_savings = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    requirement = db.relationship("Requirement", backref="packets")


class PacketItem(db.Model):
    __tablename__ = "packet_items"
    id = db.Column(db.Integer, primary_key=True)
    packet_id = db.Column(db.Integer, db.ForeignKey("shopping_packets.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_snapshot = db.Column(db.Numeric(12, 2), nullable=False)
    donated_quantity = db.Column(db.Integer, nullable=False, default=0)
    listing = db.relationship("Listing")
    packet = db.relationship("ShoppingPacket", backref="items")


class IntentProof(db.Model):
    __tablename__ = "intent_proofs"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    original_prompt = db.Column(db.Text, nullable=False)
    prompt_hash = db.Column(db.String(64), nullable=False)
    constraint_hash = db.Column(db.String(64), nullable=False)
    proof_signature = db.Column(db.String(128), nullable=False)
    constraints = db.Column(db.JSON, nullable=False, default=dict)
    state_version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default="ACTIVE")
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    organization = db.relationship("Organization", backref="intent_proofs")


class IntentVerification(db.Model):
    __tablename__ = "intent_verifications"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    intent_id = db.Column(db.Integer, db.ForeignKey("intent_proofs.id"), nullable=False)
    checkout_payload_hash = db.Column(db.String(64), nullable=False)
    dom_hash = db.Column(db.String(64), nullable=False)
    agent_log_hash = db.Column(db.String(64), nullable=False)
    verification_hash = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    reasons = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    intent = db.relationship("IntentProof", backref="verifications")


class LiquidityRoute(db.Model):
    __tablename__ = "liquidity_routes"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    intent = db.Column(db.Text, nullable=False)
    base_currency = db.Column(db.String(5), nullable=False, default="INR")
    partner_fee_bps = db.Column(db.Integer, nullable=False, default=0)
    fx_rates = db.Column(db.JSON, nullable=False, default=dict)
    total_base_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default="DRAFT")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    organization = db.relationship("Organization", backref="liquidity_routes")


class LiquidityLeg(db.Model):
    __tablename__ = "liquidity_legs"
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("liquidity_routes.id"), nullable=False)
    leg_key = db.Column(db.String(80), nullable=False)
    seller_name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.String(240), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency = db.Column(db.String(5), nullable=False)
    converted_amount = db.Column(db.Numeric(14, 2), nullable=False)
    partner_fee = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    depends_on = db.Column(db.JSON, nullable=False, default=list)
    provider_order_id = db.Column(db.String(120), nullable=True)
    provider_capture_id = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="PENDING")
    route = db.relationship("LiquidityRoute", backref="legs")


def organization_payload(org):
    return {"id": org.id, "name": org.name, "type": org.organization_type, "location": org.location, "verified": org.verified, "buyer_enabled": org.buyer_enabled, "seller_enabled": org.seller_enabled}


def product_payload(listing):
    return {"id": listing.product.id, "listing_id": listing.id, "name": listing.product.name, "sku": listing.product.sku, "category": listing.product.category, "price": float(listing.unit_price), "stock": listing.sellable_quantity, "seller": listing.seller.name, "seller_id": listing.seller.id, "location": listing.location, "condition": listing.product.condition, "surplus": listing.surplus, "donation_quantity": listing.donation_quantity, "lead_days": listing.lead_days, "image": listing.product.image_url}
