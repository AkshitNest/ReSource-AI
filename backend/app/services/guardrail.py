import hashlib
import hmac
import json
import re
from datetime import timedelta
from flask import current_app
from ..models import utcnow


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_intent(prompt):
    text = prompt.strip()
    lowered = text.lower()
    budget_match = re.search(r"(?:under|below|less than|max(?:imum)?|budget(?: of)?)\s*(?:₹|rs\.?|inr|\$)?\s*([\d,.]+)", lowered)
    currency = "INR" if "₹" in text or "inr" in lowered or "rs" in lowered else "USD"
    max_amount = float(budget_match.group(1).replace(",", "")) if budget_match else None
    merchant_match = re.search(r"(?:only\s+(?:purchase|buy)\s+from|from|at)\s+([a-z0-9][a-z0-9 .&'-]+?)(?:\.|,|$)", lowered)
    merchant = merchant_match.group(1).strip() if merchant_match else None
    quantity_match = re.search(r"(?:quantity|buy|purchase)\s*[:=]?\s*(\d+)\b", lowered)
    quantity = int(quantity_match.group(1)) if quantity_match else 1
    product_match = re.search(r"(?:buy|purchase|find|get)\s+(?:me\s+)?(.+?)(?:\s+(?:for|under|below|less than|from|at)\b|$)", lowered)
    product = product_match.group(1).strip(" .") if product_match else None
    return {"product_keywords": product.split() if product else [], "merchant": merchant, "max_amount": max_amount, "currency": currency, "quantity": quantity}


def proof_signature(prompt_hash, constraint_hash, organization_id, state_version):
    message = f"{prompt_hash}:{constraint_hash}:{organization_id}:{state_version}"
    return hmac.new(current_app.config["SECRET_KEY"].encode(), message.encode(), hashlib.sha256).hexdigest()


def proof_payload(proof):
    return {"id": proof.reference, "prompt": proof.original_prompt, "prompt_hash": proof.prompt_hash, "constraint_hash": proof.constraint_hash, "proof_signature": proof.proof_signature, "constraints": proof.constraints, "state_version": proof.state_version, "status": proof.status, "created_at": proof.created_at.isoformat()}


def verify_checkout(proof, payload):
    constraints = proof.constraints or {}
    reasons = []
    items = payload.get("items") or []
    merchant = str(payload.get("merchant", "")).strip().lower()
    amount = float(payload.get("amount", 0))
    quantity = sum(int(item.get("quantity", 0)) for item in items)
    names = " ".join(str(item.get("name", "")).lower() for item in items)
    expected_merchant = (constraints.get("merchant") or "").lower()
    if expected_merchant and merchant != expected_merchant:
        reasons.append({"code": "MERCHANT_MISMATCH", "message": f"Checkout merchant '{merchant}' is not the approved merchant '{expected_merchant}'."})
    if constraints.get("max_amount") is not None and amount > float(constraints["max_amount"]):
        reasons.append({"code": "BUDGET_EXCEEDED", "message": f"Checkout amount {amount:.2f} exceeds the approved ceiling {float(constraints['max_amount']):.2f}."})
    if quantity != int(constraints.get("quantity", 1)):
        reasons.append({"code": "QUANTITY_MISMATCH", "message": f"Checkout quantity {quantity} does not equal the approved quantity {constraints.get('quantity', 1)}."})
    keywords = [word for word in constraints.get("product_keywords", []) if len(word) > 2]
    if keywords and not any(keyword in names for keyword in keywords):
        reasons.append({"code": "PRODUCT_MISMATCH", "message": "The checkout item does not satisfy the product language in the original intent."})
    dom = payload.get("dom_snapshot") or {}
    if dom.get("merchant") and str(dom["merchant"]).strip().lower() != merchant:
        reasons.append({"code": "DOM_MERCHANT_DRIFT", "message": "The merchant in the observed page differs from the checkout payload."})
    if dom.get("total") is not None and round(float(dom["total"]), 2) != round(amount, 2):
        reasons.append({"code": "DOM_TOTAL_DRIFT", "message": "The observed page total differs from the checkout payload."})
    logs = payload.get("agent_log") or []
    serialized_logs = canonical(logs).lower()
    if any(token in serialized_logs for token in ("ignore previous", "override guardrail", "disable verification", "bypass approval")):
        reasons.append({"code": "PROMPT_INJECTION_SIGNAL", "message": "Agent execution logs contain a guardrail-bypass instruction."})
    payload_hash = sha256(canonical({key: value for key, value in payload.items() if key not in ("proof_signature",)}))
    dom_hash = sha256(canonical(dom))
    log_hash = sha256(canonical(logs))
    state = f"{proof.proof_signature}:{payload_hash}:{dom_hash}:{log_hash}:{proof.state_version}"
    verification_hash = sha256(state)
    return {"allowed": not reasons, "reasons": reasons, "checkout_payload_hash": payload_hash, "dom_hash": dom_hash, "agent_log_hash": log_hash, "verification_hash": verification_hash, "observed": {"merchant": merchant, "amount": amount, "quantity": quantity}}
