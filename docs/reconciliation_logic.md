# Reconciliation Logic - Technical Documentation

## Overview

This document describes the technical implementation of the PayFlow Recon reconciliation engine. It details the algorithms, data structures, and decision logic used to match transactions with settlements and identify discrepancies.

## Architecture

### Core Components

```
┌─────────────────┐
│  Data Loader    │ → Validates CSV files
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Reconciliation  │ → Matches records
│     Engine      │   Identifies issues
└────────┬────────┘
         │
         v
┌─────────────────┐
│     Report      │ → Generates outputs
│   Generator     │
└─────────────────┘
```

### Data Flow

1. **Input**: `transactions.csv` + `settlements.csv`
2. **Validation**: Column check, data type validation
3. **Duplicate Detection**: Identify duplicate transaction IDs
4. **Matching**: Match transactions with settlements
5. **Classification**: Assign reconciliation status
6. **Aggregation**: Calculate financial summaries
7. **Output**: Results DataFrame + Summary statistics

## Reconciliation Algorithm

### Step-by-Step Process

#### Step 1: Load and Validate

```python
loader = DataLoader()
transactions_df = loader.load_transactions('transactions.csv')
settlements_df = loader.load_settlements('settlements.csv')
```

**Validation checks**:
- Required columns present
- Date fields parseable
- Amount fields numeric
- Transaction types valid
- No empty transaction IDs

#### Step 2: Identify Duplicates

```python
def _identify_duplicates(df, source_type):
    duplicate_mask = df.duplicated(subset=['transaction_id'], keep='first')
    duplicate_indices = df[duplicate_mask].index.tolist()
    return duplicate_info
```

**Logic**:
- Use pandas `duplicated()` with `keep='first'`
- First occurrence is retained for matching
- Subsequent occurrences flagged as duplicates
- Duplicates are **excluded** from eligible records

**Why first occurrence?**
- Assumes first entry is correct
- Prevents duplicate copies from inflating totals
- Maintains referential integrity

#### Step 3: Separate Eligible Records

```python
trans_eligible = transactions_df[~transactions_df.index.isin(duplicate_indices)]
settle_eligible = settlements_df[~settlements_df.index.isin(duplicate_indices)]
```

Duplicate indices are excluded before matching begins.

#### Step 4: Separate Payments and Refunds

```python
trans_payments = trans_eligible[trans_eligible['type'] == 'PAYMENT']
trans_refunds = trans_eligible[trans_eligible['type'] == 'REFUND']
settle_payments = settle_eligible[settle_eligible['type'] == 'PAYMENT']
settle_refunds = settle_eligible[settle_eligible['type'] == 'REFUND']
```

Payments and refunds are processed separately because they have different matching logic.

#### Step 5: Match Payments

```python
for trans in trans_payments:
    settlement = settle_payments[settle_payments['transaction_id'] == trans_id]
    
    if settlement.empty:
        status = MISSING_SETTLEMENT
    else:
        status = determine_payment_status(trans, settlement)
        matched_settlement_ids.add(trans_id)
```

**Matching logic**:
1. **Transaction ID** is the primary key
2. One-to-one matching (one transaction → one settlement)
3. First matching settlement is used
4. Unmatched transactions → `MISSING_SETTLEMENT`

#### Step 6: Determine Payment Status

```python
def _determine_payment_status(trans_date, settle_date, trans_amount, settle_amount, amount_diff):
    # Check amounts first
    if amount_diff == 0:
        # Check timing
        if settle_date > accounting_period_end:
            return TIMING_DIFFERENCE
        else:
            return MATCHED
    
    # Check tolerance
    if abs(amount_diff) <= individual_tolerance:
        if settle_date > accounting_period_end:
            return TIMING_DIFFERENCE
        else:
            return MATCHED  # Within tolerance
    else:
        return AMOUNT_MISMATCH
```

**Decision tree**:

