"""
FastAPI Main Application — Multilingual Agricultural AI Assistant with RAG
Endpoints: /api/chat, /api/upload-data, /api/health, /api/languages, /api/stats
"""

import os
import sys
import time
import traceback
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Local modules
from language_detector import detect_language, SUPPORTED_LANGUAGES
from prompt_templates import get_suggestions
from query_logger import initialize_logger, log_query, get_stats
import rag_engine
import knowledge_base
import claude_client


# === Pydantic Models ===

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Farmer's question")
    language_hint: Optional[str] = Field(None, description="Optional language code hint")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class ChatResponse(BaseModel):
    success: bool
    response: str
    detected_language: dict
    suggestions: list[str]
    context_used: int
    model_used: str
    response_time_ms: int


class UploadDataRequest(BaseModel):
    category: str = Field(default="custom", description="Knowledge category")
    documents: list[dict] = Field(..., min_length=1, description="Documents to add")


class UploadDataResponse(BaseModel):
    success: bool
    documents_added: int
    vectors_added: int
    errors: list[str]


# === Application Lifecycle ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    print("=" * 60)
    print("🌾 Krishi Mitra — Multilingual Agricultural AI Assistant")
    print("=" * 60)

    # Initialize query logger
    initialize_logger()
    print("✅ Query logger initialized")

    # Load knowledge base and build FAISS index
    print("\n📚 Loading agricultural knowledge base...")
    docs = knowledge_base.load_initial_data()

    if docs:
        print(f"\n🔧 Building FAISS vector index for {len(docs)} documents...")
        vectors_added = rag_engine.add_documents(docs)
        print(f"✅ FAISS index built with {vectors_added} vectors")
    else:
        print("⚠️ No knowledge base documents found. The assistant will have limited knowledge.")

    # Show LLM API status
    if claude_client.USE_GEMINI:
        print("\n✅ LLM API: Gemini (gemini-2.0-flash) connected")
    elif claude_client.USE_CLAUDE:
        print("\n✅ LLM API: Claude connected")
    else:
        print("\n⚠️ LLM API: Not configured (using built-in fallback)")
        print("   Set GOOGLE_API_KEY or ANTHROPIC_API_KEY environment variable")

    print("\n" + "=" * 60)
    print("🚀 Service ready! API docs at http://localhost:8000/docs")
    print("=" * 60 + "\n")

    yield

    print("\n🛑 Shutting down Krishi Mitra service...")


# === FastAPI App ===

app = FastAPI(
    title="Krishi Mitra — Multilingual Agricultural AI",
    description="RAG-powered agricultural assistant supporting 11 Indian languages",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Node.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Endpoints ===

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    index_stats = rag_engine.get_index_stats()
    return {
        "status": "healthy",
        "service": "Krishi Mitra RAG Service",
        "llm_api": "gemini" if claude_client.USE_GEMINI else ("claude" if claude_client.USE_CLAUDE else "fallback"),
        "index_vectors": index_stats["total_vectors"],
        "index_documents": index_stats["total_documents"],
        "supported_languages": len(SUPPORTED_LANGUAGES),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint — processes multilingual queries through RAG pipeline.
    """
    start_time = time.time()

    try:
        query = request.message.strip()

        # Step 1: Detect language
        lang_result = detect_language(query, request.language_hint)
        print(f"[Chat] Language: {lang_result.language_name} ({lang_result.confidence:.0%}) | Query: {query[:80]}...")

        # Step 2: Retrieve relevant context from FAISS
        context_chunks = rag_engine.search(query, top_k=5, score_threshold=0.25)
        context_ids = [c.get("doc_id", c.get("id", "")) for c in context_chunks]
        print(f"[Chat] Retrieved {len(context_chunks)} context chunks")

        # Step 3: Generate response via Claude (or fallback)
        llm_result = claude_client.generate_response(
            query=query,
            context_chunks=context_chunks,
            language_code=lang_result.language_code,
        )

        response_text = llm_result["response"]
        total_time_ms = int((time.time() - start_time) * 1000)

        # Step 4: Log the query
        log_query(
            user_message=query,
            detected_language=lang_result.language_code,
            language_confidence=lang_result.confidence,
            context_ids=context_ids,
            response=response_text,
            response_time_ms=total_time_ms,
            model_used=llm_result["model_used"],
        )

        # Step 5: Get language-appropriate suggestions
        suggestions = get_suggestions(lang_result.language_code)

        return ChatResponse(
            success=True,
            response=response_text,
            detected_language=lang_result.to_dict(),
            suggestions=suggestions,
            context_used=len(context_chunks),
            model_used=llm_result["model_used"],
            response_time_ms=total_time_ms,
        )

    except Exception as e:
        traceback.print_exc()
        total_time_ms = int((time.time() - start_time) * 1000)

        # Log the error
        log_query(
            user_message=request.message,
            detected_language="unknown",
            language_confidence=0,
            context_ids=[],
            response="",
            response_time_ms=total_time_ms,
            error=str(e),
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}",
        )


@app.post("/api/upload-data", response_model=UploadDataResponse)
async def upload_data(request: UploadDataRequest):
    """
    Upload new agricultural knowledge data to enhance the assistant.
    """
    try:
        category = request.category
        documents = request.documents

        # Validate and save
        valid_count, errors = knowledge_base.add_custom_data(documents, category)

        # Add to FAISS index
        vectors_added = 0
        if valid_count > 0:
            vectors_added = rag_engine.add_documents(
                [d for d in documents if d.get("content")]
            )

        return UploadDataResponse(
            success=valid_count > 0,
            documents_added=valid_count,
            vectors_added=vectors_added,
            errors=errors,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload data: {str(e)}",
        )


@app.get("/api/languages")
async def list_languages():
    """List all supported languages."""
    languages = []
    for code, info in SUPPORTED_LANGUAGES.items():
        languages.append({
            "code": code,
            "name": info["name"],
            "native": info["native"],
            "tts_code": info["tts_code"],
        })
    return {"languages": languages, "total": len(languages)}


@app.get("/api/stats")
async def query_stats():
    """Get query statistics and analytics."""
    stats = get_stats()
    index_stats = rag_engine.get_index_stats()

    return {
        "queries": stats,
        "knowledge_base": index_stats,
        "categories": knowledge_base.get_categories(),
    }


@app.get("/api/upload-data/format")
async def upload_format():
    """Get the expected data format for the upload endpoint."""
    return knowledge_base.get_sample_data()


@app.post("/api/rebuild-index")
async def rebuild_index():
    """Rebuild the FAISS index from all data files."""
    try:
        vectors = rag_engine.rebuild_from_data_dir()
        return {"success": True, "vectors_built": vectors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Run ===

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("RAG_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
