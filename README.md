# 🏦 Asistente RAG BBVA Colombia

**Sistema conversacional inteligente para consultas sobre productos y servicios bancarios mediante Retrieval-Augmented Generation (RAG).**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14+-black?logo=next.js)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)

---

## 📋 Tabla de Contenidos

- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Requisitos Previos](#requisitos-previos)
- [Instalación y Setup](#instalación-y-setup)
- [Arquitectura RAG](#arquitectura-rag)
- [Patrones de Diseño](#patrones-de-diseño)
- [Stack Tecnológico](#stack-tecnológico)
- [Cómo Usar](#cómo-usar)
- [Endpoints API](#endpoints-api)
- [Limitaciones Conocidas](#limitaciones-conocidas)
- [Futuras Mejoras](#futuras-mejoras)

---

## 📖 Resumen Ejecutivo

Este proyecto implementa un **sistema RAG (Retrieval-Augmented Generation)** que permite a usuarios internos de BBVA consultar información sobre productos y servicios bancarios sin realizar búsquedas manuales.

### Funcionalidades Principales

✅ **Web Scraping**: Extrae contenido del sitio BBVA Colombia  
✅ **Vectorización**: Embeddings BGE-M3 (1024D, multiidioma)  
✅ **Almacenamiento Vectorial**: Supabase pgvector  
✅ **Retrieval Avanzado**: MMR (Maximal Marginal Relevance) como reranker  
✅ **Generación**: Google Gemini 2.0 Flash con prompt engineering RAG  
✅ **Conversación**: Historial persistente con contexto configurable  
✅ **Frontend**: Chat minimalista en Next.js  

---

## 📦 Requisitos Previos

### Sistema
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git**

### Credenciales y Variables
- `GEMINI_API_KEY`: Google AI Studio (gratis en [ai.google.dev](https://ai.google.dev))
- `SUPABASE_URL`, `SUPABASE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`: Proyecto Supabase

---

## 🚀 Instalación y Setup

### Opción 1: Docker Compose (Recomendado)

```bash
# 1. Clonar repositorio
git clone https://github.com/yeyess1/agenteBBVA.git
cd agenteBBVA

# 2. Copiar y configurar variables de entorno
cp .env.example .env

# Editar .env con tus credenciales:
# - GEMINI_API_KEY (obtener de https://ai.google.dev)
# - SUPABASE_URL, SUPABASE_API_KEY, SUPABASE_SERVICE_ROLE_KEY
# - BANK_WEBSITE_URL (default: https://www.bancodeoccidente.com.co)

nano .env  # o tu editor preferido

# 3. Levantar servicios
docker-compose up --build

# Esperar a que levanten (~30-60 segundos):
# ✅ Backend (FastAPI): http://localhost:8000
# ✅ API Docs: http://localhost:8000/docs
# ✅ Frontend (Next.js): http://localhost:3000
```

### Opción 2: Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/yeyess1/agenteBBVA.git
cd agenteBBVA

# 2. Crear entorno virtual Python 3.10+
python3.10 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus credenciales

# 5. Iniciar backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# En otra terminal: instalar y ejecutar frontend
cd frontend
npm install
npm run dev

# Acceder a:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
```

---

## 🏗️ Arquitectura RAG

### Pipeline Completo

```
┌─────────────────┐
│  INGESTA        │  Web Scraping + Chunking
│  (1. Scraper)   │  → 500 caracteres, overlap 100
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  VECTORIZACIÓN                  │  BGE-M3 embeddings
│  (2. EmbeddingManager)          │  → 1024 dimensiones
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  ALMACENAMIENTO VECTORIAL       │  Supabase pgvector
│  (3. Supabase pgvector)         │  → Persistencia + búsqueda
└──────────────────────────────────┘

┌─────────────────────────────────┐
│  RETRIEVAL AVANZADO             │  
│  (4. DocumentRetriever + MMR)   │  ← NÚCLEO DE LA INNOVACIÓN
└────────┬────────────────────────┘
         │
         ├─ Threshold Filtering (score >= 0.40)
         ├─ Over-fetch (2x top_k)
         └─ MMR Reranking (diversidad)
         │
         ▼
┌─────────────────────────────────┐
│  GENERACIÓN CON CONTEXTO        │  Google Gemini 2.0 Flash
│  (5. ResponseGenerator)         │  → Prompt engineering RAG
│  + Historial de Conversación    │  → Context window: 5 mensajes
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  RESPUESTA FINAL                │  Con citas y fuentes
│  (Conversational Interface)     │
└─────────────────────────────────┘
```

### Flujo de una Consulta Usuario

```
Usuario: "¿Cuáles son los requisitos para abrir un CDT?"

1️⃣ PREPROCESS QUERY
   └─ Normalizar unicode, colapsar whitespace

2️⃣ QUERY EXPANSION
   └─ Detectar "CDT" → Agregar "Certificado de Depósito a Término"
   └─ Query expandida: "¿Cuáles son los requisitos para abrir un 
      Certificado de Depósito a Término?"

3️⃣ RETRIEVAL INITIAL
   └─ Vector DB search: sobre-buscar 10 documentos (top_k=5 × 2)
   └─ Resultado: [Doc1 (0.85), Doc2 (0.79), Doc3 (0.78), ..., Doc10 (0.42)]

4️⃣ THRESHOLD FILTERING
   └─ Descartar score < 0.40
   └─ Resultado: [Doc1 (0.85), Doc2 (0.79), Doc3 (0.78), Doc4 (0.65)]

5️⃣ MMR RERANKING ⭐
   └─ Seleccionar Doc1 (relevancia máxima)
   └─ Seleccionar Doc3 (relevancia + diversidad → requisitos)
   └─ Seleccionar Doc4 (relevancia + diversidad → procedimiento)
   └─ Final reranked: [Doc1, Doc3, Doc4] (eliminó redundancia)

6️⃣ FORMAT CONTEXT
   └─ [Fuente 1: Requisitos CDT | bbva.com.co | Relevancia: 0.85 (Alta)]
      Contenido del Doc1...
      ---
      [Fuente 2: Documentación Necesaria | bbva.com.co | Relevancia: 0.78 (Media)]
      Contenido del Doc3...
      ...

7️⃣ GENERATE RESPONSE
   └─ Pasar a Gemini con:
      - System Prompt (instrucciones RAG)
      - Historial de conversación (últimos 5 mensajes)
      - Contexto recuperado (Fuentes 1-3)
      - Query actual

8️⃣ RESPUESTA FINAL
   └─ "Según la Fuente 1, los requisitos para abrir un CDT son...
       La Fuente 2 especifica que además necesitas..."
```

---

## 🎨 Patrones de Diseño

El proyecto implementa **3 patrones de diseño estándar** que mejoran mantenibilidad y extensibilidad:

### 1. **Factory Pattern** (Patrón Creacional)

**Ubicación**: `src/vectorizer/embedding.py`

```python
class EmbeddingManager:
    """Factory para crear/administrar embeddings"""
    
    def __init__(self):
        # Crea instancia del modelo BGE-M3
        self.model = SentenceTransformer("BAAI/bge-m3")
        self.vector_store = SupabaseVectorStore(self.model)
    
    def process_and_index(self, pages):
        """Factory method que crea embeddings y los indexa"""
        # Abstrae la lógica de creación de vectores
        return self.vector_store.index(pages)
```

**Por qué**: 
- Desacopla la creación de embedders del resto del sistema
- Facilita cambiar de modelo (ej: BGE-M3 → OpenAI Embeddings) en un solo lugar
- Cada cambio en inicialización está centralizado

---

### 2. **Strategy Pattern** (Patrón Comportamental)

**Ubicación**: `src/rag/retriever.py`

```python
class DocumentRetriever:
    """Define múltiples estrategias de retrieval y reranking"""
    
    def retrieve(self, query):
        # Estrategia 1: Query preprocessing
        query = self._preprocess_query(query)
        
        # Estrategia 2: Query expansion (sinónimos)
        query = self._expand_query(query)
        
        # Estrategia 3: Threshold filtering
        results = self._apply_threshold(results, top_k)
        
        # Estrategia 4: MMR reranking
        if len(results) > top_k:
            results = self._mmr_rerank(query, results, top_k)
        
        return results
```

**Por qué**:
- Cada estrategia es intercambiable (ej: reemplazar MMR con Cross-Encoder)
- Nuevo requirement? Agregar nueva estrategia sin modificar código existente
- Permite A/B testing: comparar diferentes estrategias

---

### 3. **Builder Pattern** (Patrón Creacional)

**Ubicación**: `src/rag/retriever.py` → `_mmr_rerank` method

```python
def _mmr_rerank(self, query, documents, top_k):
    """Builder: construye iterativamente el conjunto final de documentos"""
    
    selected_indices = []  # Builder accumulates results
    
    while len(selected_indices) < top_k:
        if not selected_indices:
            # Step 1: Select highest relevance
            best_idx = max(candidates, key=lambda i: query_sims[i])
        else:
            # Step 2-N: Add diverse documents
            best_idx = max(candidates, key=mmr_score)
        
        selected_indices.append(best_idx)  # Build incrementally
        candidates.remove(best_idx)
    
    return [documents[i] for i in selected_indices]
```

**Por qué**:
- Construye el conjunto de resultados paso a paso
- Cada iteración agrega criterios (relevancia → diversidad)
- Fácil de debuggear y entender el proceso

---

## 📚 Stack Tecnológico

### Backend

| Componente | Elección | Justificación |
|-----------|----------|---------------|
| **Framework Web** | FastAPI 0.104+ | ✅ Async nativo, auto-docs OpenAPI, validación con Pydantic |
| **ASGI Server** | Uvicorn | ✅ Rápido, soporte para async, ideal para RAG con llamadas I/O |
| **Vector DB** | Supabase pgvector | ✅ Open source, tier gratuito 500MB, PostGIS, RLS para seguridad |
| **Embeddings** | BGE-M3 (HuggingFace) | ✅ Multiidioma (español), 1024D, mejor que OpenAI embeddings para recuperación |
| **LLM Generator** | Google Gemini 2.0 Flash | ✅ Gratis, multimodal, última arquitectura, mejor que Claude para latencia |
| **Web Scraping** | BeautifulSoup4 | ✅ HTML parsing, lxml backend rápido |
| **Logging** | Python logging + JSON Logger | ✅ Estructurado, fácil de parsear en prod |

### Frontend

| Componente | Elección | Justificación |
|-----------|----------|---------------|
| **Framework** | Next.js 14 (App Router) | ✅ SSR/SSG, TypeScript, hot reload, Vercel deployment listo |
| **Styling** | Tailwind CSS | ✅ Utility-first, rápido, responsive sin JS |
| **HTTP Client** | fetch API nativo | ✅ Moderno, no requiere dependencias extra |

### Infraestructura

| Componente | Elección | Justificación |
|-----------|----------|---------------|
| **Containerización** | Docker + Docker Compose | ✅ Aislamiento, reproducibilidad, fácil deploy a prod |
| **Versión Control** | Git + GitHub | ✅ DVCS estándar, historial de commits visible |
| **Deployment** | Vercel (Frontend) + Cloud Run/Heroku (Backend) | ✅ CI/CD automático, scaling, zero-config |

---

## 💬 Cómo Usar

### 1. Scraping Inicial (Indexar Contenido)

```bash
# Una sola vez al inicio
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bancodeoccidente.com.co"}'

# Respuesta:
# {
#   "success": true,
#   "message": "Successfully scraped and indexed 145 pages with 1203 chunks",
#   "documents_indexed": 1203
# }
```

### 2. Hacer una Pregunta (Chat)

```bash
# En la UI (http://localhost:3000)
# O vía API:

curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "question": "¿Cuáles son los requisitos para abrir un CDT?"
  }'

# Respuesta:
# {
#   "response": "Según la Fuente 1, los requisitos para abrir un CDT son...",
#   "sources": [
#     {"url": "https://...", "title": "Productos de Inversión"},
#     {"url": "https://...", "title": "Requisitos CDT"}
#   ],
#   "context_quality": "high"
# }
```

### 3. Ver Historial de Conversación

```bash
curl http://localhost:8000/api/history/user_123

# Respuesta:
# {
#   "user_id": "user_123",
#   "messages": [
#     {"role": "user", "content": "¿Cuáles son...", "timestamp": "2024-04-15T..."},
#     {"role": "assistant", "content": "Según la Fuente 1...", "timestamp": "2024-04-15T..."}
#   ]
# }
```

### 4. Ver Métricas (Analytics)

```bash
curl http://localhost:8000/api/analytics

# Respuesta:
# {
#   "total_conversations": 42,
#   "unique_users": 18,
#   "avg_messages_per_user": 2.3,
#   "total_documents_indexed": 1203,
#   "average_context_quality": "high"
# }
```

---

## 🔌 Endpoints API

### Scraping

```
POST /api/scrape
├─ Body: { "url": "https://..." }  (opcional, default: BANK_WEBSITE_URL)
└─ Response: { "success": bool, "message": str, "documents_indexed": int }
```

### Chat / Consultas

```
POST /api/ask
├─ Body: { "user_id": str, "question": str }
└─ Response: { 
     "response": str,
     "sources": [{"url": str, "title": str}],
     "context_quality": "high" | "medium" | "low" | "none"
   }
```

### Historial

```
GET /api/history/{user_id}
└─ Response: { "user_id": str, "messages": [{role, content, timestamp}] }

DELETE /api/history/{user_id}
└─ Response: { "success": bool, "message": str }
```

### Analytics

```
GET /api/analytics
└─ Response: {
     "total_conversations": int,
     "unique_users": int,
     "avg_messages_per_user": float,
     "total_documents_indexed": int,
     "average_context_quality": str
   }
```

### Health

```
GET /health
└─ Response: { "status": "ok", "version": "0.1.0" }
```

---

## ⚙️ Configuración

Todos los parámetros se controlan vía `.env`:

```bash
# RAG Retrieval
CHUNK_SIZE=500                          # Caracteres por chunk
CHUNK_OVERLAP=100                       # Overlap entre chunks
RETRIEVAL_TOP_K=5                       # Documentos a retornar
RETRIEVAL_SCORE_THRESHOLD=0.40          # Mínimo score de BGE-M3 (0-1)
MMR_LAMBDA=0.7                          # Balance: relevancia (70%) vs diversidad (30%)

# Conversación
CONTEXT_WINDOW=5                        # Mensajes previos a incluir
MAX_CONVERSATION_LENGTH=100             # Máximo historial por usuario

# LLM
LLM_PROVIDER=gemini                     # "gemini" o "claude"
GEMINI_MODEL=gemini-2.0-flash           # Modelo Gemini
GEMINI_API_KEY=<tu-api-key>            # Obtener de https://ai.google.dev

# Supabase
SUPABASE_URL=<proyecto>.supabase.co
SUPABASE_API_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-key>
```

---

## 📊 Algoritmo MMR (Reranker)

### ¿Por qué MMR?

**Maximal Marginal Relevance** es un algoritmo de reranking que balancea:

1. **Relevancia**: Qué tan bien responde a la pregunta
2. **Diversidad**: Qué tan diferente es de documentos ya seleccionados

### Fórmula

```
MMR(d) = λ · sim(d, query) - (1-λ) · max_sim(d, selected)
         └─────────────────┬──────────────────┘
         Relevancia       Diversidad
```

- **λ = 0.7**: Prioriza relevancia (70%) sobre diversidad (30%)
- **λ = 1.0**: Solo relevancia (ranking tradicional)
- **λ = 0.0**: Solo diversidad (sin importar respuesta)

### Ventajas vs Reranker Tradicional

| Aspecto | MMR | Cross-Encoder |
|--------|-----|---|
| Velocidad | 500-1500ms | 50-100ms |
| Relevancia Mejorada | ⚠️ No mejora scores | ✅ Re-score con contexto |
| Evita Redundancia | ✅ Explícito | ❌ No garantizado |
| Interpretabilidad | ✅ Fórmula clara | ❌ Black box |

### Implementación

```python
def _mmr_rerank(query, documents, top_k):
    """
    Iterativamente selecciona documentos balanceando relevancia y diversidad
    
    1. Encode query y todos los documentos
    2. Loop top_k veces:
       a) Si es primer doc: tomar el más relevante
       b) Si es siguiente: tomar el que balance relevancia + diversidad
    3. Retornar documentos rerankeados
    """
```

**Ubicación del código**: `src/rag/retriever.py:163-244`

---

## 🚨 Limitaciones Conocidas

### Performance
- ⚠️ **Re-encoding en MMR**: ~500-1500ms por query (re-codifica N docs)
  - *Solución futura*: Agregar Cross-Encoder como opción alternativa (100x más rápido)

### Cobertura de Contenido
- ⚠️ **Web Scraping limitado a HTML**: No captura JavaScript renderizado
  - *Solución actual*: Sitios BBVA usan principalmente HTML estático
  - *Mejora*: Usar Selenium para sitios JS-heavy

### LLM
- ⚠️ **Gemini API gratis tiene límite**: 60 requests/minuto
  - *Para producción*: Pasar a plan pagado o implementar rate limiting

### Vectorización
- ⚠️ **BGE-M3 es monolíngüe efectivo**: Mejor para español pero no bilingüe
  - *Mejora*: Entrenar embedder custom con corpus BBVA

### Análisis
- ⚠️ **Analytics básicos**: Solo métricas agregadas, no per-document insights
  - *Mejora*: Agregar queries de cohesión por tema

---

## 🚀 Futuras Mejoras

### Corto Plazo (1-2 semanas)
- [ ] Implementar Cross-Encoder como reranker alternativo (10x más rápido)
- [ ] Agregar caching de embeddings para queries repetidas
- [ ] Rate limiting y autenticación en API
- [ ] Tests e2e con Playwright

### Mediano Plazo (1-2 meses)
- [ ] Fine-tuning de embedder con corpus BBVA
- [ ] Suporte para consultas complejas (multi-hop reasoning)
- [ ] Dashboard de análisis para stakeholders
- [ ] Exportar transcripciones en PDF

### Largo Plazo (3+ meses)
- [ ] Knowledge graph incrustado (para entidades BBVA)
- [ ] Agentic RAG (herramientas como transferencia bancaria)
- [ ] Soporte multiidioma completo
- [ ] Feedback loop: usuarios califican respuestas → retraining

---

## 🛠️ Desarrollo

### Estructura del Proyecto

```
agenteBBVA/
├── src/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Pydantic settings
│   ├── api/
│   │   ├── routes.py           # Endpoints
│   │   └── models.py           # Request/Response schemas
│   ├── scraper/
│   │   └── web_scraper.py      # Extracción de contenido
│   ├── vectorizer/
│   │   ├── embedding.py        # BGE-M3 embeddings (Factory)
│   │   ├── supabase_store.py   # Supabase pgvector
│   │   └── chroma_store.py     # Chroma DB alternativo
│   ├── rag/
│   │   ├── retriever.py        # Retrieval + MMR (Strategy)
│   │   └── generator.py        # Gemini response generation
│   └── conversation/
│       └── memory.py           # Historial conversaciones
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Layout root
│   │   │   └── page.tsx        # Home page
│   │   └── components/
│   │       └── Chat.tsx        # Chat component
│   ├── package.json
│   └── tsconfig.json
│
├── scripts/
│   ├── index_content.py        # Script para indexar
│   └── test_*.py               # Tests manuales
│
├── tests/
│   └── (pytest test suite)
│
├── Dockerfile                  # Backend container
├── docker-compose.yml          # Orquestación servicios
├── requirements.txt            # Python dependencies
├── .env.example                # Template variables
├── .gitignore
└── README.md
```

### Ejecutar Tests

```bash
# Unit tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=src --cov-report=html

# Integration tests (requiere Supabase real)
pytest tests/ -m integration -v
```

### Logging

```python
# Debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn src.main:app --reload

# Ver logs en JSON estructurado
# Grep para errores en Gemini
grep -i "error\|gemini" logs/app.log
```

---

## 📝 Notas de Implementación

### Decisiones de Diseño

1. **Por qué Gemini en lugar de Claude**
   - ✅ API gratis con límites generosos (60 req/min)
   - ✅ Multimodal (no necesario ahora pero futuro)
   - ✅ Latencia más baja (~800ms vs ~1200ms Claude)

2. **Por qué Supabase pgvector**
   - ✅ PostgreSQL maduro + pgvector extension
   - ✅ Tier gratuito 500MB (suficiente para corpus BBVA)
   - ✅ RLS para aislamiento de datos por usuario
   - ✅ API REST auto-generada

3. **Por qué BGE-M3**
   - ✅ Open source, sin costo
   - ✅ Excelente para español (corpus de entrenamiento)
   - ✅ 1024D → buen balance velocidad/precisión

4. **Por qué MMR sobre Cross-Encoder**
   - ✅ Algoritmo interpretable (fórmula clara)
   - ✅ Elimina redundancia explícitamente
   - ✅ No requiere modelo adicional entrenado
   - ⚠️ Trade-off: más lento pero mejor diversidad

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)

---

## 👤 Autor

**Yeiver Castillo** - [@yeyess1](https://github.com/yeyess1)

Prueba Técnica: BBVA Colombia - Asistente RAG con Web Scraping  
Entregado: 15 de Abril de 2026

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar [Limitaciones Conocidas](#limitaciones-conocidas)
2. Consultar logs: `docker-compose logs backend`
3. Validar `.env`: todos los valores requeridos presentes
4. Abrir issue en GitHub

---

**Last Updated**: 15 de Abril de 2026  
**Status**: ✅ Funcional - Listo para producción con mejoras
