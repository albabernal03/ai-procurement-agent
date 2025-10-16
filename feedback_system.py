"""
Feedback and Learning System
Learns from user decisions to improve recommendations over time
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from models import Quote, Candidate, UserProfile
import statistics


class FeedbackSystem:
    """
    Tracks user feedback and adjusts recommendation weights accordingly
    """
    
    def __init__(self, storage_path: Path = Path("data/feedback.json")):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_history = self._load_feedback()
    
    def _load_feedback(self) -> List[Dict]:
        """Load feedback history from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load feedback: {e}")
                return []
        return []
    
    def _save_feedback(self):
        """Save feedback history to storage"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Could not save feedback: {e}")
    
    def record_decision(
        self,
        quote: Quote,
        selected_sku: str,
        user_rating: Optional[int] = None,
        user_comment: Optional[str] = None
    ):
        """
        Record user's decision and optional feedback
        
        Args:
            quote: The quote that was presented
            selected_sku: SKU of the product user actually selected
            user_rating: Optional rating 1-5
            user_comment: Optional user comment
        """
        # Find selected candidate
        selected_candidate = next(
            (c for c in quote.candidates if c.item.sku == selected_sku),
            None
        )
        
        if not selected_candidate:
            print(f"⚠️  Selected SKU {selected_sku} not found in candidates")
            return
        
        # Calculate if user agreed with our recommendation
        our_recommendation_sku = quote.selected.item.sku if quote.selected else None
        agreed_with_recommendation = (selected_sku == our_recommendation_sku)
        
        # Record feedback
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": quote.user.query,
            "budget": quote.user.budget,
            "our_recommendation_sku": our_recommendation_sku,
            "user_selected_sku": selected_sku,
            "agreed": agreed_with_recommendation,
            "user_rating": user_rating,
            "user_comment": user_comment,
            "selected_product": {
                "vendor": selected_candidate.item.vendor,
                "name": selected_candidate.item.name,
                "price": selected_candidate.item.price,
                "cost_fitness": selected_candidate.cost_fitness,
                "evidence_score": selected_candidate.evidence_score,
                "availability_score": selected_candidate.availability_score,
                "total_score": selected_candidate.total_score
            },
            "weights_used": quote.user.weights
        }
        
        self.feedback_history.append(feedback_entry)
        self._save_feedback()
        
        print(f"✅ Feedback recorded: {'Agreed' if agreed_with_recommendation else 'Disagreed'} with recommendation")
    
    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        if not self.feedback_history:
            return {
                "total_decisions": 0,
                "agreement_rate": 0.0,
                "avg_rating": 0.0
            }
        
        total = len(self.feedback_history)
        agreements = sum(1 for f in self.feedback_history if f.get("agreed", False))
        ratings = [f["user_rating"] for f in self.feedback_history if f.get("user_rating")]
        
        return {
            "total_decisions": total,
            "agreement_rate": (agreements / total * 100) if total > 0 else 0.0,
            "avg_rating": statistics.mean(ratings) if ratings else 0.0,
            "total_ratings": len(ratings)
        }
    
    def analyze_user_preferences(self) -> Dict[str, float]:
        """
        Analyze what dimensions users value most based on their choices
        
        Returns:
            Suggested weight adjustments
        """
        if len(self.feedback_history) < 3:
            # Not enough data
            return {
                "alpha_cost": 0.35,
                "beta_evidence": 0.45,
                "gamma_availability": 0.20,
                "confidence": 0.0
            }
        
        # Analyze patterns in user selections
        selected_products = [f["selected_product"] for f in self.feedback_history]
        
        # Calculate average scores of selected products
        avg_cost = statistics.mean([p["cost_fitness"] for p in selected_products])
        avg_evidence = statistics.mean([p["evidence_score"] for p in selected_products])
        avg_availability = statistics.mean([p["availability_score"] for p in selected_products])
        
        # Normalize to sum to 1.0
        total = avg_cost + avg_evidence + avg_availability
        
        if total == 0:
            return {
                "alpha_cost": 0.35,
                "beta_evidence": 0.45,
                "gamma_availability": 0.20,
                "confidence": 0.0
            }
        
        suggested_alpha = avg_cost / total
        suggested_beta = avg_evidence / total
        suggested_gamma = avg_availability / total
        
        # Calculate confidence based on sample size
        confidence = min(len(self.feedback_history) / 10.0, 1.0)
        
        return {
            "alpha_cost": round(suggested_alpha, 2),
            "beta_evidence": round(suggested_beta, 2),
            "gamma_availability": round(suggested_gamma, 2),
            "confidence": round(confidence, 2)
        }
    
    def get_adaptive_weights(self, user: UserProfile) -> Dict[str, float]:
        """
        Get adaptive weights that blend user's preferences with learned patterns
        
        Args:
            user: Current user profile
            
        Returns:
            Optimized weights
        """
        learned = self.analyze_user_preferences()
        confidence = learned["confidence"]
        
        if confidence < 0.3:
            # Not enough data, use user's weights
            return user.weights
        
        # Blend user preferences with learned patterns
        # Higher confidence = more weight to learned patterns
        blended = {}
        for key in ["alpha_cost", "beta_evidence", "gamma_availability"]:
            user_weight = user.weights.get(key, 0.33)
            learned_weight = learned.get(key, 0.33)
            blended[key] = round(
                user_weight * (1 - confidence) + learned_weight * confidence,
                2
            )
        
        # Ensure they sum to 1.0
        total = sum(blended.values())
        blended = {k: round(v / total, 2) for k, v in blended.items()}
        
        return blended
    
    def get_vendor_performance(self) -> Dict[str, Dict]:
        """
        Analyze vendor performance based on user selections
        
        Returns:
            Vendor statistics
        """
        if not self.feedback_history:
            return {}
        
        vendor_stats = {}
        
        for entry in self.feedback_history:
            vendor = entry["selected_product"]["vendor"]
            
            if vendor not in vendor_stats:
                vendor_stats[vendor] = {
                    "selections": 0,
                    "total_rating": 0,
                    "ratings_count": 0,
                    "avg_price": []
                }
            
            vendor_stats[vendor]["selections"] += 1
            vendor_stats[vendor]["avg_price"].append(entry["selected_product"]["price"])
            
            if entry.get("user_rating"):
                vendor_stats[vendor]["total_rating"] += entry["user_rating"]
                vendor_stats[vendor]["ratings_count"] += 1
        
        # Calculate averages
        for vendor, stats in vendor_stats.items():
            stats["avg_rating"] = (
                stats["total_rating"] / stats["ratings_count"]
                if stats["ratings_count"] > 0 else 0
            )
            stats["avg_price"] = statistics.mean(stats["avg_price"])
            stats["selection_rate"] = stats["selections"] / len(self.feedback_history) * 100
        
        return vendor_stats


# Singleton instance
_feedback_system: Optional[FeedbackSystem] = None


def get_feedback_system() -> FeedbackSystem:
    """Get or create feedback system instance"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system


