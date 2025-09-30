# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) system for querying course materials. Built with FastAPI backend, ChromaDB vector storage, Anthropic's Claude API for generation, and vanilla JavaScript frontend.

## Environment Setup

**Required:** `.env` file in project root with:
```
ANTHROPIC_API_KEY=your_key_here
```

## Development Commands

### Running the Application

```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000

# Different port
cd backend
uv run uvicorn app:app --reload --port 8001
```

### Dependency Management

```bash
# Install/sync dependencies
uv sync

# Add new dependency
uv add package-name

# Update dependencies
uv lock --upgrade
```

### Accessing the Application

- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Query API: `POST http://localhost:8000/api/query`
- Courses API: `GET http://localhost:8000/api/courses`

## Architecture

### Core Data Flow

```
User Query → FastAPI → RAG System → AI Generator (Claude) → Tool Manager → Vector Store (ChromaDB)
                ↓                                                                    ↓
           Session Manager                                                   Semantic Search
                ↓                                                                    ↓
        Conversation History ← ← ← ← ← ← Search Results ← ← ← ← ← ← ← ← ← ← ← ← ←
```

### Key Components (`backend/`)

**`rag_system.py`** - Main orchestrator
- Coordinates all components (vector store, AI generator, session manager, tools)
- `query()`: Processes user questions with tool-based search
- `add_course_folder()`: Ingests documents from filesystem

**`ai_generator.py`** - Claude API integration
- Two-stage API calls: (1) Tool decision, (2) Final answer synthesis
- Uses `claude-sonnet-4-20250514` model
- System prompt emphasizes concise, educational responses without meta-commentary

**`vector_store.py`** - ChromaDB wrapper
- Two collections: `course_catalog` (metadata) and `course_content` (chunks)
- `search()`: Semantic search with course/lesson filtering
- `_resolve_course_name()`: Fuzzy course name matching via vector similarity

**`document_processor.py`** - Document parsing & chunking
- Sentence-based chunking: 800 chars with 100 char overlap
- Preserves semantic boundaries (doesn't split mid-sentence)
- Adds context prefixes: `"Course {title} Lesson {num} content: {chunk}"`

**`search_tools.py`** - Tool definitions for Claude
- `CourseSearchTool`: Defines search capability with parameters (query, course_name, lesson_number)
- `ToolManager`: Registers tools, executes them, tracks sources

**`session_manager.py`** - Conversation memory
- Maintains last 2 Q&A exchanges per session
- Formats history for Claude context

**`app.py`** - FastAPI server
- Mounts frontend static files at `/`
- Loads `docs/` folder on startup (auto-indexes courses)

### Document Format

Course documents in `docs/` must follow this structure:

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Content paragraphs...]

Lesson 1: [Next Lesson]
[Content continues...]
```

Supported formats: `.txt`, `.pdf`, `.docx`

### Configuration (`backend/config.py`)

Key settings:
- `CHUNK_SIZE`: 800 chars
- `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 (search results)
- `MAX_HISTORY`: 2 (conversation exchanges)
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2"
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"

### ChromaDB Storage

- **Location:** `./chroma_db` (persistent, git-ignored)
- **Collections:**
  - `course_catalog`: 1 doc per course (title, instructor, lessons_json, links)
  - `course_content`: N docs (1 per chunk with course_title, lesson_number, chunk_index)
- **Deduplication:** Uses course title as unique ID, skips existing courses

### Tool Calling Pattern

1. User query → Claude decides to use `search_course_content` tool
2. Tool executes vector search, returns formatted results with sources
3. Claude synthesizes final answer from search results
4. Sources tracked separately and returned to frontend

### Session Management

- Session ID created on first query, returned to frontend
- Frontend includes session_id in subsequent queries
- History format: `"User: {q}\nAssistant: {a}\nUser: {q2}\nAssistant: {a2}"`
- Limited to last 2 exchanges to control context size

## Working with the Codebase

### Adding New Course Documents

1. Place document in `docs/` folder with proper format
2. Restart server (auto-loads on startup)
3. Or call `rag_system.add_course_folder("docs/")` programmatically

### Modifying Search Behavior

- **Change result count:** Edit `MAX_RESULTS` in `config.py`
- **Change chunking:** Edit `CHUNK_SIZE`/`CHUNK_OVERLAP` in `config.py`
- **Add filters:** Modify `vector_store._build_filter()` and tool schema in `search_tools.py`

### Changing AI Behavior

- **System prompt:** Edit `AIGenerator.SYSTEM_PROMPT` in `ai_generator.py`
- **Model:** Edit `ANTHROPIC_MODEL` in `config.py`
- **Temperature/tokens:** Edit `base_params` in `ai_generator.py`

### Adding New Tools

1. Create tool class inheriting from `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` and `execute()`
3. Register with `tool_manager.register_tool(your_tool)` in `rag_system.py`

### Frontend Modifications

- **UI:** `frontend/index.html`
- **Logic:** `frontend/script.js` (vanilla JS, no framework)
- **Styling:** `frontend/style.css`
- **Markdown rendering:** Uses `marked.js` library

## Important Notes

### On Startup Behavior

The server automatically loads all documents from `docs/` on startup. This can be slow for large document sets. Set `clear_existing=True` in `add_course_folder()` call in `app.py` to rebuild database from scratch (clears all data first).

### On Embedding Model

Changing `EMBEDDING_MODEL` in config requires rebuilding the database (all existing vectors are incompatible). Clear ChromaDB data: delete `./chroma_db` folder or call `vector_store.clear_all_data()`.

### On Course Title Uniqueness

Course titles must be unique (used as primary key). Duplicate titles will be skipped during ingestion. The system checks existing titles before processing new documents.

### On Context Prefixes

Document chunks have context added during processing (e.g., "Course X Lesson Y content: ..."). This improves retrieval accuracy but increases token usage. Modify in `document_processor.py:186-234` if needed.

### On Tool Usage

Claude is instructed to use search tools "only" for course-specific questions and perform "one search per query maximum". Modify system prompt in `ai_generator.py` to change this behavior.
- use uv to run python files or add any dependencies