"""
Test script for improved models.py
Run with: python test_models.py
"""

from models import UserProfile, Quote, Candidate, SupplierItem

def test_valid_user():
    """Test 1: UserProfile con pesos válidos"""
    print("\n🧪 Test 1: UserProfile válido")
    try:
        user = UserProfile(
            query="DNA polymerase",
            budget=200.0,
            weights={"alpha_cost": 0.35, "beta_evidence": 0.45, "gamma_availability": 0.20}
        )
        print(f"✅ User creado: {user.query}, Budget: €{user.budget}")
        print(f"   Pesos: α={user.weights['alpha_cost']}, β={user.weights['beta_evidence']}, γ={user.weights['gamma_availability']}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_weights():
    """Test 2: Pesos inválidos (debe fallar)"""
    print("\n🧪 Test 2: Validación de pesos (debe rechazar suma != 1.0)")
    try:
        bad_user = UserProfile(
            query="Test",
            budget=100,
            weights={"alpha_cost": 0.5, "beta_evidence": 0.3, "gamma_availability": 0.1}  # suma 0.9
        )
        print(f"❌ FALLO: Debería haber rechazado pesos que suman {sum(bad_user.weights.values())}")
        return False
    except ValueError as e:
        print(f"✅ Validación funciona correctamente: {e}")
        return True

def test_negative_budget():
    """Test 3: Budget negativo (debe fallar)"""
    print("\n🧪 Test 3: Validación de budget negativo")
    try:
        bad_user = UserProfile(
            query="Test",
            budget=-50.0,
            weights={"alpha_cost": 0.4, "beta_evidence": 0.4, "gamma_availability": 0.2}
        )
        print(f"❌ FALLO: Debería haber rechazado budget negativo")
        return False
    except ValueError as e:
        print(f"✅ Validación funciona: {e}")
        return True

def test_candidate_helpers():
    """Test 4: Métodos helper de Candidate"""
    print("\n🧪 Test 4: Candidate con métodos helper")
    try:
        item = SupplierItem(
            sku="ABC123",
            vendor="BioSupplier A",
            name="Taq DNA Polymerase",
            spec_text="High fidelity, 5 U/µL",
            unit="mL",
            pack_size=100,
            price=50.0,
            stock=10,
            eta_days=5
        )
        
        candidate = Candidate(item=item)
        candidate.add_rationale("R1", "Spec OK → normalized")
        candidate.add_rationale("R2", "Within budget")
        candidate.add_flag("preferred_vendor")
        candidate.add_flag("preferred_vendor")  # Intentar duplicado
        
        print(f"✅ Candidate creado: {candidate.item.name}")
        print(f"   Rationales ({len(candidate.rationales)}): {candidate.rationales}")
        print(f"   Flags ({len(candidate.flags)}): {candidate.flags}")
        
        # Verificar que no hay duplicados en flags
        if len(candidate.flags) == 1:
            print(f"✅ Los duplicados de flags se previenen correctamente")
        else:
            print(f"⚠️  Advertencia: flags tiene duplicados")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_quote_creation():
    """Test 5: Crear un Quote completo"""
    print("\n🧪 Test 5: Quote completo")
    try:
        user = UserProfile(
            query="PCR reagents",
            budget=150.0
        )
        
        item1 = SupplierItem(
            sku="PCR001",
            vendor="VendorX",
            name="PCR Master Mix",
            spec_text="2x concentrated",
            unit="mL",
            pack_size=50,
            price=120.0,
            stock=5,
            eta_days=3
        )
        
        candidate1 = Candidate(item=item1)
        candidate1.add_rationale("R2", "Within budget")
        candidate1.total_score = 0.85
        
        quote = Quote(
            user=user,
            candidates=[candidate1],
            selected=candidate1,
            notes="Test quote generated successfully"
        )
        
        print(f"✅ Quote creado:")
        print(f"   Query: {quote.user.query}")
        print(f"   Candidatos: {len(quote.candidates)}")
        print(f"   Seleccionado: {quote.selected.item.name if quote.selected else 'None'}")
        print(f"   Generado: {quote.generated_at}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Ejecuta todos los tests"""
    print("="*60)
    print("🧬 TESTING IMPROVED MODELS.PY")
    print("="*60)
    
    results = [
        test_valid_user(),
        test_invalid_weights(),
        test_negative_budget(),
        test_candidate_helpers(),
        test_quote_creation()
    ]
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"📊 RESULTADOS: {passed}/{total} tests pasados")
    
    if passed == total:
        print("✅ ¡TODOS LOS TESTS PASARON!")
    else:
        print(f"⚠️  {total - passed} test(s) fallaron")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()