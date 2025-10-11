import json
import os
from typing import Any, Dict

from .supplier_match_tool import validate_supplier
from .date_check_tool import validate_dates
from .simple_overbilling_tool import validate_billing
from .po_contract_resolver_tool import resolve_invoice_to_po_and_contract
from .line_item_validation_tool import validate_line_items
from .duplicate_invoice_check_tool import check_for_duplicates


def run_validations(invoice_filename: str, repo_root: str | None = None) -> Dict[str, Any]:
    repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    # Avoid duplicate logging of resolution failures; triage orchestrator logs them upstream
    outcome = resolve_invoice_to_po_and_contract(invoice_filename, repo_root=repo_root)

    invoice = outcome.get("invoice")
    po_item = outcome.get("po_item")
    contract = outcome.get("contract")

    results = []

    # Short-circuit if required dependencies are missing to avoid irrelevant failures
    missing_exceptions: list[str] = []
    if not isinstance(invoice, dict):
        missing_exceptions.append("invoice_not_found")
    if not isinstance(po_item, dict):
        missing_exceptions.append("po_item_not_found")
    if not isinstance(contract, dict):
        missing_exceptions.append("contract_not_found")

    if missing_exceptions:
        results.append({
            "tool": "dependency_check",
            "status": "FAIL",
            "exceptions": missing_exceptions,
        })
        return {
            "validation": "FAIL",
            "invoice": invoice if isinstance(invoice, dict) else "<not found>",
            "po_item": po_item if isinstance(po_item, dict) else "<not found>",
            "contract": contract if isinstance(contract, dict) else "<not found>",
            "tool_results": results,
        }

    # Each tool returns { tool, status, exceptions }
    results.append(validate_supplier(invoice, contract))
    results.append(validate_billing(invoice, po_item))
    results.append(validate_dates(invoice, contract, po_item))
    results.append(validate_line_items(invoice, po_item))
    
    # Add duplicate check (this doesn't require PO/contract data)
    duplicate_check = check_for_duplicates(invoice_filename, repo_root=repo_root)
    results.append(duplicate_check)

    all_pass = all(r.get("status") == "PASS" for r in results)

    return {
        "validation": "PASS" if all_pass else "FAIL",
        "invoice": invoice if isinstance(invoice, dict) else "<not found>",
        "po_item": po_item if isinstance(po_item, dict) else "<not found>",
        "contract": contract if isinstance(contract, dict) else "<not found>",
        "tool_results": results,
    }


# Simple wrapper for ADK automatic function calling (single-arg schema)
def run_validations_tool(invoice_filename: str) -> Dict[str, Any]:
    return run_validations(invoice_filename)


def run_validations_and_format(invoice_filename: str) -> str:
    """
    Wrapper that returns a human-readable summary string with per-tool PASS/FAIL
    and reasons, followed by the overall validation line.
    """
    report = run_validations(invoice_filename)
    lines: list[str] = []
    tool_results = report.get("tool_results") or []
    for r in tool_results:
        tool = r.get("tool", "<tool>")
        status = r.get("status", "FAIL")
        if status == "PASS":
            lines.append(f"{tool}: PASS")
        else:
            reasons = r.get("exceptions") or []
            # Handle both string and dict exceptions
            reason_strs = []
            for reason in reasons:
                if isinstance(reason, dict):
                    reason_strs.append(str(reason))
                else:
                    reason_strs.append(str(reason))
            reason_str = ", ".join(reason_strs) if reason_strs else "<none>"
            lines.append(f"{tool}: FAIL - reasons: {reason_str}")
    lines.append(f"validation: {report.get('validation', 'FAIL')}")
    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Validation runner for invoice → PO → contract")
    parser.add_argument("--invoice-filename", "-i", required=True)
    parser.add_argument("--output", "-o", required=False, help="Path to write JSON report when FAIL")
    args = parser.parse_args()

    report = run_validations(args.invoice_filename)
    print(json.dumps(report, indent=2))

    if report.get("validation") != "PASS" and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()


