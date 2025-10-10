import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


def normalize_token(value: Optional[str]) -> Optional[str]:
    """
    Uppercase and strip all non-alphanumeric characters from a token
    (e.g., PO numbers, contract IDs). Returns None if input is falsy.
    """
    if not value:
        return value
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def read_json_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def find_base_json_dirs(repo_root: str) -> List[str]:
    candidates = []
    for name in ["json_files", "json files"]:
        full = os.path.join(repo_root, name)
        if os.path.isdir(full):
            candidates.append(full)
    return candidates


def find_subdir_case_insensitive(parent: str, target_name: str) -> Optional[str]:
    if not os.path.isdir(parent):
        return None
    names = os.listdir(parent)
    for n in names:
        if n.lower() == target_name.lower():
            candidate = os.path.join(parent, n)
            if os.path.isdir(candidate):
                return candidate
    return None


def resolve_directories(repo_root: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns lists of candidate directories for invoices, POs, and contracts.
    Supports both json_files/* and json files/* layouts with varied casing.
    """
    base_dirs = find_base_json_dirs(repo_root)
    invoice_dirs: List[str] = []
    po_dirs: List[str] = []
    contract_dirs: List[str] = []

    for base in base_dirs:
        inv = find_subdir_case_insensitive(base, "invoices")
        if inv:
            invoice_dirs.append(inv)

        pos = find_subdir_case_insensitive(base, "pos")
        if pos:
            po_dirs.append(pos)

        cons = find_subdir_case_insensitive(base, "contracts")
        if cons:
            contract_dirs.append(cons)

    return invoice_dirs, po_dirs, contract_dirs


def find_invoice_path(invoice_filename: str, invoice_dirs: List[str]) -> Optional[str]:
    # If user passed an absolute or relative path including a directory, use it if it exists
    if os.path.sep in invoice_filename or invoice_filename.startswith("."):
        abs_path = invoice_filename
        if not os.path.isabs(abs_path):
            abs_path = os.path.abspath(abs_path)
        return abs_path if os.path.isfile(abs_path) else None

    # Otherwise search within candidate invoice dirs
    for d in invoice_dirs:
        candidate = os.path.join(d, invoice_filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def list_invoices(invoice_dirs: List[str]) -> List[str]:
    files: List[str] = []
    for d in invoice_dirs:
        try:
            for name in sorted(os.listdir(d)):
                if name.endswith(".json"):
                    files.append(os.path.join(d, name))
        except Exception:
            continue
    return files


def find_po_item_by_po_number(normalized_po: str, po_dirs: List[str]) -> Optional[Dict[str, Any]]:
    for d in po_dirs:
        try:
            for name in os.listdir(d):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(d, name)
                data = read_json_file(path)
                if not data:
                    continue
                for item in data.get("purchase_orders", []):
                    po_num = normalize_token(item.get("po_number"))
                    if po_num and po_num == normalized_po:
                        # Return only the matching PO item, and annotate source file for context
                        match = dict(item)
                        match["_source_file"] = path
                        return match
        except Exception:
            continue
    return None


def find_contract_by_id(normalized_contract_id: str, contract_dirs: List[str]) -> Optional[Dict[str, Any]]:
    for d in contract_dirs:
        try:
            for name in os.listdir(d):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(d, name)
                data = read_json_file(path)
                if not data:
                    continue
                cid = normalize_token(data.get("contract_id"))
                if cid and cid == normalized_contract_id:
                    data["_source_file"] = path
                    return data
        except Exception:
            continue
    return None


def resolve_invoice_to_po_and_contract(
    invoice_filename: str,
    repo_root: Optional[str] = None
) -> Dict[str, Union[str, Dict[str, Any]]]:
    """
    Core tool function: Given an invoice filename (just name or full path),
    load the invoice, extract PO number, find the matching PO item, pull
    the contract by contract_id, and return all three.
    Missing parts are represented as the literal string "<not found>".
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    invoice_dirs, po_dirs, contract_dirs = resolve_directories(root)

    result: Dict[str, Union[str, Dict[str, Any]]] = {
        "invoice": "<not found>",
        "po_item": "<not found>",
        "contract": "<not found>",
    }

    invoice_path = find_invoice_path(invoice_filename, invoice_dirs)
    invoice_data = read_json_file(invoice_path) if invoice_path else None
    if not invoice_data:
        return result
    result["invoice"] = invoice_data

    inv_po_number = invoice_data.get("purchase_order_number")
    normalized_po = normalize_token(inv_po_number)
    if not normalized_po:
        return result

    po_item = find_po_item_by_po_number(normalized_po, po_dirs)
    if not po_item:
        return result
    result["po_item"] = po_item

    contract_id = po_item.get("contract_id")
    normalized_cid = normalize_token(contract_id)
    if not normalized_cid:
        return result

    contract_data = find_contract_by_id(normalized_cid, contract_dirs)
    if not contract_data:
        return result
    result["contract"] = contract_data

    return result


def _standalone_prompt_select_invoice(invoice_dirs: List[str]) -> Optional[str]:
    files = list_invoices(invoice_dirs)
    if not files:
        print("No invoice files found.")
        return None
    print("Available invoices:")
    for idx, p in enumerate(files, 1):
        print(f"  {idx}. {os.path.basename(p)}")
    try:
        choice = input("Enter the number of the invoice to process (or press Enter to cancel): ")
        if not choice.strip():
            return None
        n = int(choice)
        if 1 <= n <= len(files):
            return files[n - 1]
    except Exception:
        return None
    return None


def main_cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Resolve invoice → PO item → contract")
    parser.add_argument("--invoice-filename", "-i", dest="invoice_filename", help="Invoice filename or path")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    invoice_dirs, po_dirs, contract_dirs = resolve_directories(repo_root)

    invoice_filename = args.invoice_filename
    if not invoice_filename:
        selected = _standalone_prompt_select_invoice(invoice_dirs)
        if not selected:
            print(json.dumps({
                "invoice": "<not found>",
                "po_item": "<not found>",
                "contract": "<not found>"
            }, indent=2))
            return
        invoice_filename = selected

    outcome = resolve_invoice_to_po_and_contract(invoice_filename, repo_root=repo_root)
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main_cli()


