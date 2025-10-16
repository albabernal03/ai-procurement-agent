# AI Procurement Agent - Estado Actual del Proyecto

## 🎯 Descripción
Sistema inteligente de procurement para laboratorios que usa IA para recomendar productos basándose en costo, evidencia científica y disponibilidad.

## ✅ Componentes Implementados

### 1. **Búsqueda de Productos**
- ✅ SerpAPI (Google Shopping) - Búsqueda real en internet
- ✅ Base de datos mock (25+ productos de laboratorio)
- ✅ Query Expansion con LLM (5 queries por búsqueda)
- ✅ Deduplicación inteligente

### 2. **Literatura Científica**
- ✅ PubMed API real (100% gratis)
- ✅ Evidence scoring basado en artículos científicos
- ✅ Cache de 24h para optimizar llamadas

### 3. **Razonamiento con LLM**
- ✅ Groq API (Llama 3.3-70b) - GRATIS
- ✅ Análisis de queries
- ✅ Query expansion automática
- ✅ Explicaciones en lenguaje natural
- ✅ Sugerencias de alternativas

### 4. **Sistema de Reglas**
- ✅ R1: Validación de especificaciones
- ✅ R2: Cumplimiento de presupuesto
- ✅ R3: Calidad de evidencia científica
- ✅ R4: Disponibilidad y stock
- ✅ R5: Aprendizaje de políticas

### 5. **Scoring Multi-Criterio**
- ✅ α (cost): Fitness de costo
- ✅ β (evidence): Score de evidencia científica
- ✅ γ (availability): Disponibilidad y ETA
- ✅ Vendor bonus (10% para preferidos)

### 6. **Sistema de Feedback y Aprendizaje** ⭐
- ✅ Registro de decisiones del usuario
- ✅ Análisis de preferencias
- ✅ Adaptive weights (ajuste automático de α, β, γ)
- ✅ Estadísticas de vendors
- ✅ Confidence-based blending

### 7. **Interfaz**
- ✅ Streamlit UI
- ✅ FastAPI backend
- ✅ Reportes HTML
- ✅ Sistema de feedback interactivo

## 📁 Estructura del Proyecto

```
mvp_ai_procurement_agent/
├── models.py                    # Modelos Pydantic
├── orchestrator.py              # Pipeline principal
├── rules.py                     # Motor de reglas (R1-R5)
├── scoring.py                   # Scoring multi-criterio
├── normalizer.py                # Normalización de datos
├── evidence.py                  # Evidence scoring
├── llm_agent.py                 # Agente LLM (Groq)
├── feedback_system.py           # Sistema de aprendizaje
├── config.py                    # Configuración de APIs
├── app_streamlit.py             # Interfaz Streamlit
├── main.py                      # API FastAPI
├── quotation.py                 # Generación de reportes
├── connectors/
│   ├── suppliers.py             # Conector híbrido
│   ├── literature.py            # PubMed connector
│   └── serp_connector.py        # SerpAPI connector
├── utils/
│   └── cache.py                 # Sistema de caché
├── data/
│   └── feedback.json            # Historial de feedback
├── cache/                       # Cache de APIs
├── outputs/                     # Reportes HTML
└── .env                         # API keys

```

## 🔑 APIs Configuradas

- ✅ **Groq API**: LLM gratuito (Llama 3.3-70b)
- ✅ **SerpAPI**: Búsqueda en Google Shopping
- ✅ **PubMed**: Literatura científica (gratis, sin key)

## 📊 Métricas de Aprendizaje Actuales

```
Total Decisions: 3
Agreement Rate: 0.0%
Avg Rating: 4.0/5.0

Learned Preferences:
  α (cost): 0.43
  β (evidence): 0.00
  γ (availability): 0.57
  Confidence: 30%

Vendors Performance:
  - StonyLab: 5.0/5.0 (33.3% selection rate)
  - Thermo Fisher: 4.0/5.0 (33.3%)
  - New England Biolabs: 3.0/5.0 (33.3%)
```

## 🚀 Próximas Mejoras Posibles

### Opción A: Visualización
- [ ] Dashboard con gráficos (Plotly/Recharts)
- [ ] Comparación visual de productos
- [ ] Timeline de precios
- [ ] Network graph de vendors

### Opción B: Más Inteligencia
- [ ] ML para ranking (XGBoost/LightGBM)
- [ ] NER para extracción de specs
- [ ] Embeddings para similaridad semántica
- [ ] Predicción de satisfacción

### Opción C: Más Datos
- [ ] APIs adicionales (Sigma-Aldrich, etc.)
- [ ] Web scraping de catálogos
- [ ] Base de datos SQL (PostgreSQL)
- [ ] Redis para caché distribuido

### Opción D: Deployment
- [ ] Docker containerization
- [ ] Railway/Render deployment
- [ ] CI/CD con GitHub Actions
- [ ] Monitoreo con Prometheus

### Opción E: Features Avanzados
- [ ] Comparación de carritos completos
- [ ] Detección de productos complementarios
- [ ] Alertas de precios
- [ ] Sistema de notificaciones

## 🐛 Issues Conocidos

- ⚠️ Streamlit warning sobre `use_container_width` (deprecation, no afecta funcionalidad)

## 📝 Notas de Desarrollo

- **Python**: 3.10+
- **Framework principal**: FastAPI + Streamlit
- **LLM**: Groq (Llama 3.3-70b-versatile)
- **Cache**: File-based (puede migrar a Redis)
- **Storage**: JSON files (puede migrar a PostgreSQL)

## 🔧 Cómo Ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
GROQ_API_KEY=tu_key
SERPAPI_KEY=tu_key
PUBMED_EMAIL=tu_email

# Ejecutar Streamlit
streamlit run app_streamlit.py

# O ejecutar API
uvicorn main:app --reload
```

## 📚 Documentación Adicional

- Configuración de APIs: Ver `config.py`
- Sistema de reglas: Ver `rules.py` (R1-R5)
- Feedback system: Ver `feedback_system.py`
- LLM agent: Ver `llm_agent.py`

---

**Última actualización**: 2025-10-16
**Estado**: ✅ Funcional y operativo
**Siguiente paso sugerido**: Dashboard visual o Deployment