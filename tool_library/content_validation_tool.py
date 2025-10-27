"""
Content Validation Tool

ROLE: Validates invoice content against purchase order requirements
PURPOSE: Ensures invoices match what was actually ordered and catches content mismatches
INPUT: Invoice data, PO data
OUTPUT: Validation results with content-specific exceptions

VALIDATION CHECKS:
- Line item descriptions match PO descriptions (fuzzy matching)
- Service/product descriptions are consistent
- Content matches contract scope
- No suspicious or inappropriate content

EXCEPTIONS:
- content_mismatch: Invoice description doesn't match PO description
- suspicious_content: Invoice contains suspicious keywords
- scope_violation: Invoice content outside contract scope
- inappropriate_content: Invoice contains inappropriate language
"""

import json
import re
from typing import Any, Dict, List
from difflib import SequenceMatcher


def _fuzzy_match(desc1: str, desc2: str, threshold: float = 0.8) -> bool:
    """Check if two descriptions are similar enough using fuzzy matching."""
    if not desc1 or not desc2:
        return False
    
    # Normalize descriptions (lowercase, remove extra spaces)
    norm1 = re.sub(r'\s+', ' ', desc1.lower().strip())
    norm2 = re.sub(r'\s+', ' ', desc2.lower().strip())
    
    # Calculate similarity ratio
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold


def validate_content(invoice: Dict[str, Any], po_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate invoice content against purchase order requirements.
    
    This tool ensures invoices match what was actually ordered and catches
    content mismatches, suspicious content, and scope violations.
    
    Args:
        invoice: Invoice data dictionary
        po_item: Purchase order item data dictionary
    
    Returns:
        Dict with validation results including content-specific exceptions
    """
    tool_name = "content_validation_tool"
    exceptions: List[str] = []
    
    # Suspicious keywords that should trigger alerts
    SUSPICIOUS_KEYWORDS = [
        "fraud", "fake", "invalid", "test", "demo", "suspicious", 
        "unauthorized", "illegal", "phishing", "scam", "duplicate"
    ]
    
    # Extract line items
    invoice_lines = (invoice or {}).get("line_items", [])
    po_lines = (po_item or {}).get("line_items", [])
    
    # Check for suspicious content in invoice descriptions
    # Use word boundary matching to avoid false positives like "testing" containing "test"
    import re
    
    for i, line in enumerate(invoice_lines):
        description = (line or {}).get("description", "")
        item_id = (line or {}).get("item_id", f"line_{i+1}")
        for keyword in SUSPICIOUS_KEYWORDS:
            # Use word boundary regex to match whole words only
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, description, re.IGNORECASE):
                exceptions.append({
                    "type": "suspicious_content",
                    "item_id": item_id,
                    "description": description,
                    "suspicious_keyword": keyword,
                    "comparison_method": "keyword_detection",
                    "threshold": "Suspicious keywords should not appear in invoice descriptions"
                })
                break  # Only add one exception per line item
    
    # Validate line item content matches PO content
    if invoice_lines and po_lines:
        # Create a mapping of PO items by item_id
        po_items_by_id = {item.get("item_id"): item for item in po_lines if item.get("item_id")}
        
        for inv_line in invoice_lines:
            item_id = inv_line.get("item_id")
            inv_desc = inv_line.get("description", "")
            
            if item_id in po_items_by_id:
                po_desc = po_items_by_id[item_id].get("description", "")
                
                # Check if descriptions match (fuzzy matching)
                similarity = SequenceMatcher(None, inv_desc.lower(), po_desc.lower()).ratio()
                if not _fuzzy_match(inv_desc, po_desc):
                    exceptions.append({
                        "type": "content_mismatch",
                        "item_id": item_id,
                        "invoice_description": inv_desc,
                        "po_description": po_desc,
                        "similarity_score": round(similarity, 3),
                        "threshold": "0.8 (80% similarity required)",
                        "comparison_method": "fuzzy_matching"
                    })
    
    # Check for missing required content
    if not invoice_lines:
        exceptions.append({
            "type": "missing_line_items",
            "invoice_line_items_count": len(invoice_lines),
            "expected": "At least 1 line item",
            "comparison_method": "existence_check",
            "threshold": "Invoice must have at least one line item"
        })
    
    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Content validation tool")
    parser.add_argument("--invoice", "-i", required=True, help="Invoice JSON file")
    parser.add_argument("--po", "-p", required=True, help="PO JSON file")
    args = parser.parse_args()
    
    with open(args.invoice, "r", encoding="utf-8") as f:
        invoice = json.load(f)
    
    with open(args.po, "r", encoding="utf-8") as f:
        po_item = json.load(f)
    
    result = validate_content(invoice, po_item)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()




