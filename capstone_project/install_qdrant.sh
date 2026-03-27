#!/bin/bash
# Quick installation script for Qdrant packages

echo "============================================================"
echo "Installing Qdrant packages for IT Support Agent"
echo "============================================================"
echo ""

echo "Installing qdrant-client..."
pip install qdrant-client==1.7.0

echo ""
echo "Installing langchain-qdrant..."
pip install langchain-qdrant==0.2.0

echo ""
echo "============================================================"
echo "✅ Qdrant packages installed successfully!"
echo "============================================================"
echo ""
echo "You can now:"
echo "  1. Run RAG ingestion: cd backend && python -m rag.ingest --reset"
echo "  2. Run tests: pytest tests/unit/test_rag*.py -v"
echo ""
