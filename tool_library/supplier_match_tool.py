import json
from typing import Any, Dict, List


def validate_supplier(invoice: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate supplier and bill-to consistency between invoice and contract.

    Returns a dict: { tool, status, exceptions }
    """
    exceptions: List[str] = []
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

    if inv_supplier.get("name") != con_supplier.get("name"):
        exceptions.append("supplier_name_mismatch")
    if inv_supplier.get("vendor_id") != con_supplier.get("vendor_id"):
        exceptions.append("supplier_vendor_id_mismatch")
    if inv_billto.get("name") != con_client.get("name"):
        exceptions.append("bill_to_name_mismatch")

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


