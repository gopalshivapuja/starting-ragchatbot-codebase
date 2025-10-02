"""
Tests for ai_generator.py - Verify AI correctly calls tools.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from ai_generator import AIGenerator
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager


class TestAIGeneratorToolCalling:
    """Tests for AIGenerator's tool calling functionality."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_calling_for_content_query(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that AI correctly invokes CourseSearchTool for content queries."""
        # Setup mocks
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First response: AI decides to use tool
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {
            "query": "What is covered in lesson 5",
            "course_name": "MCP",
            "lesson_number": 5,
        }
        tool_response.content = [tool_use_block]

        # Second response: AI provides final answer
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Lesson 5 covers MCP client creation."
        final_response.content = [text_block]

        mock_client.messages.create = Mock(side_effect=[tool_response, final_response])

        # Create AI generator and tool manager
        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        # Execute
        result = ai_gen.generate_response(
            query="What is covered in lesson 5 of MCP course?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Assertions
        assert result == "Lesson 5 covers MCP client creation."
        assert mock_client.messages.create.call_count == 2
        mock_vector_store.search.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_no_tool_calling_for_general_query(self, mock_anthropic_class):
        """Test that AI doesn't use tools for general knowledge queries."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # AI responds directly without tools
        response = Mock()
        response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "RAG stands for Retrieval-Augmented Generation."
        response.content = [text_block]

        mock_client.messages.create = Mock(return_value=response)

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        result = ai_gen.generate_response(query="What is RAG?")

        assert result == "RAG stands for Retrieval-Augmented Generation."
        assert mock_client.messages.create.call_count == 1

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_parameters_extracted_correctly(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that tool parameters are correctly extracted and passed."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Setup tool response with specific parameters
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_456"
        tool_use_block.input = {
            "query": "client setup",
            "course_name": "MCP Course",
            "lesson_number": 5,
        }
        tool_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.text = "Client setup details..."
        final_response.content = [text_block]

        mock_client.messages.create = Mock(side_effect=[tool_response, final_response])

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        ai_gen.generate_response(
            query="Tell me about client setup",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Verify search was called with correct parameters
        mock_vector_store.search.assert_called_once_with(
            query="client setup", course_name="MCP Course", lesson_number=5
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_definitions_formatted_correctly(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that tool definitions are properly passed to API."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        response = Mock()
        response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.text = "Response"
        response.content = [text_block]
        mock_client.messages.create = Mock(return_value=response)

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        tools = tool_manager.get_tool_definitions()

        ai_gen.generate_response(
            query="Test query", tools=tools, tool_manager=tool_manager
        )

        # Get the call arguments
        call_args = mock_client.messages.create.call_args

        # Verify tools were passed
        assert "tools" in call_args[1]
        assert len(call_args[1]["tools"]) > 0
        assert call_args[1]["tools"][0]["name"] == "search_course_content"

    @patch("ai_generator.anthropic.Anthropic")
    def test_conversation_history_included(self, mock_anthropic_class):
        """Test that conversation history is included in API calls."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        response = Mock()
        response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.text = "Response with context"
        response.content = [text_block]
        mock_client.messages.create = Mock(return_value=response)

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        history = "User: Previous question\nAssistant: Previous answer"

        ai_gen.generate_response(
            query="Follow-up question", conversation_history=history
        )

        # Verify history was included in system prompt
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous question" in system_content
        assert "Previous answer" in system_content

    @patch("ai_generator.anthropic.Anthropic")
    def test_api_error_handling(self, mock_anthropic_class):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Simulate API error
        mock_client.messages.create = Mock(side_effect=Exception("API Error"))

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        with pytest.raises(Exception) as exc_info:
            ai_gen.generate_response(query="Test query")

        assert "API Error" in str(exc_info.value)

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_result_passed_back_to_api(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that tool results are properly passed back to the API."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_789"
        tool_use_block.input = {"query": "test"}
        tool_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.text = "Final answer"
        final_response.content = [text_block]

        mock_client.messages.create = Mock(side_effect=[tool_response, final_response])

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        ai_gen.generate_response(
            query="Test",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Verify second API call included tool results
        assert mock_client.messages.create.call_count == 2
        second_call_args = mock_client.messages.create.call_args_list[1]

        # Check that messages include tool results
        messages = second_call_args[1]["messages"]
        assert (
            len(messages) >= 2
        )  # Should have user message, assistant message, and tool result
        assert any("tool_result" in str(msg) for msg in messages)

    @patch("ai_generator.anthropic.Anthropic")
    def test_sequential_tool_calling_two_rounds(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that Claude can make 2 sequential tool calls."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First API call: initial query with tool use
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "get_course_outline"
        tool_use_1.id = "tool_1"
        tool_use_1.input = {"course_name": "MCP"}
        first_response.content = [tool_use_1]

        # Second API call: after first tool, Claude wants another tool
        second_response = Mock()
        second_response.stop_reason = "tool_use"
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "tool_2"
        tool_use_2.input = {"query": "lesson 3", "course_name": "MCP"}
        second_response.content = [tool_use_2]

        # Third API call: final answer
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Here's the outline and lesson 3 content"
        final_response.content = [text_block]

        mock_client.messages.create = Mock(
            side_effect=[first_response, second_response, final_response]
        )

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)

        result = ai_gen.generate_response(
            query="Show me MCP outline and lesson 3",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
            max_tool_rounds=2,
        )

        # Verify 3 API calls made (initial, second tool, final)
        assert mock_client.messages.create.call_count == 3
        assert result == "Here's the outline and lesson 3 content"

        # Verify second API call had tools available
        second_call = mock_client.messages.create.call_args_list[1]
        assert "tools" in second_call[1]
        assert len(second_call[1]["tools"]) > 0

    @patch("ai_generator.anthropic.Anthropic")
    def test_max_rounds_enforced(self, mock_anthropic_class, mock_vector_store):
        """Test that max rounds limit is enforced."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Claude always wants to use tools
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.id = "tool_x"
        tool_use.input = {"query": "test"}
        tool_response.content = [tool_use]

        # Final response after forced synthesis
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Forced final answer"
        final_response.content = [text_block]

        # Return tool_use twice, then final answer
        mock_client.messages.create = Mock(
            side_effect=[
                tool_response,  # Initial: wants tool
                tool_response,  # Round 1: wants tool again
                final_response,  # Round 2 (max): forced final without tools
            ]
        )

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_gen.generate_response(
            query="Test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
            max_tool_rounds=2,
        )

        # Should have 3 API calls (initial + 2 rounds)
        assert mock_client.messages.create.call_count == 3

        # Third call should NOT have tools (forced final)
        third_call = mock_client.messages.create.call_args_list[2]
        assert "tools" not in third_call[1]

        assert result == "Forced final answer"

    @patch("ai_generator.anthropic.Anthropic")
    def test_natural_termination_after_one_tool(
        self, mock_anthropic_class, mock_vector_store
    ):
        """Test that Claude can naturally stop after one tool if satisfied."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # First response: wants tool
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.id = "tool_1"
        tool_use.input = {"query": "test"}
        tool_response.content = [tool_use]

        # Second response: provides answer (natural stop)
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Answer after one tool"
        final_response.content = [text_block]

        mock_client.messages.create = Mock(side_effect=[tool_response, final_response])

        ai_gen = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")
        ai_gen.client = mock_client

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        result = ai_gen.generate_response(
            query="Simple query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
            max_tool_rounds=2,
        )

        # Only 2 API calls (didn't use second round)
        assert mock_client.messages.create.call_count == 2
        assert result == "Answer after one tool"
