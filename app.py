"""
PayFlow Recon - Intelligent Payment Reconciliation System
Professional Streamlit Dashboard for Payment Reconciliation
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

from data_loader import DataLoader, ValidationError
from reconciliation import ReconciliationEngine, ReconciliationStatus
from report_generator import ReportGenerator


# Page configuration
st.set_page_config(
    page_title="PayFlow Recon",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional financial SaaS look
st.markdown("""
<style>
    /* Main background and text */
    .main {
        background-color: #F8F9FA;
    }
    
    /* Header styling */
    h1 {
        color: #1A237E;
        font-weight: 600;
    }
    
    h2 {
        color: #283593;
        font-weight: 500;
        margin-top: 1.5rem;
    }
    
    h3 {
        color: #3F51B5;
        font-weight: 500;
    }
    
    /* KPI Cards */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border: 1px solid #E8EAF6;
    }
    
    div[data-testid="stMetric"] label {
        color: #5E6C84;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1A237E;
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1A237E;
    }
    
    section[data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #1A237E;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        border: none;
        transition: background-color 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #283593;
    }
    
    /* Dataframe styling */
    .dataframe {
        font-size: 0.875rem;
    }
    
    /* Success/Warning/Error boxes */
    .stSuccess {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
    }
    
    .stWarning {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
    }
    
    .stError {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
    }
    
    /* File uploader */
    section[data-testid="stFileUploader"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px dashed #C5CAE9;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border-color: #E8EAF6;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def initialize_session_state():
    """Initialize session state variables"""
    if 'transactions_df' not in st.session_state:
        st.session_state.transactions_df = None
    if 'settlements_df' not in st.session_state:
        st.session_state.settlements_df = None
    if 'reconciliation_results' not in st.session_state:
        st.session_state.reconciliation_results = None
    if 'sample_data_loaded' not in st.session_state:
        st.session_state.sample_data_loaded = False


def load_sample_data():
    """Load the provided sample CSV files"""
    try:
        loader = DataLoader()
        st.session_state.transactions_df = loader.load_transactions('transactions.csv')
        st.session_state.settlements_df = loader.load_settlements('settlements.csv')
        st.session_state.sample_data_loaded = True
        return True, "Sample data loaded successfully!"
    except Exception as e:
        return False, f"Error loading sample data: {str(e)}"


def run_reconciliation():
    """Run the reconciliation engine"""
    if st.session_state.transactions_df is None or st.session_state.settlements_df is None:
        return False, "Please load transaction and settlement data first"
    
    try:
        engine = ReconciliationEngine()
        st.session_state.reconciliation_results = engine.reconcile(
            st.session_state.transactions_df,
            st.session_state.settlements_df
        )
        return True, "Reconciliation completed successfully!"
    except Exception as e:
        return False, f"Reconciliation error: {str(e)}"


def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1A237E/FFFFFF?text=PayFlow+Recon", 
                 use_column_width=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "🔄 Reconciliation", "📊 Transactions", 
             "⚠️ Exceptions", "📥 Reports", "ℹ️ About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Data status
        st.subheader("Data Status")
        if st.session_state.transactions_df is not None:
            st.success(f"✓ Transactions: {len(st.session_state.transactions_df)} records")
        else:
            st.warning("○ No transaction data")
        
        if st.session_state.settlements_df is not None:
            st.success(f"✓ Settlements: {len(st.session_state.settlements_df)} records")
        else:
            st.warning("○ No settlement data")
        
        if st.session_state.reconciliation_results is not None:
            st.success("✓ Reconciliation complete")
        else:
            st.info("○ Ready to reconcile")
        
        return page


def render_dashboard():
    """Render the main dashboard page"""
    st.title("💰 PayFlow Recon Dashboard")
    st.markdown("**Intelligent Payment Reconciliation System**")
    
    if st.session_state.reconciliation_results is None:
        st.info("👋 Welcome! Load data and run reconciliation to see your dashboard.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📂 Load Sample Data", use_container_width=True):
                success, message = load_sample_data()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("🔄 Go to Reconciliation", use_container_width=True):
                st.session_state.current_page = "reconciliation"
                st.rerun()
        
        return
    
    # Get reconciliation data
    summary = st.session_state.reconciliation_results['summary']
    results_df = st.session_state.reconciliation_results['results']
    rounding = st.session_state.reconciliation_results['rounding_analysis']
    
    # KPI Cards Row 1
    st.markdown("### 📊 Transaction Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Transactions",
            f"{summary['total_internal_transactions']:,}",
            help="Total internal transaction records"
        )
    
    with col2:
        st.metric(
            "Total Transaction Value",
            f"₹{summary['total_internal_payment_value']:,.2f}",
            help="Total value of all internal transactions"
        )
    
    with col3:
        st.metric(
            "Total Settlements",
            f"{summary['total_bank_settlements']:,}",
            help="Total bank settlement records"
        )
    
    with col4:
        st.metric(
            "Total Settlement Value",
            f"₹{summary['total_bank_payment_value']:,.2f}",
            help="Total value of all bank settlements"
        )
    
    # KPI Cards Row 2
    st.markdown("### ✅ Reconciliation Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Matched Transactions",
            f"{summary['matched_count']:,}",
            f"₹{summary['matched_amount']:,.2f}",
            help="Transactions successfully matched"
        )
    
    with col2:
        st.metric(
            "Timing Differences",
            f"{summary['timing_difference_count']:,}",
            f"₹{summary['timing_difference_amount']:,.2f}",
            help="Transactions settled outside accounting period"
        )
    
    with col3:
        st.metric(
            "Missing Settlements",
            f"{summary['missing_settlement_count']:,}",
            f"₹{summary['missing_settlement_amount']:,.2f}",
            delta=f"-{summary['missing_settlement_count']}" if summary['missing_settlement_count'] > 0 else None,
            delta_color="inverse",
            help="Transactions with no bank settlement"
        )
    
    with col4:
        total_exceptions = (
            summary['timing_difference_count'] +
            summary['missing_settlement_count'] +
            summary['unmatched_bank_entry_count'] +
            summary['duplicate_transaction_count'] +
            summary['duplicate_bank_count'] +
            summary['unmatched_refund_count']
        )
        st.metric(
            "Total Exceptions",
            f"{total_exceptions:,}",
            delta=f"-{total_exceptions}" if total_exceptions > 0 else "Perfect!",
            delta_color="inverse",
            help="Total discrepancies requiring investigation"
        )
    
    # KPI Cards Row 3
    st.markdown("### ⚠️ Exception Details")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Duplicate Entries",
            f"{summary['duplicate_bank_count']:,}",
            f"₹{summary['duplicate_bank_amount']:,.2f}",
            help="Duplicate bank settlement entries"
        )
    
    with col2:
        st.metric(
            "Unmatched Refunds",
            f"{summary['unmatched_refund_count']:,}",
            f"₹{summary['unmatched_refund_amount']:,.2f}",
            help="Refunds with no matching transaction"
        )
    
    with col3:
        variance_delta = f"₹{rounding['total_variance']:.3f}"
        st.metric(
            "Rounding Variance",
            f"{rounding['count']:,} txns",
            variance_delta,
            delta_color="off",
            help="Transactions with aggregate rounding differences"
        )
    
    with col4:
        st.metric(
            "Unexplained Variance",
            f"₹{abs(summary['unexplained_variance']):.3f}",
            delta_color="off",
            help="Total unexplained financial variance"
        )
    
    # Charts
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Reconciliation Status Distribution")
        
        # Status distribution pie chart
        status_counts = results_df['status'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            hole=0.4,
            marker=dict(
                colors=['#4CAF50', '#FF9800', '#F44336', '#2196F3', '#9C27B0', '#795548', '#607D8B']
            )
        )])
        
        fig.update_layout(
            showlegend=True,
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 💰 Financial Reconciliation")
        
        # Financial bar chart
        financial_data = pd.DataFrame({
            'Category': ['Internal\nTransactions', 'Bank\nSettlements', 'Matched\nAmount', 'Timing\nDifferences'],
            'Amount': [
                summary['total_internal_payment_value'],
                summary['total_bank_payment_value'],
                summary['matched_amount'],
                summary['timing_difference_amount']
            ]
        })
        
        fig = px.bar(
            financial_data,
            x='Category',
            y='Amount',
            color='Category',
            color_discrete_sequence=['#1A237E', '#283593', '#4CAF50', '#FF9800']
        )
        
        fig.update_layout(
            showlegend=False,
            height=350,
            yaxis_title="Amount (INR)",
            xaxis_title="",
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Warnings and Alerts
    if total_exceptions > 0:
        st.markdown("---")
        st.warning(f"⚠️ **{total_exceptions} exceptions require investigation.** Please review the Exceptions page for details.")
    
    if rounding['exceeds_threshold']:
        st.warning(f"⚠️ **Aggregate rounding variance (₹{rounding['total_variance']:.3f}) exceeds threshold (₹{rounding['threshold']:.2f}).** Review affected transactions.")


def render_reconciliation():
    """Render the reconciliation page"""
    st.title("🔄 Reconciliation")
    st.markdown("Load transaction and settlement data to perform reconciliation")
    
    # Load Sample Data Button
    st.markdown("### 📂 Load Sample Data")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Load the provided sample datasets (transactions.csv and settlements.csv)")
    with col2:
        if st.button("📂 Load Sample Data", use_container_width=True):
            with st.spinner("Loading sample data..."):
                success, message = load_sample_data()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    st.markdown("---")
    
    # File Upload Section
    st.markdown("### 📤 Upload Custom Data")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Internal Transactions**")
        trans_file = st.file_uploader(
            "Upload transactions CSV",
            type=['csv'],
            key='trans_upload',
            help="CSV file with columns: transaction_id, amount, transaction_date, type, original_transaction_id"
        )
        
        if trans_file:
            try:
                loader = DataLoader()
                # Save uploaded file temporarily
                with open('temp_transactions.csv', 'wb') as f:
                    f.write(trans_file.getvalue())
                
                st.session_state.transactions_df = loader.load_transactions('temp_transactions.csv')
                st.success(f"✓ Loaded {len(st.session_state.transactions_df)} transactions")
                
                # Show preview
                with st.expander("Preview Data"):
                    st.dataframe(st.session_state.transactions_df.head(), use_container_width=True)
                
            except ValidationError as e:
                st.error(f"Validation Error: {str(e)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col2:
        st.markdown("**Bank Settlements**")
        settle_file = st.file_uploader(
            "Upload settlements CSV",
            type=['csv'],
            key='settle_upload',
            help="CSV file with columns: transaction_id, amount, settlement_date, type, original_transaction_id"
        )
        
        if settle_file:
            try:
                loader = DataLoader()
                # Save uploaded file temporarily
                with open('temp_settlements.csv', 'wb') as f:
                    f.write(settle_file.getvalue())
                
                st.session_state.settlements_df = loader.load_settlements('temp_settlements.csv')
                st.success(f"✓ Loaded {len(st.session_state.settlements_df)} settlements")
                
                # Show preview
                with st.expander("Preview Data"):
                    st.dataframe(st.session_state.settlements_df.head(), use_container_width=True)
                
            except ValidationError as e:
                st.error(f"Validation Error: {str(e)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Show data preview if loaded
    if st.session_state.transactions_df is not None and st.session_state.settlements_df is not None:
        st.markdown("---")
        st.markdown("### 📊 Data Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            loader = DataLoader()
            trans_summary = loader.get_data_summary(st.session_state.transactions_df, 'transactions')
            st.info(f"""
            **Transactions Summary**
            - Total Records: {trans_summary['total_records']}
            - Payments: {trans_summary['payment_count']}
            - Refunds: {trans_summary['refund_count']}
            - Unique IDs: {trans_summary['unique_transaction_ids']}
            - Duplicates: {trans_summary['duplicate_transaction_ids']}
            - Total Amount: ₹{trans_summary['total_amount']:,.2f}
            """)
        
        with col2:
            settle_summary = loader.get_data_summary(st.session_state.settlements_df, 'settlements')
            st.info(f"""
            **Settlements Summary**
            - Total Records: {settle_summary['total_records']}
            - Payments: {settle_summary['payment_count']}
            - Refunds: {settle_summary['refund_count']}
            - Unique IDs: {settle_summary['unique_transaction_ids']}
            - Duplicates: {settle_summary['duplicate_transaction_ids']}
            - Total Amount: ₹{settle_summary['total_amount']:,.2f}
            """)
        
        # Run Reconciliation Button
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Run Reconciliation", use_container_width=True, type="primary"):
                with st.spinner("Running reconciliation..."):
                    success, message = run_reconciliation()
                    if success:
                        st.success(message)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(message)


def render_transactions():
    """Render the transactions detail page"""
    st.title("📊 Transaction Details")
    
    if st.session_state.reconciliation_results is None:
        st.warning("Please run reconciliation first to view transaction details.")
        return
    
    results_df = st.session_state.reconciliation_results['results']
    
    # Filters
    st.markdown("### 🔍 Filters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.multiselect(
            "Status",
            options=results_df['status'].unique(),
            default=results_df['status'].unique()
        )
    
    with col2:
        type_filter = st.multiselect(
            "Type",
            options=results_df['type'].unique(),
            default=results_df['type'].unique()
        )
    
    with col3:
        search_term = st.text_input("Search Transaction ID", "")
    
    # Apply filters
    filtered_df = results_df[
        (results_df['status'].isin(status_filter)) &
        (results_df['type'].isin(type_filter))
    ]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['transaction_id'].str.contains(search_term, case=False, na=False)
        ]
    
    # Display results
    st.markdown(f"### 📋 Results ({len(filtered_df)} records)")
    
    # Color code by status
    def color_status(val):
        if val == 'MATCHED':
            return 'background-color: #E8F5E9'
        elif val == 'TIMING_DIFFERENCE':
            return 'background-color: #FFF3E0'
        elif 'DUPLICATE' in val:
            return 'background-color: #E1F5FE'
        else:
            return 'background-color: #FFEBEE'
    
    styled_df = filtered_df.style.applymap(color_status, subset=['status'])
    
    st.dataframe(styled_df, use_container_width=True, height=500)
    
    # Export filtered results
    if len(filtered_df) > 0:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "📥 Download Filtered Results",
            csv,
            f"filtered_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv"
        )


def render_exceptions():
    """Render the exceptions page"""
    st.title("⚠️ Exceptions")
    
    if st.session_state.reconciliation_results is None:
        st.warning("Please run reconciliation first to view exceptions.")
        return
    
    results_df = st.session_state.reconciliation_results['results']
    summary = st.session_state.reconciliation_results['summary']
    rounding = st.session_state.reconciliation_results['rounding_analysis']
    
    # Exception summary
    exceptions_df = results_df[results_df['status'] != 'MATCHED']
    
    st.markdown(f"### 📊 Exception Summary")
    st.info(f"Found **{len(exceptions_df)}** exceptions requiring investigation")
    
    # Group exceptions by type
    exception_groups = exceptions_df.groupby('status').size().reset_index(name='count')
    
    for _, group in exception_groups.iterrows():
        status = group['status']
        count = group['count']
        
        with st.expander(f"**{status}** ({count} records)", expanded=True):
            status_df = exceptions_df[exceptions_df['status'] == status]
            
            # Show explanation for first record
            if len(status_df) > 0:
                st.markdown(f"**Explanation:** {status_df.iloc[0]['explanation']}")
                st.markdown(f"**Recommended Action:** {status_df.iloc[0]['investigation_action']}")
            
            # Show records
            st.dataframe(status_df, use_container_width=True)
    
    # Rounding variance details
    if rounding['exceeds_threshold']:
        st.markdown("---")
        st.markdown("### 🔢 Rounding Variance Analysis")
        st.warning(f"Aggregate rounding variance (₹{rounding['total_variance']:.3f}) exceeds threshold (₹{rounding['threshold']:.2f})")
        
        if rounding['count'] > 0:
            rounding_df = pd.DataFrame(rounding['rounding_items'])
            st.dataframe(rounding_df, use_container_width=True)


def render_reports():
    """Render the reports download page"""
    st.title("📥 Reports")
    
    if st.session_state.reconciliation_results is None:
        st.warning("Please run reconciliation first to generate reports.")
        return
    
    results_df = st.session_state.reconciliation_results['results']
    summary = st.session_state.reconciliation_results['summary']
    rounding = st.session_state.reconciliation_results['rounding_analysis']
    
    st.markdown("### 📑 Available Reports")
    
    generator = ReportGenerator()
    
    # Report 1: Full Reconciliation
    with st.container():
        st.markdown("#### 1. Complete Reconciliation Report")
        st.write("Detailed CSV report with all transactions and reconciliation results")
        
        full_csv = generator.generate_full_reconciliation_csv(results_df, summary)
        
        st.download_button(
            "📥 Download Full Report (CSV)",
            full_csv,
            f"reconciliation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Report 2: Exceptions Only
    with st.container():
        st.markdown("#### 2. Exceptions Report")
        st.write("CSV report containing only discrepancies and exceptions")
        
        exceptions_csv = generator.generate_exceptions_csv(results_df, summary)
        
        st.download_button(
            "📥 Download Exceptions Report (CSV)",
            exceptions_csv,
            f"exceptions_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Report 3: Executive Summary
    with st.container():
        st.markdown("#### 3. Executive Summary")
        st.write("Formatted text summary with key metrics and financial overview")
        
        summary_text = generator.generate_summary_report(summary, rounding)
        
        # Show preview
        with st.expander("Preview Summary Report"):
            st.text(summary_text)
        
        st.download_button(
            "📥 Download Summary Report (TXT)",
            summary_text,
            f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "text/plain",
            use_container_width=True
        )


def render_about():
    """Render the about/assumptions page"""
    st.title("ℹ️ About PayFlow Recon")
    
    st.markdown("""
    ## Intelligent Payment Reconciliation System
    
    PayFlow Recon automates the reconciliation of internal payment transactions with bank settlement records,
    identifying discrepancies and providing actionable insights for finance teams.
    
    ### 🎯 Key Features
    
    - **Automated Matching**: Intelligent matching of transactions with settlements
    - **Duplicate Detection**: Identifies duplicate entries in both datasets
    - **Timing Analysis**: Detects period-end timing differences
    - **Refund Validation**: Validates refund references against original transactions
    - **Rounding Variance**: Analyzes both individual and aggregate rounding differences
    - **Financial Precision**: Uses Decimal arithmetic for accurate financial calculations
    - **Professional Reports**: Generates downloadable CSV and text reports
    
    ---
    
    ### 📋 Business Assumptions
    
    **Accounting Period:** November 1-30, 2026
    
    **Currency:** INR (Indian Rupees)
    
    **Matching Logic:**
    - Transaction IDs are the primary matching keys
    - Payments are recorded immediately upon occurrence
    - Bank settlements typically occur 1-2 days after transaction
    - Refunds must reference an existing original transaction
    
    **Tolerances:**
    - Individual rounding tolerance: ₹0.01
    - Aggregate rounding threshold: ₹0.02
    
    **Duplicate Handling:**
    - Duplicates are identified before matching
    - Duplicate copies are excluded from financial totals
    - First occurrence is retained for matching
    
    ---
    
    ### 🔍 Reconciliation Statuses
    
    - **MATCHED**: Transaction and settlement match perfectly
    - **TIMING_DIFFERENCE**: Transaction settled outside accounting period
    - **AMOUNT_MISMATCH**: Significant difference in amounts
    - **MISSING_SETTLEMENT**: Transaction has no bank settlement
    - **UNMATCHED_BANK_ENTRY**: Bank settlement has no transaction record
    - **DUPLICATE_TRANSACTION_ENTRY**: Duplicate in transaction file
    - **DUPLICATE_BANK_ENTRY**: Duplicate in settlement file
    - **UNMATCHED_REFUND**: Refund references non-existent transaction
    
    ---
    
    ### 👥 Contact & Support
    
    For technical support or questions about reconciliation results, please contact your finance operations team.
    
    **Version:** 1.0.0  
    **Built for:** Onelab AI Fitness Assessment  
    **Technology:** Python, Streamlit, Pandas, Plotly
    """)


def main():
    """Main application"""
    initialize_session_state()
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Render selected page
    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "🔄 Reconciliation":
        render_reconciliation()
    elif page == "📊 Transactions":
        render_transactions()
    elif page == "⚠️ Exceptions":
        render_exceptions()
    elif page == "📥 Reports":
        render_reports()
    elif page == "ℹ️ About":
        render_about()


if __name__ == "__main__":
    main()
