"""
Test script for improved scoring.py
Run with: python test_scoring.py
"""

from models import UserProfile, Candidate, SupplierItem
from scoring import ScoringEngine, compute_scores


def create_test_candidate(sku: str, vendor: str, price: float, stock: int, eta_days: int) -> Candidate:
    """Helper to create test candidates"""
    item = SupplierItem(
        sku=sku,
        vendor=vendor,
        name=f"Product {sku}",
        spec_text="Test specification",
        unit="mL",
        pack_size=100,
        price=price,
        stock=stock,
        eta_days=eta_days
    )
    return Candidate(item=item)


def test_cost_fitness_calculation():
    """Test cost fitness relative to median"""
    print("\n🧪 Test: Cost Fitness Calculation")
    
    user = UserProfile(query="test", budget=200.0)
    
    # Create candidates with different prices
    # Median will be 100
    candidates = [
        create_test_candidate("C1", "VendorA", 50.0, 10, 3),   # Cheap
        create_test_candidate("C2", "VendorB", 100.0, 10, 3),  # Median
        create_test_candidate("C3", "VendorC", 150.0, 10, 3),  # Expensive
    ]
    
    # Set some baseline scores
    for c in candidates:
        c.evidence_score = 0.5
        c.availability_score = 1.0
    
    engine = ScoringEngine()
    result = engine.compute_scores(candidates, user)
    
    # Verify: cheaper should have higher cost_fitness
    assert result[0].item.price == 50.0, "First should be cheapest"
    
    cheap = next(c for c in result if c.item.price == 50.0)
    median = next(c for c in result if c.item.price == 100.0)
    expensive = next(c for c in result if c.item.price == 150.0)
    
    assert cheap.cost_fitness > median.cost_fitness, "Cheap should beat median"
    assert median.cost_fitness > expensive.cost_fitness, "Median should beat expensive"
    
    print(f"✅ Cost fitness funciona correctamente")
    print(f"   - €50:  cost_fitness={cheap.cost_fitness:.3f}")
    print(f"   - €100: cost_fitness={median.cost_fitness:.3f}")
    print(f"   - €150: cost_fitness={expensive.cost_fitness:.3f}")
    
    return True


def test_vendor_bonus():
    """Test preferred vendor bonus"""
    print("\n🧪 Test: Vendor Preference Bonus")
    
    user = UserProfile(
        query="test",
        budget=200.0,
        preferred_vendors=["PreferredVendor"]
    )
    
    # Two identical products, one from preferred vendor
    candidates = [
        create_test_candidate("P1", "PreferredVendor", 100.0, 10, 3),
        create_test_candidate("P2", "OtherVendor", 100.0, 10, 3),
    ]
    
    # Set identical baseline scores
    for c in candidates:
        c.evidence_score = 0.7
        c.availability_score = 1.0
        c.cost_fitness = 0.5
    
    engine = ScoringEngine()
    result = engine.compute_scores(candidates, user)
    
    preferred = next(c for c in result if c.item.vendor == "PreferredVendor")
    other = next(c for c in result if c.item.vendor == "OtherVendor")
    
    # Preferred should score higher due to bonus
    assert preferred.total_score > other.total_score, "Preferred vendor should score higher"
    assert "preferred_vendor" in preferred.flags, "Should flag preferred vendor"
    
    # Bonus should be approximately 10%
    bonus_ratio = preferred.total_score / other.total_score
    assert 1.09 < bonus_ratio < 1.11, f"Bonus should be ~10%, got {bonus_ratio:.3f}"
    
    print(f"✅ Vendor bonus funciona correctamente")
    print(f"   - Preferido: total_score={preferred.total_score:.4f}")
    print(f"   - Otro:      total_score={other.total_score:.4f}")
    print(f"   - Bonus ratio: {bonus_ratio:.3f} (~10%)")
    
    return True


def test_weighted_scoring():
    """Test weighted combination of scores"""
    print("\n🧪 Test: Weighted Score Calculation")
    
    # Custom weights: prioritize evidence over cost
    user = UserProfile(
        query="test",
        budget=200.0,
        weights={
            "alpha_cost": 0.2,
            "beta_evidence": 0.6,
            "gamma_availability": 0.2
        }
    )
    
    # Candidate A: cheap but low evidence
    # Price: 50 (median will be 100, so cost_fitness will be ~0.75)
    cand_a = create_test_candidate("A1", "VendorA", 50.0, 10, 3)
    cand_a.evidence_score = 0.3
    cand_a.availability_score = 1.0
    
    # Candidate B: expensive but high evidence
    # Price: 150 (above median, so cost_fitness will be ~0.33)
    cand_b = create_test_candidate("B1", "VendorB", 150.0, 10, 3)
    cand_b.evidence_score = 0.9
    cand_b.availability_score = 1.0
    
    candidates = [cand_a, cand_b]
    
    engine = ScoringEngine()
    result = engine.compute_scores(candidates, user)
    
    # With 60% weight on evidence, B should win despite being more expensive
    assert result[0].item.sku == "B1", "High-evidence candidate should win"
    
    # Get actual computed values
    result_a = next(c for c in result if c.item.sku == "A1")
    result_b = next(c for c in result if c.item.sku == "B1")
    
    # Verify the calculation matches the formula
    # Note: cost_fitness is computed by the engine based on median
    expected_a = 0.2 * result_a.cost_fitness + 0.6 * 0.3 + 0.2 * 1.0
    expected_b = 0.2 * result_b.cost_fitness + 0.6 * 0.9 + 0.2 * 1.0
    
    assert abs(result_a.total_score - expected_a) < 0.01, \
        f"Score A mismatch: {result_a.total_score} vs {expected_a}"
    assert abs(result_b.total_score - expected_b) < 0.01, \
        f"Score B mismatch: {result_b.total_score} vs {expected_b}"
    
    # B should win because evidence weight is high (60%)
    assert result_b.total_score > result_a.total_score, \
        "High evidence should win with β=0.6"
    
    print(f"✅ Weighted scoring funciona correctamente")
    print(f"   - Weights: α=0.2, β=0.6, γ=0.2")
    print(f"   - A (cheap €50, low evidence 0.3):")
    print(f"     cost_fitness={result_a.cost_fitness:.3f}, total={result_a.total_score:.4f}")
    print(f"   - B (expensive €150, high evidence 0.9):")
    print(f"     cost_fitness={result_b.cost_fitness:.3f}, total={result_b.total_score:.4f}")
    print(f"   - Winner: {result[0].item.sku} (evidence prioritized)")
    
    return True


