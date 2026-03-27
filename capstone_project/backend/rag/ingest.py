"""
RAG document ingestion pipeline.
Implemented following TDD - all tests in test_rag_ingest.py should pass.
"""

import backend.env_bootstrap  # noqa: F401 — loads backend/.env before OpenAI embeddings init

import os
import shutil
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_core.documents import Document

from backend.rag.config_paths import get_qdrant_path

# Ollama is optional
try:
    from langchain_community.embeddings import OllamaEmbeddings
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaEmbeddings = None

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", None)  # For Qdrant server mode
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLLECTION_NAME = "it_support_kb"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs" / "backend" / "rag" / "docs"


def load_documents(docs_dir: Optional[str] = None) -> List[Document]:
    """
    Load all markdown documents from a directory.

    Args:
        docs_dir: Directory containing markdown files (default: backend/rag/docs)

    Returns:
        List of loaded documents

    Raises:
        FileNotFoundError: If directory doesn't exist or contains no documents
    """
    if docs_dir is None:
        docs_dir = str(DOCS_DIR)

    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")

    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False
    )

    documents = loader.load()

    if len(documents) == 0:
        raise FileNotFoundError(f"No markdown documents found in: {docs_dir}")

    return documents


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Document]:
    """
    Split documents into smaller chunks for better retrieval.

    Args:
        documents: List of documents to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of document chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = text_splitter.split_documents(documents)
    return chunks


def get_embeddings(embeddings: Optional[any] = None):
    """
    Get the appropriate embeddings model based on configuration.

    Args:
        embeddings: Optional pre-configured embeddings model (for testing)

    Returns:
        Embeddings model (OpenAI or Ollama)
    """
    if embeddings is not None:
        return embeddings

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


def create_vector_store(
    chunks: List[Document],
    persist_directory: Optional[str] = None,
    embeddings: Optional[any] = None,
    collection_name: Optional[str] = None
) -> QdrantVectorStore:
    """
    Create and persist Qdrant vector store from document chunks.

    Args:
        chunks: List of document chunks
        persist_directory: Directory to persist the vector store (local mode)
        embeddings: Optional embeddings model (for testing)
        collection_name: Name of the collection

    Returns:
        QdrantVectorStore instance
    """
    if collection_name is None:
        collection_name = COLLECTION_NAME

    if persist_directory is None:
        persist_directory = get_qdrant_path()

    embeddings_model = get_embeddings(embeddings)

    # Create vectorstore with local disk storage
    vectorstore = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings_model,
        collection_name=collection_name,
        path=persist_directory  # Use path parameter directly
    )

    return vectorstore


def reset_vector_store(persist_directory: Optional[str] = None):
    """
    Delete existing vector store.

    Args:
        persist_directory: Directory containing the vector store
    """
    if persist_directory is None:
        persist_directory = get_qdrant_path()

    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)


def ingest_documents(
    docs_dir: Optional[str] = None,
    reset: bool = False,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    embeddings: Optional[any] = None,
    collection_name: Optional[str] = None
) -> QdrantVectorStore:
    """
    Main ingestion pipeline: load → chunk → embed → store.

    Args:
        docs_dir: Directory containing markdown files
        reset: If True, delete existing vector store before ingesting
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        embeddings: Optional embeddings model (for testing)
        collection_name: Name of the collection

    Returns:
        QdrantVectorStore instance
    """
    persist_dir = get_qdrant_path()

    if reset:
        reset_vector_store(persist_dir)

    # Load documents
    documents = load_documents(docs_dir)

    # Chunk documents
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)

    # Create vector store
    vectorstore = create_vector_store(chunks, persist_dir, embeddings, collection_name)

    return vectorstore


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest IT support documents")
    parser.add_argument("--reset", action="store_true", help="Delete existing vector store")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap")

    args = parser.parse_args()

    print("=" * 60)
    print("IT Support Agent - Document Ingestion")
    print("=" * 60)

    vectorstore = ingest_documents(
        reset=args.reset,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )

    # Close Qdrant client explicitly to reduce noisy __del__ / ImportError on interpreter shutdown.
    try:
        client = getattr(vectorstore, "client", None)
        if client is not None and hasattr(client, "close"):
            client.close()
    except Exception:
        pass

    print("✓ Ingestion complete!")
    print("=" * 60)
