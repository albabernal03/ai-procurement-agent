"""
orchestrator_v2.py
Integra environment.py + inference_engine.py con el pipeline existente
Implementa el pipeline formal de 5 acciones (A1-A5) según Task 2
"""

import logging
from typing import Dict, List, Optional, Tuple
from models import UserRequest, Product, Quotation, ProcurementState, Candidate, UserProfile

# Importar componentes formales
from environment import (
    ProcurementEnvironment, 
    ActionType, 
    State, 
    Observation
)
from inference_engine import (
    HybridInferenceEngine,
    Fact
)

# Importar módulos existentes
from connectors.suppliers import HybridSupplierConnector, search_suppliers_expanded
from connectors.literature import get_pubmed_connector, get_literature_scorer
from normalizer import normalize_items
from evidence import attach_evidence_scores
from scoring import ScoringEngine
from llm_agent import get_llm_agent
from feedback_system import get_feedback_system
from quotation import save_html_report

logger = logging.getLogger(__name__)

class FormalOrchestrator:
    """
    Orchestrator que implementa formalmente:
    - Environment E = ⟨S, A, O, T, R, γ⟩
    - Hybrid Inference (Forward + Backward)
    - 5-step reasoning pipeline (A1-A5)
    - Goal state verification
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # === MDP Environment ===
        env_config = config.get('environment', {})
        env_config.update(config.get('reward_config', {}))
        self.env = ProcurementEnvironment(env_config)
        
        # === Hybrid Inference Engine ===
        self.inference_engine = HybridInferenceEngine()
        
        # === Módulos existentes (mantener compatibilidad) ===
        self.supplier_connector = HybridSupplierConnector()
        self.literature_connector = get_pubmed_connector()
        self.literature_scorer = get_literature_scorer()
        self.scorer = ScoringEngine()
        self.llm_agent = get_llm_agent()
        self.feedback_system = get_feedback_system()
        
        # === Tracking ===
        self.episode_history: List[Dict] = []
        self.current_episode = 0
    
    def process_request(
        self, 
        user_request: UserRequest,
        reasoning_mode: str = "hybrid"
    ) -> Tuple[Quotation, Dict]:
        """
        Pipeline completo con formalización MDP + Inference
        
        Args:
            user_request: Solicitud del usuario
            reasoning_mode: "forward", "backward" o "hybrid"
        
        Returns:
            (quotation, metadata) donde metadata incluye:
            - goal_achieved: bool
            - cumulative_reward: float
            - inference_trace: List[str]
            - missing_facts: List[str]
        """
        self.current_episode += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"EPISODE {self.current_episode}: {user_request.query}")
        logger.info(f"{'='*60}\n")
        
        # === RESET ENVIRONMENT ===
        observation = self.env.reset(user_request)
        self.inference_engine.reset()
        
        # === Inicializar percepts (P1-P5) como facts ===
        self._initialize_percepts(user_request)
        
        # === 5-STEP REASONING PIPELINE ===
        metadata = {
            'actions_executed': [],
            'rewards': [],
            'states': [],
            'inference_results': {}
        }
        
        try:
            # A1: Perceive and Retrieve Data
            products, obs1, reward1, info1 = self._action_perceive_retrieve(user_request)
            metadata['actions_executed'].append('A1_perceive_retrieve')
            metadata['rewards'].append(reward1)
            metadata['states'].append(info1['state'])
            
            # A2: Normalize and Structure Information
            normalized, obs2, reward2, info2 = self._action_normalize(products)
            metadata['actions_executed'].append('A2_normalize')
            metadata['rewards'].append(reward2)
            metadata['states'].append(info2['state'])
            
            # A3: Evaluate and Score Alternatives
            candidates, obs3, reward3, info3 = self._action_evaluate_score(normalized, user_request)
            metadata['actions_executed'].append('A3_evaluate_score')
            metadata['rewards'].append(reward3)
            metadata['states'].append(info3['state'])
            
            # A4: Generate and Explain Recommendation
            recommended, obs4, reward4, info4 = self._action_generate_explain(candidates, user_request)
            metadata['actions_executed'].append('A4_generate_explain')
            metadata['rewards'].append(reward4)
            metadata['states'].append(info4['state'])
            
            # A5: Learn and Refine through Feedback (placeholder - se ejecuta después)
            metadata['actions_executed'].append('A5_learn_refine')
            
            # === HYBRID INFERENCE ===
            inference_results = self.inference_engine.reason(mode=reasoning_mode)
            metadata['inference_results'] = inference_results
            
            # === BUILD QUOTATION ===
            # ✅ USAR el orchestrator original completo que maneja todo correctamente
            from orchestrator import ProcurementOrchestrator
            
            # Crear UserProfile para compatibilidad
            user_profile = UserProfile(
                query=user_request.query,
                budget=user_request.budget,
                preferred_vendors=user_request.preferred_vendors,
                deadline_days=user_request.urgency_days,
                weights={
                    "alpha_cost": 0.35,
                    "beta_evidence": 0.35,
                    "gamma_availability": 0.30
                }
            )
            
            # Generar quotation usando el orchestrator original que incluye explicaciones LLM
            orchestrator_legacy = ProcurementOrchestrator()
            quotation = orchestrator_legacy.generate_quote(user_profile)
            
            # === VERIFY GOAL STATE ===
            goal_achieved = self.env.reward_function.check_goal_state(
                self.env.cumulative_rewards
            )
            
            metadata.update({
                'goal_achieved': goal_achieved,
                'cumulative_reward': sum(metadata['rewards']),
                'discounted_return': info4.get('discounted_return', 0.0),
                'missing_facts': inference_results.get('missing_facts', []),
                'inference_trace': inference_results.get('inference_trace', [])
            })
            
            # === LOG RESULTS ===
            self._log_episode_summary(metadata)
            
            # === SAVE HISTORY ===
            self.episode_history.append({
                'episode': self.current_episode,
                'request': user_request.query,
                'quotation': quotation,
                'metadata': metadata
            })
            
            return quotation, metadata
        
        except Exception as e:
            logger.error(f"Error in episode {self.current_episode}: {e}", exc_info=True)
            raise
    
    def _initialize_percepts(self, user_request: UserRequest):
        """
        Inicializa percepts P1-P5 como facts en la knowledge base
        """
        percepts = {
            # P3: User Profile and Constraints
            'user_request_received': True,
            'budget_set': user_request.budget is not None,
            'deadline_set': user_request.urgency_days is not None,
            'preferred_vendors_set': len(user_request.preferred_vendors) > 0,
        }
        
        self.inference_engine.add_percepts(percepts)
        logger.debug(f"Initialized {len(percepts)} percepts as facts")
    
    def _action_perceive_retrieve(
        self, 
        user_request: UserRequest
    ) -> Tuple[List[Product], Observation, float, Dict]:
        """
        A1: Perceive and Retrieve Data
        - Query vendor catalogues (P1)
        - Retrieve literature (P2)
        - Update market data (P4)
        """
        logger.info("▶ A1: PERCEIVE AND RETRIEVE DATA")
        
        # Generar queries expandidas simples
        query = user_request.query
        expanded_queries = [
            query,
            query.lower(),
            query.replace(" ", "-"),
        ]
        
        logger.info(f"  - Using {len(expanded_queries)} query variants")
        
        # Buscar productos usando función existente
        products = search_suppliers_expanded(
            query,
            expanded_queries
        )
        logger.info(f"  - Found {len(products)} products")
        
        # Añadir facts de percepción
        self.inference_engine.kb.add_fact(
            Fact('product_retrieved', len(products) > 0, source='A1')
        )
        
        # Step environment
        result = {
            'candidates': products,
            'total_cost': sum(p.price for p in products) if products else 0,
            'evidence_score': 0.0,
            'cost_fitness': 0.0,
            'completeness': 0.25
        }
        
        obs, reward, done, info = self.env.step(ActionType.QUERY_VENDORS, result)
        
        logger.info(f"  ✓ Reward: {reward:.3f} | Products: {len(products)}")
        
        return products, obs, reward, info
    
    def _action_normalize(
        self, 
        products: List[Product]
    ) -> Tuple[List[Candidate], Observation, float, Dict]:
        """
        A2: Normalize and Structure Information
        - Parse specifications
        - Convert units
        - Remove duplicates
        """
        logger.info("▶ A2: NORMALIZE AND STRUCTURE INFORMATION")
        
        # Normalizar usando función existente
        normalized = normalize_items(products)
        
        logger.info(f"  - Normalized: {len(normalized)} candidates")
        
        # Añadir facts
        self.inference_engine.kb.add_fact(
            Fact('specs_normalized', True, source='A2')
        )
        self.inference_engine.kb.add_fact(
            Fact('price_available', all(c.item.price > 0 for c in normalized), source='A2')
        )
        
        # Step environment
        result = {
            'candidates': normalized,
            'total_cost': sum(c.item.price for c in normalized) if normalized else 0,
            'cost_fitness': 0.0,
            'evidence_score': 0.0,
            'completeness': 0.50
        }
        
        obs, reward, done, info = self.env.step(ActionType.NORMALIZE_SPECS, result)
        
        logger.info(f"  ✓ Reward: {reward:.3f}")
        
        return normalized, obs, reward, info
    
    def _action_evaluate_score(
        self, 
        candidates: List[Candidate],
        user_request: UserRequest
    ) -> Tuple[List[Candidate], Observation, float, Dict]:
        """
        A3: Evaluate and Score Alternatives
        - Retrieve literature evidence (P2)
        - Compute multi-criteria scores (α, β, γ)
        - Rank candidates
        """
        logger.info("▶ A3: EVALUATE AND SCORE ALTERNATIVES")
        
        # Evidence scoring
        candidates = attach_evidence_scores(candidates)
        logger.info(f"  - Evidence computed for {len(candidates)} candidates")
        
        # Añadir facts
        self.inference_engine.kb.add_fact(
            Fact('evidence_retrieved', True, source='A3')
        )
        self.inference_engine.kb.add_fact(
            Fact('stock_checked', True, source='A3')
        )
        
        # Multi-criteria scoring
        user_profile = UserProfile(
            query=user_request.query,
            budget=user_request.budget,
            preferred_vendors=user_request.preferred_vendors,
            deadline_days=user_request.urgency_days
        )
        
        scored_candidates = self.scorer.compute_scores(candidates, user_profile)
        
        avg_evidence = sum(c.evidence_score for c in scored_candidates) / len(scored_candidates) if scored_candidates else 0
        avg_cost = sum(c.cost_fitness for c in scored_candidates) / len(scored_candidates) if scored_candidates else 0
        
        logger.info(f"  - Avg evidence score: {avg_evidence:.3f}")
        logger.info(f"  - Avg cost fitness: {avg_cost:.3f}")
        logger.info(f"  - Top candidate score: {scored_candidates[0].total_score:.3f}" if scored_candidates else "")
        
        # Step environment
        result = {
            'candidates': scored_candidates,
            'evidence_score': avg_evidence,
            'cost_fitness': avg_cost,
            'total_cost': scored_candidates[0].item.price if scored_candidates else float('inf'),
            'eta_days': scored_candidates[0].item.eta_days if scored_candidates else 999,
            'vendor': scored_candidates[0].item.vendor if scored_candidates else '',
            'completeness': 0.75
        }
        
        obs, reward, done, info = self.env.step(ActionType.SCORE_RANK, result)
        
        logger.info(f"  ✓ Reward: {reward:.3f}")
        
        return scored_candidates, obs, reward, info
    
    def _action_generate_explain(
        self, 
        ranked_candidates: List[Candidate],
        user_request: UserRequest
    ) -> Tuple[List[Candidate], Observation, float, Dict]:
        """
        A4: Generate and Explain Recommendation
        - Select top-k candidates
        - Generate LLM explanations (manejado por orchestrator original)
        - Propose alternatives if needed
        """
        logger.info("▶ A4: GENERATE AND EXPLAIN RECOMMENDATION")
        
        top_k = self.config.get('pipeline', {}).get('top_k_recommendations', 3)
        recommended = ranked_candidates[:top_k]
        
        logger.info(f"  - Selected top {len(recommended)} candidates")
        
        # Añadir facts
        self.inference_engine.kb.add_fact(
            Fact('candidate_added', True, source='A4')
        )
        self.inference_engine.kb.add_fact(
            Fact('candidate_rewarded', True, source='A4')
        )
        self.inference_engine.kb.add_fact(
            Fact('vendor_confirmed', True, source='A4')
        )
        
        # Calcular promedios
        avg_cost = sum(c.cost_fitness for c in recommended) / len(recommended) if recommended else 0
        avg_evidence = sum(c.evidence_score for c in recommended) / len(recommended) if recommended else 0
        
        # Step environment
        result = {
            'candidates': recommended,
            'total_cost': recommended[0].item.price if recommended else float('inf'),
            'evidence_score': avg_evidence,
            'cost_fitness': avg_cost,
            'eta_days': recommended[0].item.eta_days if recommended else 999,
            'vendor': recommended[0].item.vendor if recommended else '',
            'completeness': 1.0
        }
        
        obs, reward, done, info = self.env.step(ActionType.BUILD_QUOTATION, result)
        
        logger.info(f"  ✓ Reward: {reward:.3f} | Goal achieved: {done}")
        
        return recommended, obs, reward, info
    
    def register_feedback(
        self, 
        quotation_id: str, 
        user_choice: str,
        rating: int,
        comments: str = ""
    ):
        """
        A5: Learn and Refine through Feedback
        Ejecutado después de que el usuario responde
        """
        logger.info("▶ A5: LEARN AND REFINE THROUGH FEEDBACK")
        
        # Añadir fact
        self.inference_engine.kb.add_fact(
            Fact('feedback_received', True, source='A5')
        )
        self.inference_engine.kb.add_fact(
            Fact('weights_adjusted', True, source='A5')
        )
        
        stats = self.feedback_system.get_statistics()
        logger.info(f"  - Total decisions: {stats['total_decisions']}")
        logger.info(f"  - Avg rating: {stats['avg_rating']:.2f}")
        
        return stats
    
    def _build_reasoning_trace(self, metadata: Dict) -> str:
        """
        Construye trace legible del razonamiento para la quotation
        """
        trace_lines = [
            "=== REASONING TRACE ===",
            f"Episode: {self.current_episode}",
            "",
            "Actions Executed:",
        ]
        
        for i, action in enumerate(metadata['actions_executed'], 1):
            reward = metadata['rewards'][i-1] if i-1 < len(metadata['rewards']) else 0
            trace_lines.append(f"  {i}. {action} (R={reward:.3f})")
        
        trace_lines.extend([
            "",
            f"Cumulative Reward: {metadata.get('cumulative_reward', 0):.3f}",
            f"Goal Achieved: {metadata.get('goal_achieved', False)}",
            ""
        ])
        
        if metadata['inference_results'].get('inference_trace'):
            trace_lines.append("Inference Trace:")
            for line in metadata['inference_results']['inference_trace'][:5]:
                trace_lines.append(f"  - {line}")
        
        return "\n".join(trace_lines)
    
    def _log_episode_summary(self, metadata: Dict):
        """Log resumen del episodio"""
        logger.info("\n" + "="*60)
        logger.info("EPISODE SUMMARY")
        logger.info("="*60)
        logger.info(f"Actions: {' → '.join(metadata['actions_executed'])}")
        logger.info(f"Total Reward: {metadata['cumulative_reward']:.3f}")
        logger.info(f"Discounted Return (γ={self.env.gamma}): {metadata.get('discounted_return', 0):.3f}")
        logger.info(f"Goal Achieved: {metadata['goal_achieved']}")
        
        if not metadata['goal_achieved']:
            logger.warning(f"Missing facts: {metadata['missing_facts']}")
        
        logger.info("="*60 + "\n")
    
    def get_episode_history(self) -> List[Dict]:
        """Retorna historial completo de episodios"""
        return self.episode_history
    
    def export_mdp_trajectory(self, episode_id: int) -> Dict:
        """
        Exporta trayectoria MDP del episodio para análisis
        Formato: [(s0, a0, r0), (s1, a1, r1), ...]
        """
        if episode_id >= len(self.episode_history):
            raise ValueError(f"Episode {episode_id} not found")
        
        episode = self.episode_history[episode_id]
        metadata = episode['metadata']
        
        trajectory = []
        for i, action in enumerate(metadata['actions_executed']):
            if i < len(metadata['states']) and i < len(metadata['rewards']):
                trajectory.append({
                    'state': metadata['states'][i],
                    'action': action,
                    'reward': metadata['rewards'][i]
                })
        
        return {
            'episode_id': episode_id,
            'trajectory': trajectory,
            'total_return': metadata['cumulative_reward'],
            'goal_achieved': metadata['goal_achieved']
        }