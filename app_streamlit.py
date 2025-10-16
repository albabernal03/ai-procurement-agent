import pandas as pd
import streamlit as st
from models import UserProfile
from orchestrator import generate_quote
from pathlib import Path
from feedback_system import get_feedback_system

st.set_page_config(page_title="AI Procurement Agent — MVP", layout="wide")

# Initialize session state
if 'quote' not in st.session_state:
    st.session_state.quote = None
if 'feedback_submitted' not in st.session_state:
    st.session_state.feedback_submitted = False

st.title("AI Procurement Agent — MVP")
st.caption("Busca un reactivo/equipo, aplica reglas y puntúa (coste / evidencia / disponibilidad)")

# Sidebar: pesos y restricciones
with st.sidebar:
    st.header("Config")
    budget = st.number_input("Budget (EUR)", min_value=0.0, value=200.0, step=10.0)
    deadline_days = st.number_input("Deadline (days)", min_value=0, value=7, step=1)
    alpha = st.slider("α Cost", 0.0, 1.0, 0.35, 0.05)
    beta = st.slider("β Evidence", 0.0, 1.0, 0.45, 0.05)
    gamma = st.slider("γ Availability", 0.0, 1.0, 0.20, 0.05)
    preferred = st.text_input("Preferred vendors (comma-separated)", "BioSupplier A")
    weights = {"alpha_cost": alpha, "beta_evidence": beta, "gamma_availability": gamma}
    
    # Show learning stats in sidebar
    st.markdown("---")
    st.subheader("📊 Learning Stats")
    feedback_system = get_feedback_system()
    stats = feedback_system.get_statistics()
    st.metric("Total Decisions", stats['total_decisions'])
    st.metric("Agreement Rate", f"{stats['agreement_rate']:.1f}%")
    if stats['avg_rating'] > 0:
        st.metric("Avg Rating", f"{stats['avg_rating']:.1f}/5.0")

query = st.text_input("What do you need? (e.g., 'DNA polymerase', 'PCR membrane')", "DNA polymerase")

if st.button("Generate quote"):
    user = UserProfile(
        query=query,
        budget=budget,
        preferred_vendors=[v.strip() for v in preferred.split(",") if v.strip()],
        deadline_days=deadline_days,
        weights=weights,
        currency="EUR",
    )
    st.session_state.quote = generate_quote(user)
    st.session_state.feedback_submitted = False

# Display quote if it exists
if st.session_state.quote is not None:
    quote = st.session_state.quote
    
    if quote.selected:
        st.subheader("Top Recommendation")
        sel = quote.selected
        st.markdown(
            f"**{sel.item.vendor} — {sel.item.name} ({sel.item.sku})**  \n"
            f"Price: {sel.item.price} EUR · Stock: {sel.item.stock} · ETA: {sel.item.eta_days} days  \n"
            f"Scores → Cost: {sel.cost_fitness}, Evidence: {sel.evidence_score}, Availability: {sel.availability_score}, **Total: {sel.total_score}**"
        )
    else:
        st.info(quote.notes or "No suitable candidate selected.")

    if quote.candidates:
        rows = []
        for i, c in enumerate(quote.candidates, start=1):
            rows.append({
                "#": i,
                "Vendor": c.item.vendor,
                "SKU": c.item.sku,
                "Name": c.item.name,
                "Price (EUR)": c.item.price,
                "Stock": c.item.stock,
                "ETA (d)": c.item.eta_days,
                "Cost": c.cost_fitness,
                "Evidence": c.evidence_score,
                "Availability": c.availability_score,
                "Total": c.total_score,
                "Flags": ", ".join(c.flags),
                "Rationales": " | ".join(c.rationales),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width='stretch')
        
        # Feedback section
        st.markdown("---")
        st.subheader("💬 Provide Feedback")
        
        if st.session_state.feedback_submitted:
            st.success("✅ Feedback already submitted for this quote. Generate a new quote to provide more feedback.")
        else:
            # Create product options
            product_options = []
            for i, c in enumerate(quote.candidates, 1):
                label = f"#{i} - {c.item.vendor} - {c.item.name[:40]}... (€{c.item.price})"
                product_options.append((label, c.item.sku))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_idx = st.selectbox(
                    "Which product would you choose?",
                    options=range(len(product_options)),
                    format_func=lambda x: product_options[x][0],
                    key="product_selector"
                )
            
            with col2:
                user_rating = st.slider("Rate (1-5)", 1, 5, 3, key="rating")
            
            with col3:
                user_comment = st.text_input("Optional comment", key="comment")
            
            if st.button("Submit Feedback", type="primary"):
                selected_sku = product_options[selected_idx][1]
                
                feedback_system.record_decision(
                    quote=quote,
                    selected_sku=selected_sku,
                    user_rating=user_rating,
                    user_comment=user_comment if user_comment else None
                )
                
                st.session_state.feedback_submitted = True
                
                # Show updated stats
                new_stats = feedback_system.get_statistics()
                st.success(f"✅ Thank you! Feedback recorded. System has learned from {new_stats['total_decisions']} decisions.")
                st.rerun()
        
        st.download_button(
            "Open HTML report",
            data=(Path("outputs")/"quotation_report.html").read_bytes() if (Path("outputs")/"quotation_report.html").exists() else b"",
            file_name="quotation_report.html",
            mime="text/html",
            disabled=not (Path("outputs")/"quotation_report.html").exists()
        )