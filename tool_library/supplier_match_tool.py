import json
import re
from typing import Any, Dict, List, Tuple


def _highlight_diff(str1: str, str2: str) -> str:
    """
    Highlight the differences between two strings for better visibility.
    Returns a string showing differences between str1 and str2.
    """
    if str1 == str2:
        return "Strings are identical"
    
    # Show character-by-character comparison
    diff_parts = []
    max_len = max(len(str1), len(str2))
    
    for i in range(max_len):
        char1 = str1[i] if i < len(str1) else ''
        char2 = str2[i] if i < len(str2) else ''
        
        if char1 != char2:
            # Find where the difference starts
            if char1 == ' ':
                diff_parts.append(f"Position {i}: '[SPACE]' vs '{char2}'")
            elif char2 == ' ':
                diff_parts.append(f"Position {i}: '{char1}' vs '[SPACE]'")
            else:
                diff_parts.append(f"Position {i}: '{char1}' vs '{char2}'")
    
    if diff_parts:
        return f"First difference at position {diff_parts[0].split(':')[0].split()[-1]}"
    
    return f"Length difference: {len(str1)} vs {len(str2)} chars"


def _get_string_details(value: Any) -> str:
    """Get detailed information about a string value."""
    if not isinstance(value, str):
        return str(value)
    
    # Show the value with metadata
    details = f"{value!r}"  # Use repr to show quotes and special chars
    # Count spaces to make them visible
    space_count = value.count(' ')
    if space_count > 0:
        details += f" ({space_count} spaces)"
    
    return details


def validate_supplier(invoice: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate supplier and bill-to consistency between invoice and contract.

    Returns a dict: { tool, status, exceptions } where exceptions contain detailed mismatch information
    """
    exceptions: List[str | Dict[str, Any]] = []
    tool_name = "supplier_match_tool"

    inv_supplier = (invoice or {}).get("supplier_info", {})
    inv_billto = (invoice or {}).get("bill_to_info", {})
    parties = (contract or {}).get("parties", {})
    con_supplier = parties.get("supplier", {})
    con_client = parties.get("client", {})

    if not invoice:
        exceptions.append("invoice: <not found>")
    if not contract:
        exceptions.append("contract: <not found>")

    # Check supplier name mismatch with detailed information
    inv_name = inv_supplier.get("name", "")
    con_name = con_supplier.get("name", "")
    if inv_name != con_name:
        # Create detailed exception with actual values and differences
        diff_analysis = _highlight_diff(inv_name, con_name)
        inv_details = _get_string_details(inv_name)
        con_details = _get_string_details(con_name)
        
        exceptions.append({
            "type": "supplier_name_mismatch",
            "invoice_value": inv_name,
            "expected_value": con_name,
            "invoice_value_details": inv_details,
            "expected_value_details": con_details,
            "difference": diff_analysis,
            "comparison_method": "exact_match",
            "threshold": "100% exact match required"
        })
    
    # Check vendor ID mismatch with detailed information
    inv_vendor_id = inv_supplier.get("vendor_id", "")
    con_vendor_id = con_supplier.get("vendor_id", "")
    if inv_vendor_id != con_vendor_id:
        diff_analysis = _highlight_diff(inv_vendor_id, con_vendor_id)
        inv_vid_details = _get_string_details(inv_vendor_id)
        con_vid_details = _get_string_details(con_vendor_id)
        
        exceptions.append({
            "type": "supplier_vendor_id_mismatch",
            "invoice_value": inv_vendor_id,
            "expected_value": con_vendor_id,
            "invoice_value_details": inv_vid_details,
            "expected_value_details": con_vid_details,
            "difference": diff_analysis,
            "comparison_method": "exact_match",
            "threshold": "100% exact match required"
        })
    
    # Check bill-to name mismatch
    inv_billto_name = inv_billto.get("name", "")
    con_client_name = con_client.get("name", "")
    if inv_billto_name != con_client_name:
        diff_analysis = _highlight_diff(inv_billto_name, con_client_name)
        inv_billto_details = _get_string_details(inv_billto_name)
        con_client_details = _get_string_details(con_client_name)
        
        exceptions.append({
            "type": "bill_to_name_mismatch",
            "invoice_value": inv_billto_name,
            "expected_value": con_client_name,
            "invoice_value_details": inv_billto_details,
            "expected_value_details": con_client_details,
            "difference": diff_analysis,
            "comparison_method": "exact_match",
            "threshold": "100% exact match required"
        })

    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Supplier/bill-to validation")
    parser.add_argument("--invoice", required=True, help="Path to invoice JSON")
    parser.add_argument("--contract", required=True, help="Path to contract JSON")
    args = parser.parse_args()

    with open(args.invoice, "r", encoding="utf-8") as f:
        invoice = json.load(f)
    with open(args.contract, "r", encoding="utf-8") as f:
        contract = json.load(f)

    result = validate_supplier(invoice, contract)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()


