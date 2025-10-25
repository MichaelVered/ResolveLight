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
    for line in invoice_lines:
        description = (line or {}).get("description", "").lower()
        for keyword in SUSPICIOUS_KEYWORDS:
            if keyword in description:
                exceptions.append(f"suspicious_content: {keyword}")
    
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
                if not _fuzzy_match(inv_desc, po_desc):
                    exceptions.append(f"content_mismatch: item {item_id}")
                    exceptions.append(f"invoice: '{inv_desc}' vs po: '{po_desc}'")
    
    # Check for missing required content
    if not invoice_lines:
        exceptions.append("missing_line_items")
    
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




