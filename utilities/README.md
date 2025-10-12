# Utilities

This folder contains utility scripts for testing and maintenance of the ResolveLight project.

## Test Scripts

### `test_golden_set.py`

A comprehensive test suite that validates the entire agentic workflow against the golden dataset.

**Purpose:**
- Tests all invoices in the golden dataset through the complete agentic workflow
- Validates fuzzy matching, validation, and triage routing
- Provides detailed reporting on test results

**Usage:**
```bash
python utilities/test_golden_set.py
```

**What it tests:**
1. **Fuzzy Matching**: PO and contract resolution with confidence scores
2. **Validation**: All validation tools (supplier, billing, dates, line items, duplicates)
3. **Triage & Routing**: Final routing decisions and queue assignments

**Output:**
- Per-invoice detailed results
- Summary statistics
- Exception tracking
- Queue routing analysis

**Example Output:**
```
🎯 GOLDEN SET TEST SUITE
============================================================
📋 Found 11 invoice files

🔍 Testing: invoice_Aegis_PO-2025-304A.json
============================================================
1️⃣ Testing Fuzzy Matching...
   ✅ Confidence: 100.0%
   ✅ PO Found: True
   ✅ Contract Found: True
2️⃣ Testing Validation...
   ✅ Validation: PASS
3️⃣ Testing Triage & Routing...
   ✅ Final Status: APPROVED
   📋 No routing queue (approved)

📊 TEST SUMMARY
================================================================================
Total Invoices Tested: 11
Successful Tests: 11
Failed Tests: 0

📋 Validation Results:
   Passed: 11/11
   Failed: 0/11

📋 Routing Results:
   high_value_approval: 1 invoices
   approved: 10 invoices

⚠️  Exceptions Found:
   invoice_Nexus_PO-2025-NEX-001.json: EXC-C7E8E2D996E0 → high_value_approval

🎉 All tests passed!
```

**Exit Codes:**
- `0`: All tests passed
- `1`: One or more tests failed

**Key Features:**
- **Comprehensive Coverage**: Tests all components of the agentic workflow
- **Detailed Reporting**: Shows exactly what passed/failed and why
- **Exception Tracking**: Identifies invoices that require manual review
- **Queue Analysis**: Shows routing distribution across different queues
- **Golden Dataset Validation**: Ensures the synthetic data works correctly

This script is essential for:
- Validating changes to the agentic workflow
- Ensuring the golden dataset remains consistent
- Identifying regressions in validation logic
- Monitoring the health of the entire system
