import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

DATE_FMT = "%Y-%m-%d"


def _parse(d: str) -> datetime:
    return datetime.strptime(d, DATE_FMT)


def validate_dates(invoice: Dict[str, Any], contract: Dict[str, Any], po_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks:
    - invoice.issue_date within contract window [effective_date, end_date]
    - due_date equals Net 30 when terms are Net 30
    - invoice issue_date >= PO effective_date (if present)
    """
    tool_name = "date_check_tool"
    exceptions: List[str] = []

    try:
        inv_issue = _parse(invoice.get("issue_date"))
        inv_due = _parse(invoice.get("due_date"))
    except Exception:
        exceptions.append("invoice_date_parse_error")
        return {"tool": tool_name, "status": "FAIL", "exceptions": exceptions}

    try:
        con_eff = _parse(contract.get("contract_metadata", {}).get("effective_date"))
        con_end = _parse(contract.get("contract_metadata", {}).get("end_date"))
    except Exception:
        exceptions.append("contract_date_parse_error")
        return {"tool": tool_name, "status": "FAIL", "exceptions": exceptions}

    if not (con_eff <= inv_issue <= con_end):
        exceptions.append("invoice_issue_out_of_contract_window")

    if (invoice.get("payment_terms") == "Net 30") and (inv_due != inv_issue + timedelta(days=30)):
        exceptions.append("due_date_not_net30")

    po_eff = po_item.get("effective_date")
    if po_eff:
        try:
            po_eff_dt = _parse(po_eff)
            if inv_issue < po_eff_dt:
                exceptions.append("invoice_issue_before_po_effective_date")
        except Exception:
            exceptions.append("po_effective_date_parse_error")

    return {
        "tool": tool_name,
        "status": "PASS" if not exceptions else "FAIL",
        "exceptions": exceptions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Invoice/PO/Contract date validation")
    parser.add_argument("--invoice", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--po", required=True, help="Path to a JSON with a single PO item, or a POs file with the item")
    parser.add_argument("--po-number", required=False, help="If --po is a POs file, specify the po_number to isolate")
    args = parser.parse_args()

    invoice = json.load(open(args.invoice, "r", encoding="utf-8"))
    contract = json.load(open(args.contract, "r", encoding="utf-8"))
    po_data = json.load(open(args.po, "r", encoding="utf-8"))

    if "purchase_orders" in po_data:
        if args.po_number:
            items = [x for x in po_data["purchase_orders"] if x.get("po_number") == args.po_number]
            po_item = items[0] if items else {}
        else:
            po_item = po_data["purchase_orders"][0] if po_data.get("purchase_orders") else {}
    else:
        po_item = po_data

    res = validate_dates(invoice, contract, po_item)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()


