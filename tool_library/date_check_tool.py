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
    exceptions: List[Dict[str, Any] | str] = []

    # Extract invoice dates
    try:
        inv_issue_str = invoice.get("issue_date")
        inv_due_str = invoice.get("due_date")
        inv_issue = _parse(inv_issue_str) if inv_issue_str else None
        inv_due = _parse(inv_due_str) if inv_due_str else None
    except Exception as e:
        exceptions.append({
            "type": "invoice_date_parse_error",
            "issue_date": inv_issue_str,
            "due_date": inv_due_str,
            "error": str(e),
            "required_format": "YYYY-MM-DD"
        })
        return {"tool": tool_name, "status": "FAIL", "exceptions": exceptions}

    # Extract contract dates
    contract_metadata = contract.get("contract_metadata", {}) if contract else {}
    try:
        con_eff_str = contract_metadata.get("effective_date")
        con_end_str = contract_metadata.get("end_date")
        con_eff = _parse(con_eff_str) if con_eff_str else None
        con_end = _parse(con_end_str) if con_end_str else None
    except Exception as e:
        exceptions.append({
            "type": "contract_date_parse_error",
            "effective_date": con_eff_str,
            "end_date": con_end_str,
            "error": str(e),
            "required_format": "YYYY-MM-DD"
        })
        return {"tool": tool_name, "status": "FAIL", "exceptions": exceptions}

    # Check invoice date within contract window
    if con_eff and con_end and inv_issue:
        if not (con_eff <= inv_issue <= con_end):
            days_before = (con_eff - inv_issue).days if inv_issue < con_eff else 0
            days_after = (inv_issue - con_end).days if inv_issue > con_end else 0
            
            exceptions.append({
                "type": "invoice_issue_out_of_contract_window",
                "invoice_issue_date": inv_issue_str,
                "contract_effective_date": con_eff_str,
                "contract_end_date": con_end_str,
                "expected_range": f"{con_eff_str} to {con_end_str}",
                "days_out_of_range": days_before if days_before > 0 else days_after,
                "comparison_method": "date_range_validation",
                "threshold": "Invoice date must be within contract window"
            })

    # Check Net 30 due date calculation
    payment_terms = invoice.get("payment_terms") if invoice else None
    if payment_terms == "Net 30" and inv_issue and inv_due:
        expected_due = inv_issue + timedelta(days=30)
        if inv_due != expected_due:
            days_diff = (inv_due - expected_due).days if isinstance(inv_due, datetime) and isinstance(expected_due, datetime) else "N/A"
            exceptions.append({
                "type": "due_date_not_net30",
                "invoice_due_date": inv_due_str,
                "invoice_issue_date": inv_issue_str,
                "expected_due_date": expected_due.strftime(DATE_FMT) if isinstance(expected_due, datetime) else "N/A",
                "days_difference": days_diff,
                "comparison_method": "net_30_calculation",
                "threshold": "Due date must be exactly 30 days after issue date"
            })

    # Check PO effective date
    po_eff_str = po_item.get("effective_date") if po_item else None
    if po_eff_str and inv_issue:
        try:
            po_eff_dt = _parse(po_eff_str)
            if inv_issue < po_eff_dt:
                days_before = (po_eff_dt - inv_issue).days
                exceptions.append({
                    "type": "invoice_issue_before_po_effective_date",
                    "invoice_issue_date": inv_issue_str,
                    "po_effective_date": po_eff_str,
                    "days_before": days_before,
                    "comparison_method": "date_comparison",
                    "threshold": "Invoice date must be on or after PO effective date"
                })
        except Exception as e:
            exceptions.append({
                "type": "po_effective_date_parse_error",
                "po_effective_date": po_eff_str,
                "error": str(e),
                "required_format": "YYYY-MM-DD"
            })

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


