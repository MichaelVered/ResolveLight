# ResolveLight Operator Manual
## Invoice-to-Pay Processing System

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [Daily Operations](#daily-operations)
4. [Understanding Invoice Processing](#understanding-invoice-processing)
5. [Exception Queues and Resolution](#exception-queues-and-resolution)
6. [Monitoring and Logs](#monitoring-and-logs)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## 🎯 System Overview

ResolveLight is an automated invoice processing system that validates, matches, and routes invoices for payment. The system uses artificial intelligence to:

- **Match invoices** to purchase orders and contracts
- **Validate** invoice details against business rules
- **Detect duplicates** and prevent overpayments
- **Route exceptions** to appropriate queues for human review
- **Approve valid invoices** for automatic payment

### What This Means for You

As an operator, you'll primarily work with:
- **Approved invoices** that process automatically
- **Exception queues** that need your review and action
- **System logs** for monitoring and troubleshooting

---

## 🚀 Getting Started

### Starting the System

1. **Open Terminal** in Cursor
2. **Activate Virtual Environment** (use your keyboard shortcut: `Option + Command + V`)
3. **Run the System**:
   ```bash
   python runner.py
   ```

### Your First Invoice

When you start the system, you'll see:
```
Running agent SourceToPay, type exit to exit.
[user]: 
```

To process an invoice, simply provide the file path:
```
[user]: /path/to/invoice_file.json
```

The system will automatically:
1. Find the matching purchase order and contract
2. Validate the invoice details
3. Make a routing decision
4. Show you the result

---

## 📊 Daily Operations

### Processing Invoices

#### Step 1: Submit Invoice
Provide the full path to your invoice JSON file:
```
[user]: json_files/golden_invoices/invoice_Aegis_PO-2025-304A.json
```

#### Step 2: Review Results
The system will show you a detailed report:

**✅ APPROVED Invoices:**
```
[contract_matching_agent]: Invoice: invoice_id: INV-AEG-2025-001, purchase_order_number: PO-2025-304A
PO Item: po_number: PO-2025-304A, contract_id: CON-TECH-2025-004
Contract: contract_id: CON-TECH-2025-004, contract_title: 2025 Master Services Agreement - Project Aegis

[validation_agent]: supplier_match_tool: PASS
simple_overbilling_tool: PASS
date_check_tool: PASS
validation: PASS

[triage_agent]: APPROVED
```

**❌ REJECTED Invoices:**
```
[contract_matching_agent]: Invoice: invoice_id: INV-NEX-2025-001, purchase_order_number: <not found>
PO Item: po_number: <not found>, contract_id: <not found>
Contract: contract_id: <not found>, contract_title: <not found>

[validation_agent]: dependency_check: FAIL - reasons: po_item_not_found, contract_not_found
validation: FAIL

[triage_agent]: REJECTED - reasons: po_item_not_found, contract_not_found
```

### Understanding the Results

#### ✅ APPROVED
- Invoice is valid and ready for payment
- All validations passed
- No human intervention needed
- Payment will be processed automatically

#### ❌ REJECTED
- Invoice has issues that prevent automatic payment
- Check the specific failure reasons
- Invoice will be routed to an exception queue for review

---

## 🔍 Understanding Invoice Processing

### The Three-Step Process

#### 1. Contract Matching
**What it does:** Finds the purchase order and contract for the invoice
**What you see:**
- Invoice details (ID, PO number)
- Matched PO information
- Contract details

**Common issues:**
- `<not found>` means the PO or contract doesn't exist
- Check if invoice has correct PO number
- Verify PO and contract files are in the system

#### 2. Validation
**What it does:** Checks invoice against business rules
**Validation checks:**
- **Supplier Match:** Is the supplier correct?
- **Overbilling:** Is the amount within limits?
- **Date Check:** Are dates valid?
- **Line Items:** Do line items match the PO?

**What you see:**
- Each validation tool result (PASS/FAIL)
- Overall validation status

#### 3. Triage Resolution
**What it does:** Makes final routing decision
**Possible outcomes:**
- **APPROVED:** Ready for payment
- **REJECTED:** Sent to exception queue
- **PENDING_APPROVAL:** Needs manager approval

---

## 🚨 Exception Queues and Resolution

When invoices are rejected, they're sent to specialized queues based on the type of problem.

### High Priority Queues (Manager Approval Required)

#### 🔴 Duplicate Invoices
**What it is:** Potential duplicate payments detected
**What to do:**
1. Check the duplicate detection log
2. Compare with previously processed invoices
3. If truly duplicate, reject permanently
4. If not duplicate, investigate matching logic

#### 🔴 Missing Data
**What it is:** Missing purchase order or contract data
**What to do:**
1. Verify PO number is correct
2. Check if PO file exists in the system
3. Create missing PO or contract if needed
4. Re-process the invoice

#### 🔴 Low Confidence Matches
**What it is:** Fuzzy matching below 70% confidence
**What to do:**
1. Review the matching analysis
2. Check for typos in PO numbers or supplier names
3. Manually verify the match
4. Update data if needed and re-process

#### 🔴 Price Discrepancies
**What it is:** Line item validation failures
**What to do:**
1. Compare invoice line items with PO line items
2. Check for quantity or price differences
3. Verify if changes are legitimate
4. Approve if valid, reject if not

#### 🔴 Billing Discrepancies
**What it is:** Overbilling or arithmetic errors
**What to do:**
1. Check total amounts against PO limits
2. Verify calculations are correct
3. Check for unauthorized charges
4. Approve if within limits, reject if overbilling

#### 🔴 High Value Approval
**What it is:** Invoices over $10,000
**What to do:**
1. Review all details carefully
2. Verify against contract terms
3. Check for proper authorization
4. Approve if all checks pass

### Medium Priority Queues (No Manager Approval Required)

#### 🟡 Supplier Mismatch
**What it is:** Supplier information doesn't match
**What to do:**
1. Check supplier name and vendor ID
2. Verify against PO and contract
3. Update supplier information if needed
4. Re-process the invoice

#### 🟡 Date Discrepancies
**What it is:** Date validation failures
**What to do:**
1. Check invoice date, due date, and payment terms
2. Verify against contract terms
3. Check for reasonable date ranges
4. Approve if dates are valid

### Normal Priority Queues

#### 🟢 General Exceptions
**What it is:** Other validation failures
**What to do:**
1. Review the specific error message
2. Check all invoice details
3. Verify against business rules
4. Take appropriate action

---

## 📈 Monitoring and Logs

### Key Log Files

#### `payments.log`
**What it contains:** All approved payments
**When to check:** Daily to verify approved invoices
**Format:**
```
[2025-01-15 10:30:15] APPROVED: INV-AEG-2025-001 - $6,000.00 - Quantum Apps Co.
```

#### `exceptions_ledger.log`
**What it contains:** All rejected invoices and reasons
**When to check:** When investigating issues
**Format:**
```
[2025-01-15 10:35:22] REJECTED: INV-NEX-2025-001 - missing_data - PO not found
```

#### Queue-Specific Logs
**What they contain:** Invoices routed to specific queues
**Files:**
- `queue_duplicate_invoices.log`
- `queue_missing_data.log`
- `queue_low_confidence_matches.log`
- `queue_price_discrepancies.log`
- `queue_billing_discrepancies.log`
- `queue_high_value_approval.log`
- `queue_supplier_mismatch.log`
- `queue_date_discrepancies.log`
- `queue_general_exceptions.log`

### Daily Monitoring Checklist

1. **Check payments.log** - Verify approved invoices
2. **Review exception queues** - Process pending items
3. **Monitor system performance** - Check processing times
4. **Verify data integrity** - Ensure all files are accessible

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue: "PO not found" or "Contract not found"
**Possible causes:**
- Incorrect PO number in invoice
- Missing PO or contract file
- File path issues

**Solutions:**
1. Verify PO number in invoice matches PO file name
2. Check if PO file exists in `json_files/POs/` directory
3. Check if contract file exists in `json_files/contracts/` directory
4. Ensure file names match exactly (case-sensitive)

#### Issue: "Low confidence match"
**Possible causes:**
- Typos in PO numbers or supplier names
- Inconsistent naming conventions
- Missing or incorrect data

**Solutions:**
1. Check for typos in invoice data
2. Verify supplier name matches exactly
3. Check vendor ID consistency
4. Update data and re-process

#### Issue: "Validation failed"
**Possible causes:**
- Amount exceeds limits
- Date issues
- Supplier mismatch
- Line item problems

**Solutions:**
1. Check specific validation error
2. Verify against PO and contract terms
3. Check for data entry errors
4. Update incorrect data

#### Issue: System not responding
**Possible causes:**
- API key issues
- Network problems
- System overload

**Solutions:**
1. Check API key configuration
2. Restart the system
3. Check network connectivity
4. Review system logs for errors

### Getting Help

1. **Check logs first** - Most issues are logged with details
2. **Review this manual** - Common solutions are documented
3. **Contact support** - For complex issues not covered here

---

## ✅ Best Practices

### Daily Operations

1. **Start with approved invoices** - Process clean invoices first
2. **Review exceptions promptly** - Don't let queues build up
3. **Check logs regularly** - Monitor system health
4. **Verify data quality** - Ensure PO and contract files are accurate

### Data Management

1. **Keep files organized** - Use consistent naming conventions
2. **Update data promptly** - Fix issues as they're discovered
3. **Backup regularly** - Keep copies of important files
4. **Document changes** - Note any manual overrides or fixes

### Exception Handling

1. **Prioritize high-priority queues** - Handle manager approval items first
2. **Investigate thoroughly** - Don't just approve to clear queues
3. **Document decisions** - Note why you approved or rejected items
4. **Follow up** - Ensure issues are resolved, not just bypassed

### System Maintenance

1. **Monitor performance** - Watch for slow processing times
2. **Clean up logs** - Archive old log files regularly
3. **Update data** - Keep PO and contract files current
4. **Test changes** - Verify fixes work before processing production invoices

---

## 📞 Quick Reference

### Keyboard Shortcuts
- **Option + Command + V** - Activate virtual environment

### Common Commands
- **Process invoice:** `json_files/golden_invoices/invoice_filename.json`
- **Exit system:** `exit`
- **View logs:** Check `system_logs/` directory

### File Locations
- **Invoices:** `json_files/golden_invoices/`
- **POs:** `json_files/POs/`
- **Contracts:** `json_files/contracts/`
- **Logs:** `system_logs/`

### Status Meanings
- **APPROVED** - Ready for payment
- **REJECTED** - Sent to exception queue
- **PENDING_APPROVAL** - Needs manager review
- **PASS** - Validation successful
- **FAIL** - Validation failed

---

*This manual covers the essential operations for ResolveLight. For technical details or advanced configuration, refer to the main README.MD file.*
