"""
Hybrid Supplier Connector
Combines mock database with real SerpAPI search
"""

import re
from typing import List
from pathlib import Path
from models import SupplierItem
from config import APIConfig


class HybridSupplierConnector:
    """
    Combines multiple data sources:
    1. SerpAPI (real online search) - if enabled
    2. Mock database (fallback)
    3. CSV cache (legacy)
    """
    
    def __init__(self):
        self.mock_database = self._create_mock_database()
    
    def search_suppliers(self, query: str) -> List[SupplierItem]:
        """
        Search for suppliers using hybrid approach
        
        Priority:
        1. SerpAPI (if enabled and USE_WEB_SEARCH is true)
        2. Mock database
        3. CSV fallback
        
        Args:
            query: Search query
            
        Returns:
            List of matching supplier items
        """
        query_lower = query.lower().strip()
        
        if not query_lower:
            return []
        
        results = []
        
        # Strategy 1: Try SerpAPI first (real products)
        if APIConfig.SERPAPI_ENABLED and APIConfig.USE_WEB_SEARCH:
            try:
                from connectors.serp_connector import search_products_online
                print(f"🌐 Searching online via SerpAPI: '{query}'")
                serp_results = search_products_online(query, max_results=5)
                results.extend(serp_results)
                print(f"   Found {len(serp_results)} online products")
            except Exception as e:
                print(f"⚠️  SerpAPI search failed: {e}")
        
        # Strategy 2: Add mock database results
        mock_results = self._search_mock_database(query_lower)
        results.extend(mock_results)
        print(f"🗄️  Found {len(mock_results)} products from mock database")
        
        # Strategy 3: Try CSV as last resort
        if not results:
            csv_results = self._search_csv(query_lower)
            results.extend(csv_results)
            if csv_results:
                print(f"📄 Found {len(csv_results)} products from CSV")
        
        # Remove duplicates based on vendor + name
        results = self._deduplicate_items(results)
        
        print(f"✅ Total unique products found: {len(results)}")
        
        return results
    
    def _deduplicate_items(self, items: List[SupplierItem]) -> List[SupplierItem]:
        """Remove duplicate items based on vendor + name"""
        seen = set()
        unique = []
        
        for item in items:
            key = (item.vendor.lower(), item.name.lower())
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique
    
    def _search_mock_database(self, query: str) -> List[SupplierItem]:
        """Search mock database"""
        matches = []
        
        for item in self.mock_database:
            item_text = f"{item.name} {item.spec_text}".lower()
            
            # Simple keyword matching
            query_words = query.split()
            match_score = sum(1 for word in query_words if word in item_text)
            
            if match_score > 0:
                matches.append((match_score, item))
        
        # Sort by relevance and return top 10
        matches.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in matches[:10]]
    
    def _search_csv(self, query: str) -> List[SupplierItem]:
        """Fallback: search CSV file"""
        csv_path = Path("data/sample_suppliers.csv")
        
        if not csv_path.exists():
            return []
        
        try:
            import csv
            results = []
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    item_text = f"{row.get('name', '')} {row.get('spec_text', '')}".lower()
                    if query in item_text:
                        results.append(SupplierItem(
                            sku=row['sku'],
                            vendor=row['vendor'],
                            name=row['name'],
                            spec_text=row.get('spec_text', ''),
                            unit=row.get('unit', 'unit'),
                            pack_size=float(row.get('pack_size', 1)),
                            price=float(row.get('price', 0)),
                            currency=row.get('currency', 'EUR'),
                            stock=int(row.get('stock', 0)),
                            eta_days=int(row.get('eta_days', 7))
                        ))
            
            return results
        except Exception as e:
            print(f"CSV read error: {e}")
            return []
    
    def _create_mock_database(self) -> List[SupplierItem]:
        """Create comprehensive mock database"""
        
        products = [
            # DNA/RNA reagents
            {
                "sku": "TAQ-001", "vendor": "ThermoFisher Scientific",
                "name": "Taq DNA Polymerase", 
                "spec": "High fidelity, 5 U/µL, for PCR amplification",
                "unit": "mL", "pack": 1.0, "price": 89.50, "stock": 25, "eta": 3
            },
            {
                "sku": "DNAP-500", "vendor": "New England Biolabs",
                "name": "Q5 High-Fidelity DNA Polymerase",
                "spec": "Ultra-high fidelity, hot-start, 2x master mix",
                "unit": "mL", "pack": 0.5, "price": 145.00, "stock": 18, "eta": 2
            },
            {
                "sku": "POL-300", "vendor": "Promega",
                "name": "GoTaq DNA Polymerase",
                "spec": "Standard Taq for routine PCR, 5 U/µL",
                "unit": "mL", "pack": 1.0, "price": 65.00, "stock": 40, "eta": 5
            },
            {
                "sku": "RNA-KIT-001", "vendor": "Qiagen",
                "name": "RNeasy Mini Kit",
                "spec": "RNA extraction, 50 preps, includes columns and buffers",
                "unit": "kit", "pack": 1.0, "price": 220.00, "stock": 12, "eta": 4
            },
            {
                "sku": "RT-PCR-200", "vendor": "Bio-Rad",
                "name": "iScript Reverse Transcription Kit",
                "spec": "cDNA synthesis, for RT-PCR, 100 reactions",
                "unit": "kit", "pack": 1.0, "price": 180.00, "stock": 8, "eta": 6
            },
            
            # PCR reagents
            {
                "sku": "PCR-MIX-100", "vendor": "ThermoFisher Scientific",
                "name": "PCR Master Mix 2X",
                "spec": "Ready-to-use mix with buffer, dNTPs, MgCl2, Taq",
                "unit": "mL", "pack": 5.0, "price": 125.00, "stock": 30, "eta": 2
            },
            {
                "sku": "DNTPS-SET", "vendor": "Sigma-Aldrich",
                "name": "dNTP Set 100mM",
                "spec": "dATP, dCTP, dGTP, dTTP, molecular biology grade",
                "unit": "mL", "pack": 4.0, "price": 95.00, "stock": 22, "eta": 3
            },
            {
                "sku": "PRIM-KIT-50", "vendor": "IDT",
                "name": "Custom PCR Primers",
                "spec": "Desalted, 25nmol scale, custom sequence",
                "unit": "tube", "pack": 2.0, "price": 45.00, "stock": 100, "eta": 7
            },
            
            # Enzymes
            {
                "sku": "REST-ECO-100", "vendor": "New England Biolabs",
                "name": "EcoRI Restriction Enzyme",
                "spec": "20,000 units/mL, high concentration",
                "unit": "mL", "pack": 0.5, "price": 78.00, "stock": 15, "eta": 3
            },
            {
                "sku": "LIG-T4-50", "vendor": "Promega",
                "name": "T4 DNA Ligase",
                "spec": "High concentration, 3 U/µL, for cloning",
                "unit": "µL", "pack": 100.0, "price": 92.00, "stock": 20, "eta": 4
            },
            
            # Proteins
            {
                "sku": "BSA-100G", "vendor": "Sigma-Aldrich",
                "name": "Bovine Serum Albumin (BSA)",
                "spec": "Fraction V, 98% purity, molecular biology grade",
                "unit": "g", "pack": 100.0, "price": 85.00, "stock": 50, "eta": 2
            },
            {
                "sku": "AB-GAPDH", "vendor": "Cell Signaling Technology",
                "name": "GAPDH Antibody",
                "spec": "Rabbit monoclonal, WB/IHC validated, 1:1000",
                "unit": "mL", "pack": 0.1, "price": 320.00, "stock": 8, "eta": 10
            },
            
            # Cell culture
            {
                "sku": "DMEM-500", "vendor": "Gibco",
                "name": "DMEM Medium",
                "spec": "High glucose, with L-glutamine, without pyruvate",
                "unit": "mL", "pack": 500.0, "price": 45.00, "stock": 60, "eta": 2
            },
            {
                "sku": "FBS-500ML", "vendor": "Gibco",
                "name": "Fetal Bovine Serum (FBS)",
                "spec": "Heat inactivated, South American origin",
                "unit": "mL", "pack": 500.0, "price": 380.00, "stock": 15, "eta": 5
            },
            {
                "sku": "PBS-1L", "vendor": "Lonza",
                "name": "Phosphate Buffered Saline (PBS)",
                "spec": "1X, pH 7.4, sterile filtered",
                "unit": "L", "pack": 1.0, "price": 28.00, "stock": 80, "eta": 2
            },
        ]
        
        # Convert to SupplierItem objects
        items = []
        for p in products:
            items.append(SupplierItem(
                sku=p["sku"],
                vendor=p["vendor"],
                name=p["name"],
                spec_text=p["spec"],
                unit=p["unit"],
                pack_size=p["pack"],
                price=p["price"],
                currency="EUR",
                stock=p["stock"],
                eta_days=p["eta"]
            ))
        
        return items


# Singleton instance
_connector = HybridSupplierConnector()

def search_suppliers_expanded(query: str, expanded_queries: List[str]) -> List[SupplierItem]:
    """
    Search using multiple expanded queries and combine results
    
    Args:
        query: Original query
        expanded_queries: List of expanded search terms
        
    Returns:
        Combined and deduplicated list of supplier items
    """
    all_results = []
    
    print(f"🔍 Searching with {len(expanded_queries)} expanded queries:")
    for i, exp_query in enumerate(expanded_queries, 1):
        print(f"   {i}. '{exp_query}'")
        results = _connector.search_suppliers(exp_query)
        all_results.extend(results)
    
    # Deduplicate
    unique_results = _connector._deduplicate_items(all_results)
    
    print(f"✅ Found {len(all_results)} total → {len(unique_results)} unique products")
    
    return unique_results


def search_suppliers(query: str) -> List[SupplierItem]:
    """
    Main entry point for supplier search
    
    Args:
        query: Search query
        
    Returns:
        List of matching supplier items
    """
    return _connector.search_suppliers(query)