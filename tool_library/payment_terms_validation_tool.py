"""
Payment Terms Validation Tool

ROLE: Validates invoice payment terms against contract requirements
PURPOSE: Ensures invoices use only approved payment terms (Net 30)
INPUT: Invoice data, Contract data
OUTPUT: Validation results with payment terms-specific exceptions

VALIDATION CHECKS:
- Invoice payment terms match contract payment terms
- Payment terms format validation (Net X format)
- Standard payment terms enforcement (Net 30)

SUPPORTED PAYMENT TERMS:
- Net 30 (30 days) - Standard payment terms
- Net 15 (15 days) - Accelerated payment
- Net 45 (45 days) - Extended payment
- Net 60 (60 days) - Extended payment

EXCEPTIONS:
- invalid_payment_terms: Invoice uses non-standard payment terms
- payment_terms_mismatch: Invoice terms differ from contract terms
- invalid_payment_terms_format: Payment terms format is invalid
"""

import json
import re
from typing import Any, Dict, List


def validate_payment_terms(invoice: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate invoice payment terms against contract requirements.
    
    This tool ensures invoices use approved payment terms and maintains
    consistency with contract specifications.
    
    Args:
        invoice: Invoice data dictionary
        contract: Contract data dictionary
    
    Returns:
        Dict with validation results including payment terms-specific exceptions
    """
    tool_name = "payment_terms_validation_tool"
    exceptions: List[str] = []
    
    # Supported payment terms (can be expanded)
    SUPPORTED_TERMS = {"Net 15", "Net 30", "Net 45", "Net 60"}
    
    # Extract payment terms information
    invoice_terms = (invoice or {}).get("payment_terms", "").strip()
    contract_terms = (contract or {}).get("payment_terms", "Net 30").strip()
    
    # Check if invoice payment terms are provided
    if not invoice_terms:
        exceptions.append("missing_payment_terms")
        return {
            "tool": tool_name,
            "status": "FAIL",
            "exceptions": exceptions,
        }
    
    # Validate payment terms format (should be "Net X" where X is a number)
    net_pattern = r'^Net\s+(\d+)$'
    if not re.match(net_pattern, invoice_terms, re.IGNORECASE):
        exceptions.append("invalid_payment_terms_format")
    
    # Check if payment terms are supported
    if invoice_terms not in SUPPORTED_TERMS:
        exceptions.append("unsupported_payment_terms")
    
    # Check payment terms consistency with contract (if contract specifies terms)
    if contract_terms and contract_terms != invoice_terms:
        exceptions.append("payment_terms_mismatch")
    
    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Payment terms validation tool")
    parser.add_argument("--invoice", "-i", required=True, help="Invoice JSON file")
    parser.add_argument("--contract", "-c", required=True, help="Contract JSON file")
    args = parser.parse_args()
    
    with open(args.invoice, "r", encoding="utf-8") as f:
        invoice = json.load(f)
    
    with open(args.contract, "r", encoding="utf-8") as f:
        contract = json.load(f)
    
    result = validate_payment_terms(invoice, contract)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
