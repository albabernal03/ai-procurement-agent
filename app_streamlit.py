import pandas as pd
import streamlit as st
import yaml
from pathlib import Path
from models import UserProfile
from feedback_system import get_feedback_system

# Importar el nuevo orchestrator
from orchestrator_v2 import FormalOrchestrator

st.set_page_config(page_title="AI Procurement Agent — MVP (Formal)", layout="wide")

# Load formal config
@st.cache_resource
def load_orchestrator():
    with open('config_formal.yaml') as f:
        config = yaml.safe_load(f)
    return FormalOrchestrator(config)

# Initialize session state
if 'quote' not in st.session_state:
    st.session_state.quote = None
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'feedback_submitted' not in st.session_state:
    st.session_state.feedback_submitted = False

st.title("🤖 AI Procurement Agent — Formal MVP")
st.caption("Sistema formalizado con MDP, Hybrid Inference y Goal State Verification")

# Sidebar: pesos y restricciones
with st.sidebar:
    st.header("⚙️ Configuration")
    budget = st.number_input("Budget (EUR)", min_value=0.0, value=5000.0, step=100.0)
    deadline_days = st.number_input("Deadline (days)", min_value=0, value=15, step=1)
    
    st.markdown("#### Scoring Weights")
    alpha = st.slider("α Cost", 0.0, 1.0, 0.35, 0.05)
    beta = st.slider("β Evidence", 0.0, 1.0, 0.35, 0.05)
    gamma = st.slider("γ Availability", 0.0, 1.0, 0.30, 0.05)
    
    preferred = st.text_input("Preferred vendors (comma-separated)", "Thermo Fisher, New England Biolabs")
    
    st.markdown("#### Inference Mode")
    reasoning_mode = st.selectbox("Reasoning Mode", ["hybrid", "forward", "backward"])
    
    weights = {"alpha_cost": alpha, "beta_evidence": beta, "gamma_availability": gamma}
    
    # Show learning stats in sidebar
    st.markdown("---")
    st.subheader("📊 Learning Stats")
    feedback_system = get_feedback_system()
    stats = feedback_system.get_statistics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Decisions", stats['total_decisions'])
        st.metric("Agreement Rate", f"{stats['agreement_rate']:.1f}%")
    with col2:
        if stats['avg_rating'] > 0:
            st.metric("Avg Rating", f"{stats['avg_rating']:.1f}/5.0")
        learned = stats.get('learned_weights', {})
        if learned and 'confidence' in learned:
            st.metric("Confidence", f"{learned['confidence']:.0%}")
    
    # Show learned weights
    if stats['total_decisions'] > 0:
        learned = stats.get('learned_weights', {})
        if learned and 'alpha' in learned:
            st.markdown("**Learned Weights:**")
            st.text(f"α: {learned.get('alpha', 0):.3f}")
            st.text(f"β: {learned.get('beta', 0):.3f}")
            st.text(f"γ: {learned.get('gamma', 0):.3f}")

# Main query input
query = st.text_input(
    "What do you need? (e.g., 'PCR enzymes', 'Taq polymerase')", 
    "PCR enzymes for molecular biology"
)

if st.button("🚀 Generate Quote", type="primary"):
    with st.spinner("Processing request through formal pipeline (A1→A2→A3→A4→A5)..."):
        # Create UserProfile (compatibility with old format)
        user = UserProfile(
            query=query,
            budget=budget,
            preferred_vendors=[v.strip() for v in preferred.split(",") if v.strip()],
            deadline_days=deadline_days,
            weights=weights,
            currency="EUR",
        )
        
        # Create UserRequest for new orchestrator
        from models import UserRequest
        user_request = UserRequest(
            query=query,
            budget=budget,
            urgency_days=deadline_days,
            preferred_vendors=[v.strip() for v in preferred.split(",") if v.strip()]
        )
        
        # Load orchestrator and process
        orchestrator = load_orchestrator()
        
        try:
            quotation, metadata = orchestrator.process_request(
                user_request,
                reasoning_mode=reasoning_mode
            )
            
            st.session_state.quote = quotation
            st.session_state.metadata = metadata
            st.session_state.feedback_submitted = False
            
        except Exception as e:
            st.error(f"Error processing request: {e}")
            st.exception(e)

