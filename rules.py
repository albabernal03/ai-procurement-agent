"""
Enhanced Rule Engine for AI Procurement Agent
Implements production rules R1-R5 with improved explainability and structure
"""

from typing import List
from models import Candidate, UserProfile


class RuleEngine:
    """
    Applies production rules to candidates with full traceability.
    Each rule follows the IF-THEN pattern described in Task 4.
    """
    
    def __init__(self):
        self.rules_fired = 0
        self.execution_log = []
    
    def apply_rules(self, cands: List[Candidate], user: UserProfile) -> List[Candidate]:
        """
        Main entry point: applies all production rules in priority order.
        
        Args:
            cands: List of candidates to evaluate
            user: User profile with constraints
            
        Returns:
            Filtered and annotated list of candidates
        """
        self.rules_fired = 0
        self.execution_log = []
        
        filtered: List[Candidate] = []
        
        for c in cands:
            # Apply rules in order (as defined in your document)
            self._apply_r1_spec_validation(c, user)
            self._apply_r2_budget_compliance(c, user)
            self._apply_r3_evidence_quality(c, user)
            self._apply_r4_availability_check(c, user)
            self._apply_r5_policy_learning(c, user)
            
            filtered.append(c)
        
        return filtered
    
    def _apply_r1_spec_validation(self, c: Candidate, user: UserProfile):
        """
        R1: Specification Validation
        IF spec_text missing THEN flag for clarification ELSE normalize
        """
        rule_id = "R1"
        
        if not c.item.spec_text or len(c.item.spec_text.strip()) == 0:
            c.add_flag("spec_missing")
            c.add_rationale(rule_id, "Missing spec → flagged for clarification")
            # Penalize evidence score
            c.evidence_score = max(0.0, c.evidence_score * 0.5)
            self._log_rule(rule_id, "violated", c.item.sku)
        else:
            c.add_rationale(rule_id, "Spec OK → normalized")
            # Small bonus for having complete spec
            c.evidence_score = min(1.0, c.evidence_score * 1.05)
            self._log_rule(rule_id, "passed", c.item.sku)
        
        self.rules_fired += 1
    
    def _apply_r2_budget_compliance(self, c: Candidate, user: UserProfile):
        """
        R2: Budget Compliance
        IF price > budget THEN search_substitute ELSE mark_as_candidate
        """
        rule_id = "R2"
        
        if c.item.price > user.budget:
            c.add_flag("over_budget")
            overage = c.item.price - user.budget
            c.add_rationale(
                rule_id,
                f"Price €{c.item.price:.2f} exceeds budget €{user.budget:.2f} "
                f"by €{overage:.2f} → substitute recommended"
            )
            # Zero cost fitness for over-budget items
            c.cost_fitness = 0.0
            self._log_rule(rule_id, "violated", c.item.sku)
        else:
            # Calculate cost fitness: closer to budget = lower score
            # Better value = higher score
            budget_usage = c.item.price / user.budget
            c.cost_fitness = max(0.0, 1.0 - budget_usage)
            
            c.add_rationale(
                rule_id,
                f"Within budget (€{c.item.price:.2f}/€{user.budget:.2f}) → "
                f"cost_fitness={c.cost_fitness:.2f}"
            )
            self._log_rule(rule_id, "passed", c.item.sku)
        
        self.rules_fired += 1
    
    def _apply_r3_evidence_quality(self, c: Candidate, user: UserProfile):
        """
        R3: Evidence Quality Threshold
        IF evidence_score < threshold THEN penalize ELSE reward
        """
        rule_id = "R3"
        threshold = user.weights.get("min_evidence_threshold", 0.2)
        
        if c.evidence_score < threshold:
            c.add_flag("low_evidence")
            c.add_rationale(
                rule_id,
                f"Evidence score {c.evidence_score:.2f} below threshold "
                f"{threshold:.2f} → penalized"
            )
            self._log_rule(rule_id, "flagged", c.item.sku)
        else:
            c.add_rationale(
                rule_id,
                f"Evidence score {c.evidence_score:.2f} meets threshold "
                f"{threshold:.2f} → approved"
            )
            self._log_rule(rule_id, "passed", c.item.sku)
        
        self.rules_fired += 1
    
    def _apply_r4_availability_check(self, c: Candidate, user: UserProfile):
        """
        R4: Stock and Delivery Validation
        IF out_of_stock THEN suggest_substitute ELSE calculate_availability_score
        """
        rule_id = "R4"
        
        if c.item.stock <= 0:
            c.add_flag("out_of_stock")
            c.availability_score = 0.0
            c.add_rationale(
                rule_id,
                f"Out of stock → availability_score=0, substitute suggested"
            )
            self._log_rule(rule_id, "violated", c.item.sku)
        else:
            # Calculate availability based on ETA vs deadline
            if c.item.eta_days <= user.deadline_days:
                c.availability_score = 1.0
            else:
                # Decay score for late deliveries
                delay = c.item.eta_days - user.deadline_days
                c.availability_score = max(0.0, 1.0 - (delay * 0.05))
            
            c.add_rationale(
                rule_id,
                f"In stock ({c.item.stock} units), ETA {c.item.eta_days}d → "
                f"availability_score={c.availability_score:.2f}"
            )
            self._log_rule(rule_id, "passed", c.item.sku)
        
        self.rules_fired += 1
    
    def _apply_r5_policy_learning(self, c: Candidate, user: UserProfile):
        """
        R5: Adaptive Policy Updates (placeholder for future RL)
        Currently logs that learning loop is pending implementation
        """
        rule_id = "R5"
        
        # Check if we have preferred vendors
        is_preferred = c.item.vendor in user.preferred_vendors
        
        if is_preferred:
            c.add_flag("preferred_vendor")
            c.add_rationale(
                rule_id,
                f"Vendor '{c.item.vendor}' is in preferred list → bonus applied"
            )
            # Small bonus to total score (will be applied in scoring phase)
            self._log_rule(rule_id, "passed", c.item.sku)
        else:
            c.add_rationale(
                rule_id,
                "Policy updates pending (feedback loop TBD)"
            )
            self._log_rule(rule_id, "neutral", c.item.sku)
        
        self.rules_fired += 1
    
    def _log_rule(self, rule_id: str, status: str, sku: str):
        """Internal logging for rule execution tracking"""
        self.execution_log.append({
            "rule": rule_id,
            "status": status,
            "sku": sku
        })
    
    def get_summary(self) -> dict:
        """Returns execution summary for debugging/monitoring"""
        return {
            "total_rules_fired": self.rules_fired,
            "execution_log": self.execution_log
        }


def apply_rules(cands: List[Candidate], user: UserProfile) -> List[Candidate]:
    """
    Legacy function signature for backward compatibility.
    Uses RuleEngine internally.
    
    Args:
        cands: List of candidates
        user: User profile
        
    Returns:
        Candidates with applied rules
    """
    engine = RuleEngine()
    return engine.apply_rules(cands, user)