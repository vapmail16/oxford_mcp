"""
Unit tests for RAG document ingestion.
RED PHASE - These tests will fail until we implement ingest.py

Test Priority: P0-P1 (Critical for RAG accuracy)
Category: Unit, RAG
"""

import pytest
from pathlib import Path


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestDocumentLoading:
    """Tests for loading documents from filesystem"""

    def test_load_documents_from_directory_returns_documents(self, temp_docs_dir):
        """
        Test Name: RAG_LoadDocuments_ValidDirectory_ReturnsDocuments
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents

        # Act
        documents = load_documents(str(temp_docs_dir))

        # Assert
        assert len(documents) > 0
        assert all(hasattr(doc, 'page_content') for doc in documents)
        assert all(hasattr(doc, 'metadata') for doc in documents)

    def test_load_documents_from_empty_directory_raises_error(self, tmp_path):
        """
        Test Name: RAG_LoadDocuments_EmptyDirectory_RaisesError
        Priority: P1
        Category: Negative
        """
        from backend.rag.ingest import load_documents

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            load_documents(str(tmp_path))

    def test_load_documents_preserves_metadata(self, temp_docs_dir):
        """
        Test Name: RAG_LoadDocuments_ValidFiles_PreservesMetadata
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents

        # Act
        documents = load_documents(str(temp_docs_dir))

        # Assert
        for doc in documents:
            assert 'source' in doc.metadata
            assert doc.metadata['source'].endswith('.md')


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestDocumentChunking:
    """Tests for document chunking"""

    def test_chunk_documents_creates_chunks(self, temp_docs_dir):
        """
        Test Name: RAG_ChunkDocuments_ValidDocs_CreatesChunks
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents, chunk_documents

        # Arrange
        documents = load_documents(str(temp_docs_dir))

        # Act
        chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

        # Assert
        assert len(chunks) >= len(documents)  # Should create at least as many chunks
        assert all(hasattr(chunk, 'page_content') for chunk in chunks)

    def test_chunk_size_500_produces_appropriate_chunks(self, temp_docs_dir):
        """
        Test Name: RAG_ChunkDocuments_Size500_AppropriateChunks
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents, chunk_documents

        # Arrange
        documents = load_documents(str(temp_docs_dir))

        # Act
        chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

        # Assert
        for chunk in chunks:
            assert len(chunk.page_content) <= 600  # Some tolerance
            assert len(chunk.page_content) > 0

    def test_chunk_overlap_preserves_context(self, temp_docs_dir):
        """
        Test Name: RAG_ChunkDocuments_WithOverlap_PreservesContext
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents, chunk_documents

        # Arrange
        documents = load_documents(str(temp_docs_dir))

        # Act
        chunks_no_overlap = chunk_documents(documents, chunk_size=500, chunk_overlap=0)
        chunks_with_overlap = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

        # Assert
        # With overlap should create more chunks
        assert len(chunks_with_overlap) >= len(chunks_no_overlap)


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.rag
class TestEmbeddings:
    """Tests for embeddings generation"""

    def test_get_embeddings_openai_returns_embeddings_model(self, monkeypatch):
        """
        Test Name: RAG_GetEmbeddings_OpenAI_ReturnsModel
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import get_embeddings

        # Arrange
        monkeypatch.setenv("MODEL_PROVIDER", "openai")

        # Act
        embeddings = get_embeddings()

        # Assert
        assert embeddings is not None
        assert hasattr(embeddings, 'embed_documents') or hasattr(embeddings, 'embed_query')

    def test_get_embeddings_ollama_returns_embeddings_model(self, monkeypatch):
        """
        Test Name: RAG_GetEmbeddings_Ollama_ReturnsModel
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import get_embeddings

        # Arrange
        monkeypatch.setenv("MODEL_PROVIDER", "ollama")

        # Act
        embeddings = get_embeddings()

        # Assert
        assert embeddings is not None


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestVectorStore:
    """Tests for vector store creation"""

    def test_create_vector_store_persists_chunks(self, temp_docs_dir, mock_embeddings, tmp_path):
        """
        Test Name: RAG_CreateVectorStore_ValidChunks_PersistsToDatabase
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import load_documents, chunk_documents, create_vector_store

        # Arrange
        documents = load_documents(str(temp_docs_dir))
        chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)
        persist_dir = str(tmp_path / "test_chroma")

        # Act
        vectorstore = create_vector_store(chunks, persist_directory=persist_dir, embeddings=mock_embeddings)

        # Assert
        assert vectorstore is not None
        assert Path(persist_dir).exists()

    def test_reset_vector_store_deletes_existing(self, tmp_path):
        """
        Test Name: RAG_ResetVectorStore_ExistingStore_DeletesDirectory
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import reset_vector_store

        # Arrange
        persist_dir = tmp_path / "test_chroma"
        persist_dir.mkdir()
        test_file = persist_dir / "test.txt"
        test_file.write_text("test")

        # Act
        reset_vector_store(str(persist_dir))

        # Assert
        assert not persist_dir.exists()


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestIngestPipeline:
    """Tests for complete ingestion pipeline"""

    def test_ingest_documents_complete_pipeline(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_IngestDocuments_CompletePipeline_Success
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)

        # Act
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            chunk_size=500,
            chunk_overlap=50,
            embeddings=mock_embeddings
        )

        # Assert
        assert vectorstore is not None
        assert Path(persist_dir).exists()

    def test_ingest_documents_with_reset_clears_existing(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_IngestDocuments_WithReset_ClearsExisting
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)

        # Create existing vectorstore
        ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=False,
            embeddings=mock_embeddings
        )

        # Act - ingest with reset=True
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Assert
        assert vectorstore is not None