def test_ranking():
    """Test that candidates are properly ranked"""
    print("\n🧪 Test: Candidate Ranking")
    
    user = UserProfile(query="test", budget=200.0)
    
    # Create 5 candidates with varying scores
    candidates = []
    for i in range(5):
        c = create_test_candidate(f"C{i}", "Vendor", 100.0, 10, 3)
        c.cost_fitness = 0.5 + (i * 0.1)
        c.evidence_score = 0.3 + (i * 0.15)
        c.availability_score = 0.6 + (i * 0.1)
        candidates.append(c)
    
    engine = ScoringEngine()
    result = engine.compute_scores(candidates, user)
    
    # Verify descending order
    for i in range(len(result) - 1):
        assert result[i].total_score >= result[i+1].total_score, \
            f"Should be sorted: {result[i].total_score} >= {result[i+1].total_score}"
    
    print(f"✅ Ranking funciona correctamente")
    print(f"   - Scores: {[f'{c.total_score:.3f}' for c in result]}")
    print(f"   - Order: descending ✓")
    
    return True


def test_statistics_collection():
    """Test that statistics are collected"""
    print("\n🧪 Test: Statistics Collection")
    
    user = UserProfile(query="test", budget=200.0)
    
    candidates = [
        create_test_candidate("C1", "VendorA", 50.0, 10, 3),
        create_test_candidate("C2", "VendorB", 100.0, 10, 3),
        create_test_candidate("C3", "VendorC", 150.0, 10, 3),
    ]
    
    for c in candidates:
        c.evidence_score = 0.5
        c.availability_score = 1.0
    
    engine = ScoringEngine()
    engine.compute_scores(candidates, user)
    
    stats = engine.get_statistics()
    
    # Verify statistics structure
    assert "total_candidates" in stats
    assert stats["total_candidates"] == 3
    assert "total_score" in stats
    assert "mean" in stats["total_score"]
    assert "median" in stats["total_score"]
    
    print(f"✅ Statistics collection funciona")
    print(f"   - Candidates: {stats['total_candidates']}")
    print(f"   - Mean score: {stats['total_score']['mean']:.3f}")
    print(f"   - Median score: {stats['total_score']['median']:.3f}")
    
    return True


def test_edge_cases():
    """Test edge cases"""
    print("\n🧪 Test: Edge Cases")
    
    user = UserProfile(query="test", budget=100.0)
    
    # Empty list
    result_empty = compute_scores([], user)
    assert result_empty == [], "Empty list should return empty"
    print("   ✓ Empty list handled")
    
    # Single candidate
    single = [create_test_candidate("S1", "VendorX", 50.0, 10, 3)]
    single[0].evidence_score = 0.7
    single[0].availability_score = 1.0
    result_single = compute_scores(single, user)
    assert len(result_single) == 1
    assert result_single[0].total_score > 0
    print(f"   ✓ Single candidate: score={result_single[0].total_score:.3f}")
    
    # Over-budget candidate (should have cost_fitness=0 from rules)
    expensive = create_test_candidate("E1", "VendorY", 200.0, 10, 3)
    expensive.flags.append("over_budget")
    expensive.cost_fitness = 0.0  # Set by R2
    expensive.evidence_score = 0.9
    expensive.availability_score = 1.0
    
    result_expensive = compute_scores([expensive], user)
    assert result_expensive[0].total_score < 0.7, "Over-budget should score low despite high evidence"
    print(f"   ✓ Over-budget candidate: score={result_expensive[0].total_score:.3f}")
    
    print(f"✅ Edge cases manejados correctamente")
    return True


def run_all_tests():
    """Run all scoring tests"""
    print("="*60)
    print("📊 TESTING IMPROVED SCORING.PY")
    print("="*60)
    
    results = [
        test_cost_fitness_calculation(),
        test_vendor_bonus(),
        test_weighted_scoring(),
        test_ranking(),
        test_statistics_collection(),
        test_edge_cases()
    ]
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"📊 RESULTADOS: {passed}/{total} tests pasados")
    
    if passed == total:
        print("✅ ¡TODOS LOS TESTS DE SCORING PASARON!")
    else:
        print(f"⚠️  {total - passed} test(s) fallaron")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()