```
Amount difference = 0?
├─ YES → Settlement date in period?
│         ├─ YES → MATCHED
│         └─ NO  → TIMING_DIFFERENCE
│
└─ NO  → Within tolerance?
          ├─ YES → Settlement date in period?
          │        ├─ YES → MATCHED
          │        └─ NO  → TIMING_DIFFERENCE
          │
          └─ NO  → AMOUNT_MISMATCH
```

**Priority**: Timing differences are identified even when amounts match.

#### Step 7: Identify Unmatched Bank Settlements

```python
for settle in settle_payments:
    if settle_id not in matched_settlement_ids:
        if settle_id not in trans_payments['transaction_id'].values:
            status = UNMATCHED_BANK_ENTRY
```

Bank settlements without corresponding internal transactions.

#### Step 8: Validate Refunds

```python
for refund in settle_refunds:
    original_txn_id = refund['original_transaction_id']
    
    if pd.isna(original_txn_id) or str(original_txn_id).strip() == '':
        status = UNMATCHED_REFUND
    elif original_txn_id not in valid_transaction_ids:
        status = UNMATCHED_REFUND
    else:
        status = MATCHED
```

**Refund validation**:
1. Check `original_transaction_id` is present
2. Verify original transaction exists in **all transactions** (not just payments)
3. If valid → `MATCHED`
4. If invalid → `UNMATCHED_REFUND`

#### Step 9: Analyze Rounding Variance

```python
rounding_items = []
for result in payment_results:
    if result['status'] in [MATCHED, TIMING_DIFFERENCE]:
        if 0 < abs(amount_diff) <= individual_tolerance:
            rounding_items.append(result)

total_variance = sum(abs(diff) for diff in rounding_items)
exceeds_threshold = total_variance > aggregate_tolerance
```

**Two-level check**:
1. **Individual**: Each transaction within ±₹0.01
2. **Aggregate**: Sum of absolute differences

**Why absolute values?**
- Positive and negative differences could cancel out
- Absolute sum shows true cumulative variance
- Example: +₹0.005 × 10 transactions = ₹0.05 (not ₹0.00)

#### Step 10: Compile Results

All matched payments, refunds, and duplicates are compiled into a single DataFrame with columns:
- `transaction_id`
- `type`
- `transaction_date`
- `settlement_date`
- `transaction_amount`
- `settlement_amount`
- `amount_difference`
- `status`
- `explanation`
- `investigation_action`

#### Step 11: Calculate Summary

Financial summary includes:

```python
# Total internal payment value
sum(amount for payment in trans_eligible if payment['type'] == 'PAYMENT')

# Total bank payment value
sum(amount for payment in settle_eligible if payment['type'] == 'PAYMENT')

# Matched amount (use settlement amounts)
sum(settle_amount for result in results 
    if result['status'] in [MATCHED, TIMING_DIFFERENCE])

# Missing settlements
sum(trans_amount for result in results 
    if result['status'] == MISSING_SETTLEMENT)

# Unexplained variance
internal_total - matched_amount - missing_amount
```

## Financial Precision

### Decimal Arithmetic

```python
from decimal import Decimal

trans_amount = Decimal(str(trans['amount']))
settle_amount = Decimal(str(settle['amount']))
amount_diff = trans_amount - settle_amount
```

**Why Decimal?**
- Binary floating-point arithmetic has precision errors
- Example: `0.1 + 0.2 = 0.30000000000000004` (float)
- Decimal provides exact decimal representation
- Critical for financial calculations

### Rounding Example

```python
# Internal: ₹100.005
# Bank: ₹100.000
# Difference: ₹0.005 (within ₹0.01 tolerance)

Decimal('100.005') - Decimal('100.000') = Decimal('0.005')

# 10 transactions
total_variance = Decimal('0.005') * 10 = Decimal('0.050')

# Exceeds threshold
Decimal('0.050') > Decimal('0.02')  # True
```

## Edge Cases

### Empty DataFrames

```python
if trans_payments.empty and settle_payments.empty:
    return []  # No matching needed

if trans_payments.empty:
    # All settlements are unmatched

if settle_payments.empty:
    # All transactions are missing settlements
```

