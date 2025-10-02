from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content** - Search for specific content within course materials
2. **get_course_outline** - Get course overview including title, course link, instructor, and complete lesson list with numbers and titles

Tool Usage Guidelines:
- **Outline/overview queries**: Use get_course_outline tool to retrieve course structure
- **Content queries**: Use search_course_content tool for specific course content or detailed materials
- **Sequential tool usage**: You may use up to 2 tool calls per query when needed
  - Use multiple tools when a question requires both overview and specific content
  - Example: Get outline first, then search for specific lesson content
  - Each tool call should build on previous results
- **Tool reasoning**: After receiving tool results, decide if you need more information or can answer
- Synthesize all tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Sequential Tool Usage Examples:
- "Show me the MCP course outline and explain lesson 3" → Use get_course_outline, then search_course_content
- "Compare instructors of two courses" → Get outline for first course, then get outline for second course
- "What courses cover authentication? Show me those materials" → Search broadly first, then search specific course

When NOT to use multiple tools:
- Simple questions answerable with one tool call
- General knowledge questions (use existing knowledge)
- Questions about single specific topics (one search sufficient)

Between Tool Calls:
- After receiving tool results, briefly assess what you learned
- Decide if another tool call would help answer the user's question more completely
- Only call additional tools if they provide essential information not yet obtained
- After receiving all needed information, provide your final answer

Response Protocol for Outline Queries:
- When providing course outlines, include:
  - Course title
  - Course link (if available)
  - Instructor (if available)
  - Complete list of lessons with their numbers and titles
- Format lessons clearly (e.g., "Lesson 1: Introduction to Topic")

General Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the tool results" or "I used the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum sequential tool calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_sequential_tool_execution(
                response, api_params, tool_manager, max_tool_rounds
            )

        # Return direct response
        return self._extract_text_from_response(response)

    def _handle_sequential_tool_execution(
        self,
        initial_response,
        base_params: Dict[str, Any],
        tool_manager,
        max_rounds: int = 2,
    ):
        """
        Handle sequential tool execution across multiple rounds.

        Args:
            initial_response: First response from Claude (with tool_use)
            base_params: Base API parameters (contains system, messages, tools)
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default 2)

        Returns:
            Final response text after all rounds
        """
        # Initialize message history and round counter
        messages = base_params["messages"].copy()
        current_round = 0
        current_response = initial_response

        # Main loop - continue until natural stop or max rounds reached
        while current_round < max_rounds:
            # Check if Claude wants to use tools
            if current_response.stop_reason != "tool_use":
                # Claude is done - has final answer without needing more tools
                return self._extract_text_from_response(current_response)

            # Execute all requested tools
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add assistant's response (contains tool_use blocks)
            messages.append({"role": "assistant", "content": current_response.content})

            # Add tool results as user message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Increment round counter
            current_round += 1

            # Prepare next API call
            if current_round < max_rounds:
                # Still within limit - keep tools available for potential next round
                next_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"],
                    "tools": base_params.get("tools", []),  # KEEP TOOLS AVAILABLE
                    "tool_choice": {"type": "auto"},
                }
            else:
                # Max rounds reached - force final answer without tools
                next_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"],
                    # NO tools - force Claude to synthesize final answer
                }

            # Make next API call
            try:
                current_response = self.client.messages.create(**next_params)
            except Exception as e:
                # Handle API errors gracefully
                return f"Error during tool execution: {str(e)}"

        # Loop exited - extract final answer
        return self._extract_text_from_response(current_response)

    def _extract_text_from_response(self, response):
        """
        Extract text content from response, handling multiple content blocks.

        Args:
            response: Anthropic API response

        Returns:
            Extracted text as string
        """
        text_parts = []
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                text_parts.append(block.text)
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        return " ".join(text_parts) if text_parts else ""
