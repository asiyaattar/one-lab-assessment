"""
Data Loader and Validation Module for PayFlow Recon
Handles CSV loading, validation, and data quality checks
"""

import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Tuple, Dict, List, Optional
import os


class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass


class DataLoader:
    """
    Loads and validates transaction and settlement CSV files
    """
    
    REQUIRED_TRANSACTION_COLUMNS = [
        'transaction_id', 
        'amount', 
        'transaction_date', 
        'type', 
        'original_transaction_id'
    ]
    
    REQUIRED_SETTLEMENT_COLUMNS = [
        'transaction_id', 
        'amount', 
        'settlement_date', 
        'type', 
        'original_transaction_id'
    ]
    
    VALID_TRANSACTION_TYPES = ['PAYMENT', 'REFUND']
    
    def __init__(self, accounting_period_start: str = "2026-11-01", 
                 accounting_period_end: str = "2026-11-30"):
        """
        Initialize DataLoader with accounting period
        
        Args:
            accounting_period_start: Start date of accounting period (YYYY-MM-DD)
            accounting_period_end: End date of accounting period (YYYY-MM-DD)
        """
        self.accounting_period_start = pd.to_datetime(accounting_period_start)
        self.accounting_period_end = pd.to_datetime(accounting_period_end)
    
    def load_transactions(self, file_path: str) -> pd.DataFrame:
        """
        Load and validate transaction CSV file
        
        Args:
            file_path: Path to transactions CSV file
            
        Returns:
            Validated DataFrame with transactions
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            # Load CSV
            df = pd.read_csv(file_path)
            
            # Check if file is empty
            if df.empty:
                raise ValidationError("Transaction file is empty")
            
            # Validate columns
            self._validate_columns(df, self.REQUIRED_TRANSACTION_COLUMNS, "transactions")
            
            # Validate data
            df = self._validate_transaction_data(df)
            
            return df
            
        except pd.errors.EmptyDataError:
            raise ValidationError("Transaction file is empty or corrupted")
        except pd.errors.ParserError as e:
            raise ValidationError(f"Failed to parse transaction CSV: {str(e)}")
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Error loading transactions: {str(e)}")
    
    def load_settlements(self, file_path: str) -> pd.DataFrame:
        """
        Load and validate settlement CSV file
        
        Args:
            file_path: Path to settlements CSV file
            
        Returns:
            Validated DataFrame with settlements
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            # Load CSV
            df = pd.read_csv(file_path)
            
            # Check if file is empty
            if df.empty:
                raise ValidationError("Settlement file is empty")
            
            # Validate columns
            self._validate_columns(df, self.REQUIRED_SETTLEMENT_COLUMNS, "settlements")
            
            # Validate data
            df = self._validate_settlement_data(df)
            
            return df
            
        except pd.errors.EmptyDataError:
            raise ValidationError("Settlement file is empty or corrupted")
        except pd.errors.ParserError as e:
            raise ValidationError(f"Failed to parse settlement CSV: {str(e)}")
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Error loading settlements: {str(e)}")
    
    def _validate_columns(self, df: pd.DataFrame, required_columns: List[str], 
                         file_type: str) -> None:
        """
        Validate that DataFrame contains all required columns
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            file_type: Type of file being validated (for error messages)
            
        Raises:
            ValidationError: If columns are missing
        """
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValidationError(
                f"Missing required columns in {file_type} file: {', '.join(missing_columns)}"
            )
    
    def _validate_transaction_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate transaction data quality
        
        Args:
            df: Transaction DataFrame
            
        Returns:
            Validated and cleaned DataFrame
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        
        # Validate transaction IDs (must not be null/empty)
        if df['transaction_id'].isnull().any():
            null_count = df['transaction_id'].isnull().sum()
            errors.append(f"Found {null_count} null transaction IDs")
        
        empty_ids = df['transaction_id'].astype(str).str.strip().eq('')
        if empty_ids.any():
            empty_count = empty_ids.sum()
            errors.append(f"Found {empty_count} empty transaction IDs")
        
        # Validate transaction types
        invalid_types = ~df['type'].isin(self.VALID_TRANSACTION_TYPES)
        if invalid_types.any():
            invalid_values = df.loc[invalid_types, 'type'].unique()
            errors.append(
                f"Invalid transaction types found: {', '.join(map(str, invalid_values))}. "
                f"Valid types: {', '.join(self.VALID_TRANSACTION_TYPES)}"
            )
        
        # Validate and parse amounts
        df, amount_errors = self._validate_amounts(df, 'amount')
        errors.extend(amount_errors)
        
        # Validate and parse dates
        df, date_errors = self._validate_dates(df, 'transaction_date')
        errors.extend(date_errors)
        
        # Validate refund references
        refund_errors = self._validate_refund_references(df)
        errors.extend(refund_errors)
        
        if errors:
            raise ValidationError("Transaction validation failed:\n" + "\n".join(f"- {e}" for e in errors))
        
        return df
    
    def _validate_settlement_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate settlement data quality
        
        Args:
            df: Settlement DataFrame
            
        Returns:
            Validated and cleaned DataFrame
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        
        # Validate transaction IDs
        if df['transaction_id'].isnull().any():
            null_count = df['transaction_id'].isnull().sum()
            errors.append(f"Found {null_count} null transaction IDs")
        
        empty_ids = df['transaction_id'].astype(str).str.strip().eq('')
        if empty_ids.any():
            empty_count = empty_ids.sum()
            errors.append(f"Found {empty_count} empty transaction IDs")
        
        # Validate transaction types
        invalid_types = ~df['type'].isin(self.VALID_TRANSACTION_TYPES)
        if invalid_types.any():
            invalid_values = df.loc[invalid_types, 'type'].unique()
            errors.append(
                f"Invalid transaction types found: {', '.join(map(str, invalid_values))}. "
                f"Valid types: {', '.join(self.VALID_TRANSACTION_TYPES)}"
            )
        
        # Validate and parse amounts
        df, amount_errors = self._validate_amounts(df, 'amount')
        errors.extend(amount_errors)
        
        # Validate and parse dates
        df, date_errors = self._validate_dates(df, 'settlement_date')
        errors.extend(date_errors)
        
        if errors:
            raise ValidationError("Settlement validation failed:\n" + "\n".join(f"- {e}" for e in errors))
        
        return df
    
    def _validate_amounts(self, df: pd.DataFrame, column: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate amount column contains valid numeric values
        
        Args:
            df: DataFrame
            column: Name of amount column
            
        Returns:
            Tuple of (cleaned DataFrame, list of error messages)
        """
        errors = []
        
        # Check for null amounts
        if df[column].isnull().any():
            null_count = df[column].isnull().sum()
            errors.append(f"Found {null_count} null amounts")
        
        # Try to convert to numeric
        df[column] = pd.to_numeric(df[column], errors='coerce')
        
        # Check for non-numeric values that were coerced to NaN
        invalid_amounts = df[column].isnull()
        if invalid_amounts.any():
            invalid_count = invalid_amounts.sum()
            errors.append(f"Found {invalid_count} invalid (non-numeric) amounts")
        
        return df, errors
    
    def _validate_dates(self, df: pd.DataFrame, column: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate date column contains valid dates
        
        Args:
            df: DataFrame
            column: Name of date column
            
        Returns:
            Tuple of (cleaned DataFrame, list of error messages)
        """
        errors = []
        
        # Check for null dates
        if df[column].isnull().any():
            null_count = df[column].isnull().sum()
            errors.append(f"Found {null_count} null dates in {column}")
        
        # Try to parse dates
        try:
            df[column] = pd.to_datetime(df[column], errors='coerce')
            
            # Check for invalid dates that were coerced to NaT
            invalid_dates = df[column].isnull()
            if invalid_dates.any():
                invalid_count = invalid_dates.sum()
                errors.append(f"Found {invalid_count} invalid dates in {column}")
        except Exception as e:
            errors.append(f"Failed to parse dates in {column}: {str(e)}")
        
        return df, errors
    
    def _validate_refund_references(self, df: pd.DataFrame) -> List[str]:
        """
        Validate that refunds have original_transaction_id populated
        
        Args:
            df: Transaction DataFrame
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check refunds have original_transaction_id
        refunds = df[df['type'] == 'REFUND']
        if not refunds.empty:
            missing_refs = refunds['original_transaction_id'].isnull() | \
                          (refunds['original_transaction_id'].astype(str).str.strip() == '')
            if missing_refs.any():
                missing_count = missing_refs.sum()
                errors.append(
                    f"Found {missing_count} refund(s) without original_transaction_id reference"
                )
        
        return errors
    
    def get_data_summary(self, df: pd.DataFrame, file_type: str) -> Dict:
        """
        Generate summary statistics for loaded data
        
        Args:
            df: DataFrame to summarize
            file_type: Type of data (transactions or settlements)
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'file_type': file_type,
            'total_records': len(df),
            'payment_count': len(df[df['type'] == 'PAYMENT']),
            'refund_count': len(df[df['type'] == 'REFUND']),
            'date_range': None,
            'total_amount': None,
            'unique_transaction_ids': df['transaction_id'].nunique(),
            'duplicate_transaction_ids': len(df) - df['transaction_id'].nunique()
        }
        
        # Date range
        date_column = 'transaction_date' if file_type == 'transactions' else 'settlement_date'
        if date_column in df.columns and not df[date_column].isnull().all():
            summary['date_range'] = {
                'start': df[date_column].min(),
                'end': df[date_column].max()
            }
        
        # Total amount (using Decimal for precision)
        if 'amount' in df.columns and not df['amount'].isnull().all():
            total = sum(Decimal(str(amt)) for amt in df['amount'].dropna())
            summary['total_amount'] = float(total)
        
        return summary


