from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime

class UserProfile(BaseModel):
    query: str = Field(..., description="Free-text description, e.g., 'DNA polymerase for PCR'")
    budget: float = Field(..., description="Max total budget in EUR", gt=0)
    preferred_vendors: List[str] = Field(default_factory=list)
    deadline_days: int = Field(14, ge=0)
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "alpha_cost": 0.35,
            "beta_evidence": 0.45,
            "gamma_availability": 0.20
        }
    )
    currency: str = "EUR"
    
    @validator('weights')
    def validate_weights_sum(cls, v):
        """Ensure weights sum to approximately 1.0"""
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")
        return v
    
    @validator('budget')
    def validate_budget_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget must be positive")
        return v

class SupplierItem(BaseModel):
    sku: str
    vendor: str
    name: str
    spec_text: str
    unit: str
    pack_size: float
    price: float
    currency: str = "EUR"
    stock: int
    eta_days: int
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v
    
    @validator('stock')
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Stock cannot be negative")
        return v

class Candidate(BaseModel):
    item: SupplierItem
    normalized: Dict[str, float] = Field(default_factory=dict)
    
    # Scores
    evidence_score: float = Field(0.0, ge=0, le=1)
    cost_fitness: float = Field(0.0, ge=0, le=1)
    availability_score: float = Field(0.0, ge=0, le=1)
    total_score: float = 0.0
    
    # Explainability
    rationales: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    
    # Metadata for traceability
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_rationale(self, rule_id: str, message: str):
        """Helper method to add rationales consistently"""
        self.rationales.append(f"{rule_id}: {message}")
    
    def add_flag(self, flag: str):
        """Helper method to avoid duplicate flags"""
        if flag not in self.flags:
            self.flags.append(flag)

class Quote(BaseModel):
    user: UserProfile
    candidates: List[Candidate]
    selected: Optional[Candidate] = None
    notes: Optional[str] = None
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }