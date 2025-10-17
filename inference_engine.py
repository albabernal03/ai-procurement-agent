"""
inference_engine.py
Implementa hybrid inference mechanism según Task 4:
- Forward chaining (data-driven)
- Backward chaining (goal-driven)
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RuleID(Enum):
    """Production Rules R1-R5"""
    R1_VALIDATE_SPECS = "R1"
    R2_BUDGET_COMPLIANCE = "R2"
    R3_EVIDENCE_QUALITY = "R3"
    R4_AVAILABILITY = "R4"
    R5_LEARNING = "R5"

@dataclass
class Fact:
    """Representa un hecho en la knowledge base"""
    name: str
    value: any
    confidence: float = 1.0
    source: str = "inferred"
    
    def __hash__(self):
        return hash(self.name)

@dataclass
class ProductionRule:
    """
    Production Rule: IF conditions THEN actions ELSE alternative
    """
    rule_id: RuleID
    conditions: List[str]  # Lista de nombres de facts necesarios
    action: str
    else_action: Optional[str] = None
    priority: int = 0
    
    def is_triggered(self, facts: Set[Fact]) -> bool:
        """Verifica si todas las condiciones están satisfechas"""
        fact_names = {f.name for f in facts}
        return all(cond in fact_names for cond in self.conditions)

class KnowledgeBase:
    """Base de conocimiento con hechos y reglas"""
    
    def __init__(self):
        self.facts: Set[Fact] = set()
        self.rules: List[ProductionRule] = []
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Define las 5 production rules del documento"""
        
        # R1: Validación de especificaciones
        self.rules.append(ProductionRule(
            rule_id=RuleID.R1_VALIDATE_SPECS,
            conditions=["product_retrieved"],
            action="normalize_spec",
            else_action="request_spec_from_supplier",
            priority=10  # Alta prioridad
        ))
        
        # R2: Cumplimiento de presupuesto
        self.rules.append(ProductionRule(
            rule_id=RuleID.R2_BUDGET_COMPLIANCE,
            conditions=["price_available", "budget_set"],
            action="mark_as_candidate",
            else_action="search_equivalent_product",
            priority=9
        ))
        
        # R3: Calidad de evidencia científica
        self.rules.append(ProductionRule(
            rule_id=RuleID.R3_EVIDENCE_QUALITY,
            conditions=["evidence_retrieved"],
            action="reward_candidate",
            else_action="penalize_candidate",
            priority=7
        ))
        
        # R4: Disponibilidad
        self.rules.append(ProductionRule(
            rule_id=RuleID.R4_AVAILABILITY,
            conditions=["stock_checked"],
            action="confirm_vendor",
            else_action="substitute_from_preferred_vendor",
            priority=8
        ))
        
        # R5: Aprendizaje (retroalimentación)
        self.rules.append(ProductionRule(
            rule_id=RuleID.R5_LEARNING,
            conditions=["feedback_received"],
            action="adjust_weights",
            else_action="retain_policy",
            priority=5
        ))
    
    def add_fact(self, fact: Fact):
        """Añade nuevo hecho a la KB"""
        self.facts.add(fact)
        logger.debug(f"Added fact: {fact.name} = {fact.value}")
    
    def get_fact(self, name: str) -> Optional[Fact]:
        """Recupera un hecho por nombre"""
        for fact in self.facts:
            if fact.name == name:
                return fact
        return None
    
    def has_fact(self, name: str) -> bool:
        """Verifica si existe un hecho"""
        return any(f.name == name for f in self.facts)

class ForwardChainer:
    """
    Forward Chaining (data-driven inference)
    Desde facts → reglas → nuevos facts → acciones
    """
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.triggered_rules: List[RuleID] = []
    
    def infer(self, max_iterations: int = 10) -> List[str]:
        """
        Ejecuta forward chaining hasta que no se puedan disparar más reglas
        Retorna lista de acciones ejecutadas
        """
        actions_executed = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            triggered_this_round = False
            
            # Ordena reglas por prioridad
            sorted_rules = sorted(self.kb.rules, key=lambda r: r.priority, reverse=True)
            
            for rule in sorted_rules:
                if rule.rule_id in self.triggered_rules:
                    continue  # Ya disparada en esta inferencia
                
                if rule.is_triggered(self.kb.facts):
                    # THEN branch
                    action = self._execute_action(rule.action, rule.rule_id)
                    actions_executed.append(action)
                    self.triggered_rules.append(rule.rule_id)
                    triggered_this_round = True
                    
                    logger.info(f"[FORWARD] Triggered {rule.rule_id.value} → {rule.action}")
                
                elif rule.else_action:
                    # ELSE branch (condiciones no satisfechas)
                    action = self._execute_action(rule.else_action, rule.rule_id)
                    actions_executed.append(action)
                    triggered_this_round = True
                    
                    logger.info(f"[FORWARD] {rule.rule_id.value} ELSE → {rule.else_action}")
            
            if not triggered_this_round:
                break  # No más reglas aplicables
        
        logger.info(f"Forward chaining completed in {iteration} iterations")
        return actions_executed
    
    def _execute_action(self, action: str, rule_id: RuleID) -> str:
        """Ejecuta una acción y genera nuevos facts si corresponde"""
        
        # Mapeo de acciones a nuevos facts generados
        action_to_facts = {
            'normalize_spec': [Fact('specs_normalized', True, source=rule_id.value)],
            'mark_as_candidate': [Fact('candidate_added', True, source=rule_id.value)],
            'search_equivalent_product': [Fact('substitute_search_needed', True, source=rule_id.value)],
            'reward_candidate': [Fact('candidate_rewarded', True, source=rule_id.value)],
            'penalize_candidate': [Fact('candidate_penalized', True, source=rule_id.value)],
            'confirm_vendor': [Fact('vendor_confirmed', True, source=rule_id.value)],
            'substitute_from_preferred_vendor': [Fact('substitute_requested', True, source=rule_id.value)],
            'adjust_weights': [Fact('weights_adjusted', True, source=rule_id.value)],
            'retain_policy': [Fact('policy_retained', True, source=rule_id.value)]
        }
        
        new_facts = action_to_facts.get(action, [])
        for fact in new_facts:
            self.kb.add_fact(fact)
        
        return f"{rule_id.value}:{action}"