def load_sample_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the supplied sample CSV files from the data folder
    
    Returns:
        Tuple of (transactions_df, settlements_df)
        
    Raises:
        ValidationError: If files cannot be loaded
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct paths to sample data files
    transactions_path = os.path.join(script_dir, 'transactions.csv')
    settlements_path = os.path.join(script_dir, 'settlements.csv')
    
    loader = DataLoader()
    
    transactions_df = loader.load_transactions(transactions_path)
    settlements_df = loader.load_settlements(settlements_path)
    
    return transactions_df, settlements_df


if __name__ == "__main__":
    """Test the data loader with sample files"""
    print("Testing DataLoader with sample files...")
    print("-" * 60)
    
    try:
        loader = DataLoader()
        
        # Load transactions
        print("\n1. Loading transactions.csv...")
        transactions_df = loader.load_transactions('transactions.csv')
        print(f"✓ Successfully loaded {len(transactions_df)} transaction records")
        
        # Get summary
        trans_summary = loader.get_data_summary(transactions_df, 'transactions')
        print(f"  - Payments: {trans_summary['payment_count']}")
        print(f"  - Refunds: {trans_summary['refund_count']}")
        print(f"  - Unique IDs: {trans_summary['unique_transaction_ids']}")
        print(f"  - Duplicates: {trans_summary['duplicate_transaction_ids']}")
        print(f"  - Total Amount: INR {trans_summary['total_amount']:.2f}")
        
        # Load settlements
        print("\n2. Loading settlements.csv...")
        settlements_df = loader.load_settlements('settlements.csv')
        print(f"✓ Successfully loaded {len(settlements_df)} settlement records")
        
        # Get summary
        settle_summary = loader.get_data_summary(settlements_df, 'settlements')
        print(f"  - Payments: {settle_summary['payment_count']}")
        print(f"  - Refunds: {settle_summary['refund_count']}")
        print(f"  - Unique IDs: {settle_summary['unique_transaction_ids']}")
        print(f"  - Duplicates: {settle_summary['duplicate_transaction_ids']}")
        print(f"  - Total Amount: INR {settle_summary['total_amount']:.2f}")
        
        print("\n" + "=" * 60)
        print("✓ All validation tests passed!")
        print("=" * 60)
        
    except ValidationError as e:
        print(f"\n✗ Validation Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
