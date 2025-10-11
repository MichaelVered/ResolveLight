"""
Line Item Validation Tool

ROLE: Flexible line-by-line validation that handles various real-world scenarios
PURPOSE: Catches discrepancies that total-only validation would miss, with graceful handling of missing line items
INPUT: Invoice data, PO item data
OUTPUT: Detailed validation results with specific line item discrepancies

SCENARIOS HANDLED:
1. Both invoice and PO have line items: Full detailed validation
2. Only invoice has line items: Validates against PO description/total
3. Only PO has line items: Validates invoice total against PO line items
4. Neither has line items: PASSES (total validation handles this)

VALIDATION CHECKS (when both have line items):
- Item existence: Invoice line items exist on PO
- Unit price matching: Invoice unit price = PO unit price
- Quantity validation: Invoice quantity ≤ PO quantity
- Line total calculation: Invoice line total = unit_price × quantity
- Description matching: Fuzzy matching of item descriptions
- Uninvoiced items: Identifies PO items not on invoice (potential underbilling)

VALIDATION CHECKS (when only invoice has line items):
- Line items total matches billing amount
- Invoice total doesn't exceed PO total value
- Line item descriptions match PO description (fuzzy)

VALIDATION CHECKS (when only PO has line items):
- Invoice total matches PO line items total
- Invoice total doesn't exceed PO total value

KEY BENEFIT: Prevents subtle billing errors while handling real-world data variations:
- Wrong unit prices (same total, different per-unit cost)
- Quantity overbilling (more items than ordered)
- Item substitutions (different products, same total)
- Missing line items in either document

NOTE: This is the ONLY tool that validates individual line items with flexible scenario handling
"""
import json
from typing import Any, Dict, List, Optional


