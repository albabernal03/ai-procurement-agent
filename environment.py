"""
environment.py
Formaliza el entorno como MDP según Task 1:
E = ⟨S, A, O, T, R, γ⟩
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from models import Product, UserRequest, ProcurementState

class ActionType(Enum):
    """A = {a1, a2, a3, a4, a5, a6, a7}"""
    QUERY_VENDORS = "a1"           # Query or update vendor catalogues
    NORMALIZE_SPECS = "a2"         # Parse and normalize specifications
    RETRIEVE_LITERATURE = "a3"     # Retrieve literature by keywords
    SCORE_RANK = "a4"              # Score and rank candidates
    PROPOSE_SUBSTITUTES = "a5"     # Propose equivalent alternatives
    BUILD_QUOTATION = "a6"         # Build quotation (PDF/JSON)
    REQUEST_CLARIFICATION = "a7"   # Request clarification from user

@dataclass
class State:
    """
    St = {ut, Ct, Pt, At, Et, Xt, Kt}
    
    - ut: user need / profile
    - Ct: candidate product set (normalized specs)
    - Pt: vendor prices (base, shipping, discounts)
    - At: stock / ETA (availability)
    - Et: literature evidence (papers, citations, venue)
    - Xt: exchange rates
    - Kt: policy / constraints (budget, preferred vendors)
    """
    user_request: UserRequest
    candidates: List[Product] = field(default_factory=list)
    prices: Dict[str, float] = field(default_factory=dict)
    availability: Dict[str, Dict] = field(default_factory=dict)
    evidence: Dict[str, Dict] = field(default_factory=dict)
    exchange_rates: Dict[str, float] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serializa el estado para logging/debugging"""
        return {
            'user_request': self.user_request.query,
            'n_candidates': len(self.candidates),
            'has_evidence': bool(self.evidence),
            'constraints': self.constraints
        }

@dataclass
class Observation:
    """
    Ot = f(St) + ε
    Observación parcial y ruidosa del estado real
    """
    state_snapshot: Dict[str, Any]
    noise_level: float = 0.0  # ε - nivel de incertidumbre
    completeness: float = 1.0  # % de información disponible
    
    @classmethod
    def from_state(cls, state: State, noise: float = 0.05) -> 'Observation':
        """Genera observación desde el estado con ruido opcional"""
        snapshot = state.to_dict()
        return cls(
            state_snapshot=snapshot,
            noise_level=noise,
            completeness=np.random.uniform(0.85, 1.0)  # Simula datos incompletos
        )

class RewardFunction:
    """
    R = r1 + r2 + r3 + r4 - r5
    
    - r1: lower total cost relative to budget target
    - r2: higher evidence quality (citations, journal reputation)
    - r3: timely availability within requested window
    - r4: alignment with user preferences
    - r5: penalties (out-of-stock, missing specs, stale data)
    """
    
    def __init__(self, config: Dict[str, float]):
        # Thresholds para goal state G
        self.theta_cost = config.get('theta_cost', 0.7)      # θC
        self.theta_evidence = config.get('theta_evidence', 0.6)  # θE
        self.theta_quotation = config.get('theta_quotation', 0.8) # θQ
        
        # Pesos de las componentes de reward
        self.w1 = config.get('w1_cost', 1.0)
        self.w2 = config.get('w2_evidence', 1.0)
        self.w3 = config.get('w3_availability', 1.0)
        self.w4 = config.get('w4_preferences', 0.5)
        self.w5_penalty = config.get('w5_penalty', 2.0)
    
    def compute(self, state: State, action: ActionType, result: Dict) -> float:
        """Calcula R(s,a) basado en el resultado de la acción"""
        r1 = self._reward_cost(state, result)
        r2 = self._reward_evidence(state, result)
        r3 = self._reward_availability(state, result)
        r4 = self._reward_preferences(state, result)
        r5 = self._penalty(state, result)
        
        total_reward = (
            self.w1 * r1 + 
            self.w2 * r2 + 
            self.w3 * r3 + 
            self.w4 * r4 - 
            self.w5_penalty * r5
        )
        
        return total_reward
    
    def _reward_cost(self, state: State, result: Dict) -> float:
        """r1: Lower cost vs budget → reward ∈ [0,1]"""
        budget = state.constraints.get('budget', float('inf'))
        total_cost = result.get('total_cost', float('inf'))
        
        if total_cost > budget:
            return 0.0
        
        # Cuanto más bajo el % del budget usado, mayor reward
        return 1.0 - (total_cost / budget)
    
    def _reward_evidence(self, state: State, result: Dict) -> float:
        """r2: Higher evidence score → reward ∈ [0,1]"""
        return result.get('evidence_score', 0.0)
    
    def _reward_availability(self, state: State, result: Dict) -> float:
        """r3: Timely availability → reward ∈ [0,1]"""
        eta_days = result.get('eta_days', 999)
        deadline = state.constraints.get('deadline_days', 30)
        
        if eta_days > deadline:
            return 0.0
        
        return 1.0 - (eta_days / deadline)
    
    def _reward_preferences(self, state: State, result: Dict) -> float:
        """r4: Alignment with preferred vendors"""
        vendor = result.get('vendor', '')
        preferred = state.constraints.get('preferred_vendors', [])
        
        return 1.0 if vendor in preferred else 0.5
    
    def _penalty(self, state: State, result: Dict) -> float:
        """r5: Penalties for violations"""
        penalty = 0.0
        
        if result.get('out_of_stock', False):
            penalty += 0.5
        
        if result.get('missing_specs', 0) > 0:
            penalty += 0.3
        
        if result.get('stale_data', False):
            penalty += 0.2
        
        return penalty
    
    def check_goal_state(self, cumulative_rewards: Dict[str, float]) -> bool:
        """
        Verifica si se alcanzó el goal state G:
        G = {RC ≥ θC, RE ≥ θE, RQ ≥ θQ}
        """
        RC = cumulative_rewards.get('cost', 0.0)
        RE = cumulative_rewards.get('evidence', 0.0)
        RQ = cumulative_rewards.get('quotation_completeness', 0.0)
        
        return (
            RC >= self.theta_cost and
            RE >= self.theta_evidence and
            RQ >= self.theta_quotation
        )

