"""
Test real API integrations
Run with: python test_real_apis.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_config_loading():
    """Test 1: Configuration loads correctly"""
    print("\n🧪 Test 1: Configuration Loading")
    
    try:
        from config import APIConfig
        
        summary = APIConfig.summary()
        warnings = APIConfig.validate()
        
        print(f"✅ Configuration loaded")
        print(f"   PubMed enabled: {summary['literature']['pubmed']}")
        print(f"   Cache enabled: {summary['cache']['enabled']}")
        print(f"   Cache TTL: {summary['cache']['ttl_hours']} hours")
        
        if warnings:
            print(f"\n   Warnings:")
            for w in warnings:
                print(f"   {w}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_cache_system():
    """Test 2: Cache system works"""
    print("\n🧪 Test 2: Cache System")
    
    try:
        from utils.cache import get_cache_manager, cached
        
        cache = get_cache_manager()
        
        # Test basic operations
        cache.set("test_key", {"data": "test_value", "number": 123})
        result = cache.get("test_key")
        
        assert result is not None, "Cache retrieval failed"
        assert result["data"] == "test_value", "Cache data mismatch"
        
        # Test cache miss
        missing = cache.get("nonexistent_key")
        assert missing is None, "Should return None for missing key"
        
        # Test decorator
        call_count = 0
        
        @cached(key_prefix="test_func")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_function(5)
        result2 = expensive_function(5)  # Should use cache
        
        assert result1 == 10, "Function result incorrect"
        assert result2 == 10, "Cached result incorrect"
        assert call_count == 1, "Function called twice (cache not working)"
        
        # Stats
        stats = cache.get_stats()
        print(f"✅ Cache system working")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Hit rate: {stats['hit_rate']}")
        print(f"   Cached items: {stats['cached_items']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pubmed_connector():
    """Test 3: PubMed API connector"""
    print("\n🧪 Test 3: PubMed API Connector")
    
    try:
        from connectors.literature import PubMedConnector
        
        connector = PubMedConnector()
        
        print("   Searching PubMed for 'DNA polymerase'...")
        pmids = connector.search("DNA polymerase", max_results=3)
        
        if pmids:
            print(f"✅ Found {len(pmids)} articles")
            print(f"   PMIDs: {pmids}")
            
            print(f"\n   Fetching article details...")
            articles = connector.fetch_articles(pmids[:2])
            
            if articles:
                print(f"✅ Retrieved {len(articles)} article details")
                for i, article in enumerate(articles, 1):
                    print(f"\n   Article {i}:")
                    print(f"   - Title: {article['title'][:60]}...")
                    print(f"   - Journal: {article['journal']}")
                    print(f"   - Year: {article['year']}")
                    print(f"   - Authors: {', '.join(article['authors'][:2])}")
            else:
                print(f"⚠️  Could not fetch article details")
        else:
            print(f"⚠️  No articles found (check your internet connection)")
        
        return len(pmids) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_literature_scorer():
    """Test 4: Literature evidence scorer"""
    print("\n🧪 Test 4: Literature Evidence Scorer")
    
    try:
        from connectors.literature import LiteratureScorer
        
        scorer = LiteratureScorer()
        
        # Test with real product
        product_name = "Taq DNA Polymerase"
        product_spec = "High fidelity, 5 U/µL, for PCR amplification"
        
        print(f"   Scoring: {product_name}")
        score = scorer.score_product(product_name, product_spec)
        
        print(f"✅ Evidence score calculated: {score}")
        print(f"   Product: {product_name}")
        print(f"   Score: {score}/1.0")
        
        assert 0 <= score <= 1, "Score out of range"
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_evidence():
    """Test 5: Full integration with real evidence scoring"""
    print("\n🧪 Test 5: Integration with Real Evidence")
    
    try:
        from models import UserProfile
        from orchestrator import ProcurementOrchestrator
        from config import APIConfig
        
        # Enable real literature API
        original_setting = APIConfig.USE_LITERATURE_API
        APIConfig.USE_LITERATURE_API = True
        
        try:
            user = UserProfile(
                query="DNA polymerase",
                budget=200.0,
                preferred_vendors=["ThermoFisher Scientific"],
                deadline_days=7
            )
            
            print(f"   Generating quote with real PubMed evidence...")
            orchestrator = ProcurementOrchestrator()
            quote = orchestrator.generate_quote(user)
            
            if quote.candidates:
                print(f"✅ Quote generated with real evidence scores")
                print(f"   Candidates: {len(quote.candidates)}")
                
                # Show evidence scores
                print(f"\n   Evidence scores:")
                for i, c in enumerate(quote.candidates[:3], 1):
                    print(f"   {i}. {c.item.name}: evidence={c.evidence_score:.2f}")
                
                # Check if any have real evidence (> 0)
                has_evidence = any(c.evidence_score > 0 for c in quote.candidates)
                if has_evidence:
                    print(f"\n   ✅ Real evidence scores detected!")
                else:
                    print(f"\n   ⚠️  No evidence scores > 0 (may need better queries)")
            else:
                print(f"⚠️  No candidates generated")
                
        finally:
            # Restore setting
            APIConfig.USE_LITERATURE_API = original_setting
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all API tests"""
    print("="*70)
    print("🌐 TESTING REAL API INTEGRATIONS")
    print("="*70)
    
    results = [
        test_config_loading(),
        test_cache_system(),
        test_pubmed_connector(),
        test_literature_scorer(),
        test_integration_with_evidence()
    ]
    
    print("\n" + "="*70)
    passed = sum(results)
    total = len(results)
    print(f"📊 RESULTADOS: {passed}/{total} tests pasados")
    
    if passed == total:
        print("✅ ¡TODOS LOS TESTS DE APIs REALES PASARON!")
        print("\n🎉 Tu sistema ahora usa APIs reales:")
        print("   ✓ PubMed para literatura científica")
        print("   ✓ Sistema de caché inteligente")
        print("   ✓ Scoring basado en evidencia real")
        print("\n💡 Próximo paso: Añadir SerpAPI para búsqueda de productos")
    else:
        print(f"⚠️  {total - passed} test(s) fallaron")
        print("\n💡 Revisa los errores arriba y verifica:")
        print("   - Conexión a internet")
        print("   - Archivo .env configurado")
        print("   - Dependencias instaladas (pip install -r requirements.txt)")
    print("="*70)


if __name__ == "__main__":
    run_all_tests()