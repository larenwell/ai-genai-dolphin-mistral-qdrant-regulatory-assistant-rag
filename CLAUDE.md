# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) assistant for Spanish regulatory compliance queries with a unique bilingual architecture:
- **Knowledge Base**: Pure English documents
- **User Interface**: Spanish only
- **Translation Pipeline**: ES→EN (query) → EN retrieval → EN context → ES response
- Uses Mistral AI for LLM and OCR, Qdrant for vector storage, Ollama for embeddings

## Essential Commands

### System Management
```bash
# Start entire system (6 services: Qdrant, Ollama, PostgreSQL, LocalStack, RAG, Prisma)
./rag_system.sh start

# Check status of all services
./rag_system.sh status

# View detailed system health
./rag_system.sh check

# Stop all services
./rag_system.sh stop

# Emergency restart (kills all processes and containers)
./rag_system.sh emergency

# Monitor services continuously
./rag_system.sh monitor [interval_seconds]
```

### Development Workflow
```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run main application (requires all services running)
chainlit run src/ui/app.py --host 0.0.0.0 --port 8000

# Start Qdrant only
./rag_system.sh start qdrant

# Start Ollama only
./rag_system.sh start ollama

# View RAG service logs
./rag_system.sh logs rag

# View Prisma Studio logs
./rag_system.sh logs datalayer
```

### Document Ingestion Pipeline
```bash
# STEP 1: Extract PDFs/DOCX → Markdown (uses Mistral OCR)
python3 src/extraction/generate_markdown.py

# STEP 2: Process Markdown → Chunks → Embeddings → Qdrant
python3 src/ingestion/test_recursive_character_chunking.py

# STEP 3: Validate ingestion completeness
python3 scripts/validate_ingestion_status.py

# Alternative chunking methods
python3 src/ingestion/test_semantic_chunking.py
python3 src/ingestion/test_structural_chunking.py
python3 src/ingestion/test_hybrid_chunking.py
```

### Testing and Evaluation
```bash
# Run RAG evaluation with RAGAS metrics
cd src/evaluation/
python3 evaluate_ragas.py

# Translate documents batch (English → Spanish or vice versa)
python3 src/translation/translate_documents_batch.py \
  --input-dir output/markdown/NFPA \
  --output-dir output/markdown/NFPA_EN \
  --resume
```

## Critical Architecture Details

### Translation Pipeline (FASE B)
The system uses **explicit translation** (not mental translation by LLM):

1. **User asks in Spanish** → `translate_retrieval.py` translates to English
2. **Query embedding** → Generated from English translation using `nomic-embed-text`
3. **Qdrant search** → Retrieves English context from KB
4. **Context translation** → English context translated back to Spanish
5. **LLM generation** → Mistral generates Spanish response from Spanish context

**Critical files:**
- `src/translation/translate_retrieval.py` - Real-time Q&A translation
- `config/prompt_config.py` - Language configuration and prompts
- `src/ui/app.py` - Main application with translation pipeline integration

### Question Type Classification
The system classifies questions into 4 types to optimize response style:

- **factual**: Short answers with specific data (e.g., "What is the deadline?")
- **interpretative**: Detailed explanations with legal reasoning
- **comparative**: Side-by-side comparisons of regulations
- **procedural**: Step-by-step process instructions

Classification happens in `src/ui/app.py:classify_question_type()` and affects prompt engineering in `config/prompt_config.py:RESPONSE_STYLES`.

### Service Dependencies
The RAG system requires all 6 services running simultaneously:

1. **Qdrant** (port 6333) - Vector database for embeddings
2. **Ollama** (port 11434) - Local embeddings with `nomic-embed-text` model
3. **PostgreSQL** (port 5432) - Chainlit data layer persistence
4. **LocalStack** (port 4566) - AWS S3 emulation for Chainlit
5. **Chainlit RAG** (port 8000) - Main application
6. **Prisma Studio** (port 5555) - Database management UI

**Always validate services before starting RAG:**
```bash
./rag_system.sh validate
```

### Embedding and Chunking Strategy
- **Model**: `nomic-embed-text` via Ollama (768 dimensions)
- **Distance metric**: Cosine similarity
- **Default chunking**: Recursive character splitting (1000 chars, 200 overlap)
- **Chunking methods**: recursive_character, semantic, structural, hybrid_p80_markdown
- **Top-K**: Dynamic based on question type (3-7 chunks)

**Key insight**: Different question types use different `top_k` values:
- Factual: top_k=3 (minimal context)
- Interpretative: top_k=5 (moderate context)
- Comparative: top_k=7 (extensive context)
- Procedural: top_k=5 (moderate context)

### File Organization
```
src/
├── embeddings/embedding_qdrant.py    # Qdrant client with auto-collection creation
├── llm/mistral_llm.py                # Mistral LLM with dynamic prompts
├── translation/translate_retrieval.py # Real-time ES↔EN translation
├── extraction/generate_markdown.py    # PDF/DOCX → Markdown with Mistral OCR
├── ingestion/                         # Chunking and vector storage scripts
├── ui/app.py                          # Chainlit interface with question classification
└── evaluation/                        # RAGAS evaluation framework

config/
├── prompt_config.py                   # Centralized prompts and language config
└── display_config.py                  # UI display configuration

output/
├── markdown/                          # Extracted markdown by category
├── chunking/                          # Generated chunks by method
├── embeddings_preview/                # Embedding previews for validation
├── analysis/                          # Ingestion validation reports
└── evaluation/                        # RAGAS evaluation results
```

