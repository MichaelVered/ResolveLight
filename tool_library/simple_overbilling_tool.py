import json
from typing import Any, Dict, List


def validate_billing(invoice: Dict[str, Any], po_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure invoice billing amount does not exceed PO total_value.
    Also verify arithmetic of subtotal + tax_amount == billing_amount.
    """
    tool_name = "simple_overbilling_tool"
    exceptions: List[Dict[str, Any] | str] = []

    inv_sum = (invoice or {}).get("summary", {})
    inv_total = float(inv_sum.get("billing_amount", 0.0))
    inv_sub = float(inv_sum.get("subtotal", 0.0))
    inv_tax = float(inv_sum.get("tax_amount", 0.0))
    
    # Check arithmetic: subtotal + tax == total
    calculated_total = round(inv_sub + inv_tax, 2)
    inv_total_rounded = round(inv_total, 2)
    
    if calculated_total != inv_total_rounded:
        exceptions.append({
            "type": "billing_amount_mismatch",
            "invoice_subtotal": inv_sub,
            "invoice_tax": inv_tax,
            "calculated_total": calculated_total,
            "invoice_billing_amount": inv_total,
            "difference": round(inv_total - calculated_total, 2),
            "comparison_method": "arithmetic_validation",
            "threshold": "Subtotal + tax must equal billing amount (within rounding)"
        })

    po_total = float((po_item or {}).get("total_value", 0.0))
    if inv_total > po_total:
        excess = round(inv_total - po_total, 2)
        percentage_excess = round((excess / po_total * 100), 2) if po_total > 0 else 0
        exceptions.append({
            "type": "invoice_exceeds_po",
            "invoice_total": inv_total,
            "po_total_value": po_total,
            "excess": excess,
            "percentage_excess": percentage_excess,
            "comparison_method": "total_value_validation",
            "threshold": "Invoice total must not exceed PO total value"
        })

    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Overbilling validation")
    parser.add_argument("--invoice", required=True)
    parser.add_argument("--po", required=True, help="Path to a JSON with a single PO item, or POs file + --po-number")
    parser.add_argument("--po-number", required=False)
    args = parser.parse_args()

    invoice = json.load(open(args.invoice, "r", encoding="utf-8"))
    po_data = json.load(open(args.po, "r", encoding="utf-8"))
    if "purchase_orders" in po_data:
        if args.po_number:
            items = [x for x in po_data["purchase_orders"] if x.get("po_number") == args.po_number]
            po_item = items[0] if items else {}
        else:
            po_item = po_data["purchase_orders"][0] if po_data.get("purchase_orders") else {}
    else:
        po_item = po_data

    print(json.dumps(validate_billing(invoice, po_item), indent=2))


if __name__ == "__main__":
    main()


