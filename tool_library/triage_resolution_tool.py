import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from .validation_runner_tool import run_validations
from .po_contract_resolver_tool import resolve_invoice_to_po_and_contract


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_logs_dir(repo_root: str) -> str:
    logs_dir = os.path.join(repo_root, "system_logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def _append_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def _format_fail_reasons(tool_results: List[Dict[str, Any]]) -> List[str]:
    reasons: List[str] = []
    for r in tool_results or []:
        if r.get("status") == "FAIL":
            tool = r.get("tool", "tool")
            exc = r.get("exceptions") or []
            msg = f"{tool}: " + ", ".join(exc) if exc else f"{tool}: <no details>"
            reasons.append(msg)
    return reasons


def triage_and_route(invoice_filename: str, repo_root: str | None = None) -> Dict[str, Any]:
    """
    Orchestrates final routing based on validation report.
    On PASS: append approved payment entries per invoice line.
    On FAIL: append to exceptions ledger and HITL queue with headers and timestamps.
    Returns a summary dict of actions taken.
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    logs_dir = _ensure_logs_dir(root)
    payments_log = os.path.join(logs_dir, "payments.log")
    exceptions_log = os.path.join(logs_dir, "exceptions_ledger.log")
    hitl_log = os.path.join(logs_dir, "hitl_queue.log")

    # Gather artifacts
    # Allow resolver to log early resolution failures for exceptions coverage
    resolution = resolve_invoice_to_po_and_contract(invoice_filename, repo_root=root)
    invoice = resolution.get("invoice") if isinstance(resolution.get("invoice"), dict) else {}
    po_item = resolution.get("po_item") if isinstance(resolution.get("po_item"), dict) else {}
    contract = resolution.get("contract") if isinstance(resolution.get("contract"), dict) else {}

    report = run_validations(invoice_filename, repo_root=root)
    validation = report.get("validation")
    tool_results = report.get("tool_results") or []

    actions: List[str] = []

    if validation == "PASS":
        inv_id = invoice.get("invoice_id", "<unknown>")
        po_num = invoice.get("purchase_order_number", "<unknown>")
        _append_line(payments_log, f"[INFO] [{_ts()}] Invoice {inv_id} approved. Routing to Payment System.")
        # Each line item as an approved payment record
        for li in invoice.get("line_items", []) or []:
            item_id = li.get("item_id")
            desc = li.get("description")
            total = li.get("line_total")
            _append_line(
                payments_log,
                f"    payment_item: invoice_id={inv_id}, po_number={po_num}, item_id={item_id}, description={desc}, amount={total}"
            )
        actions.append("APPROVED → Payments logged")
        return {
            "status": "APPROVED",
            "actions": actions,
            "logs": {
                "payments_log": payments_log
            }
        }

    # REJECTED / FAILED
    inv_id = invoice.get("invoice_id", "<unknown>")
    po_num = invoice.get("purchase_order_number", "<unknown>")
    exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
    reasons = _format_fail_reasons(tool_results)

    # Exceptions & Learning Ledger entry
    _append_line(exceptions_log, f"[EXCEPTION] [{_ts()}] id={exception_id} status=OPEN type=VALIDATION_FAILED invoice_id={inv_id} po_number={po_num}")
    _append_line(exceptions_log, "    failure_reasons:")
    for r in reasons:
        _append_line(exceptions_log, f"      - {r}")
    # Structured JSON payload for AI systems to parse precisely
    try:
      inv_total = float((invoice.get("summary") or {}).get("billing_amount") or 0.0)
    except Exception:
      inv_total = 0.0
    try:
      po_total = float((po_item or {}).get("total_value") or 0.0)
    except Exception:
      po_total = 0.0
    remaining = round(po_total - inv_total, 2)
    exception_record = {
        "exception_id": exception_id,
        "timestamp": _ts(),
        "status": "OPEN",
        "exception_type": "VALIDATION_FAILED",
        "summary": {
            "invoice_id": inv_id,
            "po_number": po_num,
            "contract_id": (po_item or {}).get("contract_id"),
            "invoice_total": inv_total,
            "po_total": po_total,
            "po_remaining_after_invoice": remaining,
        },
        "file_paths": {
            "invoice_path": invoice_filename if invoice_filename else None,
            "po_source_file": (po_item or {}).get("_source_file"),
            "contract_source_file": (contract or {}).get("_source_file"),
        },
        "tool_results": tool_results,
        "invoice": invoice,
        "po_item": po_item,
        "contract": contract,
    }
    for line in json.dumps(exception_record, ensure_ascii=False, indent=2).splitlines():
        _append_line(exceptions_log, "    " + line)

    # HITL queue entry
    summary = "; ".join(reasons) if reasons else "Validation failed."
    _append_line(hitl_log, f"[INFO] [{_ts()}] HITL_TASK created for exception_id={exception_id}")
    _append_line(hitl_log, f"    title: Invoice {inv_id} validation failed (PO {po_num})")
    _append_line(hitl_log, f"    description: {summary}")
    # Include key figures and quick context for finance reviewers
    _append_line(hitl_log, f"    key_figures: invoice_total={inv_total}, po_total={po_total}, remaining_after_invoice={remaining}")
    _append_line(hitl_log, "    suggested_actions:")
    _append_line(hitl_log, "      - Verify supplier details and PO association if supplier/tool mismatches present")
    _append_line(hitl_log, "      - Confirm invoice arithmetic (subtotal + tax == billing) and compare to PO remaining")
    _append_line(hitl_log, "      - If dates mismatch, adjust due date or route back to vendor for correction")
    # Link back to machine-readable exception record
    _append_line(hitl_log, f"    exception_record_hint: file={exceptions_log} id={exception_id}")

    actions.append("REJECTED → Exception logged & HITL task created")
    return {
        "status": "REJECTED",
        "exception_id": exception_id,
        "actions": actions,
        "logs": {
            "exceptions_log": exceptions_log,
            "hitl_log": hitl_log
        }
    }


def triage_and_route_tool(invoice_filename: str) -> str:
    """Wrapper for ADK – returns a concise, human-readable summary string."""
    res = triage_and_route(invoice_filename)
    status = res.get("status")
    if status == "APPROVED":
        return f"APPROVED: routed to payments. Log: {res['logs']['payments_log']}"
    return f"REJECTED: exception_id={res.get('exception_id')} logs: {json.dumps(res.get('logs'))}"


