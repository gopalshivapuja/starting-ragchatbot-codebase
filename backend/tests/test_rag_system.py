"""
Tests for rag_system.py - End-to-end content query testing.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from rag_system import RAGSystem


class TestRAGSystemContentQueries:
    """Tests for end-to-end content query handling."""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_content_query_complete_flow(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test complete flow of content query from input to response."""
        # Setup mocks
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="Lesson 5 covers MCP client creation."
        )
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_sm_instance.get_conversation_history = Mock(return_value=None)
        mock_sm_instance.add_exchange = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        # Create RAG system
        rag = RAGSystem(mock_config)

        # Mock tool manager to return sources
        rag.tool_manager.get_last_sources = Mock(
            return_value=[
                {
                    "text": "MCP Course - Lesson 5",
                    "link": "https://example.com/lesson/5",
                }
            ]
        )
        rag.tool_manager.reset_sources = Mock()

        # Execute query
        response, sources = rag.query(
            "What is covered in lesson 5 of MCP course?", session_id="test_session"
        )

        # Assertions
        assert response == "Lesson 5 covers MCP client creation."
        assert len(sources) > 0
        assert sources[0]["text"] == "MCP Course - Lesson 5"

        # Verify AI generator was called with tools
        mock_ai_instance.generate_response.assert_called_once()
        call_args = mock_ai_instance.generate_response.call_args
        assert "tools" in call_args[1]
        assert "tool_manager" in call_args[1]

        # Verify session was updated
        mock_sm_instance.add_exchange.assert_called_once()

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_outline_query_flow(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test outline query flow."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="Course outline: Lesson 0, Lesson 1, Lesson 5"
        )
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_sm_instance.get_conversation_history = Mock(return_value=None)
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)
        rag.tool_manager.get_last_sources = Mock(
            return_value=[{"text": "MCP Course", "link": "https://example.com/course"}]
        )

        response, sources = rag.query("What is the outline of MCP course?")

        assert "Course outline" in response
        assert len(sources) > 0

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_general_query_without_tools(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test general knowledge query that doesn't need tools."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="RAG is Retrieval-Augmented Generation."
        )
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_sm_instance.get_conversation_history = Mock(return_value=None)
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])

        response, sources = rag.query("What is RAG?")

        assert "Retrieval-Augmented Generation" in response
        assert len(sources) == 0

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_session_management(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test that session history is properly managed."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        history = "User: Previous question\nAssistant: Previous answer"
        mock_sm_instance.get_conversation_history = Mock(return_value=history)
        mock_sm_instance.add_exchange = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])

        rag.query("Follow-up question", session_id="test_session")

        # Verify history was retrieved
        mock_sm_instance.get_conversation_history.assert_called_once_with(
            "test_session"
        )

        # Verify history was passed to AI
        call_args = mock_ai_instance.generate_response.call_args
        assert call_args[1]["conversation_history"] == history

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_source_reset_after_retrieval(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test that sources are reset after being retrieved."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)
        rag.tool_manager.get_last_sources = Mock(return_value=[{"text": "source"}])
        rag.tool_manager.reset_sources = Mock()

        rag.query("Test query")

        # Verify sources were reset
        rag.tool_manager.reset_sources.assert_called_once()

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_error_handling_in_query(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test error handling when query fails."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(side_effect=Exception("API Error"))
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)

        with pytest.raises(Exception) as exc_info:
            rag.query("Test query")

        assert "API Error" in str(exc_info.value)

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_tools_registered_on_initialization(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test that both search and outline tools are registered."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)

        # Verify both tools are registered
        tool_definitions = rag.tool_manager.get_tool_definitions()
        tool_names = [t["name"] for t in tool_definitions]

        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_empty_query_handling(
        self,
        mock_doc_proc,
        mock_session_mgr,
        mock_vector_store,
        mock_ai_gen,
        mock_config,
    ):
        """Test handling of empty queries."""
        mock_vs_instance = Mock()
        mock_vector_store.return_value = mock_vs_instance

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="Please provide a question."
        )
        mock_ai_gen.return_value = mock_ai_instance

        mock_sm_instance = Mock()
        mock_session_mgr.return_value = mock_sm_instance

        mock_dp_instance = Mock()
        mock_doc_proc.return_value = mock_dp_instance

        rag = RAGSystem(mock_config)
        rag.tool_manager.get_last_sources = Mock(return_value=[])

        response, sources = rag.query("")

        assert isinstance(response, str)
        assert len(sources) == 0
