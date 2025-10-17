# Learning Scenarios: Agent Failure Cases
## Scenarios Where Valid Invoices Are Incorrectly Rejected

These scenarios demonstrate cases where the ResolveLight agent fails to approve valid invoices due to knowledge, skill, or experience limitations in a stateless processing environment.

---

## 1. Contract Amendment Scenario
**Agent Limitation:** Cannot detect contract amendments or version changes

**Scenario:** 
- Invoice references original contract ID `CON-TECH-2025-001`
- Contract amendment `CON-TECH-2025-001-A` increases Q1 NTE from $65K to $80K
- Invoice amount: $75,000
- **Agent Action:** Rejects for exceeding original Q1 limit ($65K)
- **Reality:** Invoice is valid under the amended contract terms

**Learning Need:** Contract version management and amendment tracking

---

## 2. Multi-Currency with Exchange Rate Fluctuation
**Agent Limitation:** No currency conversion or exchange rate handling

**Scenario:**
- PO created in USD: $10,000
- Invoice submitted in EUR: €9,200
- Current exchange rate: 1 USD = 0.92 EUR (making €9,200 = $10,000)
- **Agent Action:** Rejects for "currency mismatch" and "amount discrepancy"
- **Reality:** Amounts are equivalent after currency conversion

**Learning Need:** Multi-currency support and real-time exchange rate integration

---

## 3. Pro-rated Billing for Partial Deliverables
**Agent Limitation:** Cannot understand partial completion or milestone-based billing

**Scenario:**
- Contract specifies 100% completion for $50,000
- Invoice bills 60% completion for $30,000
- **Agent Action:** Rejects for "insufficient line item detail" and "unclear billing basis"
- **Reality:** This is standard milestone-based billing practice

**Learning Need:** Milestone and percentage-based billing logic

---

## 4. Vendor Name Variations and Legal Entity Changes
**Agent Limitation:** Rigid supplier matching without understanding corporate structures

**Scenario:**
- PO lists supplier as "ABC Corp"
- Invoice comes from "ABC Corporation LLC"
- Same vendor, different legal entity name
- **Agent Action:** Rejects for "supplier mismatch"
- **Reality:** Both names refer to the same company

**Learning Need:** Fuzzy supplier matching and corporate entity recognition

---

## 5. Complex Line Item Aggregation
**Agent Limitation:** Cannot handle aggregated billing or service bundling

**Scenario:**
- PO has 5 separate line items at $2,000 each
- Invoice presents as single "Professional Services Package" for $10,000
- **Agent Action:** Rejects for "line item count mismatch" and "description inconsistency"
- **Reality:** Service bundling is a common business practice

**Learning Need:** Flexible line item matching and service aggregation understanding

---

## Key Insights

These scenarios highlight the gap between rule-based validation and real-world business complexity. The agent needs:

1. **Contextual Understanding** - Beyond simple field matching
2. **Business Logic Knowledge** - Understanding industry practices
3. **Flexible Matching** - Handling variations and edge cases
4. **External Data Integration** - Exchange rates, contract amendments
5. **Pattern Recognition** - Identifying valid business patterns vs. errors

## Testing Strategy

To improve the agent's performance:
1. Create test cases for each scenario
2. Implement enhanced validation logic
3. Add external data sources (exchange rates, contract versions)
4. Develop fuzzy matching algorithms
5. Build business rule knowledge base
