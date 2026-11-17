# Business Assumptions - PayFlow Recon

## Accounting Period

**Period**: November 1-30, 2026

All reconciliation is performed within this accounting period. Transactions recorded in November but settled in December are classified as timing differences, not missing settlements.

## Currency

**Currency**: INR (Indian Rupees)

All monetary amounts are in Indian Rupees. The system uses Python's `Decimal` type for precise financial calculations, avoiding floating-point arithmetic errors.

## Transaction Matching

### Primary Key
- **Transaction ID** is the primary matching key between internal records and bank settlements
- Transaction IDs must be unique within each dataset (duplicates are flagged)
- Matching is case-sensitive

### Transaction Types
Two types of transactions are supported:
1. **PAYMENT**: Standard customer payment
2. **REFUND**: Refund of a previous payment

## Payment Processing Flow

### Internal Recording
- Payments are **recorded immediately** when they occur
- Transaction date reflects when the payment was initiated

### Bank Settlement
- Banks settle funds in **batches**
- Settlement typically occurs **1-2 days** after the transaction
- Settlement date reflects when the bank actually processed the funds

### Month-End Scenario
- A transaction on November 30 may settle on December 1 or 2
- This is a **timing difference**, not a missing payment
- Such transactions should appear in December's reconciliation

## Refund Handling

### Valid Refunds
- Must reference an `original_transaction_id`
- The original transaction must exist in the internal transaction ledger
- Refund amounts are typically negative

### Invalid Refunds
- Refunds with no `original_transaction_id` are flagged
- Refunds referencing non-existent transactions are classified as **UNMATCHED_REFUND**
- These require investigation to locate the original transaction

## Financial Tolerances

### Individual Rounding Tolerance
**Value**: ₹0.01

- Small differences up to ₹0.01 per transaction are considered acceptable rounding
- Transactions within this tolerance are marked as MATCHED
- Example: Internal ₹100.005 vs Bank ₹100.00 = ₹0.005 difference (within tolerance)

### Aggregate Rounding Threshold
**Value**: ₹0.02

- The **sum of absolute individual rounding differences** across all transactions
- If the aggregate exceeds ₹0.02, it's flagged for review
- Example: Ten transactions with ₹0.005 difference each = ₹0.05 aggregate (exceeds threshold)

### Why Both Tolerances?

Individual small differences may be acceptable, but their cumulative effect can be significant. Both thresholds ensure:
1. Individual transactions aren't falsely flagged
2. Systematic rounding issues are detected

## Duplicate Entry Handling

### Detection
- Duplicates are identified by **transaction_id**
- The first occurrence is retained
- Subsequent occurrences are flagged as duplicates

### Financial Impact
- **Duplicate amounts are excluded** from financial totals
- This prevents inflating matched amounts
- Example: If TX001 appears twice in settlements, only one ₹107 is counted

### Classification
- `DUPLICATE_TRANSACTION_ENTRY`: Duplicate in internal records
- `DUPLICATE_BANK_ENTRY`: Duplicate in bank settlements

## Data Quality Assumptions

### Required Fields
All records must contain:
- `transaction_id` (string, non-empty)
- `amount` (numeric, can be negative for refunds)
- `transaction_date` or `settlement_date` (valid date)
- `type` (must be PAYMENT or REFUND)
- `original_transaction_id` (required for refunds, optional for payments)

### Valid Data
- Dates must be parseable (YYYY-MM-DD format)
- Amounts must be numeric
- Transaction types must be PAYMENT or REFUND
- Empty files are handled gracefully

### Invalid Records
- Records failing validation are **not silently discarded**
- Clear error messages are provided
- The entire file is rejected if critical errors are found

## Reconciliation Priority

When classifying discrepancies, the following precedence is used:

1. **Duplicates** (detected first, excluded from matching)
2. **Timing Differences** (matched by ID, but settlement date outside period)
3. **Amount Mismatches** (matched by ID, but amounts differ significantly)
4. **Missing Settlements** (internal transaction with no bank settlement)
5. **Unmatched Bank Entries** (bank settlement with no internal transaction)
6. **Unmatched Refunds** (refund referencing non-existent original transaction)

## Financial Calculations

### Totals Calculation

**Internal Payment Total**:
```
Sum of all payment amounts in transactions.csv
(excluding duplicates, excluding refunds)
```

**Bank Settlement Total**:
```
Sum of all payment amounts in settlements.csv
(excluding duplicates, excluding refunds)
```

**Matched Amount**:
```
Sum of settlement amounts for MATCHED and TIMING_DIFFERENCE status
(using bank settlement amounts, not internal amounts)
```

### Unexplained Variance

```
Unexplained Variance = Internal Total - Matched Amount - Missing Settlements
```

A small unexplained variance (typically the rounding variance) is acceptable.

## Reporting Assumptions

### Report Generation
- Reports include metadata (generation date, accounting period)
- CSV reports use comma delimiters
- Text reports use UTF-8 encoding

### Audit Trail
- Original CSV files are **never modified**
- All changes are tracked in reconciliation results
- Reports can be regenerated at any time

## Use Case Assumptions

### Users
- Finance operations analysts
- Accounting team members
- Auditors

### Environment
- Internal use within finance department
- No sensitive PII in transaction data
- Desktop/laptop with modern web browser

### Workflow
1. Export transactions from internal system
2. Receive settlement file from bank
3. Upload both files to PayFlow Recon
4. Review dashboard and exceptions
5. Download reports for documentation
6. Investigate flagged exceptions

## Limitations Acknowledged

- **Single Accounting Period**: One month at a time
- **Manual Upload**: No automated data pipeline
- **Post-Processing**: Reconciliation happens after settlement, not real-time
- **No Historical Trend Analysis**: Each month is independent

## Edge Cases Handled

✅ Empty settlement file (all transactions flagged as missing settlements)  
✅ Empty transaction file (all settlements flagged as unmatched)  
✅ All records perfectly matched  
✅ Multiple duplicates of same transaction ID  
✅ Refunds without original transactions  
✅ Negative payment amounts  
✅ Zero-value transactions  

## Edge Cases Not Handled

❌ Multi-currency reconciliation  
❌ Partial settlements (one transaction → multiple settlements)  
❌ Split transactions (one payment → multiple internal records)  
❌ Historical data migration  
❌ Real-time streaming reconciliation  

---

**Last Updated**: November 17, 2026  
**Version**: 1.0