class TransitionModel:
    """
    T: S × A → S'
    St+1 = T(St, At) + external changes
    """
    
    def __init__(self, stochastic: bool = True):
        self.stochastic = stochastic
    
    def transition(self, state: State, action: ActionType, result: Dict) -> State:
        """Transición determinista + cambios externos estocásticos"""
        new_state = State(
            user_request=state.user_request,
            candidates=result.get('candidates', state.candidates),
            prices=result.get('prices', state.prices),
            availability=result.get('availability', state.availability),
            evidence=result.get('evidence', state.evidence),
            exchange_rates=state.exchange_rates,
            constraints=state.constraints
        )
        
        if self.stochastic:
            new_state = self._apply_external_changes(new_state)
        
        return new_state
    
    def _apply_external_changes(self, state: State) -> State:
        """Simula cambios externos estocásticos (precios, stock, etc.)"""
        # Por ejemplo: algunos productos se agotan aleatoriamente
        for candidate in state.candidates:
            if np.random.random() < 0.05:  # 5% chance
                # Candidate tiene item.sku, no sku directamente
                sku = candidate.item.sku if hasattr(candidate, 'item') else getattr(candidate, 'sku', 'unknown')
                state.availability[sku] = {
                    'stock': 0,
                    'eta_days': np.random.randint(7, 30)
                }
        
        return state

class ProcurementEnvironment:
    """
    E = ⟨S, A, O, T, R, γ⟩
    Entorno MDP completo para el agente de procurement
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gamma = config.get('discount_factor', 0.95)  # γ - discount factor
        
        # Componentes del MDP
        self.reward_function = RewardFunction(config.get('reward_config', {}))
        self.transition_model = TransitionModel(stochastic=True)
        
        # Estado actual
        self.current_state: Optional[State] = None
        self.episode_rewards: List[float] = []
        self.cumulative_rewards: Dict[str, float] = {
            'cost': 0.0,
            'evidence': 0.0,
            'quotation_completeness': 0.0
        }
    
    def reset(self, user_request: UserRequest) -> Observation:
        """Inicializa nuevo episodio"""
        self.current_state = State(
            user_request=user_request,
            constraints={
                'budget': user_request.budget,
                'deadline_days': user_request.urgency_days,
                'preferred_vendors': user_request.preferred_vendors
            }
        )
        self.episode_rewards = []
        self.cumulative_rewards = {'cost': 0.0, 'evidence': 0.0, 'quotation_completeness': 0.0}
        
        return Observation.from_state(self.current_state)
    
    def step(self, action: ActionType, result: Dict) -> Tuple[Observation, float, bool, Dict]:
        """
        Ejecuta acción y retorna (observation, reward, done, info)
        Similar a OpenAI Gym interface
        """
        # Calcula reward
        reward = self.reward_function.compute(self.current_state, action, result)
        self.episode_rewards.append(reward)
        
        # *** ACTUALIZAR CUMULATIVE REWARDS ***
        # Acumular los componentes individuales del reward
        self.cumulative_rewards['cost'] += result.get('cost_fitness', 0.0)
        self.cumulative_rewards['evidence'] += result.get('evidence_score', 0.0)
        self.cumulative_rewards['quotation_completeness'] = result.get('completeness', 0.0)
        
        # Transición de estado
        self.current_state = self.transition_model.transition(
            self.current_state, action, result
        )
        
        # Genera nueva observación
        observation = Observation.from_state(self.current_state)
        
        # Check si alcanzamos goal state G
        done = self.reward_function.check_goal_state(self.cumulative_rewards)
        
        # Info adicional
        info = {
            'cumulative_reward': sum(self.episode_rewards),
            'discounted_return': self._compute_discounted_return(),
            'goal_achieved': done,
            'state': self.current_state.to_dict(),
            'cumulative_rewards': self.cumulative_rewards.copy()  # Para debugging
        }
        
        return observation, reward, done, info
    def _compute_discounted_return(self) -> float:
        """
        Calcula retorno descontado: Σ γ^t * r_t
        """
        return sum(
            (self.gamma ** t) * r 
            for t, r in enumerate(self.episode_rewards)
        )
    
    def get_state_space_size(self) -> int:
        """Retorna dimensionalidad aproximada del espacio de estados"""
        # Útil para dimensionar redes neuronales si usamos deep RL
        return len(self.current_state.to_dict())
    
    def get_action_space(self) -> List[ActionType]:
        """Retorna acciones disponibles"""
        return list(ActionType)