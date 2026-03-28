"""
KB RETRIEVER (QDRANT)
=====================
What this module demonstrates:
  - Loading an existing Qdrant collection as a retriever.
  - Running semantic search and formatting context text for prompts.
  - Returning source labels so API layers can show explicit citations.
"""

import backend.env_bootstrap  # noqa: F401 — loads backend/.env for OpenAI embeddings when used as CLI

import os
from typing import List, Optional, Tuple
from pathlib import Path

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from backend.rag.config_paths import get_qdrant_path

# Ollama is optional
try:
    from langchain_community.embeddings import OllamaEmbeddings
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaEmbeddings = None

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", None)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLLECTION_NAME = "it_support_kb"


def get_embeddings(embeddings: Optional[any] = None):
    """
    Get the appropriate embeddings model based on configuration.

    Args:
        embeddings: Optional pre-configured embeddings model (for testing)

    Returns:
        Embeddings model (OpenAI or Ollama)
    """
    # Test hook: caller can inject a fake embedding model.
    if embeddings is not None:
        return embeddings

    # Runtime selection: openai (default) or ollama.
    if MODEL_PROVIDER == "ollama":
        if not OLLAMA_AVAILABLE:
            raise ImportError("langchain-ollama not installed. Install with: pip install langchain-ollama")
        return OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
    else:
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def get_qdrant_client(path: Optional[str] = None, url: Optional[str] = None) -> QdrantClient:
    """
    Get Qdrant client (either local or remote).

    Args:
        path: Local storage path (for disk-based mode)
        url: Remote Qdrant server URL (for server mode)

    Returns:
        QdrantClient instance
    """
    if url or QDRANT_URL:
        # Server mode
        return QdrantClient(
            url=url or QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
    else:
        # Local disk mode
        storage_path = path or get_qdrant_path()
        return QdrantClient(path=storage_path)


def get_retriever(
    persist_directory: Optional[str] = None,
    embeddings: Optional[any] = None,
    search_kwargs: Optional[dict] = None,
    collection_name: Optional[str] = None
):
    """
    Get a retriever from persisted vector store.

    Args:
        persist_directory: Directory containing persisted vectorstore
        embeddings: Optional embeddings model (for testing)
        search_kwargs: Optional search parameters (e.g., {"k": 5})
        collection_name: Name of the collection

    Returns:
        Retriever instance
    """
    # Step 1: normalize defaults.
    if collection_name is None:
        collection_name = COLLECTION_NAME

    if persist_directory is None:
        persist_directory = get_qdrant_path()

    if search_kwargs is None:
        search_kwargs = {"k": 5}

    # Step 2: resolve embeddings and open existing collection.
    embeddings_model = get_embeddings(embeddings)

    # Load existing vectorstore from disk
    vectorstore = QdrantVectorStore.from_existing_collection(
        collection_name=collection_name,
        embedding=embeddings_model,
        path=persist_directory
    )

    # Step 3: convert vector store into a retriever object.
    retriever = vectorstore.as_retriever(
        search_kwargs=search_kwargs
    )

    return retriever


def retrieve_documents(
    query: str,
    vectorstore: Optional[QdrantVectorStore] = None,
    retriever: Optional[any] = None,
    k: int = 5
) -> List[Document]:
    """
    Retrieve relevant documents for a query.

    Args:
        query: User query
        vectorstore: Optional QdrantVectorStore instance
        retriever: Optional pre-configured retriever
        k: Number of documents to retrieve

    Returns:
        List of relevant documents
    """
    # Accept either retriever-style objects or direct vectorstore access.
    if retriever is not None:
        # Use provided retriever
        if hasattr(retriever, 'invoke'):
            return retriever.invoke(query)
        elif hasattr(retriever, 'get_relevant_documents'):
            return retriever.get_relevant_documents(query)
        else:
            raise ValueError("Retriever must have 'invoke' or 'get_relevant_documents' method")

    elif vectorstore is not None:
        # Use vectorstore directly
        return vectorstore.similarity_search(query, k=k)

    else:
        raise ValueError("Either vectorstore or retriever must be provided")


def format_docs_for_context(
    documents: List[Document],
    include_sources: bool = False
) -> str:
    """
    Format retrieved documents into a readable context string.

    Args:
        documents: List of retrieved documents
        include_sources: Whether to include source metadata

    Returns:
        Formatted context string
    """
    # Empty retrieval should produce an empty context string.
    if not documents:
        return ""

    context_parts = []

    for i, doc in enumerate(documents, 1):
        content = doc.page_content.strip()

        if include_sources and 'source' in doc.metadata:
            source = doc.metadata['source']
            # Extract filename from path
            source_name = Path(source).name
            context_parts.append(f"[Source: {source_name}]\n{content}")
        else:
            context_parts.append(content)

    # Join with double newlines for readability in LLM prompts.
    context = "\n\n".join(context_parts)

    return context


def retrieve_and_format(
    query: str,
    retriever: Optional[any] = None,
    vectorstore: Optional[QdrantVectorStore] = None,
    k: int = 5,
    return_sources: bool = False
) -> str | Tuple[str, List[str]]:
    """
    Complete RAG pipeline: retrieve documents and format as context.

    Args:
        query: User query
        retriever: Optional pre-configured retriever
        vectorstore: Optional Chroma vectorstore
        k: Number of documents to retrieve
        return_sources: Whether to return source list along with context

    Returns:
        Formatted context string, or (context, sources) tuple if return_sources=True
    """
    # Step 1: semantic retrieval.
    documents = retrieve_documents(
        query=query,
        vectorstore=vectorstore,
        retriever=retriever,
        k=k
    )

    # Step 2: format retrieved chunks into a single context block.
    context = format_docs_for_context(documents, include_sources=False)

    if return_sources:
        # Step 3 (optional): build a stable, de-duplicated source list.
        sources = []
        for doc in documents:
            if 'source' in doc.metadata:
                source = Path(doc.metadata['source']).name
                if source not in sources:
                    sources.append(source)

        return context, sources
    else:
        return context


def get_rag_context(
    query: str,
    persist_directory: Optional[str] = None,
    embeddings: Optional[any] = None,
    k: int = 5
) -> Tuple[str, List[str]]:
    """
    High-level function to get RAG context and sources for a query.
    This is the main function to use in the FastAPI application.

    Args:
        query: User query
        persist_directory: Optional vectorstore directory
        embeddings: Optional embeddings model
        k: Number of documents to retrieve

    Returns:
        Tuple of (context_string, list_of_sources)
    """
    # High-level helper used by API/router code:
    # load retriever -> retrieve context -> return context + source labels.
    retriever = get_retriever(
        persist_directory=persist_directory,
        embeddings=embeddings,
        search_kwargs={"k": k}
    )

    context, sources = retrieve_and_format(
        query=query,
        retriever=retriever,
        return_sources=True
    )

    return context, sources


if __name__ == "__main__":
    """
    Demo script to test retrieval
    """
    import argparse

    parser = argparse.ArgumentParser(description="Test RAG retrieval")
    parser.add_argument("query", help="Query to test")
    parser.add_argument("--k", type=int, default=3, help="Number of results")

    args = parser.parse_args()

    print("=" * 60)
    print("IT Support Agent - RAG Retrieval Test")
    print("=" * 60)
    print(f"\nQuery: {args.query}")
    print(f"Retrieving top {args.k} results...\n")

    try:
        context, sources = get_rag_context(
            query=args.query,
            k=args.k
        )

        print("Context:")
        print("-" * 60)
        print(context)
        print("-" * 60)
        print(f"\nSources: {', '.join(sources)}")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you've run the ingestion first:")
        print("  cd backend && python -m rag.ingest --reset")
