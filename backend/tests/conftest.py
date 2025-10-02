"""
Pytest fixtures for RAG system tests.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

# Add backend directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models import Course, CourseChunk, Lesson
from vector_store import SearchResults


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore for testing."""
    store = Mock()

    # Mock successful search results
    def mock_search(
        query: str,
        course_name: str = None,
        lesson_number: int = None,
        limit: int = None,
    ):
        # Simulate search results
        if "empty" in query.lower():
            return SearchResults(documents=[], metadata=[], distances=[])

        if "error" in query.lower():
            return SearchResults.empty("Search error occurred")

        # Return sample results
        return SearchResults(
            documents=[
                "This is content from lesson 5 about MCP client.",
                "The lesson covers client setup and connection.",
            ],
            metadata=[
                {"course_title": "MCP Course", "lesson_number": 5, "chunk_index": 0},
                {"course_title": "MCP Course", "lesson_number": 5, "chunk_index": 1},
            ],
            distances=[0.1, 0.2],
        )

    store.search = Mock(side_effect=mock_search)
    store.get_lesson_link = Mock(return_value="https://example.com/lesson/5")

    # Mock course outline retrieval
    def mock_get_course_outline(course_name: str):
        if course_name.lower() == "nonexistent":
            return None
        return {
            "course_title": "MCP: Build Rich-Context AI Apps",
            "course_link": "https://example.com/mcp-course",
            "instructor": "Test Instructor",
            "lessons": [
                {
                    "lesson_number": 0,
                    "lesson_title": "Introduction",
                    "lesson_link": "https://example.com/lesson/0",
                },
                {
                    "lesson_number": 1,
                    "lesson_title": "Why MCP",
                    "lesson_link": "https://example.com/lesson/1",
                },
                {
                    "lesson_number": 5,
                    "lesson_title": "Creating An MCP Client",
                    "lesson_link": "https://example.com/lesson/5",
                },
            ],
        }

    store.get_course_outline = Mock(side_effect=mock_get_course_outline)

    return store


@pytest.fixture
def sample_course():
    """Create a sample course for testing."""
    return Course(
        title="MCP: Build Rich-Context AI Apps",
        course_link="https://example.com/mcp-course",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Introduction",
                lesson_link="https://example.com/lesson/0",
            ),
            Lesson(
                lesson_number=1,
                title="Why MCP",
                lesson_link="https://example.com/lesson/1",
            ),
            Lesson(
                lesson_number=5,
                title="Creating An MCP Client",
                lesson_link="https://example.com/lesson/5",
            ),
        ],
    )


@pytest.fixture
def sample_chunks():
    """Create sample course chunks for testing."""
    return [
        CourseChunk(
            content="This is content from lesson 5 about MCP client.",
            course_title="MCP Course",
            lesson_number=5,
            chunk_index=0,
        ),
        CourseChunk(
            content="The lesson covers client setup and connection.",
            course_title="MCP Course",
            lesson_number=5,
            chunk_index=1,
        ),
    ]


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing."""
    client = Mock()

    # Mock successful API response with tool use
    def mock_create_with_tool(**kwargs):
        response = Mock()
        response.stop_reason = "tool_use"

        # Create tool use content block
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {
            "query": "What is covered in lesson 5",
            "course_name": "MCP",
            "lesson_number": 5,
        }

        response.content = [tool_use_block]
        return response

    # Mock final response after tool execution
    def mock_create_final(**kwargs):
        response = Mock()
        response.stop_reason = "end_turn"

        # Create text content block
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Lesson 5 covers MCP client creation and setup."

        response.content = [text_block]
        return response

    # Configure the mock to return different responses
    client.messages.create = Mock(
        side_effect=[
            mock_create_with_tool(),  # First call - tool use
            mock_create_final(),  # Second call - final answer
        ]
    )

    return client


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test_api_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    return config
