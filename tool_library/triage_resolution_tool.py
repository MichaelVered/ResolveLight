import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from .validation_runner_tool import run_validations
from .po_contract_resolver_tool import resolve_invoice_to_po_and_contract
from .fuzzy_matching_tool import fuzzy_resolve_invoice_to_po_and_contract
from .duplicate_invoice_check_tool import check_for_duplicates, mark_invoice_as_processed


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
            # Handle both string and dict exceptions
            exc_strs = []
            for e in exc:
                if isinstance(e, dict):
                    exc_strs.append(str(e))
                else:
                    exc_strs.append(str(e))
            msg = f"{tool}: " + ", ".join(exc_strs) if exc_strs else f"{tool}: <no details>"
            reasons.append(msg)
    return reasons


def _determine_routing_queue(tool_results: List[Dict[str, Any]], invoice_data: Dict[str, Any], matching_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine the appropriate routing queue based on validation failures and confidence scores.
    
    Args:
        tool_results: Results from validation tools
        invoice_data: Invoice data
        matching_details: Details from fuzzy matching
    
    Returns:
        Dict with queue information and routing decision
    """
    routing_info = {
        "queue_name": "general_exceptions",
        "priority": "normal",
        "routing_reason": "General validation failure",
        "requires_manager_approval": False,
        "confidence_score": 0.0,
        "specific_issues": []
    }
    
    # Check for duplicate detection
    duplicate_tool = next((r for r in tool_results if r.get("tool") == "duplicate_invoice_check_tool"), None)
    if duplicate_tool and duplicate_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "duplicate_invoices",
            "priority": "high",
            "routing_reason": "Potential duplicate invoice detected",
            "requires_manager_approval": True,
            "specific_issues": ["duplicate_detected"]
        })
        return routing_info
    
    # Check for missing data issues
    dependency_tool = next((r for r in tool_results if r.get("tool") == "dependency_check"), None)
    if dependency_tool and dependency_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "missing_data",
            "priority": "high",
            "routing_reason": "Missing PO or contract data",
            "requires_manager_approval": True,
            "specific_issues": ["missing_po", "missing_contract"]
        })
        return routing_info
    
    # Check for low confidence matching
    po_confidence = matching_details.get("po_match", {}).get("confidence", 0.0)
    supplier_confidence = matching_details.get("supplier_match", {}).get("confidence", 0.0)
    overall_confidence = matching_details.get("overall_confidence", 0.0)
    
    if overall_confidence < 0.7:  # Low confidence threshold
        routing_info.update({
            "queue_name": "low_confidence_matches",
            "priority": "high",
            "routing_reason": f"Low confidence matching ({overall_confidence:.1%})",
            "requires_manager_approval": True,
            "confidence_score": overall_confidence,
            "specific_issues": ["low_po_confidence", "low_supplier_confidence"]
        })
        return routing_info
    
    # Check for line item validation failures
    line_item_tool = next((r for r in tool_results if r.get("tool") == "line_item_validation_tool"), None)
    if line_item_tool and line_item_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "price_discrepancies",
            "priority": "high",
            "routing_reason": "Line item validation failed",
            "requires_manager_approval": True,
            "specific_issues": ["price_mismatch", "quantity_mismatch"]
        })
        return routing_info
    
    # Check for supplier matching issues
    supplier_tool = next((r for r in tool_results if r.get("tool") == "supplier_match_tool"), None)
    if supplier_tool and supplier_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "supplier_mismatch",
            "priority": "medium",
            "routing_reason": "Supplier information mismatch",
            "requires_manager_approval": False,
            "specific_issues": ["supplier_name_mismatch", "vendor_id_mismatch"]
        })
        return routing_info
    
    # Check for billing/overbilling issues
    billing_tool = next((r for r in tool_results if r.get("tool") == "simple_overbilling_tool"), None)
    if billing_tool and billing_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "billing_discrepancies",
            "priority": "high",
            "routing_reason": "Billing amount exceeds PO or arithmetic error",
            "requires_manager_approval": True,
            "specific_issues": ["overbilling", "arithmetic_error"]
        })
        return routing_info
    
    # Check for date issues
    date_tool = next((r for r in tool_results if r.get("tool") == "date_check_tool"), None)
    if date_tool and date_tool.get("status") == "FAIL":
        routing_info.update({
            "queue_name": "date_discrepancies",
            "priority": "medium",
            "routing_reason": "Date validation failed",
            "requires_manager_approval": False,
            "specific_issues": ["date_mismatch", "payment_terms_error"]
        })
        return routing_info
    
    # Check invoice value for high-value routing
    invoice_amount = float(invoice_data.get("summary", {}).get("billing_amount", 0))
    if invoice_amount > 10000:  # High-value threshold
        routing_info.update({
            "queue_name": "high_value_approval",
            "priority": "high",
            "routing_reason": f"High-value invoice (${invoice_amount:,.2f})",
            "requires_manager_approval": True,
            "specific_issues": ["high_value"]
        })
        return routing_info
    
    return routing_info


def _create_queue_specific_log_entry(queue_info: Dict[str, Any], invoice_data: Dict[str, Any], exception_id: str, tool_results: List[Dict[str, Any]]) -> str:
    """
    Create a queue-specific log entry with detailed context for human reviewers.
    """
    queue_name = queue_info["queue_name"]
    priority = queue_info["priority"]
    routing_reason = queue_info["routing_reason"]
    
    inv_id = invoice_data.get("invoice_id", "<unknown>")
    po_num = invoice_data.get("purchase_order_number", "<unknown>")
    amount = float(invoice_data.get("summary", {}).get("billing_amount", 0))
    
    # Create detailed context based on queue type
    context_details = []
    
    if queue_name == "duplicate_invoices":
        duplicate_tool = next((r for r in tool_results if r.get("tool") == "duplicate_invoice_check_tool"), None)
        if duplicate_tool:
            context_details.append("DUPLICATE DETECTION:")
            for exc in duplicate_tool.get("exceptions", []):
                if exc.get("type") == "potential_duplicate":
                    context_details.append(f"  - Confidence: {exc.get('confidence', 0):.1%}")
                    context_details.append(f"  - Match reasons: {', '.join(exc.get('match_reasons', []))}")
    
    elif queue_name == "low_confidence_matches":
        context_details.append("MATCHING CONFIDENCE:")
        context_details.append(f"  - Overall confidence: {queue_info.get('confidence_score', 0):.1%}")
        context_details.append("  - Review matching logic and consider manual verification")
    
    elif queue_name == "price_discrepancies":
        line_item_tool = next((r for r in tool_results if r.get("tool") == "line_item_validation_tool"), None)
        if line_item_tool:
            context_details.append("LINE ITEM DISCREPANCIES:")
            for exc in line_item_tool.get("exceptions", []):
                if exc.get("discrepancies"):
                    context_details.append(f"  - Item {exc.get('item_id')}: {exc.get('description')}")
                    for disc in exc.get("discrepancies", []):
                        if disc.get("status") == "FAIL":
                            context_details.append(f"    * {disc.get('field')}: {disc.get('invoice_value')} vs PO {disc.get('po_value')}")
    
    elif queue_name == "billing_discrepancies":
        billing_tool = next((r for r in tool_results if r.get("tool") == "simple_overbilling_tool"), None)
        if billing_tool:
            context_details.append("BILLING ISSUES:")
            for exc in billing_tool.get("exceptions", []):
                context_details.append(f"  - {exc}")
    
    # Create the log entry
    log_entry = f"""
QUEUE: {queue_name.upper()}
PRIORITY: {priority.upper()}
EXCEPTION_ID: {exception_id}
INVOICE: {inv_id} (PO: {po_num}, Amount: ${amount:,.2f})
ROUTING_REASON: {routing_reason}
TIMESTAMP: {_ts()}

CONTEXT:
{chr(10).join(context_details) if context_details else "  - General validation failure"}

SUGGESTED_ACTIONS:
  - Review the specific issues listed above
  - Contact supplier if data discrepancies found
  - Verify PO and contract details if matching issues
  - Approve manually if all checks pass after review

MANAGER_APPROVAL_REQUIRED: {'YES' if queue_info['requires_manager_approval'] else 'NO'}
"""
    
    return log_entry.strip()


def triage_and_route(invoice_filename: str, repo_root: str | None = None) -> Dict[str, Any]:
    """
    Enhanced triage and routing with granular queue management.
    
    This function:
    1. Performs duplicate detection
    2. Uses fuzzy matching for better resolution
    3. Runs comprehensive validation
    4. Routes to specific queues based on failure types
    5. Creates detailed context for human reviewers
    
    Args:
        invoice_filename: Path to invoice file
        repo_root: Root directory of the project
    
    Returns:
        Dict with routing results and actions taken
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    logs_dir = _ensure_logs_dir(root)
    
    # Step 1: Check for duplicates first
    duplicate_check = check_for_duplicates(invoice_filename, repo_root=root)
    if duplicate_check.get("status") == "FAIL":
        # Handle duplicate immediately
        inv_id = "<unknown>"
        try:
            with open(invoice_filename, "r", encoding="utf-8") as f:
                invoice_data = json.load(f)
                inv_id = invoice_data.get("invoice_id", "<unknown>")
        except Exception:
            pass
        
        exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
        
        # Log to duplicate queue
        duplicate_log = os.path.join(logs_dir, "queue_duplicate_invoices.log")
        log_entry = _create_queue_specific_log_entry(
            {"queue_name": "duplicate_invoices", "priority": "high", "routing_reason": "Duplicate detected"},
            invoice_data if 'invoice_data' in locals() else {},
            exception_id,
            [duplicate_check]
        )
        _append_line(duplicate_log, log_entry)
        
        return {
            "status": "REJECTED",
            "exception_id": exception_id,
            "routing_queue": "duplicate_invoices",
            "priority": "high",
            "actions": ["REJECTED → Duplicate detected, routed to duplicate queue"],
            "logs": {"duplicate_queue_log": duplicate_log}
        }
    
    # Step 2: Use fuzzy matching for better resolution
    resolution = fuzzy_resolve_invoice_to_po_and_contract(invoice_filename, repo_root=root)
    invoice = resolution.get("invoice") if isinstance(resolution.get("invoice"), dict) else {}
    po_item = resolution.get("po_item") if isinstance(resolution.get("po_item"), dict) else {}
    contract = resolution.get("contract") if isinstance(resolution.get("contract"), dict) else {}
    matching_details = resolution.get("matching_details", {})
    
    # Step 3: Run comprehensive validation
    report = run_validations(invoice_filename, repo_root=root)
    validation = report.get("validation")
    tool_results = report.get("tool_results") or []
    
    actions: List[str] = []
    
    if validation == "PASS":
        # Check if we need manager approval for high-value invoices
        invoice_amount = float(invoice.get("summary", {}).get("billing_amount", 0))
        overall_confidence = matching_details.get("overall_confidence", 1.0)
        
        if invoice_amount > 10000 or overall_confidence < 0.9:
            # Route to high-value approval queue even if validation passes
            exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
            queue_info = {
                "queue_name": "high_value_approval",
                "priority": "high",
                "routing_reason": f"High-value invoice (${invoice_amount:,.2f}) or low confidence ({overall_confidence:.1%})",
                "requires_manager_approval": True
            }
            
            approval_log = os.path.join(logs_dir, "queue_high_value_approval.log")
            log_entry = _create_queue_specific_log_entry(queue_info, invoice, exception_id, tool_results)
            _append_line(approval_log, log_entry)
            
            # Mark as processed for duplicate detection
            mark_invoice_as_processed(invoice_filename, "PENDING_MANAGER_APPROVAL", repo_root=root)
            
            return {
                "status": "PENDING_APPROVAL",
                "exception_id": exception_id,
                "routing_queue": "high_value_approval",
                "priority": "high",
                "actions": ["PENDING → Routed to manager approval queue"],
                "logs": {"approval_queue_log": approval_log}
            }
        else:
            # Standard approval
            inv_id = invoice.get("invoice_id", "<unknown>")
            po_num = invoice.get("purchase_order_number", "<unknown>")
            
            payments_log = os.path.join(logs_dir, "payments.log")
            _append_line(payments_log, f"[INFO] [{_ts()}] Invoice {inv_id} approved. Routing to Payment System.")
            
            # Log each line item as approved payment
            for li in invoice.get("line_items", []) or []:
                item_id = li.get("item_id")
                desc = li.get("description")
                total = li.get("line_total")
                _append_line(
                    payments_log,
                    f"    payment_item: invoice_id={inv_id}, po_number={po_num}, item_id={item_id}, description={desc}, amount={total}"
                )
            
            # Mark as processed for duplicate detection
            mark_invoice_as_processed(invoice_filename, "APPROVED", repo_root=root)
            
            actions.append("APPROVED → Payments logged")
            return {
                "status": "APPROVED",
                "actions": actions,
                "logs": {"payments_log": payments_log}
            }
    
    # Step 4: Handle validation failures with granular routing
    inv_id = invoice.get("invoice_id", "<unknown>")
    exception_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
    
    # Determine routing queue based on failure types
    queue_info = _determine_routing_queue(tool_results, invoice, matching_details)
    queue_name = queue_info["queue_name"]
    priority = queue_info["priority"]
    
    # Create queue-specific log file
    queue_log = os.path.join(logs_dir, f"queue_{queue_name}.log")
    log_entry = _create_queue_specific_log_entry(queue_info, invoice, exception_id, tool_results)
    _append_line(queue_log, log_entry)
    
    # Also log to general exceptions ledger for audit trail
    exceptions_log = os.path.join(logs_dir, "exceptions_ledger.log")
    _append_line(exceptions_log, f"[EXCEPTION] [{_ts()}] id={exception_id} status=OPEN type=VALIDATION_FAILED invoice_id={inv_id} queue={queue_name}")
    
    # Mark as processed for duplicate detection
    mark_invoice_as_processed(invoice_filename, f"REJECTED_{queue_name.upper()}", repo_root=root)
    
    actions.append(f"REJECTED → Routed to {queue_name} queue")
    return {
        "status": "REJECTED",
        "exception_id": exception_id,
        "routing_queue": queue_name,
        "priority": priority,
        "requires_manager_approval": queue_info["requires_manager_approval"],
        "actions": actions,
        "logs": {
            "queue_log": queue_log,
            "exceptions_log": exceptions_log
        }
    }


def triage_and_route_tool(invoice_filename: str) -> str:
    """Wrapper for ADK – returns a concise, human-readable summary string."""
    res = triage_and_route(invoice_filename)
    status = res.get("status")
    if status == "APPROVED":
        return f"APPROVED: routed to payments. Log: {res['logs']['payments_log']}"
    return f"REJECTED: exception_id={res.get('exception_id')} logs: {json.dumps(res.get('logs'))}"


