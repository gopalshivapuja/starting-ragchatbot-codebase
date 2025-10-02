"""
Tests for search_tools.py - CourseSearchTool and CourseOutlineTool.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Tests for CourseSearchTool.execute() method."""

    def test_successful_search_with_results(self, mock_vector_store):
        """Test successful search that returns results."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is covered in lesson 5", course_name="MCP", lesson_number=5)

        # Verify search was called
        mock_vector_store.search.assert_called_once_with(
            query="What is covered in lesson 5",
            course_name="MCP",
            lesson_number=5
        )

        # Verify result format
        assert isinstance(result, str)
        assert len(result) > 0
        assert "[MCP Course" in result
        assert "Lesson 5" in result
        assert "This is content from lesson 5" in result

    def test_search_without_filters(self, mock_vector_store):
        """Test search without course or lesson filters."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is MCP")

        mock_vector_store.search.assert_called_once_with(
            query="What is MCP",
            course_name=None,
            lesson_number=None
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_with_empty_results(self, mock_vector_store):
        """Test search that returns no results."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="empty query")

        assert "No relevant content found" in result

    def test_search_with_course_filter_only(self, mock_vector_store):
        """Test search with only course filter."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="MCP concepts", course_name="MCP")

        mock_vector_store.search.assert_called_once_with(
            query="MCP concepts",
            course_name="MCP",
            lesson_number=None
        )

        assert isinstance(result, str)

    def test_search_with_error(self, mock_vector_store):
        """Test search that encounters an error."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="error query")

        assert "Search error occurred" in result

    def test_source_tracking(self, mock_vector_store):
        """Test that sources are properly tracked."""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="What is covered in lesson 5", course_name="MCP", lesson_number=5)

        # Verify sources were tracked
        assert len(tool.last_sources) > 0
        assert "text" in tool.last_sources[0]
        assert "MCP Course" in tool.last_sources[0]["text"]
        assert "Lesson 5" in tool.last_sources[0]["text"]

    def test_get_tool_definition(self, mock_vector_store):
        """Test tool definition is properly formatted."""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]


class TestCourseOutlineTool:
    """Tests for CourseOutlineTool.execute() method."""

    def test_successful_outline_retrieval(self, mock_vector_store):
        """Test successful course outline retrieval."""
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="MCP")

        # Verify outline was requested
        mock_vector_store.get_course_outline.assert_called_once_with("MCP")

        # Verify result format
        assert isinstance(result, str)
        assert "Course: MCP: Build Rich-Context AI Apps" in result
        assert "Course Link:" in result
        assert "Instructor:" in result
        assert "Lessons" in result
        assert "Lesson 0: Introduction" in result

    def test_outline_for_nonexistent_course(self, mock_vector_store):
        """Test outline request for nonexistent course."""
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="nonexistent")

        assert "No course found matching 'nonexistent'" in result

    def test_outline_source_tracking(self, mock_vector_store):
        """Test that outline sources are tracked."""
        tool = CourseOutlineTool(mock_vector_store)

        tool.execute(course_name="MCP")

        # Verify source tracking
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "MCP: Build Rich-Context AI Apps"
        assert "link" in tool.last_sources[0]

    def test_get_tool_definition(self, mock_vector_store):
        """Test outline tool definition is properly formatted."""
        tool = CourseOutlineTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert "course_name" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["course_name"]


class TestToolManager:
    """Tests for ToolManager."""

    def test_register_and_get_definitions(self, mock_vector_store):
        """Test registering tools and getting their definitions."""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        assert any(d["name"] == "search_course_content" for d in definitions)
        assert any(d["name"] == "get_course_outline" for d in definitions)

    def test_execute_search_tool(self, mock_vector_store):
        """Test executing search tool through manager."""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        result = manager.execute_tool("search_course_content", query="test query")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_outline_tool(self, mock_vector_store):
        """Test executing outline tool through manager."""
        manager = ToolManager()
        outline_tool = CourseOutlineTool(mock_vector_store)
        manager.register_tool(outline_tool)

        result = manager.execute_tool("get_course_outline", course_name="MCP")

        assert isinstance(result, str)
        assert "Course:" in result

    def test_execute_nonexistent_tool(self, mock_vector_store):
        """Test executing a tool that doesn't exist."""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, mock_vector_store):
        """Test retrieving sources from last tool execution."""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="test query")
        sources = manager.get_last_sources()

        assert len(sources) > 0

    def test_reset_sources(self, mock_vector_store):
        """Test resetting sources after retrieval."""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="test query")
        manager.reset_sources()

        sources = manager.get_last_sources()
        assert len(sources) == 0