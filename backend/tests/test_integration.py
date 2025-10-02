"""
Integration tests - Test against real components to identify actual failures.
"""
import pytest
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variable for testing
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "test_key")

from config import config
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager


@pytest.mark.integration
class TestVectorStoreIntegration:
    """Integration tests for VectorStore with real ChromaDB."""

    def test_vector_store_with_actual_data(self):
        """Test that vector store has data loaded."""
        # Use actual vector store
        store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)

        # Check course count
        course_count = store.get_course_count()
        print(f"\n[VECTOR STORE STATUS]")
        print(f"Courses in database: {course_count}")

        if course_count == 0:
            pytest.skip("No courses loaded in database - cannot test queries")

        # Try a simple search
        results = store.search("MCP client")

        print(f"Search results count: {len(results.documents)}")
        print(f"Search has error: {results.error}")

        if results.error:
            print(f"Search error message: {results.error}")

        assert isinstance(results, SearchResults)

    def test_course_search_tool_with_real_db(self):
        """Test CourseSearchTool with actual database."""
        store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)

        course_count = store.get_course_count()
        if course_count == 0:
            pytest.skip("No courses loaded")

        tool = CourseSearchTool(store)

        result = tool.execute(query="MCP client", course_name="MCP", lesson_number=5)

        print(f"\n[COURSE SEARCH TOOL TEST]")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result)}")
        print(f"Result preview: {result[:300]}...")

        assert isinstance(result, str)
        assert len(result) > 0
