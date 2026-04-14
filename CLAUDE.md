# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **RAG (Retrieval-Augmented Generation) conversational assistant** for a Colombian bank's institutional website. The system extracts, vectorizes, and indexes content from the bank's website, then provides a conversational interface where users can ask questions about that content with conversation history tracking.

### Key Features
- **Web Scraping**: Extract content from configurable bank website URL
- **Vector Indexing**: Chroma DB for vector storage and retrieval
- **Conversation Memory**: Track conversation history per user ID with configurable context window (N previous messages)
- **RAG Pipeline**: Retrieve relevant documents and generate contextual responses via Claude API
- **User Interface**: Interactive Q&A interface
- **Cloud-Ready**: Deployed on Vercel with GitHub integration

## Technology Stack

```
Backend:        Python 3.10+
Web Framework:  FastAPI or Flask (lightweight, async-friendly)
Vector DB:      Chroma DB (local or cloud)
LLM:            Claude API (via Anthropic SDK)
Frontend:       Next.js + TypeScript (optional, separate repo)
Infrastructure: Vercel (API + frontend), Supabase MCP integration
VCS:            GitHub with Vercel auto-deployment
```

## Project Structure (Expected)

```
agenteBBVA/
├── CLAUDE.md                          # This file
├── README.md                          # User-facing documentation
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore
├── pyproject.toml                     # Project metadata (if using poetry)
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app entry point
│   ├── config.py                      # Configuration (API keys, URLs, parameters)
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── web_scraper.py             # Website content extraction
│   │
│   ├── vectorizer/
│   │   ├── __init__.py
│   │   ├── embedding.py               # Text embedding logic
│   │   └── chroma_store.py            # Chroma DB interactions
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py               # Document retrieval logic
│   │   └── generator.py               # Response generation with Claude API
│   │
│   ├── conversation/
│   │   ├── __init__.py
│   │   └── memory.py                  # Conversation history management
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes.py                  # API endpoints
│       └── models.py                  # Pydantic request/response schemas
│
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_vectorizer.py
│   └── test_rag.py
│
└── notebooks/                         # Development/analysis notebooks
    └── exploration.ipynb
```

## Key Architecture Components

### 1. **Web Scraper** (`src/scraper/web_scraper.py`)
- Configurable URL parameter for bank website
- Extracts text content (handle JavaScript-rendered content if needed)
- Cleans and chunks content for vectorization
- **Dependencies**: `beautifulsoup4`, `requests`, or `selenium` if JS-heavy

### 2. **Vectorization & Storage** (`src/vectorizer/`)
- Embed text chunks using Claude's embeddings API or open-source models (sentence-transformers)
- Store in Chroma DB with metadata (source URL, chunk index, timestamp)
- Support for batch indexing and incremental updates

### 3. **RAG Retriever** (`src/rag/retriever.py`)
- Retrieve top-K relevant documents from Chroma DB based on query similarity
- Return ranked results with relevance scores

### 4. **Response Generator** (`src/rag/generator.py`)
- Use Claude API with retrieved context
- Format prompt with conversation history and retrieved documents
- Configure token limits and temperature for consistent responses

### 5. **Conversation Memory** (`src/conversation/memory.py`)
- Store conversation history by user ID
- Retrieve last N messages (configurable parameter)
- Support persistent storage (Supabase via MCP or SQLite for local dev)

### 6. **API Layer** (`src/api/routes.py`)
- `POST /scrape` – Trigger scraping and indexing from configured URL
- `POST /ask` – Submit question with user ID, get response with sources
- `GET /history/{user_id}` – Retrieve conversation history
- `DELETE /history/{user_id}` – Clear conversation for user

## Common Development Commands

### Setup
```bash
# Clone repository and enter directory
git clone https://github.com/your-org/agenteBBVA.git
cd agenteBBVA

# Create virtual environment (Python 3.10+)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template and configure
cp .env.example .env
# Edit .env with:
#   - ANTHROPIC_API_KEY (Claude API)
#   - BANK_WEBSITE_URL (target website)
#   - CONTEXT_WINDOW (N previous messages, e.g., 5)
#   - CHROMA_DB_PATH (local path or cloud credentials)
```

### Development
```bash
# Run FastAPI server (auto-reload on changes)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Interactive testing in Python shell
python -c "from src.scraper import web_scraper; web_scraper.scrape_and_index('https://...')"

# Run specific test
pytest tests/test_rag.py::test_retrieval -v
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only integration tests (requires Chroma + API keys)
pytest tests/ -m integration -v
```

### Data & Indexing
```bash
# Initial scrape and index
python -m src.scraper.web_scraper --url "https://bank.com.co" --index

# Check indexed data in Chroma DB
python -c "from src.vectorizer import chroma_store; print(chroma_store.get_stats())"

# Clear vector index (careful!)
python -m src.vectorizer.chroma_store --clear
```