## Common Development Tasks

### Adding New Documents
1. Place PDFs/DOCX in `data/temp/`
2. Run extraction: `python3 src/extraction/generate_markdown.py`
3. Output appears in `output/markdown/`
4. Run ingestion: `python3 src/ingestion/test_recursive_character_chunking.py`
5. Validate: `python3 scripts/validate_ingestion_status.py`

### Modifying Prompts
Edit `config/prompt_config.py`:
- `SYSTEM_PROMPTS["rag_assistant"]` - Base system prompt
- `RESPONSE_STYLES` - Question type-specific instructions
- `USER_PROMPTS["rag_query"]` - User prompt template

Changes take effect immediately (restart Chainlit app).

### Debugging Service Connectivity
```bash
# Check Qdrant
curl http://localhost:6333/collections

# Check Ollama
curl http://localhost:11434/api/tags

# Check PostgreSQL
pg_isready -h localhost -p 5432

# Check LocalStack
curl http://localhost:4566/health

# Check all services
./rag_system.sh check
```

### Handling Chainlit Version Issues
The project uses Chainlit <2.6.0 to avoid data layer dependency issues:

```bash
# If you encounter Google Cloud Storage errors:
CHAINLIT_DISABLE_DATA_LAYER=true chainlit run src/ui/app.py

# Or ensure correct version:
uv remove chainlit
uv add "chainlit<2.6.0"
```

## Key Implementation Patterns

### Error Handling in Services
All service clients (`EmbeddingControllerQdrant`, `MistralLLM`) include:
- Automatic retry logic (3 attempts with exponential backoff)
- Connection validation on initialization
- Helpful error messages with remediation steps
- Graceful degradation when possible

### Metadata Structure
Every chunk stored in Qdrant includes:
```python
{
    "document_id": "unique_doc_identifier",
    "book_title": "Document Title",
    "chunk_index": 0,
    "text": "chunk content",
    "total_chunks": 100,
    "source_file": "original_filename.pdf"
}
```

Query by `document_id` to retrieve all chunks for a document.

### Translation Caching
`translate_retrieval.py` uses:
- In-memory LRU cache for repeated translations
- Batch translation support to reduce API calls
- Language auto-detection with `langdetect`

## Environment Variables Required

```bash
# Mistral AI (required)
MISTRAL_API_KEY=your_mistral_api_key

# Qdrant (required)
QDRANT_COLLECTION_NAME=asistente-normativa-sincro-kb
QDRANT_URL=http://localhost:6333  # optional, defaults to localhost

# PostgreSQL for Chainlit (required)
DATABASE_URL=postgresql://root:root@localhost:5432/postgres

# AWS LocalStack (optional, for Chainlit S3)
BUCKET_NAME=my-bucket
APP_AWS_ACCESS_KEY=random-key
APP_AWS_SECRET_KEY=random-key
APP_AWS_REGION=eu-central-1
DEV_AWS_ENDPOINT=http://localhost:4566

# Document paths (optional)
PDF_FOLDER_PATH=../data/test
```

## Testing Strategy

### Validation Workflow
1. **Ingestion validation**: Checks all expected chunks are in Qdrant
2. **Translation validation**: Ensures ES↔EN roundtrip maintains meaning
3. **RAG evaluation**: RAGAS metrics (context_recall, answer_relevancy, faithfulness)
4. **Service health**: Continuous monitoring with `./rag_system.sh monitor`

### Evaluation Metrics
Located in `src/evaluation/`:
- Context Recall: Did we retrieve the right documents?
- Answer Relevancy: Is the answer on-topic?
- Faithfulness: Is the answer grounded in context?

## Troubleshooting

### "Qdrant not responding"
```bash
# Check if running
docker ps | grep qdrant

# View logs
docker logs qdrant-rag

# Restart
./rag_system.sh start qdrant
```

### "Ollama model not found"
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull nomic-embed-text
```

### "RAG service won't start"
```bash
# Always validate dependencies first
./rag_system.sh validate

# Start missing services
./rag_system.sh start qdrant
./rag_system.sh start ollama

# Then start RAG
./rag_system.sh start rag
```

### "Empty or incorrect responses"
1. Check Qdrant has data: `curl http://localhost:6333/collections`
2. Verify collection name in `.env` matches Qdrant collection
3. Run validation: `python3 scripts/validate_ingestion_status.py`
4. Check question classification: Add debug prints in `classify_question_type()`

## Important Notes

- **Never commit `.env`** - Contains Mistral API keys
- **Screen sessions**: RAG and Prisma run in screen sessions (use `screen -r [service-name]` to attach)
- **Persistent storage**: Qdrant data persists in `qdrant_storage/` directory
- **Output organization**: All generated files go to `output/` directory structure
- **Language assumption**: KB is English-only, UI is Spanish-only
- **Docker requirement**: All services run in Docker except Ollama (which can run natively or containerized)