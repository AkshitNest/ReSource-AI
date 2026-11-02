"""Provider-agnostic agent contracts. Arithmetic and marketplace truth stay deterministic."""
from pydantic import BaseModel, Field


class RequirementItem(BaseModel):
    name: str
    quantity: int = Field(gt=0)
    mandatory: bool = True
    reason: str
    evidence: str = "buyer context"


class RequirementSpec(BaseModel):
    items: list[RequirementItem]
    assumptions: list[str] = []
    clarification_questions: list[str] = []


def demand_agent(description: str, beneficiaries: int) -> RequirementSpec:
    """Safe deterministic baseline used when no LLM provider is configured."""
    context = description.lower()
    if any(word in context for word in ("class 8", "school", "student", "syllabus")):
        return RequirementSpec(items=[
            RequirementItem(name="Subject textbooks", quantity=beneficiaries, reason="The learning context requires core course materials.", evidence="buyer description; exact titles need confirmation"),
            RequirementItem(name="Subject notebooks", quantity=beneficiaries * 5, reason="Students need one working notebook per core subject.", evidence="procurement convention"),
            RequirementItem(name="School bags", quantity=beneficiaries, reason="A durable carrier makes the learning kit usable.", evidence="buyer context"),
            RequirementItem(name="Stationery kits", quantity=beneficiaries, reason="Writing and measurement tools are required for daily work.", evidence="buyer context"),
            RequirementItem(name="Geometry boxes", quantity=beneficiaries, reason="Common Class 8 mathematics work requires geometry tools.", evidence="needs confirmation from syllabus"),
            RequirementItem(name="Personal diaries", quantity=beneficiaries, mandatory=False, reason="Useful for assignments and routines, but not essential to start.", evidence="optional recommendation"),
        ], assumptions=["Textbook titles are not asserted until the syllabus or buyer confirms them.", "Five core subjects were used to estimate notebook quantity."], clarification_questions=["Can you confirm the prescribed textbook titles or approve equivalent editions?"])
    return RequirementSpec(items=[RequirementItem(name="Essential goods from buyer description", quantity=beneficiaries, reason="Derived from the submitted requirement; a human review is recommended before sourcing.")], assumptions=["The requirement needs more detail for item-level sourcing."], clarification_questions=["What specific products, quality, and quantities should we prioritize?"])


def shopping_agent(requirement, listings):
    """Deterministic constrained heuristic: cheapest eligible listing per required item, then budget check."""
    spec = RequirementSpec.model_validate(requirement.extracted_spec)
    chosen = []
    for item in spec.items:
        matches = [listing for listing in listings if item.name.lower() in listing.product.name.lower() or listing.product.category.lower() in item.name.lower()]
        matches = [listing for listing in matches if listing.sellable_quantity >= max(item.quantity, listing.minimum_order_quantity)]
        if not matches:
            chosen.append({"name": item.name, "quantity": item.quantity, "mandatory": item.mandatory, "unavailable": True, "reason": item.reason})
            continue
        listing = sorted(matches, key=lambda row: (float(row.unit_price), row.lead_days))[0]
        donated = min(listing.donation_quantity, item.quantity) if listing.surplus else 0
        chosen.append({"name": item.name, "quantity": item.quantity, "mandatory": item.mandatory, "listing_id": listing.id, "unit_price": float(listing.unit_price), "donated_quantity": donated, "seller": listing.seller.name, "reason": item.reason, "unavailable": False})
    payable = sum(row.get("unit_price", 0) * (row["quantity"] - row.get("donated_quantity", 0)) for row in chosen)
    return {"items": chosen, "payable": round(payable, 2), "within_budget": payable <= float(requirement.budget), "assumptions": spec.assumptions, "clarification_questions": spec.clarification_questions}
