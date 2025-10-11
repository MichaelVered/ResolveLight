import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def _ensure_processed_invoices_log(repo_root: str) -> str:
    """Ensure the processed invoices log file exists and return its path."""
    logs_dir = os.path.join(repo_root, "system_logs")
    os.makedirs(logs_dir, exist_ok=True)
    return os.path.join(logs_dir, "processed_invoices.log")


def _load_processed_invoices(repo_root: str) -> List[Dict[str, Any]]:
    """
    Load the history of processed invoices from the log file.
    Returns a list of invoice records with their processing details.
    """
    log_path = _ensure_processed_invoices_log(repo_root)
    processed_invoices = []
    
    if not os.path.exists(log_path):
        return processed_invoices
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.startswith("PROCESSED:"):
                    # Parse the log entry
                    try:
                        # Extract JSON part after "PROCESSED: "
                        json_part = line[10:]  # Remove "PROCESSED: " prefix
                        invoice_record = json.loads(json_part)
                        processed_invoices.append(invoice_record)
                    except json.JSONDecodeError:
                        continue  # Skip malformed entries
    except Exception:
        pass  # Return empty list if file can't be read
    
    return processed_invoices


def _log_processed_invoice(repo_root: str, invoice_data: Dict[str, Any], processing_result: str) -> None:
    """
    Log an invoice as processed to maintain the history.
    This creates an audit trail of all processed invoices.
    """
    log_path = _ensure_processed_invoices_log(repo_root)
    
    # Create a record of the processed invoice
    invoice_record = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "invoice_id": invoice_data.get("invoice_id"),
        "supplier_name": invoice_data.get("supplier_info", {}).get("name"),
        "vendor_id": invoice_data.get("supplier_info", {}).get("vendor_id"),
        "invoice_number": invoice_data.get("invoice_id"),  # Using invoice_id as invoice number
        "billing_amount": invoice_data.get("summary", {}).get("billing_amount"),
        "po_number": invoice_data.get("purchase_order_number"),
        "processing_result": processing_result,
        "line_items_count": len(invoice_data.get("line_items", [])),
        "issue_date": invoice_data.get("issue_date")
    }
    
    # Append to log file
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"PROCESSED: {json.dumps(invoice_record)}\n")


def _calculate_duplicate_confidence(invoice1: Dict[str, Any], invoice2: Dict[str, Any]) -> float:
    """
    Calculate confidence score for potential duplicate detection.
    Returns a float between 0.0 and 1.0 (higher = more likely duplicate).
    """
    confidence = 0.0
    matches = 0
    total_checks = 0
    
    # Check supplier name match
    supplier1 = invoice1.get("supplier_info", {}).get("name", "")
    supplier2 = invoice2.get("supplier_info", {}).get("name", "")
    total_checks += 1
    if supplier1.lower() == supplier2.lower():
        matches += 1
        confidence += 0.3  # Supplier match is important
    
    # Check vendor ID match
    vendor_id1 = invoice1.get("supplier_info", {}).get("vendor_id", "")
    vendor_id2 = invoice2.get("supplier_info", {}).get("vendor_id", "")
    total_checks += 1
    if vendor_id1 == vendor_id2:
        matches += 1
        confidence += 0.2  # Vendor ID match is very important
    
    # Check invoice number match
    invoice_num1 = invoice1.get("invoice_id", "")
    invoice_num2 = invoice2.get("invoice_id", "")
    total_checks += 1
    if invoice_num1 == invoice_num2:
        matches += 1
        confidence += 0.4  # Invoice number match is critical
    
    # Check amount match (with small tolerance for rounding)
    amount1 = float(invoice1.get("summary", {}).get("billing_amount", 0))
    amount2 = float(invoice2.get("summary", {}).get("billing_amount", 0))
    total_checks += 1
    if abs(amount1 - amount2) < 0.01:  # Within 1 cent
        matches += 1
        confidence += 0.1  # Amount match is supporting evidence
    
    # Check PO number match
    po1 = invoice1.get("purchase_order_number", "")
    po2 = invoice2.get("purchase_order_number", "")
    total_checks += 1
    if po1 == po2:
        matches += 1
        confidence += 0.1  # PO match is supporting evidence
    
    return min(confidence, 1.0)  # Cap at 1.0


