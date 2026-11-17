"""
Comprehensive Test Suite for Reconciliation Engine
Tests all 12 required test cases
"""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime
import tempfile
import os

# Import modules to test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import DataLoader
from reconciliation import ReconciliationEngine, ReconciliationStatus


class TestReconciliation:
    """Test suite for reconciliation engine"""
    
    @pytest.fixture
    def engine(self):
        """Create reconciliation engine instance"""
        return ReconciliationEngine()
    
    @pytest.fixture
    def loader(self):
        """Create data loader instance"""
        return DataLoader()
    
    def test_tc01_correctly_matched_payment(self, engine):
        """
        TC01: Correctly matched payment
        Expected: MATCHED status
        """
        # Create test data
        transactions = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 100.00,
            'transaction_date': pd.to_datetime('2026-11-01'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 100.00,
            'settlement_date': pd.to_datetime('2026-11-02'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify
        tx001 = results_df[results_df['transaction_id'] == 'TX001'].iloc[0]
        assert tx001['status'] == ReconciliationStatus.MATCHED.value
        assert tx001['transaction_amount'] == 100.00
        assert tx001['settlement_amount'] == 100.00
        assert tx001['amount_difference'] == 0.0
        
        print("✓ TC01 PASSED: Correctly matched payment")
    
    def test_tc02_timing_difference(self, engine):
        """
        TC02: November transaction settled in December
        Expected: TIMING_DIFFERENCE status
        """
        transactions = pd.DataFrame([{
            'transaction_id': 'TX003',
            'amount': 121.00,
            'transaction_date': pd.to_datetime('2026-11-04'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame([{
            'transaction_id': 'TX003',
            'amount': 121.00,
            'settlement_date': pd.to_datetime('2026-12-01'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify
        tx003 = results_df[results_df['transaction_id'] == 'TX003'].iloc[0]
        assert tx003['status'] == ReconciliationStatus.TIMING_DIFFERENCE.value
        assert 'December' in tx003['explanation'] or '2026-12-01' in tx003['explanation']
        
        print("✓ TC02 PASSED: Timing difference detected")
    
    def test_tc03_duplicate_bank_settlement(self, engine):
        """
        TC03: Duplicate bank settlement
        Expected: DUPLICATE_BANK_ENTRY status
        """
        transactions = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 107.00,
            'transaction_date': pd.to_datetime('2026-11-02'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 107.00,
                'settlement_date': pd.to_datetime('2026-11-03'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'TX001',
                'amount': 107.00,
                'settlement_date': pd.to_datetime('2026-11-03'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            }
        ])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        summary = result['summary']
        
        # Verify duplicate is detected
        duplicates = results_df[results_df['status'] == ReconciliationStatus.DUPLICATE_BANK_ENTRY.value]
        assert len(duplicates) == 1
        assert duplicates.iloc[0]['transaction_id'] == 'TX001'
        
        # Verify duplicate is excluded from totals
        assert summary['duplicate_bank_count'] == 1
        assert summary['duplicate_bank_amount'] == 107.00
        
        print("✓ TC03 PASSED: Duplicate bank settlement detected")
    
    def test_tc04_unmatched_refund(self, engine):
        """
        TC04: Refund referencing nonexistent TX999
        Expected: UNMATCHED_REFUND status
        """
        transactions = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 100.00,
            'transaction_date': pd.to_datetime('2026-11-01'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'settlement_date': pd.to_datetime('2026-11-02'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'RF001',
                'amount': -200.00,
                'settlement_date': pd.to_datetime('2026-11-15'),
                'type': 'REFUND',
                'original_transaction_id': 'TX999'
            }
        ])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify
        rf001 = results_df[results_df['transaction_id'] == 'RF001'].iloc[0]
        assert rf001['status'] == ReconciliationStatus.UNMATCHED_REFUND.value
        assert 'TX999' in rf001['explanation']
        
        print("✓ TC04 PASSED: Unmatched refund detected")
    
    def test_tc05_aggregate_rounding_variance(self, engine):
        """
        TC05: Ten transactions with INR 0.005 individual differences
        Expected: Aggregate difference INR 0.05, exceeds threshold
        """
        # Create 10 transactions with 100.005
        transactions_data = []
        settlements_data = []
        
        for i in range(1, 11):
            tx_id = f'TX{i:03d}'
            transactions_data.append({
                'transaction_id': tx_id,
                'amount': 100.005,
                'transaction_date': pd.to_datetime('2026-11-10'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            })
            settlements_data.append({
                'transaction_id': tx_id,
                'amount': 100.000,
                'settlement_date': pd.to_datetime('2026-11-11'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            })
        
        transactions = pd.DataFrame(transactions_data)
        settlements = pd.DataFrame(settlements_data)
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        rounding = result['rounding_analysis']
        
        # Verify
        assert rounding['count'] == 10
        assert abs(rounding['total_variance'] - 0.050) < 0.001
        assert rounding['exceeds_threshold'] == True
        
        print(f"✓ TC05 PASSED: Aggregate rounding variance = INR {rounding['total_variance']:.3f}")
    
    def test_tc06_missing_settlement(self, engine):
        """
        TC06: Payment missing from bank file
        Expected: MISSING_SETTLEMENT status
        """
        transactions = pd.DataFrame([{
            'transaction_id': 'TX999',
            'amount': 150.00,
            'transaction_date': pd.to_datetime('2026-11-15'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame()  # Empty settlements
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify
        tx999 = results_df[results_df['transaction_id'] == 'TX999'].iloc[0]
        assert tx999['status'] == ReconciliationStatus.MISSING_SETTLEMENT.value
        assert pd.isna(tx999['settlement_amount'])
        
        print("✓ TC06 PASSED: Missing settlement detected")
    
    def test_tc07_unmatched_bank_payment(self, engine):
        """
        TC07: Bank payment absent from internal records
        Expected: UNMATCHED_BANK_ENTRY status
        """
        transactions = pd.DataFrame()  # Empty transactions
        
        settlements = pd.DataFrame([{
            'transaction_id': 'TX888',
            'amount': 250.00,
            'settlement_date': pd.to_datetime('2026-11-20'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify
        tx888 = results_df[results_df['transaction_id'] == 'TX888'].iloc[0]
        assert tx888['status'] == ReconciliationStatus.UNMATCHED_BANK_ENTRY.value
        assert pd.isna(tx888['transaction_amount'])
        
        print("✓ TC07 PASSED: Unmatched bank entry detected")
    
    def test_tc08_invalid_date(self, loader):
        """
        TC08: Invalid date
        Expected: Validation error
        """
        # Create temp file with invalid date
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("transaction_id,amount,transaction_date,type,original_transaction_id\n")
            f.write("TX001,100.00,invalid-date,PAYMENT,\n")
            temp_file = f.name
        
        try:
            # Should raise ValidationError
            with pytest.raises(Exception) as exc_info:
                loader.load_transactions(temp_file)
            
            assert 'invalid' in str(exc_info.value).lower() or 'date' in str(exc_info.value).lower()
            print("✓ TC08 PASSED: Invalid date rejected")
        finally:
            os.unlink(temp_file)
    
    def test_tc09_missing_column(self, loader):
        """
        TC09: Missing required CSV column
        Expected: Clear validation error
        """
        # Create temp file with missing 'type' column
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("transaction_id,amount,transaction_date,original_transaction_id\n")
            f.write("TX001,100.00,2026-11-01,\n")
            temp_file = f.name
        
        try:
            # Should raise ValidationError
            with pytest.raises(Exception) as exc_info:
                loader.load_transactions(temp_file)
            
            error_msg = str(exc_info.value).lower()
            assert 'missing' in error_msg or 'column' in error_msg
            assert 'type' in error_msg
            print("✓ TC09 PASSED: Missing column detected")
        finally:
            os.unlink(temp_file)
    
    def test_tc10_completely_matching_datasets(self, engine):
        """
        TC10: Completely matching datasets
        Expected: Zero unexplained discrepancy
        """
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'transaction_date': pd.to_datetime('2026-11-01'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'TX002',
                'amount': 200.00,
                'transaction_date': pd.to_datetime('2026-11-02'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'settlement_date': pd.to_datetime('2026-11-02'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'TX002',
                'amount': 200.00,
                'settlement_date': pd.to_datetime('2026-11-03'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            }
        ])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        summary = result['summary']
        
        # Verify all matched
        assert summary['matched_count'] == 2
        assert summary['missing_settlement_count'] == 0
        assert summary['unmatched_bank_entry_count'] == 0
        assert abs(summary['unexplained_variance']) < 0.01
        
        print("✓ TC10 PASSED: Perfect match with zero variance")
    
    def test_tc11_duplicate_internal_transaction(self, engine):
        """
        TC11: Duplicate internal transaction
        Expected: DUPLICATE_TRANSACTION_ENTRY status
        """
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'transaction_date': pd.to_datetime('2026-11-01'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'transaction_date': pd.to_datetime('2026-11-01'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            }
        ])
        
        settlements = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 100.00,
            'settlement_date': pd.to_datetime('2026-11-02'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        summary = result['summary']
        
        # Verify duplicate is detected
        duplicates = results_df[results_df['status'] == ReconciliationStatus.DUPLICATE_TRANSACTION_ENTRY.value]
        assert len(duplicates) == 1
        assert summary['duplicate_transaction_count'] == 1
        
        print("✓ TC11 PASSED: Duplicate transaction detected")
    
    def test_tc12_valid_refund_reference(self, engine):
        """
        TC12: Valid refund reference
        Expected: Correct refund association with MATCHED status
        """
        transactions = pd.DataFrame([{
            'transaction_id': 'TX001',
            'amount': 100.00,
            'transaction_date': pd.to_datetime('2026-11-01'),
            'type': 'PAYMENT',
            'original_transaction_id': None
        }])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TX001',
                'amount': 100.00,
                'settlement_date': pd.to_datetime('2026-11-02'),
                'type': 'PAYMENT',
                'original_transaction_id': None
            },
            {
                'transaction_id': 'RF001',
                'amount': -50.00,
                'settlement_date': pd.to_datetime('2026-11-15'),
                'type': 'REFUND',
                'original_transaction_id': 'TX001'
            }
        ])
        
        # Run reconciliation
        result = engine.reconcile(transactions, settlements)
        results_df = result['results']
        
        # Verify refund is matched correctly
        rf001 = results_df[results_df['transaction_id'] == 'RF001'].iloc[0]
        assert rf001['status'] == ReconciliationStatus.MATCHED.value
        assert 'TX001' in rf001['explanation']
        
        print("✓ TC12 PASSED: Valid refund reference processed")


def test_with_actual_sample_data():
    """
    Test with actual provided sample data
    Verifies all 4 planted discrepancies are detected
    """
    print("\n" + "=" * 60)
    print("TESTING WITH ACTUAL SAMPLE DATA")
    print("=" * 60)
    
    # Change to project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    loader = DataLoader()
    engine = ReconciliationEngine()
    
    # Load actual data
    transactions_df = loader.load_transactions('transactions.csv')
    settlements_df = loader.load_settlements('settlements.csv')
    
    print(f"\n✓ Loaded {len(transactions_df)} transactions")
    print(f"✓ Loaded {len(settlements_df)} settlements")
    
    # Run reconciliation
    result = engine.reconcile(transactions_df, settlements_df)
    results_df = result['results']
    summary = result['summary']
    rounding = result['rounding_analysis']
    
    print(f"\n✓ Reconciliation complete - {len(results_df)} results")
    
    # Verify the 4 planted discrepancies
    print("\nVerifying 4 Planted Discrepancies:")
    
    # 1. Timing difference (TX003)
    timing = results_df[results_df['status'] == ReconciliationStatus.TIMING_DIFFERENCE.value]
    assert len(timing) == 1
    assert timing.iloc[0]['transaction_id'] == 'TX003'
    print("  ✓ 1. Timing difference (TX003) - DETECTED")
    
    # 2. Rounding variance (TX031-TX040)
    assert rounding['count'] == 10
    assert abs(rounding['total_variance'] - 0.050) < 0.001
    assert rounding['exceeds_threshold'] == True
    print(f"  ✓ 2. Rounding variance (10 txns, ₹{rounding['total_variance']:.3f}) - DETECTED")
    
    # 3. Duplicate entry (TX001)
    duplicates = results_df[results_df['status'] == ReconciliationStatus.DUPLICATE_BANK_ENTRY.value]
    assert len(duplicates) == 1
    assert duplicates.iloc[0]['transaction_id'] == 'TX001'
    print("  ✓ 3. Duplicate bank entry (TX001) - DETECTED")
    
    # 4. Unmatched refund (RF001)
    refunds = results_df[results_df['status'] == ReconciliationStatus.UNMATCHED_REFUND.value]
    assert len(refunds) == 1
    assert refunds.iloc[0]['transaction_id'] == 'RF001'
    assert 'TX999' in refunds.iloc[0]['explanation']
    print("  ✓ 4. Unmatched refund (RF001 → TX999) - DETECTED")
    
    print("\n" + "=" * 60)
    print("✓ ALL 4 PLANTED DISCREPANCIES VERIFIED!")
    print("=" * 60)


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
