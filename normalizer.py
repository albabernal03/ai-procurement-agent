from typing import List
from models import SupplierItem, Candidate

# Very small demo: convert mL→L and µL→mL (pack_size normalization); ensure non-negatives.
def normalize_items(items: List[SupplierItem]) -> List[Candidate]:
    normalized = []
    for it in items:
        pack_liters = it.pack_size
        unit_norm = it.unit.lower().strip()
        if unit_norm in ("ml", "milliliter", "milliliters"):
            pack_liters = it.pack_size / 1000.0
        elif unit_norm in ("µl", "ul", "microliter", "microliters"):
            pack_liters = it.pack_size / 1_000_000.0
        elif unit_norm in ("l", "liter", "liters"):
            pack_liters = it.pack_size
        else:
            # Unknown unit; keep raw and flag
            pack_liters = it.pack_size
        cand = Candidate(item=it, normalized={"pack_liters": max(0.0, pack_liters)})
        normalized.append(cand)
    return normalized