# CLI test
if __name__ == "__main__":
    print("Testing Feedback System...")
    print("="*60)
    
    system = FeedbackSystem()
    
    # Show stats
    stats = system.get_statistics()
    print(f"\n📊 Current Statistics:")
    print(f"   Total decisions: {stats['total_decisions']}")
    print(f"   Agreement rate: {stats['agreement_rate']:.1f}%")
    print(f"   Avg rating: {stats['avg_rating']:.1f}/5.0")
    
    # Show learned preferences
    learned = system.analyze_user_preferences()
    print(f"\n🧠 Learned Preferences:")
    print(f"   α (cost): {learned['alpha_cost']:.2f}")
    print(f"   β (evidence): {learned['beta_evidence']:.2f}")
    print(f"   γ (availability): {learned['gamma_availability']:.2f}")
    print(f"   Confidence: {learned['confidence']:.0%}")
    
    # Show vendor performance
    vendors = system.get_vendor_performance()
    if vendors:
        print(f"\n🏢 Vendor Performance:")
        for vendor, stats in sorted(vendors.items(), key=lambda x: x[1]['selections'], reverse=True)[:5]:
            print(f"   {vendor}:")
            print(f"     Selections: {stats['selections']}")
            print(f"     Avg rating: {stats['avg_rating']:.1f}/5.0")
            print(f"     Selection rate: {stats['selection_rate']:.1f}%")
    
    print("\n" + "="*60)
    print("✅ Feedback System is working!")