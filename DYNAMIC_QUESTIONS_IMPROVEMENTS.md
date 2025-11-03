# Dynamic Questions Improvements

## Overview
Enhanced the LLM dynamic question generation system to provide comprehensive context, including all past questions, human answers, and related documents (exception details, invoice, PO, contract).

## Key Changes

### 1. Fixed Conversation History Retrieval
**Location:** `learning_agent/feedback_llm_service.py` - `_build_conversation_history()` method

**Problem:** The LLM was seeing `[Previous question from system]` as a placeholder instead of actual questions.

**Solution:** 
- Now retrieves the actual `conversation_history` field from the database
- Includes all previously asked questions and human responses
- Properly structures the conversation flow

```python
# Retrieve the actual conversation history from the database
conversation_history_text = initial.get('conversation_history', '')
if conversation_history_text:
    history_parts.append("\nCONVERSATION HISTORY:")
    history_parts.append("=" * 40)
    history_parts.append(conversation_history_text)
```

### 2. Added Comprehensive Context Retrieval
**Location:** `learning_agent/feedback_llm_service.py` - `_get_conversation_context()` method

**New Capability:** The LLM now receives full context before formulating questions:

#### Exception Details
- Exception ID, Type, Queue, Status
- Routing Reason
- Supplier, Amount, PO Number
- Validation Details (including all discrepancy information)

#### Invoice Details
- Invoice ID, Supplier, Total Amount
- Invoice Date, PO Number
- Line Items Summary (showing first 3 items)

#### Purchase Order Details
- PO Number, Total Amount, Status
- Contract ID
- PO Line Items Summary (showing first 3 items)

#### Contract Details
- Contract ID, Supplier
- Start/End Dates, Total Value
- Pricing Terms

### 3. Enhanced Question Generation Prompt

The LLM now receives this structured context:

```
INITIAL FEEDBACK:
Expert: [Name]
Decision: [Human Correction]
EXPERT FEEDBACK: [Feedback Text]
Correct Action: [Action]

EXCEPTION DETAILS:
==========
[All exception information]

INVOICE DETAILS:
==========
[Invoice information + line items]

PURCHASE ORDER DETAILS:
==========
[PO information + line items]

CONTRACT DETAILS:
==========
[Contract information + pricing terms]

CONVERSATION HISTORY:
========================================
QUESTION 1: [Actual first question]
RESPONSE 1: [Human's answer]

QUESTION 2: [Actual second question]
RESPONSE 2: [Human's answer]

FOLLOW-UP RESPONSES:
========================================
RESPONSE 3: [Additional responses]
```

## Benefits

1. **More Effective Questions**: The LLM can now formulate questions based on:
   - What has already been asked
   - What the human has answered
   - Specific discrepancies in the documents
   - Business rules embedded in contracts

2. **Reduced Redundancy**: Questions won't repeat information already gathered

3. **Context-Aware**: Questions can reference specific amounts, percentages, thresholds mentioned in invoices, POs, or contracts

4. **Better Learning**: The enhanced context enables extraction of more precise business rules

## Testing Recommendations

1. **Test with Price Discrepancies**: Verify that the LLM asks about specific price differences found in validation details
2. **Test with Quantity Mismatches**: Ensure PO quantities vs invoice quantities are referenced in questions
3. **Test Conversation Flow**: Confirm that follow-up questions build on previous answers
4. **Test with Missing Context**: Ensure graceful handling when exception/invoice/PO/contract data is missing

## Example Scenario

**Exception:** Price discrepancy - Invoice shows $1,200 but PO shows $1,000

**Context Now Provided:**
- Exception details showing the $200 difference
- Invoice showing item: "Widget A - Qty: 10 @ $120"
- PO showing item: "Widget A - Qty: 10 @ $100"
- Contract showing pricing terms

**Question Generation:**
Instead of generic: "What is the acceptable price threshold?"
Now asks: "I see Widget A has a $20 per unit price increase (20% over PO). What is your policy for price increases over 15% for this supplier?"

This demonstrates the LLM's ability to formulate specific, actionable questions based on comprehensive context.




