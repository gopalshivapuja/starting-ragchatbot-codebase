# User Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND                                     │
│                            (frontend/script.js)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ User types: "What is MCP?"
                                      │
                         ┌────────────▼────────────┐
                         │   sendMessage()         │
                         │   - Display user msg    │
                         │   - Show loading        │
                         └────────────┬────────────┘
                                      │
                                      │ POST /api/query
                                      │ {"query": "What is MCP?",
                                      │  "session_id": null}
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                            BACKEND - API LAYER                               │
│                              (backend/app.py)                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  @app.post("/api/query")                                               │ │
│  │  async def query_documents(request: QueryRequest)                      │ │
│  │                                                                         │ │
│  │  1. Create/Get session_id                                              │ │
│  │  2. Call rag_system.query(query, session_id)                           │ │
│  │  3. Return QueryResponse(answer, sources, session_id)                  │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ rag_system.query("What is MCP?", "session_1")
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           RAG SYSTEM ORCHESTRATOR                            │
│                           (backend/rag_system.py)                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  query(query, session_id)                                              │ │
│  │                                                                         │ │
│  │  1. Get conversation history from session_manager                      │ │
│  │  2. Build prompt with history                                          │ │
│  │  3. Call ai_generator.generate_response()                              │ │
│  │  4. Extract sources from tool_manager                                  │ │
│  │  5. Save exchange to session_manager                                   │ │
│  └───────┬────────────────────────────────────────────────┬───────────────┘ │
└──────────┼────────────────────────────────────────────────┼─────────────────┘
           │                                                 │
           │ get_conversation_history()                      │ add_exchange()
           │                                                 │
  ┌────────▼──────────┐                           ┌─────────▼─────────────┐
  │ SESSION MANAGER   │                           │   SESSION MANAGER     │
  │ (session_manager) │                           │                       │
  │                   │                           │   Store Q&A for       │
  │ Returns:          │                           │   next query          │
  │ "User: prev Q     │                           └───────────────────────┘
  │  Assistant: prev A"│
  └───────────────────┘

           │ generate_response(query, history, tools, tool_manager)
           │
