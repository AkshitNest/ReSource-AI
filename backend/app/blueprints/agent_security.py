import secrets
from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..extensions import db
from ..models import IntentProof, IntentVerification, User
from ..services.guardrail import canonical, parse_intent, proof_payload, proof_signature, sha256, verify_checkout

security_bp = Blueprint("agent_security", __name__)


def owner():
    return db.session.get(User, int(get_jwt_identity()))


@security_bp.post("/intents")
@jwt_required()
def create_intent():
    user = owner()
    data = request.get_json() or {}
    arguments = data.get("arguments") or {}
    prompt = str(data.get("prompt") or arguments.get("prompt") or "").strip()
    if not user or not prompt:
        return jsonify({"error": "A signed-in buyer and original prompt are required"}), 400
    constraints = data.get("constraints") or arguments.get("constraints") or parse_intent(prompt)
    prompt_hash = sha256(prompt)
    constraint_hash = sha256(canonical(constraints))
    reference = f"INT-{secrets.token_hex(6).upper()}"
    signature = proof_signature(prompt_hash, constraint_hash, user.organization_id, 1)
    proof = IntentProof(reference=reference, organization_id=user.organization_id, original_prompt=prompt, prompt_hash=prompt_hash, constraint_hash=constraint_hash, proof_signature=signature, constraints=constraints, expires_at=None)
    db.session.add(proof)
    db.session.commit()
    return jsonify(proof_payload(proof)), 201


@security_bp.get("/intents/<reference>")
@jwt_required()
def get_intent(reference):
    user = owner()
    proof = IntentProof.query.filter_by(reference=reference, organization_id=user.organization_id).first_or_404()
    return jsonify(proof_payload(proof))


@security_bp.post("/verify")
@jwt_required()
def verify_intent():
    user = owner()
    data = request.get_json() or {}
    arguments = data.get("arguments") or {}
    proof = IntentProof.query.filter_by(reference=data.get("intent_id") or arguments.get("intent_id"), organization_id=user.organization_id).first()
    if not proof:
        return jsonify({"error": "Intent proof not found"}), 404
    if proof.status != "ACTIVE":
        return jsonify({"error": "Intent proof is no longer active"}), 409
    result = verify_checkout(proof, data.get("checkout_payload") or arguments.get("checkout_payload") or {})
    reference = f"VER-{secrets.token_hex(6).upper()}"
    verification = IntentVerification(reference=reference, intent_id=proof.id, checkout_payload_hash=result["checkout_payload_hash"], dom_hash=result["dom_hash"], agent_log_hash=result["agent_log_hash"], verification_hash=result["verification_hash"], status="ALLOWED" if result["allowed"] else "BLOCKED", reasons=result["reasons"])
    db.session.add(verification)
    db.session.commit()
    result.update({"id": reference, "intent_id": proof.reference, "status": verification.status, "authorization_token": proof.proof_signature if result["allowed"] else None})
    return jsonify(result)


@security_bp.post("/authorize")
@jwt_required()
def authorize_capture():
    user = owner()
    data = request.get_json() or {}
    arguments = data.get("arguments") or {}
    verification = IntentVerification.query.filter_by(reference=data.get("verification_id") or arguments.get("verification_id"), status="ALLOWED").join(IntentProof).filter(IntentProof.organization_id == user.organization_id).first()
    if not verification:
        return jsonify({"error": "Only an allowed verification can authorize capture"}), 403
    return jsonify({"authorized": True, "escrow_reference": f"ESC-{secrets.token_hex(8).upper()}", "verification_id": verification.reference, "verification_hash": verification.verification_hash, "state": "HELD_UNTIL_PROVIDER_CAPTURE"})


@security_bp.get("/mcp/tools")
@jwt_required()
def mcp_tools():
    return jsonify({"protocol": "resource-ai-mcp/1", "tools": [{"name": "intent.create", "description": "Hash and sign a buyer's original purchase intent."}, {"name": "checkout.verify", "description": "Compare merchant checkout, DOM snapshot, and agent logs to an active proof."}, {"name": "checkout.authorize", "description": "Release a verified checkout to the payment adapter."}, {"name": "agent.log.digest", "description": "Create a tamper-evident digest for agent execution logs."}]})


@security_bp.post("/mcp/call")
@jwt_required()
def mcp_call():
    data = request.get_json() or {}
    tool = data.get("tool")
    arguments = data.get("arguments") or {}
    if tool == "agent.log.digest":
        logs = arguments.get("agent_log") or []
        return jsonify({"tool": tool, "result": {"digest": sha256(canonical(logs)), "entries": len(logs)}})
    if tool == "intent.create":
        prompt = str(arguments.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400
        return create_intent()
    if tool == "checkout.verify":
        return verify_intent()
    if tool == "checkout.authorize":
        return authorize_capture()
    return jsonify({"error": "Unknown MCP tool", "available": ["intent.create", "checkout.verify", "checkout.authorize", "agent.log.digest"]}), 400
