from fastapi import FastAPI
from models import UserProfile, Quote
from orchestrator import generate_quote

app = FastAPI(title="AI Procurement Agent — MVP")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/quote", response_model=Quote)
def quote(user: UserProfile):
    return generate_quote(user)
