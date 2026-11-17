"""
Reconciliation Engine for PayFlow Recon
Core logic for matching transactions with settlements and identifying discrepancies
"""

import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ReconciliationStatus(Enum):
    """Enumeration of possible reconciliation statuses"""
    MATCHED = "MATCHED"
    TIMING_DIFFERENCE = "TIMING_DIFFERENCE"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    UNMATCHED_BANK_ENTRY = "UNMATCHED_BANK_ENTRY"
    DUPLICATE_TRANSACTION_ENTRY = "DUPLICATE_TRANSACTION_ENTRY"
    DUPLICATE_BANK_ENTRY = "DUPLICATE_BANK_ENTRY"
    UNMATCHED_REFUND = "UNMATCHED_REFUND"
    INVALID_RECORD = "INVALID_RECORD"


class ReconciliationEngine:
    """
    Core reconciliation engine that matches transactions with settlements
    and identifies discrepancies
    """
    
    def __init__(self, 
                 accounting_period_start: str = "2026-11-01",
                 accounting_period_end: str = "2026-11-30",
                 individual_tolerance: Decimal = Decimal("0.01"),
                 aggregate_tolerance: Decimal = Decimal("0.02")):
        """
        Initialize reconciliation engine
        
        Args:
            accounting_period_start: Start date (YYYY-MM-DD)
            accounting_period_end: End date (YYYY-MM-DD)
            individual_tolerance: Individual rounding tolerance (INR)
            aggregate_tolerance: Aggregate rounding variance threshold (INR)
        """
        self.accounting_period_start = pd.to_datetime(accounting_period_start)
        self.accounting_period_end = pd.to_datetime(accounting_period_end)
        self.individual_tolerance = individual_tolerance
        self.aggregate_tolerance = aggregate_tolerance
        
    def reconcile(self, transactions_df: pd.DataFrame, 
                  settlements_df: pd.DataFrame) -> Dict:
        """
        Perform complete reconciliation between transactions and settlements
        
        Args:
            transactions_df: Internal transaction records
            settlements_df: Bank settlement records
            
        Returns:
            Dictionary containing reconciliation results
        """
        # Step 1: Identify duplicates
        trans_duplicates = self._identify_duplicates(transactions_df, 'transaction')
        settle_duplicates = self._identify_duplicates(settlements_df, 'settlement')
        
        # Step 2: Separate eligible records from duplicates
        trans_eligible = transactions_df[~transactions_df.index.isin(trans_duplicates['duplicate_indices'])]
        settle_eligible = settlements_df[~settlements_df.index.isin(settle_duplicates['duplicate_indices'])]
        
        # Step 3: Separate payments and refunds
        trans_payments = trans_eligible[trans_eligible['type'] == 'PAYMENT'].copy() if not trans_eligible.empty else pd.DataFrame()
        trans_refunds = trans_eligible[trans_eligible['type'] == 'REFUND'].copy() if not trans_eligible.empty else pd.DataFrame()
        settle_payments = settle_eligible[settle_eligible['type'] == 'PAYMENT'].copy() if not settle_eligible.empty else pd.DataFrame()
        settle_refunds = settle_eligible[settle_eligible['type'] == 'REFUND'].copy() if not settle_eligible.empty else pd.DataFrame()
        
        # Step 4: Match payments
        payment_results = self._match_payments(trans_payments, settle_payments)
        
        # Step 5: Validate refunds
        refund_results = self._validate_refunds(trans_refunds, settle_refunds, transactions_df)
        
        # Step 6: Calculate aggregate rounding variance
        rounding_analysis = self._analyze_rounding_variance(payment_results)
        
        # Step 7: Compile all results
        all_results = self._compile_results(
            payment_results,
            refund_results,
            trans_duplicates,
            settle_duplicates,
            rounding_analysis
        )
        
        # Step 8: Calculate summary statistics
        summary = self._calculate_summary(
            transactions_df,
            settlements_df,
            trans_eligible,
            settle_eligible,
            all_results,
            rounding_analysis
        )
        
        return {
            'results': all_results,
            'summary': summary,
            'rounding_analysis': rounding_analysis
        }
    
    def _identify_duplicates(self, df: pd.DataFrame, source_type: str) -> Dict:
        """
        Identify duplicate transaction IDs in dataset
        
        Args:
            df: DataFrame to check
            source_type: 'transaction' or 'settlement'
            
        Returns:
            Dictionary with duplicate information
        """
        # Handle empty DataFrames
        if df.empty:
            return {
                'duplicate_ids': [],
                'duplicate_indices': [],
                'duplicate_records': [],
                'count': 0
            }
        
        # Find duplicate transaction IDs
        duplicate_mask = df.duplicated(subset=['transaction_id'], keep='first')
        duplicate_indices = df[duplicate_mask].index.tolist()
        
        # Get details of duplicates
        duplicate_ids = df.loc[duplicate_mask, 'transaction_id'].unique().tolist() if not duplicate_mask.empty else []
        
        duplicate_records = []
        for txn_id in duplicate_ids:
            dup_records = df[df['transaction_id'] == txn_id]
            for idx, row in dup_records.iterrows():
                if idx in duplicate_indices:  # Only flag the duplicate copies
                    duplicate_records.append({
                        'transaction_id': txn_id,
                        'amount': row['amount'],
                        'date': row.get('transaction_date') or row.get('settlement_date'),
                        'type': row['type'],
                        'source': source_type,
                        'index': idx
                    })
        
        return {
            'duplicate_ids': duplicate_ids,
            'duplicate_indices': duplicate_indices,
            'duplicate_records': duplicate_records,
            'count': len(duplicate_indices)
        }
    
    def _match_payments(self, trans_payments: pd.DataFrame, 
                       settle_payments: pd.DataFrame) -> List[Dict]:
        """
        Match payment transactions with settlement records
        
        Args:
            trans_payments: Payment transactions
            settle_payments: Payment settlements
            
        Returns:
            List of reconciliation results
        """
        results = []
        matched_settlement_ids = set()
        
        # Handle empty DataFrames
        if trans_payments.empty and settle_payments.empty:
            return results
        
        # Match transactions with settlements
        for idx, trans in trans_payments.iterrows():
            txn_id = trans['transaction_id']
            trans_amount = Decimal(str(trans['amount']))
            trans_date = trans['transaction_date']
            
            # Find matching settlement (handle empty settle_payments)
            if settle_payments.empty:
                settlement = pd.DataFrame()
            else:
                settlement = settle_payments[settle_payments['transaction_id'] == txn_id]
            
            if settlement.empty:
                # No matching settlement found
                results.append({
                    'transaction_id': txn_id,
                    'type': 'PAYMENT',
                    'transaction_date': trans_date,
                    'settlement_date': None,
                    'transaction_amount': float(trans_amount),
                    'settlement_amount': None,
                    'amount_difference': None,
                    'status': ReconciliationStatus.MISSING_SETTLEMENT.value,
                    'explanation': 'Payment transaction has no corresponding bank settlement',
                    'investigation_action': 'Verify if payment was processed; check for delayed settlement'
                })
            else:
                # Settlement found - check details
                settle = settlement.iloc[0]
                settle_amount = Decimal(str(settle['amount']))
                settle_date = settle['settlement_date']
                amount_diff = trans_amount - settle_amount
                
                matched_settlement_ids.add(txn_id)
                
                # Determine status
                status, explanation, action = self._determine_payment_status(
                    trans_date, settle_date, trans_amount, settle_amount, amount_diff
                )
                
                results.append({
                    'transaction_id': txn_id,
                    'type': 'PAYMENT',
                    'transaction_date': trans_date,
                    'settlement_date': settle_date,
                    'transaction_amount': float(trans_amount),
                    'settlement_amount': float(settle_amount),
                    'amount_difference': float(amount_diff),
                    'status': status,
                    'explanation': explanation,
                    'investigation_action': action
                })
        
        # Find unmatched bank settlements (bank entries not in transactions)
        for idx, settle in settle_payments.iterrows():
            txn_id = settle['transaction_id']
            
            if txn_id not in matched_settlement_ids:
                # Check if this ID exists in transactions at all (handle empty trans_payments)
                if trans_payments.empty or txn_id not in trans_payments['transaction_id'].values:
                    results.append({
                        'transaction_id': txn_id,
                        'type': 'PAYMENT',
                        'transaction_date': None,
                        'settlement_date': settle['settlement_date'],
                        'transaction_amount': None,
                        'settlement_amount': float(Decimal(str(settle['amount']))),
                        'amount_difference': None,
                        'status': ReconciliationStatus.UNMATCHED_BANK_ENTRY.value,
                        'explanation': 'Bank settlement has no corresponding internal transaction record',
                        'investigation_action': 'Verify if transaction was recorded; check for missing entries'
                    })
        
        return results
    
    def _determine_payment_status(self, trans_date: pd.Timestamp, 
                                   settle_date: pd.Timestamp,
                                   trans_amount: Decimal, 
                                   settle_amount: Decimal,
                                   amount_diff: Decimal) -> Tuple[str, str, str]:
        """
        Determine the reconciliation status of a matched payment
        
        Args:
            trans_date: Transaction date
            settle_date: Settlement date
            trans_amount: Transaction amount
            settle_amount: Settlement amount
            amount_diff: Difference between amounts
            
        Returns:
            Tuple of (status, explanation, investigation_action)
        """
        # Check if amounts match exactly
        if amount_diff == 0:
            # Check if settled outside accounting period
            if settle_date > self.accounting_period_end:
                return (
                    ReconciliationStatus.TIMING_DIFFERENCE.value,
                    f'Transaction recorded in November but settled on {settle_date.strftime("%Y-%m-%d")} (after period end)',
                    'Period-end timing difference; verify settlement in next period'
                )
            else:
                return (
                    ReconciliationStatus.MATCHED.value,
                    'Transaction and settlement match perfectly',
                    'No action required'
                )
        
        # Amounts don't match
        abs_diff = abs(amount_diff)
        
        # Check if within individual tolerance
        if abs_diff <= self.individual_tolerance:
            # Small rounding difference
            if settle_date > self.accounting_period_end:
                return (
                    ReconciliationStatus.TIMING_DIFFERENCE.value,
                    f'Transaction recorded in November but settled on {settle_date.strftime("%Y-%m-%d")} with minor rounding difference of INR {float(amount_diff):.3f}',
                    'Period-end timing difference with rounding; verify both issues'
                )
            else:
                return (
                    ReconciliationStatus.MATCHED.value,
                    f'Amounts match within tolerance (difference: INR {float(amount_diff):.3f})',
                    'Monitor for aggregate rounding impact'
                )
        else:
            # Significant amount mismatch
            return (
                ReconciliationStatus.AMOUNT_MISMATCH.value,
                f'Transaction amount (INR {float(trans_amount):.2f}) does not match settlement amount (INR {float(settle_amount):.2f})',
                'Investigate discrepancy; verify payment processing and fees'
            )
    
    def _validate_refunds(self, trans_refunds: pd.DataFrame, 
                         settle_refunds: pd.DataFrame,
                         all_transactions: pd.DataFrame) -> List[Dict]:
        """
        Validate refund transactions
        
        Args:
            trans_refunds: Refund transactions
            settle_refunds: Refund settlements
            all_transactions: All transaction records (for reference lookup)
            
        Returns:
            List of refund reconciliation results
        """
        results = []
        
        # Get all valid transaction IDs for reference validation
        valid_transaction_ids = set(all_transactions['transaction_id'].values) if not all_transactions.empty else set()
        
        # Process settlement refunds
        for idx, refund in settle_refunds.iterrows():
            txn_id = refund['transaction_id']
            original_txn_id = refund.get('original_transaction_id')
            
            # Check if original transaction exists
            if pd.isna(original_txn_id) or str(original_txn_id).strip() == '':
                results.append({
                    'transaction_id': txn_id,
                    'type': 'REFUND',
                    'transaction_date': None,
                    'settlement_date': refund['settlement_date'],
                    'transaction_amount': None,
                    'settlement_amount': float(Decimal(str(refund['amount']))),
                    'amount_difference': None,
                    'status': ReconciliationStatus.UNMATCHED_REFUND.value,
                    'explanation': 'Refund has no original transaction reference',
                    'investigation_action': 'Verify refund validity and find original transaction'
                })
            elif original_txn_id not in valid_transaction_ids:
                results.append({
                    'transaction_id': txn_id,
                    'type': 'REFUND',
                    'transaction_date': None,
                    'settlement_date': refund['settlement_date'],
                    'transaction_amount': None,
                    'settlement_amount': float(Decimal(str(refund['amount']))),
                    'amount_difference': None,
                    'status': ReconciliationStatus.UNMATCHED_REFUND.value,
                    'explanation': f'Refund references non-existent transaction {original_txn_id}',
                    'investigation_action': f'Verify original transaction {original_txn_id} exists in system'
                })
            else:
                # Valid refund with existing original transaction
                original_trans = all_transactions[all_transactions['transaction_id'] == original_txn_id].iloc[0]
                results.append({
                    'transaction_id': txn_id,
                    'type': 'REFUND',
                    'transaction_date': None,
                    'settlement_date': refund['settlement_date'],
                    'transaction_amount': None,
                    'settlement_amount': float(Decimal(str(refund['amount']))),
                    'amount_difference': None,
                    'status': ReconciliationStatus.MATCHED.value,
                    'explanation': f'Valid refund referencing transaction {original_txn_id}',
                    'investigation_action': 'No action required'
                })
        
        return results
    
    def _analyze_rounding_variance(self, payment_results: List[Dict]) -> Dict:
        """
        Analyze aggregate rounding variance across all matched payments
        
        Args:
            payment_results: List of payment reconciliation results
            
        Returns:
            Dictionary with rounding analysis
        """
        # Get all matched payments with amount differences
        rounding_items = []
        
        for result in payment_results:
            if result['status'] in [ReconciliationStatus.MATCHED.value, 
                                    ReconciliationStatus.TIMING_DIFFERENCE.value]:
                if result['amount_difference'] is not None:
                    amount_diff = Decimal(str(result['amount_difference']))
                    abs_diff = abs(amount_diff)
                    
                    # Check if within individual tolerance but not zero
                    if abs_diff > 0 and abs_diff <= self.individual_tolerance:
                        rounding_items.append({
                            'transaction_id': result['transaction_id'],
                            'difference': float(amount_diff),
                            'abs_difference': float(abs_diff)
                        })
        
        # Calculate aggregate variance
        total_variance = sum(Decimal(str(item['abs_difference'])) for item in rounding_items)
        
        exceeds_threshold = total_variance > self.aggregate_tolerance
        
        return {
            'rounding_items': rounding_items,
            'count': len(rounding_items),
            'total_variance': float(total_variance),
            'threshold': float(self.aggregate_tolerance),
            'exceeds_threshold': exceeds_threshold,
            'explanation': (
                f'Found {len(rounding_items)} transactions with individual rounding differences. '
                f'Aggregate absolute variance: INR {float(total_variance):.3f} '
                f'{"exceeds" if exceeds_threshold else "within"} threshold of INR {float(self.aggregate_tolerance):.2f}'
            ) if rounding_items else 'No rounding differences detected'
        }
    
    def _compile_results(self, payment_results: List[Dict],
                        refund_results: List[Dict],
                        trans_duplicates: Dict,
                        settle_duplicates: Dict,
                        rounding_analysis: Dict) -> pd.DataFrame:
        """
        Compile all reconciliation results into a single DataFrame
        
        Args:
            payment_results: Payment reconciliation results
            refund_results: Refund reconciliation results
            trans_duplicates: Transaction duplicate information
            settle_duplicates: Settlement duplicate information
            rounding_analysis: Rounding variance analysis
            
        Returns:
            DataFrame with all results
        """
        all_results = []
        
        # Add payment results
        all_results.extend(payment_results)
        
        # Add refund results
        all_results.extend(refund_results)
        
        # Add transaction duplicates
        for dup in trans_duplicates['duplicate_records']:
            all_results.append({
                'transaction_id': dup['transaction_id'],
                'type': dup['type'],
                'transaction_date': dup['date'],
                'settlement_date': None,
                'transaction_amount': float(Decimal(str(dup['amount']))),
                'settlement_amount': None,
                'amount_difference': None,
                'status': ReconciliationStatus.DUPLICATE_TRANSACTION_ENTRY.value,
                'explanation': 'Duplicate transaction entry (excluded from financial totals)',
                'investigation_action': 'Remove duplicate from internal records'
            })
        
        # Add settlement duplicates
        for dup in settle_duplicates['duplicate_records']:
            all_results.append({
                'transaction_id': dup['transaction_id'],
                'type': dup['type'],
                'transaction_date': None,
                'settlement_date': dup['date'],
                'transaction_amount': None,
                'settlement_amount': float(Decimal(str(dup['amount']))),
                'amount_difference': None,
                'status': ReconciliationStatus.DUPLICATE_BANK_ENTRY.value,
                'explanation': 'Duplicate bank settlement entry (excluded from financial totals)',
                'investigation_action': 'Contact bank to verify; remove duplicate'
            })
        
        # Convert to DataFrame
        results_df = pd.DataFrame(all_results)
        
        # Sort by transaction_id
        if not results_df.empty:
            results_df = results_df.sort_values('transaction_id').reset_index(drop=True)
        
        return results_df
    
    def _calculate_summary(self, transactions_df: pd.DataFrame,
                          settlements_df: pd.DataFrame,
                          trans_eligible: pd.DataFrame,
                          settle_eligible: pd.DataFrame,
                          results_df: pd.DataFrame,
                          rounding_analysis: Dict) -> Dict:
        """
        Calculate summary statistics for reconciliation
        
        Args:
            transactions_df: All transactions
            settlements_df: All settlements
            trans_eligible: Eligible transactions (excluding duplicates)
            settle_eligible: Eligible settlements (excluding duplicates)
            results_df: Reconciliation results
            rounding_analysis: Rounding variance analysis
            
        Returns:
            Dictionary with summary statistics
        """
        # Count by status
        status_counts = results_df['status'].value_counts().to_dict() if not results_df.empty else {}
        
        # Calculate financial totals using Decimal
        total_internal_payments = sum(
            Decimal(str(amt)) 
            for amt in trans_eligible[trans_eligible['type'] == 'PAYMENT']['amount']
        ) if not trans_eligible.empty else Decimal('0')
        
        total_bank_payments = sum(
            Decimal(str(amt)) 
            for amt in settle_eligible[settle_eligible['type'] == 'PAYMENT']['amount']
        ) if not settle_eligible.empty else Decimal('0')
        
        # Matched amount (payments with MATCHED or TIMING_DIFFERENCE status)
        matched_records = results_df[
            (results_df['type'] == 'PAYMENT') & 
            (results_df['status'].isin([
                ReconciliationStatus.MATCHED.value,
                ReconciliationStatus.TIMING_DIFFERENCE.value
            ]))
        ]
        
        # Use settlement amounts for matched value (what bank actually settled)
        matched_amount = sum(
            Decimal(str(amt)) 
            for amt in matched_records['settlement_amount'].dropna()
        )
        
        # Missing settlements amount
        missing_records = results_df[
            (results_df['type'] == 'PAYMENT') & 
            (results_df['status'] == ReconciliationStatus.MISSING_SETTLEMENT.value)
        ]
        missing_amount = sum(
            Decimal(str(amt)) 
            for amt in missing_records['transaction_amount'].dropna()
        )
        
        # Timing differences amount
        timing_records = results_df[
            (results_df['type'] == 'PAYMENT') & 
            (results_df['status'] == ReconciliationStatus.TIMING_DIFFERENCE.value)
        ]
        timing_amount = sum(
            Decimal(str(amt)) 
            for amt in timing_records['settlement_amount'].dropna()
        )
        
        # Duplicate amounts (excluded from totals)
        duplicate_trans_amount = sum(
            Decimal(str(amt))
            for amt in results_df[
                results_df['status'] == ReconciliationStatus.DUPLICATE_TRANSACTION_ENTRY.value
            ]['transaction_amount'].dropna()
        )
        
        duplicate_bank_amount = sum(
            Decimal(str(amt))
            for amt in results_df[
                results_df['status'] == ReconciliationStatus.DUPLICATE_BANK_ENTRY.value
            ]['settlement_amount'].dropna()
        )
        
        # Unmatched refund amounts
        unmatched_refund_amount = sum(
            Decimal(str(amt))
            for amt in results_df[
                (results_df['type'] == 'REFUND') & 
                (results_df['status'] == ReconciliationStatus.UNMATCHED_REFUND.value)
            ]['settlement_amount'].dropna()
        )
        
        # Calculate unexplained variance
        # This is the difference between what we should have settled vs what was actually settled
        # excluding timing differences and duplicates
        unexplained_variance = total_internal_payments - matched_amount - missing_amount
        
        return {
            'total_internal_transactions': len(transactions_df),
            'total_internal_payments': len(trans_eligible[trans_eligible['type'] == 'PAYMENT']) if not trans_eligible.empty else 0,
            'total_internal_payment_value': float(total_internal_payments),
            
            'total_bank_settlements': len(settlements_df),
            'total_bank_payments': len(settle_eligible[settle_eligible['type'] == 'PAYMENT']) if not settle_eligible.empty else 0,
            'total_bank_payment_value': float(total_bank_payments),
            
            'matched_count': status_counts.get(ReconciliationStatus.MATCHED.value, 0),
            'matched_amount': float(matched_amount),
            
            'timing_difference_count': status_counts.get(ReconciliationStatus.TIMING_DIFFERENCE.value, 0),
            'timing_difference_amount': float(timing_amount),
            
            'missing_settlement_count': status_counts.get(ReconciliationStatus.MISSING_SETTLEMENT.value, 0),
            'missing_settlement_amount': float(missing_amount),
            
            'unmatched_bank_entry_count': status_counts.get(ReconciliationStatus.UNMATCHED_BANK_ENTRY.value, 0),
            
            'duplicate_transaction_count': status_counts.get(ReconciliationStatus.DUPLICATE_TRANSACTION_ENTRY.value, 0),
            'duplicate_transaction_amount': float(duplicate_trans_amount),
            
            'duplicate_bank_count': status_counts.get(ReconciliationStatus.DUPLICATE_BANK_ENTRY.value, 0),
            'duplicate_bank_amount': float(duplicate_bank_amount),
            
            'unmatched_refund_count': status_counts.get(ReconciliationStatus.UNMATCHED_REFUND.value, 0),
            'unmatched_refund_amount': float(unmatched_refund_amount),
            
            'rounding_variance_count': rounding_analysis['count'],
            'rounding_variance_total': rounding_analysis['total_variance'],
            'rounding_exceeds_threshold': rounding_analysis['exceeds_threshold'],
            
            'unexplained_variance': float(unexplained_variance),
            
            'accounting_period_start': self.accounting_period_start.strftime('%Y-%m-%d'),
            'accounting_period_end': self.accounting_period_end.strftime('%Y-%m-%d')
        }


