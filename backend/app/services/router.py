from decimal import Decimal, ROUND_HALF_UP
from ..models import LiquidityLeg


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_route_legs(legs):
    keys = [leg.get("key") for leg in legs]
    if not legs or any(not key for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("Each route leg needs a unique key")
    keyset = set(keys)
    for leg in legs:
        dependencies = leg.get("depends_on") or []
        if any(dependency not in keyset for dependency in dependencies):
            raise ValueError(f"Leg {leg['key']} depends on an unknown leg")
    visit = {}
    def walk(key):
        if visit.get(key) == "active":
            raise ValueError("Route dependencies contain a cycle")
        if visit.get(key) == "done":
            return
        visit[key] = "active"
        current = next(leg for leg in legs if leg["key"] == key)
        for dependency in current.get("depends_on") or []:
            walk(dependency)
        visit[key] = "done"
    for key in keys:
        walk(key)
    return True


def calculate_route(legs, base_currency, fx_rates, partner_fee_bps):
    validate_route_legs(legs)
    normalized = []
    total = Decimal("0")
    rate_map = {str(key).upper(): Decimal(str(value)) for key, value in (fx_rates or {}).items()}
    rate_map.setdefault(base_currency.upper(), Decimal("1"))
    for leg in legs:
        currency = str(leg.get("currency", base_currency)).upper()
        if currency not in rate_map:
            raise ValueError(f"Missing FX rate for {currency} to {base_currency}")
        amount = money(leg.get("amount", 0))
        converted = money(amount * rate_map[currency])
        fee = money(converted * Decimal(partner_fee_bps) / Decimal("10000"))
        total += converted + fee
        normalized.append({"key": leg["key"], "seller": leg.get("seller", ""), "description": leg.get("description", leg["key"]), "amount": amount, "currency": currency, "converted": converted, "fee": fee, "depends_on": leg.get("depends_on") or []})
    return normalized, money(total)


def route_payload(route):
    return {"id": route.reference, "intent": route.intent, "base_currency": route.base_currency, "partner_fee_bps": route.partner_fee_bps, "total_base_amount": float(route.total_base_amount), "status": route.status, "fx_rates": route.fx_rates, "legs": [{"key": leg.leg_key, "seller": leg.seller_name, "description": leg.description, "amount": float(leg.amount), "currency": leg.currency, "converted_amount": float(leg.converted_amount), "partner_fee": float(leg.partner_fee), "depends_on": leg.depends_on, "status": leg.status, "provider_order_id": leg.provider_order_id, "provider_capture_id": leg.provider_capture_id} for leg in route.legs]}


def leg_from_model(leg):
    return {"key": leg.leg_key, "seller": leg.seller_name, "description": leg.description, "amount": float(leg.amount), "currency": leg.currency, "depends_on": leg.depends_on}
