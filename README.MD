# ResolveLight

Lightweight Source-to-Pay invoice triage and validation utilities with optional agent orchestration (Google ADK). The toolkit resolves invoices to POs and contracts, validates core business rules, and routes outcomes to simple logs for payment or human-in-the-loop review.

## Overview
- Contract/PO/Invoice JSON examples live under `json_files/`.
- Core Python tools in `ResolveLight/tool_library/` perform:
  - Invoice → PO → Contract resolution
  - Supplier/bill-to checks
  - Overbilling checks
  - Date/terms checks
  - Services summary report (CSV + Markdown)
- Logs written under `system_logs/`:
  - `payments.log` for approvals
  - `exceptions_ledger.log` for failures with structured context
  - `hitl_queue.log` for human-in-the-loop routing
- Optional agents (Google ADK) are defined in YAML:
  - Root sequential agent `root_agent.yaml` orchestrates contract match → validation → triage

## Project Layout
```
ResolveLight/
  json_files/
    contracts/         # Contract JSONs
    invoices/          # Invoice JSONs (some systems may use "Invoices")
    POs/               # Purchase orders by customer/project
  system_logs/         # Output logs created at runtime
  sub_agents/          # Agent configs (ADK YAML)
  tool_library/        # Python tools with small CLIs
  root_agent.yaml      # Top-level agent orchestration (ADK)
```
Note: Directory discovery is case-insensitive for `json_files` subfolders (`invoices` vs `Invoices`, `POs` vs `pos`, etc.).

## Requirements
- Python 3.10+ (uses PEP 604 unions, e.g., `str | None`)
- No third‑party Python dependencies required for the tools themselves (standard library only)
- Optional: Google ADK if you want to run the YAML agents

Suggested environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -V  # should be 3.10+
```

## Quickstart: Common Tasks
All commands assume the project root: `/Users/mzim/ADK/ResolveLight`.

### 1) Resolve an invoice → PO item → contract
Prints a JSON object with keys `invoice`, `po_item`, `contract`.
```bash
python -m ResolveLight.tool_library.po_contract_resolver_tool \
  --invoice-filename json_files/invoices/invoice_Orion_PO-2025-301A.json
# If you omit --invoice-filename, you'll get an interactive selector
```
Behavior notes:
- Tokens like PO numbers and contract IDs are normalized (uppercase, strip non‑alphanumerics).
- If anything is missing, the value is the literal string "<not found>".
- This resolver does not write logs; logging occurs during triage (see below).

### 2) Run validations (supplier, billing, dates)
Outputs a structured JSON report, plus a simple PASS/FAIL.
```bash
python -m ResolveLight.tool_library.validation_runner_tool \
  --invoice-filename json_files/invoices/invoice_Horizon_PO-2025-308A.json
```
Expected FAIL example (no matching PO/contract by design):
```bash
python -m ResolveLight.tool_library.validation_runner_tool \
  --invoice-filename json_files/invoices/invoice_Nexus.json
# This will return validation: FAIL with dependency_check exceptions
```
Optional: write the JSON report to a file when validation fails.
```bash
python -m ResolveLight.tool_library.validation_runner_tool \
  --invoice-filename json_files/invoices/invoice_Horizon_PO-2025-308A.json \
  --output system_logs/validation_report.json
```
Report shape:
- `validation`: `PASS` or `FAIL`
- `tool_results`: list of `{ tool, status, exceptions }`
- Echoes resolved `invoice`, `po_item`, `contract` (or "<not found>")

### 3) Triage and route (approve → payments log, or reject → exception + HITL)
Returns a concise status string and writes to logs.
```bash
python -c "from ResolveLight.tool_library.triage_resolution_tool import triage_and_route_tool; \
print(triage_and_route_tool('json_files/invoices/invoice_Horizon_PO-2025-308A.json'))"
```
On PASS:
- Appends a header plus one `payment_item` line per invoice line to `system_logs/payments.log`.

On FAIL:
- Appends a structured record in `system_logs/exceptions_ledger.log` (type `VALIDATION_FAILED`).
- Enqueues a brief task in `system_logs/hitl_queue.log` with a summary and quick figures.

### 4) Generate a services summary (CSV and Markdown)
CSV (default path will be placed next to invoices):
```bash
python -m ResolveLight.tool_library.services_report_tool
# or explicitly choose an output path
python -m ResolveLight.tool_library.services_report_tool --output json_files/invoices/services_summary.csv
```
Markdown table from the CSV (auto‑generates CSV if missing):
```bash
python -c "from ResolveLight.tool_library.services_report_tool import generate_services_markdown_tool; \
print(generate_services_markdown_tool())"
```
Outputs:
- `services_summary.csv`
- `services_summary.md`

## Data Model Expectations (high level)
- Invoice
  - `invoice_id`, `purchase_order_number`, `issue_date`, `due_date`, `payment_terms`
  - `supplier_info` and `bill_to_info`
  - `summary`: `subtotal`, `tax_amount`, `billing_amount`
  - `line_items[]`: `item_id`, `description`, `line_total`, ...
- PO item
  - `po_number`, `contract_id`, `description`, `total_value`, `effective_date` (optional)
- Contract
  - `contract_id`, `contract_title`
  - `contract_metadata`: `effective_date`, `end_date`
  - `parties`: `supplier`, `client`
  - `sections[]` with an entry titled `Scope of Work (SOW)`

## Agents (Optional, Google ADK)
- Root agent: `root_agent.yaml` (class `SequentialAgent`, name `SourceToPay`)
  1. `contract_matching_agent.yaml` (LLM) → calls `resolve_invoice_to_po_and_contract`
  2. `validation_agent.yaml` (LLM) → calls `run_validations_and_format`
  3. `triage_agent.yaml` (LLM) → calls `triage_and_route_tool`

If you have ADK installed and configured, point your runner at `root_agent.yaml`.
Example (syntax depends on your ADK CLI/SDK):
```bash
# Pseudocode / example
adk run --config root_agent.yaml
```

## Logs
- `system_logs/payments.log`: approvals and per‑line payment items
- `system_logs/exceptions_ledger.log`: exceptions with machine‑readable JSON payloads under each header
- `system_logs/hitl_queue.log`: short tasks for human review with key figures

## Notes & Conventions
- Case‑insensitive directory discovery for `json_files` subfolders
- Missing artifacts propagate as "<not found>" to keep outputs predictable
- Time is logged in UTC as ISO8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- All tools accept absolute or relative invoice paths; PO/contract discovery is automatic

Change notes:
- The resolver API was simplified (no logging flags). Resolution is pure and returns
  "<not found>" placeholders; logging is handled in the triage step.

## License
This repository is provided as‑is for demonstration and internal evaluation.