# Display quote if it exists
if st.session_state.quote is not None and st.session_state.metadata is not None:
    quote = st.session_state.quote
    metadata = st.session_state.metadata
    
    # === MDP METRICS ===
    st.markdown("---")
    st.subheader("🎯 MDP Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        goal_icon = "✅" if metadata['goal_achieved'] else "❌"
        st.metric("Goal Achieved", goal_icon)
    
    with col2:
        st.metric("Cumulative Reward", f"{metadata['cumulative_reward']:.3f}")
    
    with col3:
        st.metric("Actions Executed", len(metadata['actions_executed']))
    
    with col4:
        discounted = metadata.get('discounted_return', 0.0)
        st.metric("Discounted Return", f"{discounted:.3f}")
    
    # === GOAL STATE ANALYSIS (DEBUG) ===
    if not metadata['goal_achieved']:
        st.warning("⚠️ **Goal State Not Achieved**")
        
        # Obtener cumulative rewards del orchestrator
        orchestrator = load_orchestrator()
        cumulative = orchestrator.env.cumulative_rewards
        
        # Thresholds del config
        thresholds = {
            'cost': 0.7,
            'evidence': 0.6,
            'quotation_completeness': 0.8
        }
        
        st.markdown("**Goal State Analysis:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rc = cumulative.get('cost', 0.0)
            tc = thresholds['cost']
            status = "✅" if rc >= tc else "❌"
            st.metric(
                f"RC (Cost) {status}",
                f"{rc:.3f}",
                delta=f"Threshold: {tc}",
                delta_color="normal" if rc >= tc else "inverse"
            )
        
        with col2:
            re = cumulative.get('evidence', 0.0)
            te = thresholds['evidence']
            status = "✅" if re >= te else "❌"
            st.metric(
                f"RE (Evidence) {status}",
                f"{re:.3f}",
                delta=f"Threshold: {te}",
                delta_color="normal" if re >= te else "inverse"
            )
        
        with col3:
            rq = cumulative.get('quotation_completeness', 0.0)
            tq = thresholds['quotation_completeness']
            status = "✅" if rq >= tq else "❌"
            st.metric(
                f"RQ (Quotation) {status}",
                f"{rq:.3f}",
                delta=f"Threshold: {tq}",
                delta_color="normal" if rq >= tq else "inverse"
            )
        
        st.info("💡 **Tip:** Adjust weights (α, β, γ) in sidebar or provide feedback to improve goal achievement.")
    else:
        st.success("✅ **All goal state criteria met!** (RC ≥ θC, RE ≥ θE, RQ ≥ θQ)")
    
    # === ACTIONS TRACE ===
    with st.expander("🔄 Actions Trace (A1→A2→A3→A4→A5)"):
        for i, (action, reward) in enumerate(zip(metadata['actions_executed'], metadata['rewards'])):
            st.code(f"{i+1}. {action} → Reward: {reward:.3f}")
    
    # === INFERENCE TRACE ===
    if metadata.get('inference_results', {}).get('inference_trace'):
        with st.expander("🧠 Inference Trace (Hybrid Reasoning)"):
            for trace in metadata['inference_results']['inference_trace']:
                st.text(trace)
    
    # === MISSING FACTS (if goal not achieved) ===
    if not metadata['goal_achieved'] and metadata.get('missing_facts'):
        st.warning(f"⚠️ Goal not achieved. Missing facts: {', '.join(metadata['missing_facts'])}")
    
    st.markdown("---")
    
    # === TOP RECOMMENDATION ===
    if quote.selected:
        st.subheader("⭐ Top Recommendation")
        sel = quote.selected
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {sel.item.name}")
            st.markdown(f"**Vendor:** {sel.item.vendor} | **SKU:** {sel.item.sku}")
            st.markdown(f"**Price:** €{sel.item.price:.2f} | **Stock:** {sel.item.stock} | **ETA:** {sel.item.eta_days} days")
        
        with col2:
            st.metric("Total Score", f"{sel.total_score:.4f}")
            st.metric("Cost Fitness", f"{sel.cost_fitness:.2f}")
            st.metric("Evidence Score", f"{sel.evidence_score:.2f}")
            st.metric("Availability", f"{sel.availability_score:.2f}")
    else:
        st.info(quote.notes or "No suitable candidate selected.")

    # === ALL CANDIDATES TABLE ===
    if quote.candidates:
        st.subheader("📋 All Candidates")
        
        rows = []
        for i, c in enumerate(quote.candidates, start=1):
            rows.append({
                "#": i,
                "Vendor": c.item.vendor,
                "SKU": c.item.sku,
                "Name": c.item.name[:50] + "..." if len(c.item.name) > 50 else c.item.name,
                "Price (€)": f"{c.item.price:.2f}",
                "Stock": c.item.stock,
                "ETA (d)": c.item.eta_days,
                "Cost": f"{c.cost_fitness:.2f}",
                "Evidence": f"{c.evidence_score:.2f}",
                "Avail": f"{c.availability_score:.2f}",
                "Total": f"{c.total_score:.4f}",
                "Flags": ", ".join(c.flags),
            })
        
        df = pd.DataFrame(rows)
        st.dataframe(df, width='stretch')
        
        # === FEEDBACK SECTION ===
        st.markdown("---")
        st.subheader("💬 Provide Feedback (A5: Learn and Refine)")
        
        if st.session_state.feedback_submitted:
            st.success("✅ Feedback submitted! Weights have been updated. Generate a new quote to see adapted recommendations.")
        else:
            product_options = []
            for i, c in enumerate(quote.candidates, 1):
                label = f"#{i} - {c.item.vendor} - {c.item.name[:40]}... (€{c.item.price:.2f})"
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
                user_rating = st.slider("Rate this recommendation (1-5)", 1, 5, 4, key="rating")
            
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
                
                new_stats = feedback_system.get_statistics()
                st.success(f"✅ Feedback recorded! System has learned from {new_stats['total_decisions']} decisions.")
                st.rerun()
        
        # === DOWNLOAD REPORT ===
        report_path = Path("outputs") / "quotation_report.html"
        if report_path.exists():
            st.download_button(
                "📄 Download HTML Report",
                data=report_path.read_bytes(),
                file_name="quotation_report.html",
                mime="text/html"
            )

# Footer
st.markdown("---")
st.caption("🎓 AI Procurement Agent - Formal Implementation | MDP + Hybrid Inference + Adaptive Learning")