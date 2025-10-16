"""
SerpAPI Connector for Real Product Search
Searches Google Shopping for lab supplies and reagents
"""

import re
from typing import List, Dict, Optional
import requests
from urllib.parse import quote_plus

from config import APIConfig
from utils.cache import cached
from models import SupplierItem


class SerpAPIConnector:
    """
    Connector to SerpAPI for Google Shopping search
    Documentation: https://serpapi.com/google-shopping-api
    """
    
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self):
        self.api_key = APIConfig.SERPAPI_KEY
        self.enabled = APIConfig.SERPAPI_ENABLED
        self.session = requests.Session()
    
    @cached(key_prefix="serp_search", ttl_hours=48)
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search Google Shopping for products
        
        Args:
            query: Search query (e.g., "Taq DNA Polymerase lab")
            max_results: Maximum number of results
            
        Returns:
            List of product dictionaries
        """
        if not self.enabled:
            print("⚠️  SerpAPI not enabled - returning empty results")
            return []
        
        params = {
            'api_key': self.api_key,
            'engine': 'google_shopping',
            'q': query,
            'num': min(max_results, 20),  # SerpAPI max is 20
            'gl': 'us',  # Geographic location
            'hl': 'en'   # Language
        }
        
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=APIConfig.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract shopping results
            products = data.get('shopping_results', [])
            
            return products[:max_results]
            
        except Exception as e:
            print(f"SerpAPI search error: {e}")
            return []
    
    def convert_to_supplier_items(self, products: List[Dict], query: str) -> List[SupplierItem]:
        """
        Convert SerpAPI results to SupplierItem objects
        
        Args:
            products: Raw SerpAPI product results
            query: Original search query
            
        Returns:
            List of SupplierItem objects
        """
        items = []
        
        for product in products:
            try:
                item = self._parse_product(product, query)
                if item:
                    items.append(item)
            except Exception as e:
                print(f"Error parsing product: {e}")
                continue
        
        return items
    
    def _parse_product(self, product: Dict, query: str) -> Optional[SupplierItem]:
        """Parse a single product from SerpAPI into SupplierItem"""
        
        # Extract basic info
        title = product.get('title', 'Unknown Product')
        price_str = product.get('price', '0')
        link = product.get('link', '')
        source = product.get('source', 'Unknown Vendor')
        
        # Parse price (remove currency symbols and convert)
        price = self._parse_price(price_str)
        
        # Generate SKU from product info
        sku = self._generate_sku(product)
        
        # Extract or infer specifications
        spec_text = self._extract_specifications(product, title)
        
        # Extract unit and pack size
        unit, pack_size = self._extract_unit_and_size(title, spec_text)
        
        # Estimate stock and ETA (not available from Google Shopping)
        stock = self._estimate_stock(product)
        eta_days = self._estimate_eta(source)
        
        return SupplierItem(
            sku=sku,
            vendor=source,
            name=title,
            spec_text=spec_text,
            unit=unit,
            pack_size=pack_size,
            price=price,
            currency='EUR',  # Convert if needed
            stock=stock,
            eta_days=eta_days
        )
    
    def _parse_price(self, price_str: str) -> float:
        """Extract numeric price from string"""
        try:
            # Remove currency symbols and convert to float
            clean_price = re.sub(r'[^\d.,]', '', str(price_str))
            # Handle European format (comma as decimal)
            clean_price = clean_price.replace(',', '.')
            return float(clean_price)
        except:
            return 0.0
    
    def _generate_sku(self, product: Dict) -> str:
        """Generate a SKU from product info"""
        position = product.get('position', 0)
        product_id = product.get('product_id', '')
        
        if product_id:
            return f"SERP-{product_id}"
        else:
            return f"SERP-{position:03d}"
    
    def _extract_specifications(self, product: Dict, title: str) -> str:
        """Extract specifications from product data"""
        specs = []
        
        # Extract from title
        title_lower = title.lower()
        
        # Look for common lab specs
        patterns = [
            r'\d+\s*[µumM][LlMg]',  # Volume/mass
            r'\d+\s*U/[µumM]L',      # Enzyme units
            r'\d+\s*%',              # Percentage
            r'\d+\s*reactions?',     # Reaction count
            r'\d+\s*preps?',         # Prep count
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            specs.extend(matches)
        
        # Check for highlights/snippets
        snippets = product.get('snippet', '')
        if snippets:
            specs.append(snippets)
        
        return ', '.join(specs[:3]) if specs else 'See product details'
    
    def _extract_unit_and_size(self, title: str, spec_text: str) -> tuple:
        """Extract unit and pack size from text"""
        combined_text = f"{title} {spec_text}".lower()
        
        # Look for volume patterns
        volume_match = re.search(r'(\d+\.?\d*)\s*(ml|l|µl|ul)', combined_text, re.IGNORECASE)
        if volume_match:
            size = float(volume_match.group(1))
            unit = volume_match.group(2).lower()
            
            # Normalize unit
            if unit in ['µl', 'ul']:
                return 'µL', size
            elif unit == 'ml':
                return 'mL', size
            elif unit == 'l':
                return 'L', size
        
        # Look for unit/mass patterns
        mass_match = re.search(r'(\d+\.?\d*)\s*(g|mg|kg)', combined_text, re.IGNORECASE)
        if mass_match:
            size = float(mass_match.group(1))
            unit = mass_match.group(2)
            return unit, size
        
        # Look for count patterns
        count_match = re.search(r'(\d+)\s*(reactions?|preps?|tests?|units?)', combined_text, re.IGNORECASE)
        if count_match:
            size = float(count_match.group(1))
            unit = count_match.group(2)
            return unit, size
        
        # Default
        return 'unit', 1.0
    
    def _estimate_stock(self, product: Dict) -> int:
        """Estimate stock availability"""
        # Google Shopping doesn't provide stock info
        # We'll estimate based on delivery info
        
        delivery = product.get('delivery', '').lower()
        
        if 'out of stock' in delivery or 'unavailable' in delivery:
            return 0
        elif 'limited' in delivery:
            return 5
        else:
            return 20  # Default assumption: available
    
    def _estimate_eta(self, vendor: str) -> int:
        """Estimate delivery time based on vendor"""
        vendor_lower = vendor.lower()
        
        # Known fast vendors
        fast_vendors = ['amazon', 'thermofisher', 'sigma']
        if any(v in vendor_lower for v in fast_vendors):
            return 2
        
        # Default
        return 5


# Singleton instance
_serp_connector: Optional[SerpAPIConnector] = None


def get_serp_connector() -> SerpAPIConnector:
    """Get or create SerpAPI connector instance"""
    global _serp_connector
    if _serp_connector is None:
        _serp_connector = SerpAPIConnector()
    return _serp_connector


def search_products_online(query: str, max_results: int = 10) -> List[SupplierItem]:
    """
    Search for products online using SerpAPI
    
    Args:
        query: Product search query
        max_results: Maximum results to return
        
    Returns:
        List of SupplierItem objects
    """
    connector = get_serp_connector()
    
    # Add "lab" or "laboratory" to query for better results
    enhanced_query = f"{query} laboratory reagent"
    
    products = connector.search_products(enhanced_query, max_results)
    items = connector.convert_to_supplier_items(products, query)
    
    return items


# CLI test
if __name__ == "__main__":
    print("Testing SerpAPI Connector...")
    print("="*60)
    
    if not APIConfig.SERPAPI_ENABLED:
        print("❌ SerpAPI not enabled. Set SERPAPI_KEY in .env file")
        exit(1)
    
    connector = SerpAPIConnector()
    
    # Test search
    print("\n1. Searching for 'Taq DNA Polymerase'...")
    products = connector.search_products("Taq DNA Polymerase lab", max_results=3)
    print(f"   Found {len(products)} products")
    
    if products:
        print("\n2. Converting to SupplierItem format...")
        items = connector.convert_to_supplier_items(products, "Taq DNA Polymerase")
        
        for i, item in enumerate(items, 1):
            print(f"\n   Product {i}:")
            print(f"   - Vendor: {item.vendor}")
            print(f"   - Name: {item.name[:60]}...")
            print(f"   - Price: €{item.price:.2f}")
            print(f"   - SKU: {item.sku}")
            print(f"   - Stock: {item.stock}")
    
    print("\n" + "="*60)
    print("✅ SerpAPI connector is working!")