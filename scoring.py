"""
Enhanced Multi-Criteria Scoring System for AI Procurement Agent
Implements weighted scoring with vendor preference bonuses
"""

from typing import List
import statistics
from models import Candidate, UserProfile


class ScoringEngine:
    """
    Multi-objective scoring engine that combines:
    - Cost fitness (α): Lower price relative to alternatives
    - Evidence quality (β): Scientific validation strength
    - Availability (γ): Stock and delivery reliability
    - Vendor preference bonus
    """
    
    def __init__(self):
        self.score_statistics = {}
    
    def compute_scores(self, cands: List[Candidate], user: UserProfile) -> List[Candidate]:
        """
        Main scoring pipeline:
        1. Compute individual dimension scores
        2. Apply vendor preference bonuses
        3. Calculate weighted total score
        4. Rank candidates by total score
        
        Args:
            cands: List of candidates to score
            user: User profile with weights and preferences
            
        Returns:
            Sorted list of candidates (best first)
        """
        if not cands:
            return []
        
        # Step 1: Compute cost fitness (relative to group median)
        self._compute_cost_fitness(cands, user)
        
        # Step 2: Evidence scores already computed in evidence.py
        # Just normalize if needed
        self._normalize_evidence_scores(cands)
        
        # Step 3: Availability scores already computed in rules.py (R4)
        # No additional processing needed
        
        # Step 4: Apply vendor preference bonus
        self._apply_vendor_bonus(cands, user)
        
        # Step 5: Calculate weighted total score
        self._compute_total_scores(cands, user)
        
        # Step 6: Rank by total score (descending)
        cands.sort(key=lambda x: x.total_score, reverse=True)
        
        # Step 7: Collect statistics for monitoring
        self._collect_statistics(cands)
        
        return cands
    
    def _compute_cost_fitness(self, cands: List[Candidate], user: UserProfile):
        """
        Compute cost fitness relative to group median.
        
        Strategy:
        - Items at/below median get higher scores
        - Over-budget items already have cost_fitness=0 from R2
        - Uses harmonic mean to reward significantly cheaper options
        """
        prices = [c.item.price for c in cands if c.item.price > 0]
        
        if not prices:
            # No valid prices, set all to 0.5
            for c in cands:
                if c.cost_fitness == 0:  # Don't override R2 penalties
                    continue
                c.cost_fitness = 0.5
            return
        
        median_price = statistics.median(prices)
        
        for c in cands:
            # Skip if already penalized by R2 (over budget)
            if "over_budget" in c.flags:
                continue
            
            price = c.item.price
            
            if price <= 0:
                c.cost_fitness = 0.0
                continue
            
            # Fitness formula: cheaper = better
            # At median: fitness = 0.5
            # At half median: fitness approaches 1.0
            # At double median: fitness approaches 0.0
            
            ratio = price / median_price
            
            if ratio <= 1.0:
                # Below or at median: linear increase
                c.cost_fitness = 0.5 + (1.0 - ratio) * 0.5
            else:
                # Above median: exponential decay
                c.cost_fitness = 0.5 / ratio
            
            # Clamp to [0, 1]
            c.cost_fitness = max(0.0, min(1.0, c.cost_fitness))
    
    def _normalize_evidence_scores(self, cands: List[Candidate]):
        """
        Ensure evidence scores are in [0, 1] range.
        Already computed by evidence.py, just validate.
        """
        for c in cands:
            c.evidence_score = max(0.0, min(1.0, c.evidence_score))
    
    def _apply_vendor_bonus(self, cands: List[Candidate], user: UserProfile):
        """
        Apply bonus to preferred vendors.
        Bonus is applied as a multiplier to the final score.
        """
        if not user.preferred_vendors:
            return
        
        preferred_bonus = 1.10  # 10% bonus for preferred vendors
        
        for c in cands:
            if c.item.vendor in user.preferred_vendors:
                # Mark it with a note in rationales
                if "preferred_vendor" not in c.flags:
                    c.add_flag("preferred_vendor")
                
                # Store bonus for later application
                # (will be applied in total score calculation)
                c.normalized["vendor_bonus"] = preferred_bonus
            else:
                c.normalized["vendor_bonus"] = 1.0
    
    def _compute_total_scores(self, cands: List[Candidate], user: UserProfile):
        """
        Compute weighted total score using user-defined weights.
        
        Formula:
        total_score = (α·cost + β·evidence + γ·availability) × vendor_bonus
        
        Where α + β + γ = 1.0 (validated in UserProfile)
        """
        alpha = user.weights.get("alpha_cost", 0.35)
        beta = user.weights.get("beta_evidence", 0.45)
        gamma = user.weights.get("gamma_availability", 0.20)
        
        for c in cands:
            # Base weighted score
            base_score = (
                alpha * c.cost_fitness +
                beta * c.evidence_score +
                gamma * c.availability_score
            )
            
            # Apply vendor bonus
            vendor_bonus = c.normalized.get("vendor_bonus", 1.0)
            c.total_score = base_score * vendor_bonus
            
            # Round for readability
            c.total_score = round(c.total_score, 4)
            
            # Add scoring explanation to rationales
            self._add_score_explanation(c, alpha, beta, gamma, base_score, vendor_bonus)
    
    def _add_score_explanation(
        self,
        c: Candidate,
        alpha: float,
        beta: float,
        gamma: float,
        base_score: float,
        vendor_bonus: float
    ):
        """Add detailed scoring breakdown to rationales"""
        explanation = (
            f"SCORING: ({alpha:.2f}×{c.cost_fitness:.2f}) + "
            f"({beta:.2f}×{c.evidence_score:.2f}) + "
            f"({gamma:.2f}×{c.availability_score:.2f}) = {base_score:.3f}"
        )
        
        if vendor_bonus > 1.0:
            explanation += f" × {vendor_bonus:.2f} (preferred vendor bonus)"
        
        explanation += f" → Total: {c.total_score:.4f}"
        
        c.rationales.append(explanation)
    
    def _collect_statistics(self, cands: List[Candidate]):
        """Collect statistics for monitoring and debugging"""
        if not cands:
            return
        
        scores = [c.total_score for c in cands]
        cost_scores = [c.cost_fitness for c in cands]
        evidence_scores = [c.evidence_score for c in cands]
        availability_scores = [c.availability_score for c in cands]
        
        self.score_statistics = {
            "total_candidates": len(cands),
            "total_score": {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "min": min(scores),
                "max": max(scores),
                "stdev": statistics.stdev(scores) if len(scores) > 1 else 0
            },
            "cost_fitness": {
                "mean": statistics.mean(cost_scores),
                "median": statistics.median(cost_scores)
            },
            "evidence": {
                "mean": statistics.mean(evidence_scores),
                "median": statistics.median(evidence_scores)
            },
            "availability": {
                "mean": statistics.mean(availability_scores),
                "median": statistics.median(availability_scores)
            }
        }
    
    def get_statistics(self) -> dict:
        """Return scoring statistics for analysis"""
        return self.score_statistics


def compute_scores(cands: List[Candidate], user: UserProfile) -> List[Candidate]:
    """
    Legacy function signature for backward compatibility.
    Uses ScoringEngine internally.
    
    Args:
        cands: List of candidates
        user: User profile with weights
        
    Returns:
        Sorted candidates with computed scores
    """
    engine = ScoringEngine()
    return engine.compute_scores(cands, user)