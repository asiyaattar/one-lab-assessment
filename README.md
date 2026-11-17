# PayFlow Recon - Intelligent Payment Reconciliation System

A professional payment reconciliation application that automatically matches internal transaction records with bank settlement data, identifies discrepancies, and generates comprehensive reports.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Tests](https://img.shields.io/badge/tests-13%2F13%20passing-brightgreen)

## 🎯 Project Overview

PayFlow Recon solves the critical business problem of reconciling a payment company's internal transaction records with bank settlement records. Banks settle funds in batches 1-2 days after transactions occur, and at month-end, these records must be reconciled to identify discrepancies, timing differences, and potential issues.

### Key Features

- ✅ **Automated Matching**: Intelligent transaction-to-settlement matching
- 🔍 **Duplicate Detection**: Identifies duplicate entries in both datasets
- ⏰ **Timing Analysis**: Detects transactions settled outside the accounting period
- 💰 **Rounding Variance**: Analyzes individual and aggregate rounding differences
- 🔄 **Refund Validation**: Validates refund references against original transactions
- 📊 **Professional Dashboard**: Modern financial SaaS interface with interactive charts
- 📥 **Report Generation**: Exports detailed reconciliation reports in multiple formats
- 🧪 **Thoroughly Tested**: 13 automated tests with 100% pass rate

## 📋 Table of Contents

- [Business Problem](#business-problem)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Reconciliation Logic](#reconciliation-logic)
- [Deployment](#deployment)
- [Known Limitations](#known-limitations)

## 🏢 Business Problem

### Scenario

A payments company records customer transactions immediately when payments happen. However, the bank settles these funds in batches, usually 1–2 days later. At the end of every month, the company's internal transaction records must reconcile with bank settlement records.

### Challenges

1. **Timing Differences**: November transactions may settle in December
2. **Rounding Variances**: Small individual differences compound into significant aggregate variances
3. **Duplicate Entries**: Same transaction appears multiple times in bank data
4. **Invalid Refunds**: Refunds referencing non-existent original transactions

### Solution

PayFlow Recon automatically identifies these issues and provides:
- Clear categorization of each discrepancy type
- Financial impact analysis
- Actionable investigation recommendations
- Audit-ready reports

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd Onelab-Assessment
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python -c "import streamlit; import pandas; import plotly; print('✓ All dependencies installed')"
   ```

## ⚡ Quick Start

### Run the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Run Tests

```bash
# Run all pytest tests
pytest tests/ -v

# Run integration test
python integration_test.py
```

## 📖 Usage

### 1. Load Sample Data

On the **Reconciliation** page:
- Click **"Load Sample Data"** to load the provided CSV files
- Or upload your own `transactions.csv` and `settlements.csv`

### 2. Run Reconciliation

- Review the data summary
- Click **"Run Reconciliation"**
- The system will process and match all records

### 3. View Results

Navigate through the dashboard pages:

- **Dashboard**: KPI cards, charts, and overall status
- **Transactions**: Detailed table with search and filters
- **Exceptions**: Grouped exceptions with explanations
- **Reports**: Download reconciliation reports

### 4. Download Reports

On the **Reports** page, download:
- Complete reconciliation report (CSV)
- Exceptions-only report (CSV)
- Executive summary (TXT)

## 📁 Project Structure

```
Onelab-Assessment/
│
├── app.py                      # Streamlit dashboard (main application)
├── data_loader.py             # CSV loading and validation
├── reconciliation.py          # Core reconciliation engine
├── report_generator.py        # Report generation
│
├── data/
│   ├── transactions.csv       # Sample internal transactions
│   └── settlements.csv        # Sample bank settlements
│
├── tests/
│   ├── __init__.py
│   └── test_reconciliation.py # Comprehensive test suite (13 tests)
│
├── integration_test.py        # End-to-end integration test
├── test_data_validation.py    # Data loader validation tests
├── test_reconciliation_details.py  # Detailed reconciliation tests
│
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── .gitignore                # Git ignore rules
│
└── docs/
    ├── assumptions.md        # Business assumptions
    └── reconciliation_logic.md  # Technical documentation
```

## 🧪 Testing

### Test Coverage

The application includes **13 comprehensive tests** covering:

1. **TC01**: Correctly matched payment
2. **TC02**: Timing difference (November → December)
3. **TC03**: Duplicate bank settlement
4. **TC04**: Unmatched refund (TX999 reference)
5. **TC05**: Aggregate rounding variance
6. **TC06**: Missing settlement
7. **TC07**: Unmatched bank payment
8. **TC08**: Invalid date handling
9. **TC09**: Missing column validation
10. **TC10**: Completely matching datasets
11. **TC11**: Duplicate internal transaction
12. **TC12**: Valid refund reference
13. **Integration test with actual sample data**

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_reconciliation.py::TestReconciliation::test_tc01_correctly_matched_payment -v

# Integration test
python integration_test.py

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Results

```
✓ 13/13 tests passing
✓ All 4 planted discrepancies detected
✓ Financial calculations verified correct
✓ Data integrity maintained
```

## 🔍 Reconciliation Logic

### Reconciliation Process

1. **Load Data**: Validate CSV files and data quality
2. **Identify Duplicates**: Find duplicate transaction IDs
3. **Separate Types**: Split payments and refunds
4. **Match Records**: Match transactions with settlements by ID
5. **Analyze Timing**: Check settlement dates against accounting period
6. **Validate Refunds**: Verify refund references
7. **Calculate Variances**: Individual and aggregate rounding analysis
8. **Generate Results**: Create detailed reconciliation records

### Classification Logic

| Status | Description | Action |
|--------|-------------|--------|
| **MATCHED** | Transaction and settlement match perfectly | No action required |
| **TIMING_DIFFERENCE** | Settled outside accounting period | Verify in next period |
| **AMOUNT_MISMATCH** | Significant amount difference | Investigate fees/errors |
| **MISSING_SETTLEMENT** | No bank settlement found | Check for delayed settlement |
| **UNMATCHED_BANK_ENTRY** | No internal transaction record | Verify missing entry |
| **DUPLICATE_TRANSACTION_ENTRY** | Duplicate in transaction file | Remove duplicate |
| **DUPLICATE_BANK_ENTRY** | Duplicate in settlement file | Contact bank |
| **UNMATCHED_REFUND** | Refund references non-existent transaction | Find original transaction |

### Financial Calculations

- **All calculations use Python's `Decimal` type** for financial precision
- Duplicate entries are **excluded from financial totals**
- Payments and refunds are **tracked separately**
- Individual rounding tolerance: **₹0.01**
- Aggregate rounding threshold: **₹0.02**

### Four Planted Discrepancies

The sample data contains four deliberately planted scenarios:

1. **TX003**: November transaction settled December 1st (timing difference)
2. **TX031-TX040**: Ten transactions with ₹0.005 rounding each = ₹0.05 aggregate
3. **TX001**: Duplicate bank settlement entry
4. **RF001**: Refund referencing non-existent TX999

## 🌐 Deployment

### Local Deployment

```bash
streamlit run app.py
```

### Streamlit Community Cloud

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Select `app.py` as the main file
   - Click **Deploy**

3. **Configuration**
   - Python version: 3.8+
   - No additional secrets required
   - Public access recommended for demo

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t payflow-recon .
docker run -p 8501:8501 payflow-recon
```

## 📊 Business Assumptions

### Accounting Period
- **Period**: November 1-30, 2026
- **Currency**: INR (Indian Rupees)

### Matching Rules
- Transaction IDs are the primary matching keys
- Payments recorded immediately upon occurrence
- Bank settlement occurs 1-2 days after transaction
- November transactions settled in December are timing differences, not missing payments

### Tolerances
- **Individual rounding tolerance**: ₹0.01
- **Aggregate rounding threshold**: ₹0.02

### Data Quality
- Duplicate copies excluded from financial totals
- First occurrence retained for matching
- Empty files handled gracefully
- Invalid records reported with clear errors

## ⚠️ Known Limitations

1. **CSV Format Only**: Currently supports CSV input only
2. **Single Currency**: Designed for INR; multi-currency requires modification
3. **Manual Upload**: No automated data pipeline integration
4. **In-Memory Processing**: Large datasets (>100K records) may require optimization
5. **No User Authentication**: Suitable for internal use or demo purposes
6. **Browser Dependent**: Requires modern web browser for dashboard

## 🔧 Configuration

### Adjusting Tolerances

Edit `reconciliation.py`:

```python
engine = ReconciliationEngine(
    accounting_period_start="2026-11-01",
    accounting_period_end="2026-11-30",
    individual_tolerance=Decimal("0.01"),  # Adjust here
    aggregate_tolerance=Decimal("0.02")    # Adjust here
)
```

### Custom CSV Columns

If your CSV files have different column names, update the required columns in `data_loader.py`:

```python
REQUIRED_TRANSACTION_COLUMNS = [
    'transaction_id',
    'amount',
    'transaction_date',
    'type',
    'original_transaction_id'
]
```

## 📞 Support & Contact

For questions or issues:
- Review the documentation in `docs/` folder
- Check test files for usage examples
- Run integration tests to verify setup

## 📄 License

This project was developed for the Onelab AI Fitness Assessment.

## 🙏 Acknowledgments

Built with:
- **Streamlit** - Web framework
- **Pandas** - Data manipulation
- **Plotly** - Interactive charts
- **Pytest** - Testing framework

---

**Version**: 1.0.0  
**Last Updated**: November 17, 2026  
**Status**: ✅ Production Ready
