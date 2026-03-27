"""
Enhanced RAG Agent - Question Answering with Confidence Scoring
Implemented following TDD - all tests in test_agents_rag.py should pass
"""

import os
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class RAGAgent:
    """
    RAG Agent answers questions using the knowledge base with confidence scoring.

    Responsibilities:
    - Retrieve relevant context from vector store
    - Generate answer using LLM + context
    - Calculate confidence score
    - Determine if ticket creation is needed
    - Provide source attribution
    """

    def __init__(self, model: str = None):
        """Initialize RAG agent with LLM and retriever"""
        self.llm = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7
        )

        # Answer generation prompt
        self.answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an IT support expert. Answer the user's question using the provided context.

RULES:
- Only use information from the context
- If the context doesn't contain the answer, say so
- Provide step-by-step instructions when applicable
- Be professional but friendly
- Include relevant details (URLs, commands, etc.)

Context from Knowledge Base:
{context}"""),
            ("human", "{query}")
        ])

        # Confidence assessment prompt
        self.confidence_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are evaluating how well a context answers a question.

Rate the confidence from 0.0 to 1.0:
- 1.0 = Context fully answers the question with all details
- 0.7-0.9 = Context mostly answers, minor gaps
- 0.4-0.6 = Context partially relevant
- 0.0-0.3 = Context not relevant

Return ONLY a number between 0.0 and 1.0."""),
            ("human", "Question: {query}\n\nContext: {context}\n\nConfidence score:")
        ])

    def retrieve_context(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant context from vector store.

        Args:
            query: User question
            k: Number of chunks to retrieve

        Returns:
            Dict with context and sources
        """
        try:
            from backend.rag.retriever import get_rag_context

            context, sources = get_rag_context(query=query, k=k)

            return {
                'context': context,
                'sources': sources
            }

        except Exception as e:
            print(f"RAG retrieval failed: {e}")
            return {
                'context': "",
                'sources': []
            }

    def calculate_confidence(self, query: str, context: str) -> float:
        """
        Calculate confidence score for how well context answers the query.

        Args:
            query: User question
            context: Retrieved context

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # If no context, confidence is 0
        if not context or len(context.strip()) == 0:
            return 0.0

        try:
            # Use LLM to assess confidence
            chain = self.confidence_prompt | self.llm
            response = chain.invoke({"query": query, "context": context})

            # Parse confidence score
            confidence_str = response.content.strip()

            # Extract number from response
            import re
            match = re.search(r'(\d+\.?\d*)', confidence_str)
            if match:
                confidence = float(match.group(1))
                # Ensure it's between 0 and 1
                if confidence > 1.0:
                    confidence = confidence / 10.0  # Handle 8.5 -> 0.85
                return max(0.0, min(1.0, confidence))
            else:
                # Fallback: simple heuristic based on context length
                return min(len(context) / 1000.0, 0.8)

        except Exception as e:
            print(f"Confidence calculation failed: {e}, using heuristic")
            # Fallback heuristic: longer context = higher confidence (up to 0.8)
            return min(len(context) / 1000.0, 0.8)

    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using LLM with context.

        Args:
            query: User question
            context: Retrieved context

        Returns:
            Generated answer
        """
        if not context or len(context.strip()) == 0:
            return "I couldn't find relevant information in the knowledge base to answer your question. Would you like me to create a support ticket?"

        try:
            chain = self.answer_prompt | self.llm
            response = chain.invoke({"query": query, "context": context})
            return response.content

        except Exception as e:
            print(f"Answer generation failed: {e}")
            return f"I encountered an error while generating the answer: {str(e)}"

    def should_create_ticket(
        self,
        confidence: float,
        classification: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if a ticket should be created.

        Args:
            confidence: Confidence score from RAG
            classification: Optional triage classification

        Returns:
            True if ticket should be created
        """
        # Low confidence -> create ticket
        if confidence < 0.6:
            return True

        # Urgent priority + medium confidence -> create ticket
        if classification:
            priority = classification.get('priority', 'MEDIUM')
            if priority in ['HIGH', 'URGENT'] and confidence < 0.7:
                return True

        return False

    def answer_query(
        self,
        query: str,
        classification: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a user query with RAG.

        Args:
            query: User question
            classification: Optional triage classification
            k: Number of chunks to retrieve

        Returns:
            Dict with answer, confidence, sources, needs_ticket
        """
        # Handle empty query
        if not query or len(query.strip()) == 0:
            return {
                'answer': "Please provide a question.",
                'confidence': 0.0,
                'sources': [],
                'needs_ticket': False,
                'complexity': 'simple'
            }

        # Handle very long queries (truncate)
        if len(query) > 2000:
            query = query[:2000] + "..."

        # Enhance query with category if available
        enhanced_query = query
        if classification and 'category' in classification:
            category = classification['category']
            if category != 'GENERAL':
                enhanced_query = f"{category}: {query}"

        # Step 1: Retrieve context
        retrieval = self.retrieve_context(enhanced_query, k=k)
        context = retrieval['context']
        sources = retrieval['sources']

        # Step 2: Calculate confidence
        confidence = self.calculate_confidence(query, context)

        # Step 3: Generate answer
        answer = self.generate_answer(query, context)

        # Step 4: Determine if ticket is needed
        needs_ticket = self.should_create_ticket(confidence, classification)

        # Step 5: Assess complexity
        complexity = self._assess_complexity(query, context, confidence)

        return {
            'answer': answer,
            'confidence': confidence,
            'sources': sources,
            'needs_ticket': needs_ticket,
            'complexity': complexity
        }

    def _assess_complexity(self, query: str, context: str, confidence: float) -> str:
        """
        Assess the complexity of the issue.

        Args:
            query: User question
            context: Retrieved context
            confidence: Confidence score

        Returns:
            Complexity level: 'simple', 'moderate', 'complex'
        """
        # Simple heuristic for complexity
        complexity_indicators = [
            'tried everything',
            'nothing works',
            'still broken',
            'for days',
            'for weeks',
            'multiple issues',
            'completely broken'
        ]

        query_lower = query.lower()

        # Check for complexity indicators
        indicator_count = sum(1 for indicator in complexity_indicators if indicator in query_lower)

        if indicator_count >= 2:
            return 'complex'
        elif indicator_count == 1 or confidence < 0.5:
            return 'moderate'
        else:
            return 'simple'


if __name__ == "__main__":
    """Test RAG agent"""
    agent = RAGAgent()

    test_queries = [
        "How do I reset my password?",
        "VPN error 422, what should I do?",
        "My laptop won't turn on at all",
        "What is the WiFi password?",
        "I tried all VPN fixes but nothing works"
    ]

    print("=" * 60)
    print("RAG Agent Test")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = agent.answer_query(query)
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Needs Ticket: {result['needs_ticket']}")
        print(f"  Complexity: {result['complexity']}")
        print(f"  Sources: {len(result['sources'])} documents")
        print(f"  Answer: {result['answer'][:100]}...")
