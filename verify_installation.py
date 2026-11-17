"""
Quick verification script to ensure PayFlow Recon is correctly installed
"""

print("=" * 60)
print("PAYFLOW RECON - INSTALLATION VERIFICATION")
print("=" * 60)

# Test imports
print("\n1. Testing module imports...")
try:
    from data_loader import DataLoader
    from reconciliation import ReconciliationEngine
    from report_generator import ReportGenerator
    import app
    print("   ✓ All modules import successfully")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    exit(1)

# Test data loading
print("\n2. Testing data loading...")
try:
    loader = DataLoader()
    t = loader.load_transactions('transactions.csv')
    s = loader.load_settlements('settlements.csv')
    print(f"   ✓ Data loaded: {len(t)} transactions, {len(s)} settlements")
except Exception as e:
    print(f"   ✗ Loading failed: {e}")
    exit(1)

# Test reconciliation
print("\n3. Testing reconciliation...")
try:
    engine = ReconciliationEngine()
    r = engine.reconcile(t, s)
    print(f"   ✓ Reconciliation complete: {len(r['results'])} results")
    print(f"   ✓ Found {r['summary']['matched_count']} matches")
except Exception as e:
    print(f"   ✗ Reconciliation failed: {e}")
    exit(1)

# Test report generation
print("\n4. Testing report generation...")
try:
    gen = ReportGenerator()
    report = gen.generate_full_reconciliation_csv(r['results'], r['summary'])
    print(f"   ✓ Reports generated successfully ({len(report)} characters)")
except Exception as e:
    print(f"   ✗ Report generation failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✓ INSTALLATION VERIFIED")
print("=" * 60)
print("\nTo start the application, run:")
print("  streamlit run app.py")
print("")
