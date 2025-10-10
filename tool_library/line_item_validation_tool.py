
import json
from typing import Any, Dict, List, Optional


def validate_line_items(invoice: Dict[str, Any], po_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares invoice line items against purchase order line items.

    Checks for each line item:
    - The item exists on the PO.
    - The unit price matches the PO.
    - The quantity does not exceed the PO quantity.
    """
    tool_name = "line_item_validation_tool"
    exceptions: List[Dict[str, Any]] = []

    inv_lines = (invoice or {}).get("line_items", [])
    po_lines = (po_item or {}).get("line_items", [])

    if not isinstance(invoice, dict) or not inv_lines:
        return {
            "tool": tool_name,
            "status": "FAIL",
            "exceptions": [{"error": "invoice_or_line_items_not_found"}],
        }
    if not isinstance(po_item, dict) or not po_lines:
        return {
            "tool": tool_name,
            "status": "FAIL",
            "exceptions": [{"error": "po_item_or_line_items_not_found"}],
        }

    # Create a lookup map for PO lines by their item_id for efficient matching
    po_items_map: Dict[str, Dict[str, Any]] = {
        line.get("item_id"): line for line in po_lines if line.get("item_id")
    }

    for i, inv_line in enumerate(inv_lines):
        item_id = inv_line.get("item_id")
        if not item_id:
            exceptions.append({
                "invoice_line": i + 1,
                "error": "invoice_line_missing_item_id"
            })
            continue

        po_line = po_items_map.get(item_id)
        if not po_line:
            exceptions.append({
                "invoice_line": i + 1,
                "item_id": item_id,
                "error": "item_not_found_on_po"
            })
            continue

        discrepancies: Dict[str, str] = {}
        
        # Validate Unit Price
        try:
            inv_price = float(inv_line.get("unit_price", 0.0))
            po_price = float(po_line.get("unit_price", 0.0))
            if round(inv_price, 2) != round(po_price, 2):
                discrepancies["unit_price"] = f"FAIL - Invoice: {inv_price}, PO: {po_price}"
        except (ValueError, TypeError):
            discrepancies["unit_price"] = "FAIL - could_not_parse_prices"

        # Validate Quantity
        try:
            inv_qty = int(inv_line.get("quantity", 0))
            po_qty = int(po_line.get("quantity", 0))
            if inv_qty > po_qty:
                discrepancies["quantity"] = f"FAIL - Invoice quantity ({inv_qty}) exceeds PO quantity ({po_qty})"
        except (ValueError, TypeError):
            discrepancies["quantity"] = "FAIL - could_not_parse_quantities"

        if discrepancies:
            exceptions.append({
                "invoice_line": i + 1,
                "item_id": item_id,
                "discrepancies": discrepancies,
            })

    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    """Standalone runner for testing."""
    import argparse
    parser = argparse.ArgumentParser(description="Line item validation")
    parser.add_argument("--invoice", required=True, help="Path to invoice JSON")
    parser.add_argument("--po-item", required=True, help="Path to JSON containing a single PO item with line items")
    args = parser.parse_args()

    with open(args.invoice, "r", encoding="utf-8") as f:
        invoice_data = json.load(f)
    with open(args.po_item, "r", encoding="utf-8") as f:
        po_item_data = json.load(f)

    result = validate_line_items(invoice_data, po_item_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
