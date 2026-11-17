"""
Integration Test - Complete Workflow Verification
Tests the entire application flow from data loading to report generation
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader, ValidationError
from reconciliation import ReconciliationEngine, ReconciliationStatus
from report_generator import ReportGenerator
import pandas as pd
from decimal import Decimal


def test_complete_workflow():
    """Test the complete reconciliation workflow"""
    print("=" * 80)
    print("INTEGRATION TEST: COMPLETE WORKFLOW")
    print("=" * 80)
    
    # Step 1: Load Data
    print("\n[STEP 1] Loading Data Files...")
    print("-" * 80)
    
    loader = DataLoader()
    transactions_df = loader.load_transactions('transactions.csv')
    settlements_df = loader.load_settlements('settlements.csv')
    
    print(f"✓ Transactions loaded: {len(transactions_df)} records")
    print(f"✓ Settlements loaded: {len(settlements_df)} records")
    
    # Verify data structure
    assert 'transaction_id' in transactions_df.columns
    assert 'amount' in transactions_df.columns
    assert 'transaction_date' in transactions_df.columns
    assert 'type' in transactions_df.columns
    print("✓ Data structure validated")
    
    # Step 2: Run Reconciliation
    print("\n[STEP 2] Running Reconciliation Engine...")
    print("-" * 80)
    
    engine = ReconciliationEngine()
    reconciliation_result = engine.reconcile(transactions_df, settlements_df)
    
    results_df = reconciliation_result['results']
    summary = reconciliation_result['summary']
    rounding = reconciliation_result['rounding_analysis']
    
    print(f"✓ Reconciliation complete: {len(results_df)} result records")
    print(f"✓ Matched transactions: {summary['matched_count']}")
    print(f"✓ Timing differences: {summary['timing_difference_count']}")
    print(f"✓ Exceptions found: {len(results_df[results_df['status'] != 'MATCHED'])}")
    
    # Step 3: Verify Four Planted Discrepancies
    print("\n[STEP 3] Verifying Four Planted Discrepancies...")
    print("-" * 80)
    
    # Discrepancy 1: TX003 timing difference
    tx003 = results_df[results_df['transaction_id'] == 'TX003']
    assert len(tx003) == 1, "TX003 not found"
    assert tx003.iloc[0]['status'] == ReconciliationStatus.TIMING_DIFFERENCE.value
    print("✓ 1. TX003 timing difference detected")
    
    # Discrepancy 2: Rounding variance
    assert rounding['count'] == 10, f"Expected 10 rounding items, got {rounding['count']}"
    assert abs(rounding['total_variance'] - 0.050) < 0.001
    assert rounding['exceeds_threshold'] == True
    print(f"✓ 2. Aggregate rounding variance detected (₹{rounding['total_variance']:.3f})")
    
    # Discrepancy 3: TX001 duplicate
    tx001_dup = results_df[
        (results_df['transaction_id'] == 'TX001') & 
        (results_df['status'] == ReconciliationStatus.DUPLICATE_BANK_ENTRY.value)
    ]
    assert len(tx001_dup) == 1, "TX001 duplicate not found"
    print("✓ 3. TX001 duplicate bank entry detected")
    
    # Discrepancy 4: RF001 unmatched refund
    rf001 = results_df[results_df['transaction_id'] == 'RF001']
    assert len(rf001) == 1, "RF001 not found"
    assert rf001.iloc[0]['status'] == ReconciliationStatus.UNMATCHED_REFUND.value
    assert 'TX999' in rf001.iloc[0]['explanation']
    print("✓ 4. RF001 unmatched refund detected")
    
    # Step 4: Verify Financial Calculations
    print("\n[STEP 4] Verifying Financial Calculations...")
    print("-" * 80)
    
    # Verify totals
    expected_internal_total = Decimal('7255.05')
    actual_internal_total = Decimal(str(summary['total_internal_payment_value']))
    assert abs(actual_internal_total - expected_internal_total) < Decimal('0.01')
    print(f"✓ Internal payment total: ₹{summary['total_internal_payment_value']:.2f}")
    
    # Verify duplicate exclusion
    assert summary['duplicate_bank_count'] == 1
    assert summary['duplicate_bank_amount'] == 107.00
    print(f"✓ Duplicate excluded from totals: ₹{summary['duplicate_bank_amount']:.2f}")
    
    # Verify matched amount
    print(f"✓ Matched amount: ₹{summary['matched_amount']:.2f}")
    
    # Verify unexplained variance is minimal
    assert abs(summary['unexplained_variance']) < 1.0
    print(f"✓ Unexplained variance: ₹{abs(summary['unexplained_variance']):.3f}")
    
    # Step 5: Generate Reports
    print("\n[STEP 5] Generating Reports...")
    print("-" * 80)
    
    generator = ReportGenerator()
    
    # Generate full reconciliation report
    full_report = generator.generate_full_reconciliation_csv(results_df, summary)
    assert len(full_report) > 1000, "Full report seems too short"
    assert 'TX003' in full_report
    print(f"✓ Full reconciliation report: {len(full_report)} characters")
    
    # Generate exceptions report
    exceptions_report = generator.generate_exceptions_csv(results_df, summary)
    assert 'TX003' in exceptions_report
    assert 'RF001' in exceptions_report
    print(f"✓ Exceptions report: {len(exceptions_report)} characters")
    
    # Generate summary report
    summary_report = generator.generate_summary_report(summary, rounding)
    assert 'PAYFLOW RECON' in summary_report
    assert 'RECONCILIATION SUMMARY' in summary_report
    print(f"✓ Summary report: {len(summary_report)} characters")
    
    # Step 6: Verify Data Integrity
    print("\n[STEP 6] Verifying Data Integrity...")
    print("-" * 80)
    
    # Check original data files weren't modified
    original_transactions = pd.read_csv('transactions.csv')
    original_settlements = pd.read_csv('settlements.csv')
    
    assert len(original_transactions) == 40, "Original transactions file modified!"
    assert len(original_settlements) == 42, "Original settlements file modified!"
    print("✓ Original CSV files remain unchanged")
    
    # Verify no data loss
    assert len(results_df) == len(transactions_df) + 1 + 1, \
        f"Expected {len(transactions_df) + 2} results (transactions + duplicate + refund)"
    print("✓ No data loss during reconciliation")
    
    # Verify all transaction IDs are accounted for
    trans_ids = set(transactions_df['transaction_id'])
    result_trans_ids = set(results_df[results_df['transaction_date'].notna()]['transaction_id'])
    missing_ids = trans_ids - result_trans_ids
    assert len(missing_ids) == 0, f"Missing transaction IDs: {missing_ids}"
    print("✓ All transaction IDs accounted for")
    
    # Step 7: Test Error Handling
    print("\n[STEP 7] Testing Error Handling...")
    print("-" * 80)
    
    # Test with invalid file
    try:
        loader.load_transactions('nonexistent.csv')
        assert False, "Should have raised error for missing file"
    except ValidationError:
        print("✓ Missing file error handled correctly")
    
    # Test with empty DataFrame
    empty_df = pd.DataFrame()
    result = engine.reconcile(transactions_df, empty_df)
    assert result['summary']['total_bank_settlements'] == 0
    print("✓ Empty settlement file handled correctly")
    
    # Test with empty transactions
    result = engine.reconcile(empty_df, settlements_df)
    assert result['summary']['total_internal_transactions'] == 0
    print("✓ Empty transaction file handled correctly")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST RESULTS")
    print("=" * 80)
    print("\n✓ ALL INTEGRATION TESTS PASSED!")
    print("\nVerified:")
    print("  • Data loading and validation")
    print("  • Reconciliation engine accuracy")
    print("  • Four planted discrepancies detected")
    print("  • Financial calculations correct")
    print("  • Report generation functional")
    print("  • Data integrity maintained")
    print("  • Error handling robust")
    print("\n" + "=" * 80)


def test_app_imports():
    """Test that all app modules can be imported without errors"""
    print("\n" + "=" * 80)
    print("TESTING MODULE IMPORTS")
    print("=" * 80)
    
    print("\nTesting imports...")
    
    import data_loader
    print("✓ data_loader imported")
    
    import reconciliation
    print("✓ reconciliation imported")
    
    import report_generator
    print("✓ report_generator imported")
    
    import app
    print("✓ app (Streamlit dashboard) imported")
    
    print("\n✓ All modules import successfully")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PAYFLOW RECON - INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Test imports
    if not test_app_imports():
        print("\n✗ Integration test failed - imports broken")
        sys.exit(1)
    
    # Test complete workflow
    if not test_complete_workflow():
        print("\n✗ Integration test failed - workflow broken")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✓ ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)
    print("\nThe PayFlow Recon application is ready for deployment.")
    print("")
    
    sys.exit(0)