class BackwardChainer:
    """
    Backward Chaining (goal-driven inference)
    Desde goal G → reglas necesarias → facts requeridos
    """
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.inference_trace: List[str] = []
    
    def prove_goal(self, goal: str) -> Tuple[bool, List[str]]:
        """
        Intenta probar si el goal es alcanzable
        Retorna (achieved, missing_facts)
        
        Goal state G = {RC ≥ θC, RE ≥ θE, RQ ≥ θQ}
        Traducido a facts:
        - 'quotation_complete'
        - 'cost_acceptable'
        - 'evidence_sufficient'
        """
        self.inference_trace = []
        
        # Mapeo de goals a facts necesarios
        goal_requirements = {
            'quotation_complete': [
                'candidate_added',
                'vendor_confirmed',
                'specs_normalized'
            ],
            'cost_acceptable': [
                'price_available',
                'budget_set',
                'candidate_added'
            ],
            'evidence_sufficient': [
                'evidence_retrieved',
                'candidate_rewarded'
            ]
        }
        
        required_facts = goal_requirements.get(goal, [goal])
        missing_facts = []
        
        for fact_name in required_facts:
            if not self.kb.has_fact(fact_name):
                missing_facts.append(fact_name)
                self.inference_trace.append(f"Missing: {fact_name}")
                
                # Intenta inferir backward
                inferred = self._backward_infer(fact_name)
                if inferred:
                    self.inference_trace.append(f"Inferred: {fact_name}")
                    missing_facts.remove(fact_name)
        
        achieved = len(missing_facts) == 0
        
        logger.info(f"[BACKWARD] Goal '{goal}' → {'ACHIEVED' if achieved else 'PENDING'}")
        logger.debug(f"Trace: {' → '.join(self.inference_trace)}")
        
        return achieved, missing_facts
    
    def _backward_infer(self, fact_name: str) -> bool:
        """
        Intenta inferir un fact backward buscando reglas que lo produzcan
        """
        for rule in self.kb.rules:
            # Verifica si esta regla puede generar el fact
            if self._rule_produces_fact(rule, fact_name):
                # Verifica recursivamente las condiciones
                if self._check_conditions_recursive(rule.conditions):
                    self.inference_trace.append(f"Rule {rule.rule_id.value} can produce {fact_name}")
                    return True
        
        return False
    
    def _rule_produces_fact(self, rule: ProductionRule, fact_name: str) -> bool:
        """Verifica si una regla produce un fact específico"""
        # Mapeo simplificado de acciones a facts generados
        action_produces = {
            'normalize_spec': 'specs_normalized',
            'mark_as_candidate': 'candidate_added',
            'reward_candidate': 'candidate_rewarded',
            'confirm_vendor': 'vendor_confirmed'
        }
        
        return action_produces.get(rule.action) == fact_name
    
    def _check_conditions_recursive(self, conditions: List[str], depth: int = 0) -> bool:
        """Verifica condiciones recursivamente (con límite de profundidad)"""
        if depth > 5:  # Evita recursión infinita
            return False
        
        for cond in conditions:
            if not self.kb.has_fact(cond):
                # Intenta inferir esta condición
                if not self._backward_infer(cond):
                    return False
        
        return True

class HybridInferenceEngine:
    """
    Hybrid Inference Engine que combina Forward y Backward chaining
    """
    
    def __init__(self):
        self.kb = KnowledgeBase()
        self.forward_chainer = ForwardChainer(self.kb)
        self.backward_chainer = BackwardChainer(self.kb)
    
    def add_percepts(self, percepts: Dict[str, any]):
        """
        Añade percepts como facts iniciales
        P1-P5 → Facts
        """
        for name, value in percepts.items():
            self.kb.add_fact(Fact(name, value, source="percept"))
    
    def reason(self, mode: str = "forward") -> Dict[str, any]:
        """
        Ejecuta razonamiento según el modo
        - 'forward': data-driven (desde percepts hacia acciones)
        - 'backward': goal-driven (desde goal G hacia condiciones)
        - 'hybrid': combina ambos
        """
        results = {
            'actions': [],
            'goal_achieved': False,
            'missing_facts': [],
            'inference_trace': []
        }
        
        if mode in ["forward", "hybrid"]:
            logger.info("=== FORWARD CHAINING ===")
            actions = self.forward_chainer.infer()
            results['actions'].extend(actions)
        
        if mode in ["backward", "hybrid"]:
            logger.info("=== BACKWARD CHAINING ===")
            
            # Verifica los 3 componentes del goal state G
            goals = ['quotation_complete', 'cost_acceptable', 'evidence_sufficient']
            all_achieved = True
            
            for goal in goals:
                achieved, missing = self.backward_chainer.prove_goal(goal)
                if not achieved:
                    all_achieved = False
                    results['missing_facts'].extend(missing)
            
            results['goal_achieved'] = all_achieved
            results['inference_trace'] = self.backward_chainer.inference_trace
        
        return results
    
    def reset(self):
        """Reinicia la knowledge base para nuevo episodio"""
        self.kb.facts.clear()
        self.forward_chainer.triggered_rules.clear()