All operations check for empty DataFrames before accessing columns.

### Multiple Duplicates

```python
# TX001 appears 3 times
# Index: [0, 15, 30]

duplicate_mask = [False, True, True]  # keep='first'
duplicate_indices = [15, 30]

# Index 0 is used for matching
# Indices 15, 30 are flagged as duplicates
```

### Refund Without Original

```python
# RF001 references TX999
# TX999 doesn't exist

valid_transaction_ids = set(['TX001', 'TX002', ...])  # No TX999
'TX999' not in valid_transaction_ids  # True
→ Status = UNMATCHED_REFUND
```

## Performance Considerations

### Time Complexity

- **Loading**: O(n) where n = number of rows
- **Duplicate detection**: O(n log n) (pandas duplicated)
- **Matching**: O(n × m) where n = transactions, m = settlements
  - Optimized with set lookups: O(n + m)
- **Overall**: O(n + m) for typical datasets

### Space Complexity

- Stores full DataFrames in memory
- Results DataFrame approximately same size as input
- Suitable for datasets up to ~100K rows

### Optimization for Large Datasets

```python
# Use categorical types for repeated values
df['type'] = df['type'].astype('category')

# Use efficient data types
df['amount'] = pd.to_numeric(df['amount'], downcast='float')

# Index transaction_id for faster lookups
settle_indexed = settle_payments.set_index('transaction_id')
settlement = settle_indexed.loc[txn_id] if txn_id in settle_indexed.index else None
```

## Testing Strategy

### Unit Tests

- Individual functions tested in isolation
- Mock data for controlled scenarios
- Edge cases explicitly tested

### Integration Tests

- End-to-end workflow
- Actual sample data
- Four planted discrepancies verified

### Test Coverage

```
data_loader.py       → 6 validation tests
reconciliation.py    → 12 scenario tests
report_generator.py  → 3 format tests
integration_test.py  → 7 workflow steps
```

## Error Handling

### Validation Errors

```python
class ValidationError(Exception):
    pass

try:
    df = loader.load_transactions(file_path)
except ValidationError as e:
    # User-friendly error message
    # Explains what's wrong and how to fix it
```

### Data Quality Errors

- **Missing columns**: Explicit error with column names
- **Invalid dates**: Shows affected rows
- **Invalid amounts**: Identifies non-numeric values
- **Empty files**: Clear message, not a crash

### Graceful Degradation

- Empty DataFrames handled without errors
- Missing optional fields use sensible defaults
- Partial data still produces results

## Output Format

### Results DataFrame

| Column | Type | Description |
|--------|------|-------------|
| transaction_id | str | Unique transaction identifier |
| type | str | PAYMENT or REFUND |
| transaction_date | datetime | When transaction was recorded |
| settlement_date | datetime | When bank settled |
| transaction_amount | float | Internal amount |
| settlement_amount | float | Bank amount |
| amount_difference | float | Internal - Bank |
| status | str | Reconciliation classification |
| explanation | str | Human-readable explanation |
| investigation_action | str | Recommended next step |

### Summary Dictionary

```python
{
    'total_internal_transactions': int,
    'total_internal_payment_value': float,
    'total_bank_settlements': int,
    'total_bank_payment_value': float,
    'matched_count': int,
    'matched_amount': float,
    'timing_difference_count': int,
    'missing_settlement_count': int,
    'duplicate_bank_count': int,
    'unmatched_refund_count': int,
    'rounding_variance_total': float,
    'unexplained_variance': float
}
```

## Future Enhancements

### Potential Improvements

1. **Performance**: Database backend for large datasets
2. **Matching**: Fuzzy matching for near-matches
3. **History**: Track changes over multiple periods
4. **Automation**: Scheduled runs with email alerts
5. **Multi-currency**: Support multiple currencies
6. **Partial matches**: One transaction → multiple settlements

### Extensibility

The modular design allows:
- Custom reconciliation rules
- Additional status classifications
- Alternative matching algorithms
- Pluggable report formats

---

**Last Updated**: November 17, 2026  
**Version**: 1.0
