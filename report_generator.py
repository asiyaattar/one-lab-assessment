"""
Report Generator for PayFlow Recon
Generates downloadable CSV and text reports for reconciliation results
"""

import pandas as pd
from datetime import datetime
from typing import Dict
import io


class ReportGenerator:
    """
    Generates various types of reports from reconciliation results
    """
    
    def __init__(self):
        """Initialize report generator"""
        self.generation_timestamp = datetime.now()
    
    def generate_full_reconciliation_csv(self, results_df: pd.DataFrame, 
                                        summary: Dict) -> str:
        """
        Generate complete reconciliation report as CSV string
        
        Args:
            results_df: DataFrame with reconciliation results
            summary: Summary statistics dictionary
            
        Returns:
            CSV string ready for download
        """
        # Create a copy to avoid modifying original
        report_df = results_df.copy()
        
        # Format dates
        if 'transaction_date' in report_df.columns:
            report_df['transaction_date'] = pd.to_datetime(report_df['transaction_date']).dt.strftime('%Y-%m-%d')
        if 'settlement_date' in report_df.columns:
            report_df['settlement_date'] = pd.to_datetime(report_df['settlement_date']).dt.strftime('%Y-%m-%d')
        
        # Reorder columns for better readability
        column_order = [
            'transaction_id',
            'type',
            'status',
            'transaction_date',
            'settlement_date',
            'transaction_amount',
            'settlement_amount',
            'amount_difference',
            'explanation',
            'investigation_action'
        ]
        
        # Only include columns that exist
        columns = [col for col in column_order if col in report_df.columns]
        report_df = report_df[columns]
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        
        # Write header with metadata
        csv_buffer.write(f"# PayFlow Recon - Reconciliation Report\n")
        csv_buffer.write(f"# Generated: {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        csv_buffer.write(f"# Accounting Period: {summary['accounting_period_start']} to {summary['accounting_period_end']}\n")
        csv_buffer.write(f"# Total Records: {len(report_df)}\n")
        csv_buffer.write(f"#\n")
        
        # Write the data
        report_df.to_csv(csv_buffer, index=False)
        
        return csv_buffer.getvalue()
    
    def generate_exceptions_csv(self, results_df: pd.DataFrame, 
                                summary: Dict) -> str:
        """
        Generate exceptions-only report as CSV string
        
        Args:
            results_df: DataFrame with reconciliation results
            summary: Summary statistics dictionary
            
        Returns:
            CSV string with only exception records
        """
        # Filter for exceptions only (exclude MATCHED status)
        exceptions_df = results_df[results_df['status'] != 'MATCHED'].copy()
        
        # Format dates
        if 'transaction_date' in exceptions_df.columns:
            exceptions_df['transaction_date'] = pd.to_datetime(
                exceptions_df['transaction_date']
            ).dt.strftime('%Y-%m-%d')
        if 'settlement_date' in exceptions_df.columns:
            exceptions_df['settlement_date'] = pd.to_datetime(
                exceptions_df['settlement_date']
            ).dt.strftime('%Y-%m-%d')
        
        # Reorder columns
        column_order = [
            'status',
            'transaction_id',
            'type',
            'transaction_date',
            'settlement_date',
            'transaction_amount',
            'settlement_amount',
            'amount_difference',
            'explanation',
            'investigation_action'
        ]
        
        columns = [col for col in column_order if col in exceptions_df.columns]
        exceptions_df = exceptions_df[columns]
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        
        # Write header with metadata
        csv_buffer.write(f"# PayFlow Recon - Exceptions Report\n")
        csv_buffer.write(f"# Generated: {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        csv_buffer.write(f"# Accounting Period: {summary['accounting_period_start']} to {summary['accounting_period_end']}\n")
        csv_buffer.write(f"# Total Exceptions: {len(exceptions_df)}\n")
        csv_buffer.write(f"#\n")
        
        # Write the data
        exceptions_df.to_csv(csv_buffer, index=False)
        
        return csv_buffer.getvalue()
    
    def generate_summary_report(self, summary: Dict, 
                               rounding_analysis: Dict) -> str:
        """
        Generate executive summary report as formatted text
        
        Args:
            summary: Summary statistics dictionary
            rounding_analysis: Rounding variance analysis
            
        Returns:
            Formatted text report
        """
        report = []
        
        report.append("=" * 80)
        report.append("PAYFLOW RECON - RECONCILIATION SUMMARY REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Report Generated: {self.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Accounting Period: {summary['accounting_period_start']} to {summary['accounting_period_end']}")
        report.append("")
        
        report.append("-" * 80)
        report.append("TRANSACTION OVERVIEW")
        report.append("-" * 80)
        report.append("")
        report.append("Internal Transactions:")
        report.append(f"  Total Records:        {summary['total_internal_transactions']:,}")
        report.append(f"  Payment Count:        {summary['total_internal_payments']:,}")
        report.append(f"  Total Payment Value:  INR {summary['total_internal_payment_value']:,.2f}")
        report.append("")
        report.append("Bank Settlements:")
        report.append(f"  Total Records:        {summary['total_bank_settlements']:,}")
        report.append(f"  Payment Count:        {summary['total_bank_payments']:,}")
        report.append(f"  Total Payment Value:  INR {summary['total_bank_payment_value']:,.2f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("RECONCILIATION RESULTS")
        report.append("-" * 80)
        report.append("")
        report.append(f"✓ Matched Transactions:        {summary['matched_count']:3,} "
                     f"(INR {summary['matched_amount']:,.2f})")
        report.append("")
        
        if summary['timing_difference_count'] > 0:
            report.append(f"⚠ Timing Differences:          {summary['timing_difference_count']:3,} "
                         f"(INR {summary['timing_difference_amount']:,.2f})")
            report.append(f"  These transactions were recorded in the accounting period but settled later.")
        
        if summary['missing_settlement_count'] > 0:
            report.append(f"✗ Missing Settlements:         {summary['missing_settlement_count']:3,} "
                         f"(INR {summary['missing_settlement_amount']:,.2f})")
            report.append(f"  Internal transactions with no corresponding bank settlement.")
        
        if summary['unmatched_bank_entry_count'] > 0:
            report.append(f"✗ Unmatched Bank Entries:      {summary['unmatched_bank_entry_count']:3,}")
            report.append(f"  Bank settlements with no corresponding internal transaction.")
        
        if summary['duplicate_transaction_count'] > 0:
            report.append(f"⚠ Duplicate Transactions:      {summary['duplicate_transaction_count']:3,} "
                         f"(INR {summary['duplicate_transaction_amount']:,.2f})")
            report.append(f"  Duplicate entries excluded from financial totals.")
        
        if summary['duplicate_bank_count'] > 0:
            report.append(f"⚠ Duplicate Bank Entries:      {summary['duplicate_bank_count']:3,} "
                         f"(INR {summary['duplicate_bank_amount']:,.2f})")
            report.append(f"  Duplicate bank entries excluded from financial totals.")
        
        if summary['unmatched_refund_count'] > 0:
            report.append(f"✗ Unmatched Refunds:           {summary['unmatched_refund_count']:3,} "
                         f"(INR {summary['unmatched_refund_amount']:,.2f})")
            report.append(f"  Refunds referencing non-existent transactions.")
        
        report.append("")
        
        report.append("-" * 80)
        report.append("ROUNDING VARIANCE ANALYSIS")
        report.append("-" * 80)
        report.append("")
        report.append(f"Transactions with Rounding:    {rounding_analysis['count']:,}")
        report.append(f"Aggregate Variance:            INR {rounding_analysis['total_variance']:.3f}")
        report.append(f"Threshold:                     INR {rounding_analysis['threshold']:.2f}")
        report.append(f"Exceeds Threshold:             {'YES ⚠' if rounding_analysis['exceeds_threshold'] else 'NO ✓'}")
        report.append("")
        
        if rounding_analysis['exceeds_threshold']:
            report.append("⚠ WARNING: Aggregate rounding variance exceeds the acceptable threshold.")
            report.append("  Individual differences are small, but their cumulative effect is significant.")
            report.append("")
        
        report.append("-" * 80)
        report.append("FINANCIAL RECONCILIATION")
        report.append("-" * 80)
        report.append("")
        report.append(f"Total Internal Payments:       INR {summary['total_internal_payment_value']:,.2f}")
        report.append(f"Total Bank Settlements:        INR {summary['total_bank_payment_value']:,.2f}")
        report.append(f"Matched Amount:                INR {summary['matched_amount']:,.2f}")
        report.append(f"Timing Differences:            INR {summary['timing_difference_amount']:,.2f}")
        report.append(f"Missing Settlements:           INR {summary['missing_settlement_amount']:,.2f}")
        report.append(f"Unexplained Variance:          INR {summary['unexplained_variance']:,.3f}")
        report.append("")
        
        # Overall status
        report.append("-" * 80)
        report.append("OVERALL RECONCILIATION STATUS")
        report.append("-" * 80)
        report.append("")
        
        # Count total exceptions
        total_exceptions = (
            summary['timing_difference_count'] +
            summary['missing_settlement_count'] +
            summary['unmatched_bank_entry_count'] +
            summary['duplicate_transaction_count'] +
            summary['duplicate_bank_count'] +
            summary['unmatched_refund_count']
        )
        
        if total_exceptions == 0 and not rounding_analysis['exceeds_threshold']:
            report.append("✓ Status: FULLY RECONCILED")
            report.append("  All transactions match perfectly with no exceptions.")
        elif total_exceptions == summary['timing_difference_count'] and not rounding_analysis['exceeds_threshold']:
            report.append("✓ Status: RECONCILED WITH TIMING DIFFERENCES")
            report.append("  All discrepancies are explained by period-end timing.")
        else:
            report.append("⚠ Status: EXCEPTIONS REQUIRE INVESTIGATION")
            report.append(f"  Total Exceptions: {total_exceptions}")
            report.append("  Please review the exceptions report for details.")
        
        report.append("")
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def generate_exception_details(self, results_df: pd.DataFrame) -> Dict:
        """
        Generate detailed exception information grouped by status
        
        Args:
            results_df: DataFrame with reconciliation results
            
        Returns:
            Dictionary with exceptions grouped by type
        """
        exceptions = results_df[results_df['status'] != 'MATCHED'].copy()
        
        # Group by status
        grouped = {}
        
        for status in exceptions['status'].unique():
            status_records = exceptions[exceptions['status'] == status]
            
            grouped[status] = {
                'count': len(status_records),
                'records': status_records.to_dict('records')
            }
        
        return grouped
    
    def format_currency(self, amount: float) -> str:
        """
        Format amount as INR currency
        
        Args:
            amount: Amount to format
            
        Returns:
            Formatted currency string
        """
        if amount is None:
            return "N/A"
        return f"INR {amount:,.2f}"


def test_report_generator():
    """Test report generation"""
    print("=" * 60)
    print("Testing Report Generator")
    print("=" * 60)
    
    from data_loader import DataLoader
    from reconciliation import ReconciliationEngine
    
    # Load data
    print("\n1. Loading data and running reconciliation...")
    loader = DataLoader()
    transactions_df = loader.load_transactions('transactions.csv')
    settlements_df = loader.load_settlements('settlements.csv')
    
    engine = ReconciliationEngine()
    reconciliation = engine.reconcile(transactions_df, settlements_df)
    
    results_df = reconciliation['results']
    summary = reconciliation['summary']
    rounding = reconciliation['rounding_analysis']
    
    print(f"✓ Reconciliation complete - {len(results_df)} records")
    
    # Generate reports
    print("\n2. Generating reports...")
    generator = ReportGenerator()
    
    # Full reconciliation CSV
    full_csv = generator.generate_full_reconciliation_csv(results_df, summary)
    print(f"✓ Full reconciliation CSV: {len(full_csv)} characters")
    
    # Exceptions CSV
    exceptions_csv = generator.generate_exceptions_csv(results_df, summary)
    print(f"✓ Exceptions CSV: {len(exceptions_csv)} characters")
    
    # Summary report
    summary_report = generator.generate_summary_report(summary, rounding)
    print(f"✓ Summary report: {len(summary_report)} characters")
    
    # Display summary report
    print("\n" + "=" * 60)
    print("SAMPLE SUMMARY REPORT")
    print("=" * 60)
    print(summary_report)
    
    # Test saving to files
    print("\n3. Testing file exports...")
    
    with open('test_reconciliation_report.csv', 'w', encoding='utf-8') as f:
        f.write(full_csv)
    print("✓ Saved: test_reconciliation_report.csv")
    
    with open('test_exceptions_report.csv', 'w', encoding='utf-8') as f:
        f.write(exceptions_csv)
    print("✓ Saved: test_exceptions_report.csv")
    
    with open('test_summary_report.txt', 'w', encoding='utf-8') as f:
        f.write(summary_report)
    print("✓ Saved: test_summary_report.txt")
    
    print("\n" + "=" * 60)
    print("✓ ALL REPORT GENERATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_report_generator()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
