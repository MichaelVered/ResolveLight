import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .po_contract_resolver_tool import resolve_invoice_to_po_and_contract


def _find_base_json_dirs(repo_root: str) -> List[str]:
    bases = []
    for name in ["json_files", "json files"]:
        p = os.path.join(repo_root, name)
        if os.path.isdir(p):
            bases.append(p)
    return bases


def _find_invoices(repo_root: str) -> List[str]:
    invoice_files: List[str] = []
    for base in _find_base_json_dirs(repo_root):
        for sub in os.listdir(base):
            if sub.lower() == "invoices":
                inv_dir = os.path.join(base, sub)
                try:
                    for fn in sorted(os.listdir(inv_dir)):
                        if fn.endswith(".json"):
                            invoice_files.append(os.path.join(inv_dir, fn))
                except Exception:
                    continue
    return invoice_files


def _first_sentences(text: str, max_sentences: int = 2) -> str:
    if not text:
        return text
    # Split on sentence-ending punctuation. Keep it simple and deterministic.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:max_sentences]).strip()


def _extract_invoice_services(invoice: Dict[str, Any]) -> List[str]:
    descs: List[str] = []
    for li in invoice.get("line_items", []) or []:
        d = li.get("description")
        if d:
            descs.append(str(d))
    return descs


def _extract_po_service(po_item: Dict[str, Any]) -> str:
    return str(po_item.get("description")) if po_item else "<not found>"


def _extract_contract_sow(contract: Dict[str, Any]) -> str:
    if not isinstance(contract, dict):
        return "<not found>"
    for sec in contract.get("sections", []) or []:
        if str(sec.get("section_title", "")).strip().lower() == "scope of work (sow)".lower():
            details = sec.get("details") or ""
            return _first_sentences(str(details), max_sentences=2) or "<not found>"
    return "<not found>"


def generate_services_report(repo_root: Optional[str] = None, output_path: Optional[str] = None) -> str:
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    invoices = _find_invoices(root)

    # Default output path under the first invoices dir, else repo root
    if not output_path:
        default_dir = None
        for base in _find_base_json_dirs(root):
            inv_dir = os.path.join(base, "Invoices")
            if os.path.isdir(inv_dir):
                default_dir = inv_dir
                break
            inv_dir2 = os.path.join(base, "invoices")
            if os.path.isdir(inv_dir2):
                default_dir = inv_dir2
                break
        if not default_dir:
            default_dir = root
        output_path = os.path.join(default_dir, "services_summary.csv")

    rows: List[Dict[str, Any]] = []
    for inv_path in invoices:
        outcome = resolve_invoice_to_po_and_contract(inv_path, repo_root=root)
        invoice = outcome.get("invoice") if isinstance(outcome.get("invoice"), dict) else None
        po_item = outcome.get("po_item") if isinstance(outcome.get("po_item"), dict) else None
        contract = outcome.get("contract") if isinstance(outcome.get("contract"), dict) else None

        invoice_id = (invoice or {}).get("invoice_id", "<not found>")
        invoice_po = (invoice or {}).get("purchase_order_number", "<not found>")
        invoice_services = _extract_invoice_services(invoice or {})
        po_desc = _extract_po_service(po_item or {})
        contract_id = (contract or {}).get("contract_id", "<not found>")
        contract_sow = _extract_contract_sow(contract or {})

        rows.append({
            "invoice_file": inv_path,
            "invoice_id": invoice_id,
            "invoice_po_number": invoice_po,
            "invoice_services": " | ".join(invoice_services) if invoice_services else "<not found>",
            "po_file": (po_item or {}).get("_source_file", "<not found>"),
            "po_description": po_desc or "<not found>",
            "contract_file": (contract or {}).get("_source_file", "<not found>"),
            "contract_id": contract_id,
            "contract_sow_summary": contract_sow,
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "invoice_file",
                "invoice_id",
                "invoice_po_number",
                "invoice_services",
                "po_file",
                "po_description",
                "contract_file",
                "contract_id",
                "contract_sow_summary",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def generate_services_report_tool() -> str:
    """Simple no-arg wrapper for ADK (scans all invoices and writes CSV)."""
    return generate_services_report()


def generate_services_markdown(
    repo_root: Optional[str] = None,
    csv_path: Optional[str] = None,
    md_output_path: Optional[str] = None,
) -> str:
    """
    Create an easily readable Markdown summary. If csv_path is not provided,
    we generate the CSV first and then convert it.
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if not csv_path:
        csv_path = generate_services_report(repo_root=root, output_path=None)

    # Default MD path next to CSV
    if not md_output_path:
        base_dir = os.path.dirname(csv_path)
        md_output_path = os.path.join(base_dir, "services_summary.md")

    # Read CSV rows
    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(r)

    # Build Markdown
    lines: List[str] = []
    lines.append("# Services Summary")
    lines.append("")
    lines.append("| Invoice ID | PO Number | Invoice Services | PO Description | Contract ID | Contract SOW Summary |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        inv_services = (r.get("invoice_services") or "")
        # Render each service on its own line in the cell
        inv_services_md = "<br/>".join([s.strip() for s in inv_services.split("|")]) if inv_services else ""
        lines.append(
            "| "
            + (r.get("invoice_id") or "") + " | "
            + (r.get("invoice_po_number") or "") + " | "
            + inv_services_md + " | "
            + (r.get("po_description") or "") + " | "
            + (r.get("contract_id") or "") + " | "
            + (r.get("contract_sow_summary") or "") + " |"
        )

    os.makedirs(os.path.dirname(md_output_path), exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return md_output_path


def generate_services_markdown_tool() -> str:
    return generate_services_markdown()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate services summary CSV for all invoices")
    parser.add_argument("--output", "-o", required=False, help="Output CSV path")
    args = parser.parse_args()
    path = generate_services_report(output_path=args.output)
    print(path)


if __name__ == "__main__":
    main()