def validate_line_items(invoice: Dict[str, Any], po_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares invoice line items against purchase order line items.
    
    This tool performs detailed line-by-line validation to catch discrepancies
    that would be missed by total-only validation. It handles various scenarios:
    - Both invoice and PO have line items: Full validation
    - Only invoice has line items: Validates against PO description/total
    - Only PO has line items: Validates invoice total against PO line items
    - Neither has line items: Passes (total-only validation handles this)
    
    Args:
        invoice: Invoice data dictionary
        po_item: Purchase order item data dictionary
    
    Returns:
        Dict with validation results including detailed exceptions
    """
    tool_name = "line_item_validation_tool"
    exceptions: List[Dict[str, Any]] = []
    
    # Extract line items
    inv_lines = (invoice or {}).get("line_items", [])
    po_lines = (po_item or {}).get("line_items", [])
    
    # Handle different scenarios
    has_invoice_lines = isinstance(invoice, dict) and inv_lines
    has_po_lines = isinstance(po_item, dict) and po_lines
    
    # Scenario 3: Neither has line items - PASS (total validation handles this)
    if not has_invoice_lines and not has_po_lines:
        return {
            "tool": tool_name,
            "status": "PASS",
            "exceptions": [],
            "summary": {
                "scenario": "no_line_items",
                "message": "Neither invoice nor PO has line items - total validation handles this case"
            }
        }
    
    # Scenario 2: Only PO has line items - validate invoice total against PO line items
    if not has_invoice_lines and has_po_lines:
        return _validate_invoice_total_against_po_lines(invoice, po_item, po_lines, tool_name)
    
    # Scenario 1: Only invoice has line items - validate against PO description/total
    if has_invoice_lines and not has_po_lines:
        return _validate_invoice_lines_against_po_description(invoice, po_item, inv_lines, tool_name)
    
    # Both have line items - full validation (original logic)
    
    # Create lookup maps for efficient matching
    po_items_by_id = {line.get("item_id"): line for line in po_lines if line.get("item_id")}
    po_items_by_description = {line.get("description", "").lower(): line for line in po_lines if line.get("description")}
    
    # Track which PO items have been matched
    matched_po_items = set()
    
    # Validate each invoice line item
    for i, inv_line in enumerate(inv_lines):
        line_exceptions = []
        item_id = inv_line.get("item_id")
        description = inv_line.get("description", "")
        
        if not item_id:
            exceptions.append({
                "invoice_line": i + 1,
                "error": "invoice_line_missing_item_id",
                "description": description
            })
            continue
        
        # Try to find matching PO line item
        po_line = None
        match_method = "none"
        
        # First try exact item_id match
        if item_id in po_items_by_id:
            po_line = po_items_by_id[item_id]
            match_method = "item_id_exact"
            matched_po_items.add(item_id)
        
        # If no exact match, try fuzzy description matching
        if not po_line and description:
            best_match = None
            best_similarity = 0.0
            
            for po_desc, po_item_line in po_items_by_description.items():
                similarity = _calculate_description_similarity(description.lower(), po_desc)
                if similarity > best_similarity and similarity > 0.8:  # 80% similarity threshold
                    best_similarity = similarity
                    best_match = po_item_line
            
            if best_match:
                po_line = best_match
                match_method = f"description_fuzzy_{best_similarity:.1%}"
                matched_po_items.add(po_line.get("item_id"))
        
        if not po_line:
            exceptions.append({
                "invoice_line": i + 1,
                "item_id": item_id,
                "description": description,
                "error": "item_not_found_on_po",
                "match_method": match_method
            })
            continue
        
        # Validate unit price
        try:
            inv_price = float(inv_line.get("unit_price", 0.0))
            po_price = float(po_line.get("unit_price", 0.0))
            
            if round(inv_price, 2) != round(po_price, 2):
                line_exceptions.append({
                    "field": "unit_price",
                    "status": "FAIL",
                    "invoice_value": inv_price,
                    "po_value": po_price,
                    "difference": round(inv_price - po_price, 2),
                    "percentage_diff": round(((inv_price - po_price) / po_price * 100), 2) if po_price > 0 else 0
                })
        except (ValueError, TypeError):
            line_exceptions.append({
                "field": "unit_price",
                "status": "FAIL",
                "error": "could_not_parse_prices"
            })
        
        # Validate quantity
        try:
            inv_qty = int(inv_line.get("quantity", 0))
            po_qty = int(po_line.get("quantity", 0))
            
            if inv_qty > po_qty:
                line_exceptions.append({
                    "field": "quantity",
                    "status": "FAIL",
                    "invoice_value": inv_qty,
                    "po_value": po_qty,
                    "excess": inv_qty - po_qty,
                    "percentage_excess": round(((inv_qty - po_qty) / po_qty * 100), 2) if po_qty > 0 else 0
                })
            elif inv_qty < po_qty:
                # Quantity under PO is usually OK, but log for awareness
                line_exceptions.append({
                    "field": "quantity",
                    "status": "INFO",
                    "invoice_value": inv_qty,
                    "po_value": po_qty,
                    "shortage": po_qty - inv_qty,
                    "message": "Invoice quantity is less than PO quantity"
                })
        except (ValueError, TypeError):
            line_exceptions.append({
                "field": "quantity",
                "status": "FAIL",
                "error": "could_not_parse_quantities"
            })
        
        # Validate line total calculation
        try:
            inv_line_total = float(inv_line.get("line_total", 0.0))
            calculated_total = inv_price * inv_qty
            
            if round(inv_line_total, 2) != round(calculated_total, 2):
                line_exceptions.append({
                    "field": "line_total",
                    "status": "FAIL",
                    "invoice_value": inv_line_total,
                    "calculated_value": calculated_total,
                    "difference": round(inv_line_total - calculated_total, 2)
                })
        except (ValueError, TypeError):
            line_exceptions.append({
                "field": "line_total",
                "status": "FAIL",
                "error": "could_not_parse_line_total"
            })
        
        # Add line item to exceptions if there are any failures
        if line_exceptions:
            exceptions.append({
                "invoice_line": i + 1,
                "item_id": item_id,
                "description": description,
                "match_method": match_method,
                "po_item_id": po_line.get("item_id"),
                "po_description": po_line.get("description"),
                "discrepancies": line_exceptions
            })
    
    # Check for PO items that weren't invoiced (potential underbilling)
    uninvoiced_items = []
    for po_line in po_lines:
        po_item_id = po_line.get("item_id")
        if po_item_id and po_item_id not in matched_po_items:
            uninvoiced_items.append({
                "po_item_id": po_item_id,
                "description": po_line.get("description"),
                "quantity": po_line.get("quantity"),
                "unit_price": po_line.get("unit_price"),
                "line_total": po_line.get("line_total")
            })
    
    # Add uninvoiced items as INFO-level exceptions
    if uninvoiced_items:
        exceptions.append({
            "type": "uninvoiced_items",
            "status": "INFO",
            "message": "PO items not found on invoice",
            "items": uninvoiced_items
        })
    
    # Determine overall status
    has_failures = any(
        exc.get("discrepancies") and 
        any(d.get("status") == "FAIL" for d in exc.get("discrepancies", []))
        for exc in exceptions
    )
    
    return {
        "tool": tool_name,
        "status": "PASS" if not has_failures else "FAIL",
        "exceptions": exceptions,
        "summary": {
            "total_invoice_lines": len(inv_lines),
            "total_po_lines": len(po_lines),
            "matched_lines": len(matched_po_items),
            "failed_validations": len([e for e in exceptions if e.get("discrepancies")]),
            "uninvoiced_items": len(uninvoiced_items)
        }
    }


def _validate_invoice_total_against_po_lines(invoice: Dict[str, Any], po_item: Dict[str, Any], po_lines: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    """
    Scenario 2: Only PO has line items - validate invoice total against PO line items.
    """
    exceptions: List[Dict[str, Any]] = []
    
    # Calculate total from PO line items
    po_total_from_lines = sum(
        float(line.get("line_total", 0)) for line in po_lines
    )
    
    # Get invoice total
    invoice_total = float((invoice or {}).get("summary", {}).get("billing_amount", 0))
    
    # Check if invoice total matches PO line items total
    if abs(invoice_total - po_total_from_lines) > 0.01:
        exceptions.append({
            "type": "total_mismatch",
            "invoice_total": invoice_total,
            "po_lines_total": po_total_from_lines,
            "difference": round(invoice_total - po_total_from_lines, 2),
            "message": f"Invoice total (${invoice_total}) doesn't match PO line items total (${po_total_from_lines})"
        })
    
    # Check if invoice total exceeds PO total_value
    po_total_value = float((po_item or {}).get("total_value", 0))
    if invoice_total > po_total_value:
        exceptions.append({
            "type": "exceeds_po_total",
            "invoice_total": invoice_total,
            "po_total_value": po_total_value,
            "excess": round(invoice_total - po_total_value, 2),
            "message": f"Invoice total (${invoice_total}) exceeds PO total value (${po_total_value})"
        })
    
    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
        "summary": {
            "scenario": "po_lines_only",
            "total_po_lines": len(po_lines),
            "po_lines_total": po_total_from_lines,
            "invoice_total": invoice_total,
            "po_total_value": po_total_value
        }
    }


def _validate_invoice_lines_against_po_description(invoice: Dict[str, Any], po_item: Dict[str, Any], inv_lines: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    """
    Scenario 1: Only invoice has line items - validate against PO description/total.
    """
    exceptions: List[Dict[str, Any]] = []
    
    # Get PO description and total
    po_description = (po_item or {}).get("description", "")
    po_total_value = float((po_item or {}).get("total_value", 0))
    
    # Calculate invoice total from line items
    invoice_total_from_lines = sum(
        float(line.get("line_total", 0)) for line in inv_lines
    )
    
    # Get invoice billing amount
    invoice_billing_amount = float((invoice or {}).get("summary", {}).get("billing_amount", 0))
    
    # Check if line items total matches billing amount
    if abs(invoice_total_from_lines - invoice_billing_amount) > 0.01:
        exceptions.append({
            "type": "line_items_billing_mismatch",
            "line_items_total": invoice_total_from_lines,
            "billing_amount": invoice_billing_amount,
            "difference": round(invoice_total_from_lines - invoice_billing_amount, 2),
            "message": f"Line items total (${invoice_total_from_lines}) doesn't match billing amount (${invoice_billing_amount})"
        })
    
    # Check if invoice total exceeds PO total
    if invoice_billing_amount > po_total_value:
        exceptions.append({
            "type": "exceeds_po_total",
            "invoice_total": invoice_billing_amount,
            "po_total_value": po_total_value,
            "excess": round(invoice_billing_amount - po_total_value, 2),
            "message": f"Invoice total (${invoice_billing_amount}) exceeds PO total value (${po_total_value})"
        })
    
    # Validate line item descriptions against PO description (fuzzy matching)
    po_desc_words = set(po_description.lower().split())
    for i, line in enumerate(inv_lines):
        line_desc = line.get("description", "")
        line_desc_words = set(line_desc.lower().split())
        
        # Calculate word overlap
        overlap = len(po_desc_words.intersection(line_desc_words))
        total_words = len(po_desc_words.union(line_desc_words))
        similarity = overlap / total_words if total_words > 0 else 0
        
        if similarity < 0.3:  # Low similarity threshold
            exceptions.append({
                "type": "description_mismatch",
                "invoice_line": i + 1,
                "line_description": line_desc,
                "po_description": po_description,
                "similarity": round(similarity, 2),
                "message": f"Line item description '{line_desc}' doesn't match PO description '{po_description}'"
            })
    
    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
        "summary": {
            "scenario": "invoice_lines_only",
            "total_invoice_lines": len(inv_lines),
            "invoice_total": invoice_billing_amount,
            "po_total_value": po_total_value,
            "po_description": po_description
        }
    }


def _calculate_description_similarity(desc1: str, desc2: str) -> float:
    """
    Calculate similarity between two descriptions using simple word overlap.
    More sophisticated than basic string similarity for product descriptions.
    """
    if not desc1 or not desc2:
        return 0.0
    
    # Split into words and normalize
    words1 = set(desc1.lower().split())
    words2 = set(desc2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def main() -> None:
    """Standalone runner for testing line item validation."""
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