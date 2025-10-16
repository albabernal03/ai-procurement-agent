"""
LLM Agent for Intelligent Reasoning
Uses Groq API (free) for semantic analysis and natural language generation
"""

from typing import List, Dict, Optional
from groq import Groq
from config import APIConfig
from models import Candidate, UserProfile, Quote


class LLMAgent:
    """
    Intelligent agent that uses LLM for:
    1. Query analysis and expansion
    2. Natural language explanations
    3. Alternative suggestions
    4. Implicit need detection
    """
    
    def __init__(self):
        self.enabled = APIConfig.GROQ_ENABLED
        if self.enabled:
            self.client = Groq(api_key=APIConfig.GROQ_API_KEY)
            self.model = "llama-3.3-70b-versatile"  # Modelo actualizado
        else:
            self.client = None
            self.model = None
    
    def analyze_query(self, query: str, user: UserProfile) -> Dict[str, any]:
        """
        Analyze user query to extract intent and requirements
        
        Args:
            query: User's search query
            user: User profile with constraints
            
        Returns:
            Dictionary with analysis results
        """
        if not self.enabled:
            return {
                "original_query": query,
                "expanded_queries": [query],
                "detected_needs": [],
                "recommended_specs": [],
                "warnings": []
            }
        
        prompt = f"""You are an expert in laboratory procurement and life sciences.

    User Query: "{query}"
    Budget: €{user.budget}
    Deadline: {user.deadline_days} days

    Analyze this query and provide:
    1. Expanded search terms (synonyms, related products, alternative names)
    2. Implicit needs (what else might they need?)
    3. Important specifications to look for
    4. Potential compatibility concerns

    Respond in JSON format:
    {{
    "expanded_queries": ["term1", "term2", "term3", "term4"],
    "implicit_needs": ["need1", "need2"],
    "key_specs": ["spec1", "spec2"],
    "warnings": ["warning1"]
    }}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            import re
            content = response.choices[0].message.content
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            result = json.loads(content)
            
            # Ensure original query is included
            expanded = result.get("expanded_queries", [])
            if query not in expanded:
                expanded.insert(0, query)
            
            return {
                "original_query": query,
                "expanded_queries": expanded[:5],  # Max 5 queries
                "detected_needs": result.get("implicit_needs", [])[:3],
                "recommended_specs": result.get("key_specs", [])[:5],
                "warnings": result.get("warnings", [])
            }
            
        except Exception as e:
            print(f"⚠️  LLM query analysis failed: {e}")
            return {
                "original_query": query,
                "expanded_queries": [query],
                "detected_needs": [],
                "recommended_specs": [],
                "warnings": []
            }
    
    def generate_explanation(self, candidate: Candidate, user: UserProfile, rank: int) -> str:
        """
        Generate natural language explanation for why this product was recommended
        
        Args:
            candidate: The product candidate
            user: User profile
            rank: Position in ranking (1 = best)
            
        Returns:
            Human-readable explanation
        """
        if not self.enabled:
            # Fallback to rule-based explanation
            return self._fallback_explanation(candidate, user, rank)
        
        prompt = f"""You are explaining a product recommendation to a laboratory researcher.

Product: {candidate.item.name}
Vendor: {candidate.item.vendor}
Price: €{candidate.item.price}
User Budget: €{user.budget}

Scores:
- Cost fitness: {candidate.cost_fitness:.2f}/1.0
- Scientific evidence: {candidate.evidence_score:.2f}/1.0
- Availability: {candidate.availability_score:.2f}/1.0
- Total score: {candidate.total_score:.4f}

Ranking: #{rank} out of multiple options

Flags: {', '.join(candidate.flags) if candidate.flags else 'None'}

