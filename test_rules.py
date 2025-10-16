"""
Test script for improved rules.py
Run with: python test_rules.py
"""

from models import UserProfile, Candidate, SupplierItem
from rules import RuleEngine, apply_rules


def test_r1_spec_validation():
    """Test R1: Specification validation"""
    print("\n🧪 Test R1: Specification Validation")
    
    user = UserProfile(query="test", budget=100.0)
    
    # Case 1: Missing spec
    item_no_spec = SupplierItem(
        sku="TEST001",
        vendor="VendorA",
        name="Product Without Spec",
        spec_text="",  # Missing!
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    # Case 2: Valid spec
    item_with_spec = SupplierItem(
        sku="TEST002",
        vendor="VendorA",
        name="Product With Spec",
        spec_text="High quality, 99% purity",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    candidates = [
        Candidate(item=item_no_spec, evidence_score=0.5),
        Candidate(item=item_with_spec, evidence_score=0.5)
    ]
    
    engine = RuleEngine()
    result = engine.apply_rules(candidates, user)
    
    # Verify
    assert "spec_missing" in result[0].flags, "Should flag missing spec"
    assert "spec_missing" not in result[1].flags, "Should not flag valid spec"
    assert result[0].evidence_score < 0.3, f"Should penalize (got {result[0].evidence_score})"
    assert result[1].evidence_score > 0.5, f"Should reward (got {result[1].evidence_score})"
    
    print(f"✅ R1 funciona correctamente")
    print(f"   - Sin spec: flags={result[0].flags}, evidence={result[0].evidence_score:.2f}")
    print(f"   - Con spec: flags={result[1].flags}, evidence={result[1].evidence_score:.2f}")
    return True


def test_r2_budget_compliance():
    """Test R2: Budget compliance"""
    print("\n🧪 Test R2: Budget Compliance")
    
    user = UserProfile(query="test", budget=100.0)
    
    # Case 1: Over budget
    item_expensive = SupplierItem(
        sku="EXP001",
        vendor="VendorA",
        name="Expensive Product",
        spec_text="Premium",
        unit="mL",
        pack_size=100,
        price=150.0,  # Over budget!
        stock=10,
        eta_days=3
    )
    
    # Case 2: Within budget
    item_affordable = SupplierItem(
        sku="AFF001",
        vendor="VendorA",
        name="Affordable Product",
        spec_text="Standard",
        unit="mL",
        pack_size=100,
        price=80.0,
        stock=10,
        eta_days=3
    )
    
    candidates = [
        Candidate(item=item_expensive),
        Candidate(item=item_affordable)
    ]
    
    engine = RuleEngine()
    result = engine.apply_rules(candidates, user)
    
    # Verify
    assert "over_budget" in result[0].flags, "Should flag over-budget item"
    assert result[0].cost_fitness == 0.0, "Over-budget should have 0 cost_fitness"
    assert "over_budget" not in result[1].flags, "Should not flag within-budget item"
    assert result[1].cost_fitness > 0, "Within budget should have positive cost_fitness"
    
    print(f"✅ R2 funciona correctamente")
    print(f"   - Caro (€150): flags={result[0].flags}, cost_fitness={result[0].cost_fitness:.2f}")
    print(f"   - Barato (€80): flags={result[1].flags}, cost_fitness={result[1].cost_fitness:.2f}")
    return True


def test_r3_evidence_quality():
    """Test R3: Evidence quality threshold"""
    print("\n🧪 Test R3: Evidence Quality")
    
    user = UserProfile(query="test", budget=100.0)
    
    item = SupplierItem(
        sku="TEST001",
        vendor="VendorA",
        name="Test Product",
        spec_text="Valid spec",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    # Case 1: Low evidence
    candidate_low = Candidate(item=item, evidence_score=0.1)
    
    # Case 2: High evidence
    candidate_high = Candidate(item=item, evidence_score=0.8)
    
    engine = RuleEngine()
    result = engine.apply_rules([candidate_low, candidate_high], user)
    
    # Verify
    assert "low_evidence" in result[0].flags, "Should flag low evidence"
    assert "low_evidence" not in result[1].flags, "Should not flag high evidence"
    
    print(f"✅ R3 funciona correctamente")
    print(f"   - Evidencia baja (0.1): flags={result[0].flags}")
    print(f"   - Evidencia alta (0.8): flags={result[1].flags}")
    return True


def test_r4_availability():
    """Test R4: Stock and availability"""
    print("\n🧪 Test R4: Availability Check")
    
    user = UserProfile(query="test", budget=100.0, deadline_days=7)
    
    # Case 1: Out of stock
    item_oos = SupplierItem(
        sku="OOS001",
        vendor="VendorA",
        name="Out of Stock",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=0,  # Out of stock!
        eta_days=3
    )
    
    # Case 2: In stock, fast delivery
    item_fast = SupplierItem(
        sku="FAST001",
        vendor="VendorA",
        name="Fast Delivery",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3  # Within deadline
    )
    
    # Case 3: In stock, slow delivery
    item_slow = SupplierItem(
        sku="SLOW001",
        vendor="VendorA",
        name="Slow Delivery",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=5,
        eta_days=15  # Beyond deadline
    )
    
    candidates = [
        Candidate(item=item_oos),
        Candidate(item=item_fast),
        Candidate(item=item_slow)
    ]
    
    engine = RuleEngine()
    result = engine.apply_rules(candidates, user)
    
    # Verify
    assert "out_of_stock" in result[0].flags, "Should flag OOS"
    assert result[0].availability_score == 0.0, "OOS should have 0 availability"
    assert result[1].availability_score == 1.0, "Fast delivery should have 1.0"
    assert 0 < result[2].availability_score < 1.0, "Slow delivery should be penalized"
    
    print(f"✅ R4 funciona correctamente")
    print(f"   - Sin stock: availability={result[0].availability_score:.2f}")
    print(f"   - Rápido (3d): availability={result[1].availability_score:.2f}")
    print(f"   - Lento (15d): availability={result[2].availability_score:.2f}")
    return True


def test_r5_preferred_vendors():
    """Test R5: Policy learning (preferred vendors)"""
    print("\n🧪 Test R5: Preferred Vendors")
    
    user = UserProfile(
        query="test",
        budget=100.0,
        preferred_vendors=["PreferredVendor"]
    )
    
    item_preferred = SupplierItem(
        sku="PREF001",
        vendor="PreferredVendor",
        name="From Preferred",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    item_other = SupplierItem(
        sku="OTHER001",
        vendor="OtherVendor",
        name="From Other",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    candidates = [
        Candidate(item=item_preferred),
        Candidate(item=item_other)
    ]
    
    engine = RuleEngine()
    result = engine.apply_rules(candidates, user)
    
    # Verify
    assert "preferred_vendor" in result[0].flags, "Should flag preferred vendor"
    assert "preferred_vendor" not in result[1].flags, "Should not flag other vendor"
    
    print(f"✅ R5 funciona correctamente")
    print(f"   - Preferido: flags={result[0].flags}")
    print(f"   - Otro: flags={result[1].flags}")
    return True


def test_engine_summary():
    """Test RuleEngine summary/logging"""
    print("\n🧪 Test: Engine Summary")
    
    user = UserProfile(query="test", budget=100.0)
    item = SupplierItem(
        sku="TEST001",
        vendor="TestVendor",
        name="Test",
        spec_text="Valid",
        unit="mL",
        pack_size=100,
        price=50.0,
        stock=10,
        eta_days=3
    )
    
    engine = RuleEngine()
    engine.apply_rules([Candidate(item=item)], user)
    
    summary = engine.get_summary()
    
    assert summary["total_rules_fired"] == 5, "Should fire all 5 rules"
    assert len(summary["execution_log"]) == 5, "Should log all executions"
    
    print(f"✅ Engine summary funciona")
    print(f"   - Reglas ejecutadas: {summary['total_rules_fired']}")
    print(f"   - Log entries: {len(summary['execution_log'])}")
    return True


def run_all_tests():
    """Run all rule tests"""
    print("="*60)
    print("⚙️  TESTING IMPROVED RULES.PY")
    print("="*60)
    
    results = [
        test_r1_spec_validation(),
        test_r2_budget_compliance(),
        test_r3_evidence_quality(),
        test_r4_availability(),
        test_r5_preferred_vendors(),
        test_engine_summary()
    ]
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"📊 RESULTADOS: {passed}/{total} tests pasados")
    
    if passed == total:
        print("✅ ¡TODOS LOS TESTS DE RULES PASARON!")
    else:
        print(f"⚠️  {total - passed} test(s) fallaron")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()