from typing import List
from connectors.literature import evidence_score_from_text
from models import Candidate

def attach_evidence_scores(cands: List[Candidate]) -> List[Candidate]:
    for c in cands:
        text = f"{c.item.name} {c.item.spec_text}"
        c.evidence_score = evidence_score_from_text(text)
    return cands