def check_for_duplicates(invoice_filename: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if an invoice is a potential duplicate of previously processed invoices.
    
    Args:
        invoice_filename: Path to the invoice file to check
        repo_root: Root directory of the project
    
    Returns:
        Dict with duplicate detection results
    """
    tool_name = "duplicate_invoice_check_tool"
    
    if not repo_root:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    
    # Load the invoice data
    try:
        with open(invoice_filename, "r", encoding="utf-8") as f:
            invoice_data = json.load(f)
    except Exception as e:
        return {
            "tool": tool_name,
            "status": "FAIL",
            "exceptions": [{"error": f"could_not_load_invoice: {str(e)}"}]
        }
    
    # Load processed invoices history
    processed_invoices = _load_processed_invoices(repo_root)
    
    if not processed_invoices:
        return {
            "tool": tool_name,
            "status": "PASS",
            "exceptions": [],
            "summary": {
                "total_processed_invoices": 0,
                "potential_duplicates": 0,
                "highest_confidence": 0.0
            }
        }
    
    # Check for potential duplicates
    potential_duplicates = []
    highest_confidence = 0.0
    
    for processed_invoice in processed_invoices:
        confidence = _calculate_duplicate_confidence(invoice_data, processed_invoice)
        
        if confidence > 0.5:  # Threshold for potential duplicate
            potential_duplicates.append({
                "processed_invoice": processed_invoice,
                "confidence": confidence,
                "match_reasons": _get_match_reasons(invoice_data, processed_invoice)
            })
            
            if confidence > highest_confidence:
                highest_confidence = confidence
    
    # Determine if this is likely a duplicate
    is_duplicate = highest_confidence > 0.8  # High confidence threshold
    
    exceptions = []
    if is_duplicate:
        exceptions.append({
            "type": "potential_duplicate",
            "confidence": highest_confidence,
            "message": f"High confidence duplicate detected ({highest_confidence:.1%})",
            "duplicates": potential_duplicates
        })
    elif potential_duplicates:
        exceptions.append({
            "type": "possible_duplicate",
            "confidence": highest_confidence,
            "message": f"Possible duplicate detected ({highest_confidence:.1%})",
            "duplicates": potential_duplicates
        })
    
    return {
        "tool": tool_name,
        "status": "FAIL" if is_duplicate else "PASS",
        "exceptions": exceptions,
        "summary": {
            "total_processed_invoices": len(processed_invoices),
            "potential_duplicates": len(potential_duplicates),
            "highest_confidence": highest_confidence,
            "is_likely_duplicate": is_duplicate
        }
    }


def _get_match_reasons(invoice1: Dict[str, Any], invoice2: Dict[str, Any]) -> List[str]:
    """Get human-readable reasons why two invoices might be duplicates."""
    reasons = []
    
    # Check each field for matches
    if invoice1.get("supplier_info", {}).get("name") == invoice2.get("supplier_name"):
        reasons.append("Same supplier name")
    
    if invoice1.get("supplier_info", {}).get("vendor_id") == invoice2.get("vendor_id"):
        reasons.append("Same vendor ID")
    
    if invoice1.get("invoice_id") == invoice2.get("invoice_number"):
        reasons.append("Same invoice number")
    
    amount1 = float(invoice1.get("summary", {}).get("billing_amount", 0))
    amount2 = float(invoice2.get("billing_amount", 0))
    if abs(amount1 - amount2) < 0.01:
        reasons.append("Same billing amount")
    
    if invoice1.get("purchase_order_number") == invoice2.get("po_number"):
        reasons.append("Same PO number")
    
    return reasons


def mark_invoice_as_processed(invoice_filename: str, processing_result: str, repo_root: Optional[str] = None) -> None:
    """
    Mark an invoice as processed in the history log.
    This should be called after successful processing to maintain the audit trail.
    
    Args:
        invoice_filename: Path to the processed invoice
        processing_result: Result of processing ("APPROVED", "REJECTED", etc.)
        repo_root: Root directory of the project
    """
    if not repo_root:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    
    try:
        with open(invoice_filename, "r", encoding="utf-8") as f:
            invoice_data = json.load(f)
        
        _log_processed_invoice(repo_root, invoice_data, processing_result)
    except Exception:
        pass  # Silently fail if we can't log


def main() -> None:
    """Standalone runner for testing duplicate detection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Duplicate invoice detection")
    parser.add_argument("--invoice", required=True, help="Path to invoice JSON")
    parser.add_argument("--repo-root", help="Repository root directory")
    args = parser.parse_args()
    
    result = check_for_duplicates(args.invoice, args.repo_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
