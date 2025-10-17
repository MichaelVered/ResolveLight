"""
Currency Validation Tool

ROLE: Validates invoice currency against supported currencies
PURPOSE: Ensures invoices use only approved currencies (USD only)
INPUT: Invoice data, Contract data
OUTPUT: Validation results with currency-specific exceptions

VALIDATION CHECKS:
- Invoice currency matches supported currencies (USD)
- Currency consistency between invoice and contract
- Currency format validation (3-letter ISO codes)

SUPPORTED CURRENCIES:
- USD (US Dollar) - Primary supported currency

EXCEPTIONS:
- unsupported_currency: Invoice uses non-supported currency
- currency_mismatch: Invoice currency differs from contract currency
- invalid_currency_format: Currency code format is invalid
"""

import json
from typing import Any, Dict, List


def validate_currency(invoice: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate invoice currency against supported currencies and contract requirements.
    
    This tool ensures invoices use only approved currencies and maintains
    consistency with contract terms.
    
    Args:
        invoice: Invoice data dictionary
        contract: Contract data dictionary
    
    Returns:
        Dict with validation results including currency-specific exceptions
    """
    tool_name = "currency_validation_tool"
    exceptions: List[str] = []
    
    # Supported currencies (can be expanded in the future)
    SUPPORTED_CURRENCIES = {"USD"}
    
    # Extract currency information
    invoice_currency = (invoice or {}).get("currency", "").strip().upper()
    contract_currency = (contract or {}).get("currency", "USD").strip().upper()
    
    # Check if invoice currency is provided
    if not invoice_currency:
        exceptions.append("missing_currency")
        return {
            "tool": tool_name,
            "status": "FAIL",
            "exceptions": exceptions,
        }
    
    # Validate currency format (should be 3-letter ISO code)
    if len(invoice_currency) != 3 or not invoice_currency.isalpha():
        exceptions.append("invalid_currency_format")
    
    # Check if currency is supported
    if invoice_currency not in SUPPORTED_CURRENCIES:
        exceptions.append("unsupported_currency")
    
    # Check currency consistency with contract (if contract specifies currency)
    if contract_currency and contract_currency != invoice_currency:
        exceptions.append("currency_mismatch")
    
    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Currency validation tool")
    parser.add_argument("--invoice", "-i", required=True, help="Invoice JSON file")
    parser.add_argument("--contract", "-c", required=True, help="Contract JSON file")
    args = parser.parse_args()
    
    with open(args.invoice, "r", encoding="utf-8") as f:
        invoice = json.load(f)
    
    with open(args.contract, "r", encoding="utf-8") as f:
        contract = json.load(f)
    
    result = validate_currency(invoice, contract)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()