### Deployment
```bash
# Deploy to Vercel (requires Vercel CLI)
vercel deploy

# Preview before production
vercel --prod
```

## Configuration Parameters

All configurable via environment variables in `.env`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `BANK_WEBSITE_URL` | str | (required) | Root URL of bank website to scrape |
| `ANTHROPIC_API_KEY` | str | (required) | Claude API key |
| `CONTEXT_WINDOW` | int | 5 | Number of previous messages to include in context |
| `CHUNK_SIZE` | int | 500 | Characters per text chunk for vectorization |
| `CHUNK_OVERLAP` | int | 100 | Overlap between chunks |
| `RETRIEVAL_TOP_K` | int | 5 | Number of documents to retrieve per query |
| `CHROMA_COLLECTION` | str | "bank_content" | Chroma collection name |
| `CHROMA_DB_PATH` | str | "./chroma_db" | Local path or cloud connection string |
| `MAX_CONVERSATION_LENGTH` | int | 100 | Max messages to store per user |

## Supabase MCP Integration

### Setup (Optional but Recommended)
1. Configure Supabase MCP in `settings.json` for authenticated access to Supabase PostgreSQL
2. Create table schema for conversation history:
   ```sql
   CREATE TABLE conversations (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id VARCHAR(255) NOT NULL,
     messages JSONB NOT NULL,
     created_at TIMESTAMP DEFAULT NOW(),
     updated_at TIMESTAMP DEFAULT NOW()
   );
   CREATE INDEX idx_conversations_user_id ON conversations(user_id);
   ```
3. Update `src/conversation/memory.py` to use Supabase backend instead of local storage

## Important Patterns & Decisions

### 1. **Chunking Strategy**
- Text is chunked with overlap to maintain context across splits
- Metadata (source URL, page number) preserved with each chunk for source attribution
- Configurable `CHUNK_SIZE` and `CHUNK_OVERLAP` in `.env`

### 2. **Conversation Context**
- Only last `CONTEXT_WINDOW` messages sent to Claude to control costs
- Full history stored for user reference but not in LLM prompt
- Each message tagged with timestamp and role (user/assistant)

### 3. **Error Handling**
- Scraping failures: Log and notify, don't block user queries on stale index
- Vector DB failures: Graceful degradation or retry logic
- API rate limits: Queue requests and backoff strategy

### 4. **Frontend Integration (if using Next.js)**
- Separate Next.js repo can call this FastAPI backend via CORS
- Vercel will host Next.js frontend, Python API can run as Vercel serverless function or separate service
- Alternative: Use FastAPI's `starlette.staticfiles` to serve Next.js build files directly

## Vercel Deployment Notes

### For Python API on Vercel:
- Use Vercel's Python runtime (requires `api/` directory structure)
- Install `vercel` CLI: `npm i -g vercel`
- Configure `vercel.json`:
  ```json
  {
    "buildCommand": "pip install -r requirements.txt",
    "outputDirectory": "src",
    "functions": {
      "api/*.py": {
        "runtime": "python3.11"
      }
    }
  }
  ```
- Environment variables set in Vercel dashboard (Project Settings > Environment Variables)

### For GitHub Auto-Deploy:
1. Push to GitHub repo
2. Link repo to Vercel project
3. Configure Vercel to auto-deploy on `main` branch pushes
4. Vercel will run build command and deploy automatically

## Testing Strategy

- **Unit tests**: Mock Chroma DB and Claude API for fast feedback
- **Integration tests**: Use local Chroma DB and real (or test) API keys
- **Fixtures**: Sample website content and Q&A pairs in `tests/fixtures/`

## Debugging Tips

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload

# Inspect Chroma DB contents
python -c "from src.vectorizer.chroma_store import ChromaStore; db = ChromaStore(); print(db.collection.get())"

# Test Claude API connectivity
python -c "from anthropic import Anthropic; c = Anthropic(); print(c.models.list())"

# Profile vectorization performance
time python -m src.scraper.web_scraper --url "https://..." --index
```

## Performance Considerations

- **Scraping**: Run as background job (Celery/APScheduler) if frequent updates needed
- **Embedding**: Batch vectorization for large documents (e.g., 1000+ chunks)
- **Retrieval**: Chroma DB is local/fast, but consider pagination for large result sets
- **Response Generation**: Claude API calls are sequential; consider async with `httpx.AsyncClient` if many concurrent users

## Security & Compliance

- **API Keys**: Never commit `.env`; use `settings.json` hooks or Vercel secrets
- **Conversation Data**: If using Supabase, ensure row-level security (RLS) restricts users to their own conversations
- **Rate Limiting**: Implement per-user or per-IP rate limits in FastAPI middleware
- **Input Validation**: Validate user IDs and queries against injection attacks

---

**Last Updated**: 2026-04-13  
**Status**: Project initialization phase – ready for implementation
