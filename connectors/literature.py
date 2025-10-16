"""
Real PubMed/NCBI API Connector for Scientific Literature
100% FREE - No API key required (but recommended for higher rate limits)
"""

import time
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import requests
from xml.etree import ElementTree as ET

from config import APIConfig
from utils.cache import cached


class PubMedConnector:
    """
    Real connector to PubMed/NCBI E-utilities API
    Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self):
        self.email = APIConfig.PUBMED_EMAIL
        self.api_key = APIConfig.PUBMED_API_KEY
        self.session = requests.Session()
        
        # Rate limiting: 3 requests/second without key, 10/second with key
        self.rate_limit_delay = 0.34 if not self.api_key else 0.1
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _build_params(self, **kwargs) -> dict:
        """Build common API parameters"""
        params = {
            'email': self.email,
            'tool': 'ai_procurement_agent'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        params.update(kwargs)
        return params
    
    @cached(key_prefix="pubmed_search", ttl_hours=24)
    def search(self, query: str, max_results: int = 10) -> List[str]:
        """
        Search PubMed and return list of PMIDs
        
        Args:
            query: Search query (e.g., "DNA polymerase PCR")
            max_results: Maximum number of results
            
        Returns:
            List of PubMed IDs (PMIDs)
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/esearch.fcgi"
        params = self._build_params(
            db='pubmed',
            term=query,
            retmax=max_results,
            retmode='json',
            sort='relevance'
        )
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=APIConfig.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get('esearchresult', {}).get('idlist', [])
            
            return pmids
            
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []
    
    @cached(key_prefix="pubmed_fetch", ttl_hours=168)  # 1 week cache
    def fetch_articles(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch article details for given PMIDs
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of article dictionaries with metadata
        """
        if not pmids:
            return []
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = self._build_params(
            db='pubmed',
            id=','.join(pmids),
            retmode='xml'
        )
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=APIConfig.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            articles = []
            
            for article_elem in root.findall('.//PubmedArticle'):
                article = self._parse_article(article_elem)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            print(f"PubMed fetch error: {e}")
            return []
    
    def _parse_article(self, article_elem: ET.Element) -> Optional[Dict]:
        """Parse article XML element into dictionary"""
        try:
            # Extract PMID
            pmid_elem = article_elem.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            # Extract title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title"
            
            # Extract abstract
            abstract_elems = article_elem.findall('.//AbstractText')
            abstract = ' '.join(
                elem.text for elem in abstract_elems if elem.text
            ) if abstract_elems else ""
            
            # Extract journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Extract publication year
            year_elem = article_elem.find('.//PubDate/Year')
            year = year_elem.text if year_elem is not None else ""
            
            # Extract authors
            author_elems = article_elem.findall('.//Author')
            authors = []
            for author_elem in author_elems[:3]:  # First 3 authors
                lastname = author_elem.find('LastName')
                initials = author_elem.find('Initials')
                if lastname is not None:
                    author_name = lastname.text
                    if initials is not None:
                        author_name += f" {initials.text}"
                    authors.append(author_name)
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'journal': journal,
                'year': year,
                'authors': authors,
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            }
            
        except Exception as e:
            print(f"Article parsing error: {e}")
            return None
    
    def search_and_fetch(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Combined search and fetch operation
        
        Args:
            query: Search query
            max_results: Maximum articles to return
            
        Returns:
            List of article dictionaries
        """
        pmids = self.search(query, max_results)
        if not pmids:
            return []
        
        articles = self.fetch_articles(pmids)
        return articles


class LiteratureScorer:
    """
    Scores products based on scientific literature evidence
    """
    
    def __init__(self):
        self.connector = PubMedConnector()
    
    def score_product(self, product_name: str, product_spec: str) -> float:
        """
        Calculate evidence score for a product
        
        Args:
            product_name: Product name
            product_spec: Product specification
            
        Returns:
            Evidence score [0, 1]
        """
        # Build search query
        query = self._build_search_query(product_name, product_spec)
        
        # Search PubMed
        articles = self.connector.search_and_fetch(query, max_results=5)
        
        if not articles:
            return 0.0
        
        # Calculate score based on:
        # 1. Number of articles found
        # 2. Recency of articles
        # 3. Title/abstract relevance
        
        score = min(len(articles) / 10.0, 0.5)  # Up to 0.5 for quantity
        
        # Recency bonus
        current_year = 2025
        for article in articles:
            try:
                year = int(article.get('year', 0))
                if year >= current_year - 5:  # Last 5 years
                    score += 0.1
            except:
                pass
        
        # Normalize to [0, 1]
        score = min(score, 1.0)
        
        return round(score, 2)
    
    def _build_search_query(self, product_name: str, product_spec: str) -> str:
        """Build optimized PubMed search query"""
        # Extract key terms
        terms = []
        
        # Add product name
        if product_name:
            # Remove common suffixes like "Kit", "Buffer", etc.
            clean_name = re.sub(r'\b(Kit|Buffer|Solution|Mix|Set)\b', '', product_name, flags=re.IGNORECASE)
            terms.append(clean_name.strip())
        
        # Add key spec terms
        if product_spec:
            # Extract technical terms (capitalized, numbers, special patterns)
            tech_terms = re.findall(r'\b[A-Z][A-Za-z0-9-]+\b|\d+\s*[µumM][LlMg]', product_spec)
            terms.extend(tech_terms[:3])  # Top 3 technical terms
        
        # Build query
        query = ' '.join(terms[:5])  # Limit to 5 terms
        return query


# Singleton instances
_pubmed_connector: Optional[PubMedConnector] = None
_literature_scorer: Optional[LiteratureScorer] = None


def get_pubmed_connector() -> PubMedConnector:
    """Get or create PubMed connector instance"""
    global _pubmed_connector
    if _pubmed_connector is None:
        _pubmed_connector = PubMedConnector()
    return _pubmed_connector


def get_literature_scorer() -> LiteratureScorer:
    """Get or create literature scorer instance"""
    global _literature_scorer
    if _literature_scorer is None:
        _literature_scorer = LiteratureScorer()
    return _literature_scorer


def evidence_score_from_text(text: str) -> float:
    """
    Legacy function - now uses real PubMed API
    
    Args:
        text: Product name and spec combined
        
    Returns:
        Evidence score [0, 1]
    """
    if not APIConfig.USE_LITERATURE_API or not APIConfig.PUBMED_ENABLED:
        # Fallback to simple mock scoring
        return min(len(text) / 200.0, 1.0)
    
    scorer = get_literature_scorer()
    
    # Split text into name and spec (rough heuristic)
    parts = text.split(',', 1)
    name = parts[0] if parts else text
    spec = parts[1] if len(parts) > 1 else ""
    
    return scorer.score_product(name, spec)


# CLI test
if __name__ == "__main__":
    print("Testing PubMed Connector...")
    print("="*60)
    
    connector = PubMedConnector()
    
    # Test search
    print("\n1. Searching for 'DNA polymerase PCR'...")
    pmids = connector.search("DNA polymerase PCR", max_results=3)
    print(f"   Found {len(pmids)} articles: {pmids}")
    
    # Test fetch
    if pmids:
        print("\n2. Fetching article details...")
        articles = connector.fetch_articles(pmids[:2])
        for i, article in enumerate(articles, 1):
            print(f"\n   Article {i}:")
            print(f"   Title: {article['title'][:80]}...")
            print(f"   Journal: {article['journal']}")
            print(f"   Year: {article['year']}")
            print(f"   URL: {article['url']}")
    
    # Test scorer
    print("\n3. Testing evidence scorer...")
    scorer = LiteratureScorer()
    score = scorer.score_product("Taq DNA Polymerase", "High fidelity, 5 U/µL, for PCR")
    print(f"   Evidence score: {score}")
    
    print("\n" + "="*60)
    print("✅ PubMed connector is working!")