"""
Enhanced Orchestrator for AI Procurement Agent
Implements the full perception-reasoning-action pipeline from Task 2
"""

from typing import List
from pathlib import Path
from models import UserProfile, Candidate, Quote
from connectors.suppliers import search_suppliers
from normalizer import normalize_items
from evidence import attach_evidence_scores
from rules import RuleEngine
from scoring import ScoringEngine
from quotation import save_html_report
from llm_agent import get_llm_agent
from feedback_system import get_feedback_system

class ProcurementOrchestrator:
    """
    Main orchestrator implementing the 5-stage reasoning pipeline:
    1. Perceive and Retrieve Data
    2. Normalize and Structure Information
    3. Evaluate and Score Alternatives
    4. Generate and Explain Recommendation
    5. Learn and Refine through Feedback (placeholder)
    """
    
    def __init__(self, output_dir: Path = Path("./outputs")):
        self.output_dir = output_dir
        self.rule_engine = RuleEngine()
        self.scoring_engine = ScoringEngine()
        self.llm_agent = get_llm_agent()
        self.feedback_system = get_feedback_system()
        self.execution_metadata = {}
    
    def generate_quote(self, user: UserProfile) -> Quote:
        """
        Main entry point for quote generation.
        
        Args:
            user: User profile with requirements and constraints
            
        Returns:
            Complete quote with ranked candidates and selection
        """
        try:
            # ============================================================
            # STAGE 1: PERCEIVE AND RETRIEVE DATA
            # ============================================================
            items = self._perceive_supplier_data(user)
            
            if not items:
                return self._create_empty_quote(
                    user,
                    "No supplier matches found for the query"
                )
            
            # ============================================================
            # STAGE 2: NORMALIZE AND STRUCTURE INFORMATION
            # ============================================================
            candidates = self._normalize_and_structure(items)
            
            # ============================================================
            # STAGE 3: EVALUATE AND SCORE ALTERNATIVES
            # ============================================================
            candidates = self._evaluate_candidates(candidates, user)
            
            # ============================================================
            # STAGE 4: GENERATE AND EXPLAIN RECOMMENDATION
            # ============================================================
            quote = self._generate_recommendation(candidates, user)
            
            # ============================================================
            # STAGE 5: SAVE REPORT
            # ============================================================
            self._save_outputs(quote)
            
            return quote
            
        except Exception as e:
            # Handle any unexpected errors gracefully
            return self._create_error_quote(user, str(e))
    
    def _perceive_supplier_data(self, user: UserProfile) -> List:
        """
        Stage 1: Perceive and retrieve supplier data
        Uses LLM query expansion for better results
        """
        try:
            # Use LLM to analyze and expand query
            if self.llm_agent.enabled:
                print("🧠 Analyzing query with LLM...")
                query_analysis = self.llm_agent.analyze_query(user.query, user)
                
                expanded_queries = query_analysis.get("expanded_queries", [user.query])
                self.execution_metadata["query_analysis"] = query_analysis
                self.execution_metadata["expanded_queries"] = expanded_queries
                
                # Search with expanded queries
                from connectors.suppliers import search_suppliers_expanded
                items = search_suppliers_expanded(user.query, expanded_queries)
            else:
                # Fallback to simple search
                items = search_suppliers(user.query)
            
            self.execution_metadata["suppliers_found"] = len(items)
            return items
            
        except Exception as e:
            self.execution_metadata["supplier_error"] = str(e)
            raise Exception(f"Supplier connector error: {e}")
    
    def _normalize_and_structure(self, items: List) -> List[Candidate]:
        """
        Stage 2: Normalize and structure information
        Converts heterogeneous supplier data into structured candidates
        """
        candidates = normalize_items(items)
        self.execution_metadata["candidates_normalized"] = len(candidates)
        return candidates
    
    def _evaluate_candidates(self, candidates: List[Candidate], user: UserProfile) -> List[Candidate]:
        """
        Stage 3: Evaluate and score alternatives
        
        Substages:
        3.1. Attach evidence scores (P2: Literature Feed)
        3.2. Apply production rules (R1-R5)
        3.3. Compute multi-criteria scores
        """
        # 3.1: Evidence scoring
        candidates = attach_evidence_scores(candidates)
        self.execution_metadata["evidence_attached"] = True
        
        # 3.2: Rule-based reasoning
        candidates = self.rule_engine.apply_rules(candidates, user)
        self.execution_metadata["rules_fired"] = self.rule_engine.rules_fired
        self.execution_metadata["rule_log"] = self.rule_engine.get_summary()
        
        # 3.3: Multi-criteria scoring
        candidates = self.scoring_engine.compute_scores(candidates, user)
        self.execution_metadata["scoring_stats"] = self.scoring_engine.get_statistics()
        
        return candidates
    
    def _generate_recommendation(self, candidates: List[Candidate], user: UserProfile) -> Quote:
        """
        Stage 4: Generate and explain recommendation
        Selects best candidate and builds transparent quote with LLM explanations
        """
        # Select top candidate (already sorted by scoring engine)
        selected = candidates[0] if candidates else None
        
        # Use LLM to enhance explanations
        if self.llm_agent.enabled and candidates:
            print("🤖 Generating AI explanations...")
            
            # Generate explanation for top 3 candidates
            for i, candidate in enumerate(candidates[:3], 1):
                llm_explanation = self.llm_agent.generate_explanation(candidate, user, i)
                candidate.rationales.append(f"🤖 AI Analysis: {llm_explanation}")
            
            # Generate alternatives suggestion
            if selected and len(candidates) > 1:
                alternatives_text = self.llm_agent.suggest_alternatives(selected, candidates, user)
                if alternatives_text:
                    self.execution_metadata["alternatives_suggestion"] = alternatives_text
        
        # Build notes with execution summary
        notes = self._build_execution_notes()
        
        # Add LLM summary if available
        quote = Quote(
            user=user,
            candidates=candidates,
            selected=selected,
            notes=notes
        )
        
        # Generate overall summary with LLM
        if self.llm_agent.enabled:
            llm_summary = self.llm_agent.generate_quote_summary(quote)
            quote.notes = f"{llm_summary} | {notes}"
        
        return quote
    
    def _build_execution_notes(self) -> str:
        """Build human-readable execution summary"""
        notes = []
        
        if "suppliers_found" in self.execution_metadata:
            notes.append(f"Found {self.execution_metadata['suppliers_found']} supplier items")
        
        if "rules_fired" in self.execution_metadata:
            notes.append(f"Executed {self.execution_metadata['rules_fired']} production rules")
        
        if "scoring_stats" in self.execution_metadata:
            stats = self.execution_metadata["scoring_stats"]
            if "total_score" in stats:
                notes.append(
                    f"Score range: {stats['total_score']['min']:.3f} - "
                    f"{stats['total_score']['max']:.3f} "
                    f"(mean: {stats['total_score']['mean']:.3f})"
                )
        
        if "alternatives_suggestion" in self.execution_metadata:
            notes.append(f"💡 {self.execution_metadata['alternatives_suggestion']}")
        
        return " | ".join(notes) if notes else "Quote generated successfully"
        
    def _save_outputs(self, quote: Quote):
        """Save HTML report and collect metrics"""
        save_html_report(quote, self.output_dir)
        self.execution_metadata["report_saved"] = True
    
    def _create_empty_quote(self, user: UserProfile, reason: str) -> Quote:
        """Create empty quote with explanation"""
        quote = Quote(
            user=user,
            candidates=[],
            selected=None,
            notes=reason
        )
        save_html_report(quote, self.output_dir)
        return quote
    
    def _create_error_quote(self, user: UserProfile, error: str) -> Quote:
        """Create error quote for exception handling"""
        quote = Quote(
            user=user,
            candidates=[],
            selected=None,
            notes=f"Error during quote generation: {error}"
        )
        save_html_report(quote, self.output_dir)
        return quote
    
    def get_execution_metadata(self) -> dict:
        """Return execution metadata for monitoring/debugging"""
        return self.execution_metadata


# Legacy function for backward compatibility
def generate_quote(user: UserProfile) -> Quote:
    """
    Legacy function signature maintained for backward compatibility.
    Uses ProcurementOrchestrator internally.
    
    Args:
        user: User profile with requirements
        
    Returns:
        Complete quote
    """
    orchestrator = ProcurementOrchestrator()
    return orchestrator.generate_quote(user)