┌──────────▼──────────────────────────────────────────────────────────────────┐
│                            AI GENERATOR - 1ST CALL                           │
│                          (backend/ai_generator.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  generate_response()                                                   │ │
│  │                                                                         │ │
│  │  System: "You are an AI assistant... [with history]"                   │ │
│  │  Messages: [{"role": "user", "content": "What is MCP?"}]               │ │
│  │  Tools: [search_course_content tool definition]                        │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │         Call Claude API (Anthropic)                             │  │ │
│  │  │                                                                  │  │ │
│  │  │  Claude analyzes: "This is about course content, I need to      │  │ │
│  │  │                    search for MCP information"                   │  │ │
│  │  │                                                                  │  │ │
│  │  │  Response: stop_reason = "tool_use"                             │  │ │
│  │  │  Content: [                                                      │  │ │
│  │  │    {type: "tool_use",                                            │  │ │
│  │  │     name: "search_course_content",                               │  │ │
│  │  │     input: {query: "MCP", course_name: "Introduction"}}         │  │ │
│  │  │  ]                                                               │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │  → Calls _handle_tool_execution()                                      │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ tool_manager.execute_tool(
                                  │   "search_course_content",
                                  │   query="MCP", course_name="Introduction")
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              TOOL MANAGER                                    │
│                          (backend/search_tools.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  execute_tool(tool_name, **kwargs)                                     │ │
│  │                                                                         │ │
│  │  → Find tool: tools["search_course_content"] → CourseSearchTool        │ │
│  │  → Call: tool.execute(query="MCP", course_name="Introduction")         │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           COURSE SEARCH TOOL                                 │
│                          (backend/search_tools.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  execute(query="MCP", course_name="Introduction")                      │ │
│  │                                                                         │ │
│  │  → Call vector_store.search()                                          │ │
│  │  → Format results with [Course - Lesson] headers                       │ │
│  │  → Store sources in self.last_sources                                  │ │
│  │  → Return formatted string                                             │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ vector_store.search(
                                  │   query="MCP",
                                  │   course_name="Introduction",
                                  │   lesson_number=None)
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              VECTOR STORE                                    │
│                          (backend/vector_store.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  search(query, course_name, lesson_number)                             │ │
│  │                                                                         │ │
│  │  Step 1: Resolve course name                                           │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │ _resolve_course_name("Introduction")                             │ │ │
│  │  │ → Query course_catalog collection                                │ │ │
│  │  │ → Semantic search for best match                                 │ │ │
│  │  │ → Returns: "Introduction to Model Context Protocol"             │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  Step 2: Build filter                                                  │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │ _build_filter(course_title, lesson_number)                       │ │ │
│  │  │ → Returns: {"course_title": "Introduction to MCP"}               │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  Step 3: Search content                                                │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │ course_content.query()                                           │ │ │
│  │  │   query_texts=["MCP"]                                            │ │ │
│  │  │   n_results=5                                                    │ │ │
│  │  │   where={"course_title": "Introduction to MCP"}                  │ │ │
│  │  │                                                                   │ │ │
│  │  │ ┌────────────────────────────────────────────────────────────┐  │ │ │
│  │  │ │            CHROMADB                                        │  │ │ │
│  │  │ │      (./chroma_db storage)                                 │  │ │ │
│  │  │ │                                                             │  │ │ │
│  │  │ │  1. Embed query "MCP" using all-MiniLM-L6-v2              │  │ │ │
│  │  │ │  2. Vector similarity search in course_content collection │  │ │ │
│  │  │ │  3. Filter by course_title metadata                       │  │ │ │
│  │  │ │  4. Return top 5 most similar chunks                      │  │ │ │
│  │  │ │                                                             │  │ │ │
│  │  │ │  Results:                                                   │  │ │ │
│  │  │ │  - documents: ["MCP stands for...", "MCP enables...", ...] │  │ │ │
│  │  │ │  - metadata: [{course_title, lesson_number, chunk_index}] │  │ │ │
│  │  │ │  - distances: [0.12, 0.18, 0.23, ...]                     │  │ │ │
│  │  │ └────────────────────────────────────────────────────────────┘  │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  → Return SearchResults(documents, metadata, distances)                │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ SearchResults returned
                                  │
                    ┌─────────────▼──────────────┐
                    │   SEARCH TOOL              │
                    │   Formats results:         │
                    │                            │
                    │   "[Introduction to MCP -  │
                    │    Lesson 1]               │
                    │   MCP stands for Model     │
                    │   Context Protocol..."     │
                    │                            │
                    │   Stores sources:          │
                    │   ["Introduction... - L1"] │
                    └─────────────┬──────────────┘
                                  │
                                  │ Return formatted results
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                         AI GENERATOR - 2ND CALL                              │
│                          (backend/ai_generator.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  _handle_tool_execution() continues...                                 │ │
│  │                                                                         │ │
│  │  Messages now contains:                                                │ │
│  │  [                                                                      │ │
│  │    {role: "user", content: "What is MCP?"},                            │ │
│  │    {role: "assistant", content: [tool_use block]},                     │ │
│  │    {role: "user", content: [                                           │ │
│  │      {type: "tool_result",                                             │ │
│  │       tool_use_id: "...",                                              │ │
│  │       content: "[Introduction to MCP - Lesson 1]\nMCP stands..."}     │ │
│  │    ]}                                                                   │ │
│  │  ]                                                                      │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │         Call Claude API Again (No tools this time)              │  │ │
│  │  │                                                                  │  │ │
│  │  │  Claude synthesizes search results into answer:                 │  │ │
│  │  │                                                                  │  │ │
│  │  │  Response:                                                       │  │ │
│  │  │  "MCP (Model Context Protocol) is a standardized way for AI     │  │ │
│  │  │   assistants to connect with external data sources and tools.   │  │ │
│  │  │   It enables seamless integration between AI models and various │  │ │
│  │  │   data repositories..."                                          │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │  → Return final answer text                                            │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ Return answer
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           RAG SYSTEM ORCHESTRATOR                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  query() continues...                                                  │ │
│  │                                                                         │ │
│  │  answer = "MCP (Model Context Protocol) is..."                         │ │
│  │                                                                         │ │
│  │  → Get sources from tool_manager.get_last_sources()                    │ │
│  │    sources = ["Introduction to MCP - Lesson 1"]                        │ │
│  │                                                                         │ │
│  │  → Reset tool_manager sources                                          │ │
│  │                                                                         │ │
│  │  → Save exchange to session_manager                                    │ │
│  │                                                                         │ │
│  │  → Return (answer, sources)                                            │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ (answer, sources)
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                            BACKEND - API LAYER                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  query_documents() continues...                                        │ │
│  │                                                                         │ │
│  │  Return QueryResponse(                                                 │ │
│  │    answer="MCP (Model Context Protocol) is...",                        │ │
│  │    sources=["Introduction to MCP - Lesson 1"],                         │ │
│  │    session_id="session_1"                                              │ │
│  │  )                                                                      │ │
│  └────────────────────────────┬───────────────────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  │ JSON response
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                                 FRONTEND                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  sendMessage() continues...                                            │ │
│  │                                                                         │ │
│  │  const data = await response.json();                                   │ │
│  │  // {answer: "...", sources: [...], session_id: "session_1"}           │ │
│  │                                                                         │ │
│  │  1. Store session_id for next query                                    │ │
│  │  2. Remove loading indicator                                           │ │
│  │  3. Display answer with markdown formatting                            │ │
│  │  4. Add collapsible sources section                                    │ │
│  │                                                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  CHAT UI                                                         │ │ │
│  │  │                                                                   │ │ │
│  │  │  User: What is MCP?                                              │ │ │
│  │  │                                                                   │ │ │
│  │  │  Assistant: MCP (Model Context Protocol) is a standardized      │ │ │
│  │  │             way for AI assistants to connect with external       │ │ │
│  │  │             data sources and tools...                            │ │ │
│  │  │                                                                   │ │ │
│  │  │             ▼ Sources                                            │ │ │
│  │  │               Introduction to MCP - Lesson 1                     │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Points

1. **Two Claude API Calls**: First to decide on tool use, second to synthesize results
2. **Session Management**: History maintained across queries for context
3. **Tool-Based Search**: Claude decides when and how to search
4. **Semantic Matching**: Course names don't need exact matches
5. **Source Tracking**: UI shows which course/lesson provided the answer