Write a concise (2-3 sentences) professional explanation of why this product is ranked #{rank}.
Focus on the most important factors. Be specific about trade-offs if any."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150
            )
            
            explanation = response.choices[0].message.content.strip()
            return explanation
            
        except Exception as e:
            print(f"⚠️  LLM explanation failed: {e}")
            return self._fallback_explanation(candidate, user, rank)
    
    def _fallback_explanation(self, candidate: Candidate, user: UserProfile, rank: int) -> str:
        """Fallback explanation when LLM is not available"""
        parts = []
        
        if rank == 1:
            parts.append("This is our top recommendation")
        else:
            parts.append(f"This is option #{rank}")
        
        # Highlight best score
        scores = {
            "cost-effectiveness": candidate.cost_fitness,
            "scientific evidence": candidate.evidence_score,
            "availability": candidate.availability_score
        }
        best_aspect = max(scores.items(), key=lambda x: x[1])
        parts.append(f"with excellent {best_aspect[0]} (score: {best_aspect[1]:.2f})")
        
        # Mention flags
        if candidate.flags:
            parts.append(f"Note: {', '.join(candidate.flags)}")
        
        return ". ".join(parts) + "."
    
    def suggest_alternatives(self, selected: Candidate, all_candidates: List[Candidate], user: UserProfile) -> str:
        """
        Suggest alternative products and explain trade-offs
        
        Args:
            selected: The chosen product
            all_candidates: All available candidates
            user: User profile
            
        Returns:
            Natural language suggestion text
        """
        if not self.enabled or len(all_candidates) < 2:
            return ""
        
        # Get top 3 alternatives
        alternatives = [c for c in all_candidates[:4] if c != selected][:3]
        
        if not alternatives:
            return ""
        
        alt_summary = "\n".join([
            f"- {c.item.vendor} {c.item.name}: €{c.item.price} (score: {c.total_score:.2f})"
            for c in alternatives
        ])
        
        prompt = f"""You are helping a researcher understand their options.

Selected product: {selected.item.vendor} {selected.item.name} (€{selected.item.price})
User budget: €{user.budget}

Alternatives considered:
{alt_summary}

Write 1-2 sentences explaining when the researcher might want to consider the alternatives instead.
Focus on practical trade-offs (price vs quality, speed vs cost, etc.)."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️  LLM alternatives suggestion failed: {e}")
            return ""
    
    def generate_quote_summary(self, quote: Quote) -> str:
        """
        Generate executive summary of the entire quotation
        
        Args:
            quote: Complete quote with all candidates
            
        Returns:
            Natural language summary
        """
        if not self.enabled or not quote.candidates:
            return quote.notes or "Quote generated successfully"
        
        prompt = f"""Summarize this procurement analysis for a lab manager.

Query: {quote.user.query}
Budget: €{quote.user.budget}
Options analyzed: {len(quote.candidates)}

Top recommendation: {quote.selected.item.name if quote.selected else 'None'}
Price: €{quote.selected.item.price if quote.selected else 0}
Total score: {quote.selected.total_score if quote.selected else 0:.2f}

Price range of all options: €{min(c.item.price for c in quote.candidates):.0f} - €{max(c.item.price for c in quote.candidates):.0f}

Write a 2-3 sentence executive summary highlighting the key finding and any important considerations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️  LLM summary failed: {e}")
            return quote.notes or "Quote generated successfully"


# Singleton instance
_llm_agent: Optional[LLMAgent] = None


def get_llm_agent() -> LLMAgent:
    """Get or create LLM agent instance"""
    global _llm_agent
    if _llm_agent is None:
        _llm_agent = LLMAgent()
    return _llm_agent


# CLI test
if __name__ == "__main__":
    print("Testing LLM Agent...")
    print("="*60)
    
    if not APIConfig.GROQ_ENABLED:
        print("❌ Groq not enabled. Set GROQ_API_KEY in .env file")
        exit(1)
    
    agent = LLMAgent()
    
    # Test 1: Query analysis
    print("\n1. Testing query analysis...")
    from models import UserProfile
    user = UserProfile(query="DNA polymerase", budget=200.0, deadline_days=7)
    analysis = agent.analyze_query("DNA polymerase for PCR", user)
    
    print(f"   Original: {analysis['original_query']}")
    print(f"   Expanded: {analysis['expanded_queries']}")
    print(f"   Implicit needs: {analysis['detected_needs']}")
    print(f"   Key specs: {analysis['recommended_specs']}")
    
    # Test 2: Explanation generation
    print("\n2. Testing explanation generation...")
    from models import SupplierItem, Candidate
    
    item = SupplierItem(
        sku="TEST-001",
        vendor="ThermoFisher",
        name="Taq DNA Polymerase",
        spec_text="High fidelity",
        unit="mL",
        pack_size=1.0,
        price=89.50,
        stock=25,
        eta_days=3
    )
    
    candidate = Candidate(item=item)
    candidate.cost_fitness = 0.7
    candidate.evidence_score = 0.8
    candidate.availability_score = 1.0
    candidate.total_score = 0.75
    
    explanation = agent.generate_explanation(candidate, user, rank=1)
    print(f"   Explanation: {explanation}")
    
    print("\n" + "="*60)
    print("✅ LLM Agent is working!")