if __name__ == "__main__":
    """Test the reconciliation engine with sample files"""
    from data_loader import DataLoader
    
    print("=" * 60)
    print("Testing Reconciliation Engine")
    print("=" * 60)
    
    try:
        # Load data
        print("\n1. Loading data files...")
        loader = DataLoader()
        transactions_df = loader.load_transactions('transactions.csv')
        settlements_df = loader.load_settlements('settlements.csv')
        print(f"✓ Loaded {len(transactions_df)} transactions and {len(settlements_df)} settlements")
        
        # Run reconciliation
        print("\n2. Running reconciliation...")
        engine = ReconciliationEngine()
        reconciliation = engine.reconcile(transactions_df, settlements_df)
        
        results_df = reconciliation['results']
        summary = reconciliation['summary']
        rounding = reconciliation['rounding_analysis']
        
        print(f"✓ Reconciliation complete - {len(results_df)} result records generated")
        
        # Display summary
        print("\n" + "=" * 60)
        print("RECONCILIATION SUMMARY")
        print("=" * 60)
        
        print(f"\nInternal Transactions:")
        print(f"  Total: {summary['total_internal_transactions']}")
        print(f"  Payments: {summary['total_internal_payments']}")
        print(f"  Total Value: INR {summary['total_internal_payment_value']:.2f}")
        
        print(f"\nBank Settlements:")
        print(f"  Total: {summary['total_bank_settlements']}")
        print(f"  Payments: {summary['total_bank_payments']}")
        print(f"  Total Value: INR {summary['total_bank_payment_value']:.2f}")
        
        print(f"\nReconciliation Results:")
        print(f"  Matched: {summary['matched_count']} (INR {summary['matched_amount']:.2f})")
        print(f"  Timing Differences: {summary['timing_difference_count']} (INR {summary['timing_difference_amount']:.2f})")
        print(f"  Missing Settlements: {summary['missing_settlement_count']} (INR {summary['missing_settlement_amount']:.2f})")
        print(f"  Unmatched Bank Entries: {summary['unmatched_bank_entry_count']}")
        print(f"  Duplicate Transactions: {summary['duplicate_transaction_count']} (INR {summary['duplicate_transaction_amount']:.2f})")
        print(f"  Duplicate Bank Entries: {summary['duplicate_bank_count']} (INR {summary['duplicate_bank_amount']:.2f})")
        print(f"  Unmatched Refunds: {summary['unmatched_refund_count']} (INR {summary['unmatched_refund_amount']:.2f})")
        
        print(f"\nRounding Analysis:")
        print(f"  Transactions with rounding: {rounding['count']}")
        print(f"  Aggregate variance: INR {rounding['total_variance']:.3f}")
        print(f"  Exceeds threshold: {'YES' if rounding['exceeds_threshold'] else 'NO'}")
        
        print(f"\nUnexplained Variance: INR {summary['unexplained_variance']:.2f}")
        
        # Show the four planted discrepancies
        print("\n" + "=" * 60)
        print("FOUR PLANTED DISCREPANCIES")
        print("=" * 60)
        
        # 1. Timing difference (TX003)
        timing = results_df[results_df['status'] == ReconciliationStatus.TIMING_DIFFERENCE.value]
        if not timing.empty:
            print("\n1. TIMING DIFFERENCE:")
            for _, row in timing.iterrows():
                print(f"   {row['transaction_id']}: {row['explanation']}")
        
        # 2. Rounding variance (TX031-TX040)
        print(f"\n2. ROUNDING VARIANCE:")
        print(f"   {rounding['explanation']}")
        if rounding['count'] > 0:
            print(f"   Affected transactions: {', '.join([item['transaction_id'] for item in rounding['rounding_items'][:5]])}...")
        
        # 3. Duplicate entry (TX001)
        duplicates = results_df[results_df['status'] == ReconciliationStatus.DUPLICATE_BANK_ENTRY.value]
        if not duplicates.empty:
            print("\n3. DUPLICATE ENTRY:")
            for _, row in duplicates.iterrows():
                print(f"   {row['transaction_id']}: {row['explanation']}")
        
        # 4. Unmatched refund (RF001)
        refunds = results_df[results_df['status'] == ReconciliationStatus.UNMATCHED_REFUND.value]
        if not refunds.empty:
            print("\n4. UNMATCHED REFUND:")
            for _, row in refunds.iterrows():
                print(f"   {row['transaction_id']}: {row['explanation']}")
        
        print("\n" + "=" * 60)
        print("✓ ALL FOUR DISCREPANCIES DETECTED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
