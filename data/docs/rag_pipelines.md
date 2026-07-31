# RAG (Retrieval-Augmented Generation) — Complete Reference

## What is RAG?
RAG is an architecture that improves LLM responses by retrieving relevant documents from a knowledge base before generating a response. Instead of relying solely on parametric knowledge (what the LLM learned during training), RAG supplies external, up-to-date context at inference time.

## RAG Pipeline Stages

### 1. Indexing (offline)
```
Documents → Chunking → Embedding → Vector Store
```
- Split documents into chunks (typically 512–1024 tokens with overlap)
- Embed each chunk using an embedding model (all-MiniLM-L6-v2, OpenAI ada-002, etc.)
- Store embeddings in a vector database (ChromaDB, Pinecone, Weaviate, pgvector)

### 2. Retrieval (online)
```
User Query → Embed Query → ANN Search → Top-K Chunks
```
- Embed the user's question with the same embedding model
- Run approximate nearest-neighbor (ANN) search in the vector store
- Retrieve top-k most relevant chunks (typically 3-10)

### 3. Generation (online)
```
Top-K Chunks + Query → LLM Prompt → Response
```
- Inject retrieved chunks into the LLM prompt as context
- LLM generates a response grounded in the retrieved content
- Optionally include source citations

## Chunking Strategies

### Fixed-size chunking
Simple but can cut mid-sentence:
```python
chunks = [text[i:i+500] for i in range(0, len(text), 400)]  # 100-char overlap
```

### Semantic chunking
Split on paragraph/section boundaries. Better context coherence.

### Recursive character splitting (LangChain)
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
chunks = splitter.split_text(text)
```

## Embedding Models

| Model | Size | Quality | Speed | Cost |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 90MB | Good | Fast | Free (local) |
| all-mpnet-base-v2 | 420MB | Better | Moderate | Free (local) |
| OpenAI ada-002 | API | Excellent | Fast | $0.0001/1K tokens |
| Cohere embed-v3 | API | Excellent | Fast | $0.0001/1K tokens |

For local deployment: all-MiniLM-L6-v2 is the best balance of quality and speed.

## Vector Databases Comparison

| Database | Deployment | Scale | Persistence | Best For |
|---|---|---|---|---|
| ChromaDB | Local/Server | Small-Medium | SQLite/disk | Development, small apps |
| Pinecone | Managed cloud | Huge | Always-on | Production at scale |
| Weaviate | Self-hosted/cloud | Large | Disk | Complex filtering + hybrid search |
| pgvector | PostgreSQL ext | Medium | PostgreSQL | When you already use Postgres |
| Qdrant | Self-hosted/cloud | Large | Disk | High performance, Rust-based |
| FAISS | In-memory | Large | Manual | Research, offline batch search |

## Advanced RAG Techniques

### Hybrid Search
Combine dense (vector) + sparse (BM25 keyword) retrieval:
```python
# Dense score + BM25 score, weighted combination
final_score = 0.7 * dense_score + 0.3 * bm25_score
```

### Re-ranking
After retrieving top-20 via ANN, re-rank with a cross-encoder model for precision:
```python
from sentence_transformers import CrossEncoder
ranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
scores = ranker.predict([(query, chunk) for chunk in candidates])
```

### HyDE (Hypothetical Document Embeddings)
Generate a hypothetical answer, embed it, search with that embedding:
```python
hypothetical_answer = llm.invoke(f"Write a document that answers: {query}")
results = vector_store.query(hypothetical_answer)  # often outperforms direct query embedding
```

### Multi-Query Retrieval
Generate 3-5 variants of the query, retrieve for each, deduplicate:
```python
variants = llm.invoke(f"Generate 3 search queries for: {query}")
all_results = [retrieve(v) for v in variants]
deduplicated = list({r["id"]: r for r in chain(*all_results)}.values())
```

### Parent-Child Chunking
Store small chunks for precise retrieval, but return the parent chunk for more context:
```python
# Index child chunks (128 tokens) for retrieval
# Return parent chunks (512 tokens) to the LLM
```

## RAG Evaluation Metrics
- **Faithfulness**: Is the response grounded in retrieved context? (avoid hallucination)
- **Answer relevance**: Does the response answer the actual question?
- **Context precision**: Are the retrieved chunks actually relevant?
- **Context recall**: Did retrieval miss important chunks?

Tools: RAGAs, TruLens, LangSmith

## Common RAG Failures
1. **Chunking too small**: LLM loses context; increase chunk size or use parent-child
2. **Wrong embedding model**: Domain mismatch; fine-tune or use a domain-specific model
3. **Top-k too small**: Relevant chunk not retrieved; increase k, use re-ranking
4. **No metadata filtering**: Retrieval returns irrelevant sources; add where clauses
5. **Stale index**: Ingestion pipeline not running on new docs; add incremental updates
