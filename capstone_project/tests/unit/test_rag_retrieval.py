"""
Unit tests for RAG document retrieval.
RED PHASE - These tests will fail until we implement retriever.py

Test Priority: P0-P1 (Critical for RAG accuracy)
Category: Unit, RAG
"""

import pytest
from pathlib import Path


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestVectorStoreRetrieval:
    """Tests for retrieving documents from vector store"""

    def test_retrieve_vpn_docs_returns_relevant_results(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Retrieve_VPNQuery_ReturnsRelevantDocs
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import retrieve_documents

        # Arrange - create vectorstore with sample docs
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act - query for VPN information
        results = retrieve_documents(
            query="VPN error 422",
            vectorstore=vectorstore,
            k=3
        )

        # Assert
        assert len(results) > 0
        assert len(results) <= 3
        assert all(hasattr(doc, 'page_content') for doc in results)
        assert all(hasattr(doc, 'metadata') for doc in results)

    def test_retrieve_password_docs_returns_password_content(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Retrieve_PasswordQuery_ReturnsPasswordDocs
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import retrieve_documents

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act
        results = retrieve_documents(
            query="how to reset my password",
            vectorstore=vectorstore,
            k=3
        )

        # Assert
        assert len(results) > 0
        # At least one result should mention password
        content = " ".join([doc.page_content.lower() for doc in results])
        assert "password" in content

    def test_retrieve_with_k_parameter_limits_results(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Retrieve_WithKParam_LimitsResults
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import retrieve_documents

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act - request only 2 results
        results = retrieve_documents(
            query="IT support help",
            vectorstore=vectorstore,
            k=2
        )

        # Assert
        assert len(results) <= 2

    def test_retrieve_includes_source_metadata(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Retrieve_Results_IncludeSourceMetadata
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import retrieve_documents

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        vectorstore = ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act
        results = retrieve_documents(
            query="VPN setup",
            vectorstore=vectorstore,
            k=3
        )

        # Assert
        for doc in results:
            assert 'source' in doc.metadata
            assert doc.metadata['source'].endswith('.md')


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestRetrieverInitialization:
    """Tests for initializing retriever from persisted vectorstore"""

    def test_get_retriever_loads_from_persist_dir(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_GetRetriever_FromPersistDir_LoadsVectorstore
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import get_retriever

        # Arrange - create and persist vectorstore
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)

        ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act - load retriever from persisted store
        retriever = get_retriever(
            persist_directory=persist_dir,
            embeddings=mock_embeddings
        )

        # Assert
        assert retriever is not None
        assert hasattr(retriever, 'get_relevant_documents') or hasattr(retriever, 'invoke')

    def test_get_retriever_with_search_kwargs(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_GetRetriever_WithSearchKwargs_ConfiguresCorrectly
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import get_retriever

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        # Act
        retriever = get_retriever(
            persist_directory=persist_dir,
            embeddings=mock_embeddings,
            search_kwargs={"k": 5}
        )

        # Assert
        assert retriever is not None


@pytest.mark.unit
@pytest.mark.priority_p1
@pytest.mark.rag
class TestContextFormatting:
    """Tests for formatting retrieved documents into context"""

    def test_format_docs_creates_readable_context(self):
        """
        Test Name: RAG_FormatDocs_ValidDocs_CreatesReadableContext
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.retriever import format_docs_for_context
        from langchain_core.documents import Document

        # Arrange
        docs = [
            Document(
                page_content="VPN error 422 occurs when authentication times out.",
                metadata={"source": "vpn_guide.md"}
            ),
            Document(
                page_content="To fix error 422, close and reopen VPN client.",
                metadata={"source": "vpn_guide.md"}
            )
        ]

        # Act
        context = format_docs_for_context(docs)

        # Assert
        assert isinstance(context, str)
        assert "VPN error 422" in context
        assert "authentication times out" in context
        assert "close and reopen" in context

    def test_format_docs_includes_sources(self):
        """
        Test Name: RAG_FormatDocs_WithMetadata_IncludesSources
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.retriever import format_docs_for_context
        from langchain_core.documents import Document

        # Arrange
        docs = [
            Document(
                page_content="Password reset instructions.",
                metadata={"source": "password_reset.md"}
            )
        ]

        # Act
        context = format_docs_for_context(docs, include_sources=True)

        # Assert
        assert "password_reset.md" in context or "Source:" in context

    def test_format_docs_empty_list_returns_empty_string(self):
        """
        Test Name: RAG_FormatDocs_EmptyList_ReturnsEmptyString
        Priority: P2
        Category: Negative
        """
        from backend.rag.retriever import format_docs_for_context

        # Act
        context = format_docs_for_context([])

        # Assert
        assert context == "" or context is None


@pytest.mark.unit
@pytest.mark.priority_p0
@pytest.mark.rag
class TestRAGPipeline:
    """Tests for complete RAG retrieval pipeline"""

    def test_rag_pipeline_query_to_context(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Pipeline_QueryToContext_ReturnsFormattedContext
        Priority: P0
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import get_retriever, retrieve_and_format

        # Arrange - create vectorstore
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        retriever = get_retriever(
            persist_directory=persist_dir,
            embeddings=mock_embeddings
        )

        # Act - complete pipeline
        context = retrieve_and_format(
            query="VPN troubleshooting",
            retriever=retriever
        )

        # Assert
        assert isinstance(context, str)
        assert len(context) > 0

    def test_rag_pipeline_returns_sources_list(self, temp_docs_dir, mock_embeddings, tmp_path, monkeypatch):
        """
        Test Name: RAG_Pipeline_WithSources_ReturnsSourcesList
        Priority: P1
        Category: Happy Path
        """
        from backend.rag.ingest import ingest_documents
        from backend.rag.retriever import get_retriever, retrieve_and_format

        # Arrange
        persist_dir = str(tmp_path / "test_chroma")
        monkeypatch.setenv("QDRANT_PATH", persist_dir)
        ingest_documents(
            docs_dir=str(temp_docs_dir),
            reset=True,
            embeddings=mock_embeddings
        )

        retriever = get_retriever(
            persist_directory=persist_dir,
            embeddings=mock_embeddings
        )

        # Act
        context, sources = retrieve_and_format(
            query="password reset",
            retriever=retriever,
            return_sources=True
        )

        # Assert
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert all(isinstance(s, str) for s in sources)
        assert all(s.endswith('.md') for s in sources)
