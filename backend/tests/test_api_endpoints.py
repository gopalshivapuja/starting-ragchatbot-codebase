"""
API endpoint tests for the RAG system.
Tests the FastAPI endpoints for proper request/response handling.
"""
import pytest
from fastapi.testclient import TestClient


class TestQueryEndpoint:
    """Tests for /api/query endpoint."""

    def test_query_with_valid_input(self, test_client):
        """Test query endpoint with valid input."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify data types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify session was created
        assert data["session_id"] == "test_session_123"

    def test_query_with_existing_session(self, test_client):
        """Test query endpoint with existing session ID."""
        response = test_client.post(
            "/api/query",
            json={
                "query": "What is MCP?",
                "session_id": "existing_session"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should use provided session ID
        assert data["session_id"] == "existing_session"

    def test_query_with_empty_string(self, test_client):
        """Test query endpoint with empty query string."""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still process (validation at RAG level, not API level)
        assert response.status_code == 200

    def test_query_with_missing_query_field(self, test_client):
        """Test query endpoint with missing required field."""
        response = test_client.post(
            "/api/query",
            json={"session_id": "test"}
        )

        # Should return validation error
        assert response.status_code == 422  # Unprocessable Entity

    def test_query_with_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON."""
        response = test_client.post(
            "/api/query",
            data="not json",
            headers={"Content-Type": "application/json"}
        )

        # Should return validation error
        assert response.status_code == 422

    def test_query_with_rag_error(self, test_client):
        """Test query endpoint when RAG system raises an error."""
        response = test_client.post(
            "/api/query",
            json={"query": "trigger error in query"}
        )

        # Should return internal server error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Mock RAG error" in data["detail"]

    def test_query_response_sources_format(self, test_client):
        """Test that sources are returned in correct format."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify sources structure
        sources = data["sources"]
        assert len(sources) > 0

        for source in sources:
            # Sources should be dicts with text and link
            assert isinstance(source, dict)
            assert "text" in source
            assert "link" in source


class TestCoursesEndpoint:
    """Tests for /api/courses endpoint."""

    def test_get_courses_success(self, test_client):
        """Test courses endpoint returns course statistics."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify mock data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Course A" in data["course_titles"]
        assert "Course B" in data["course_titles"]

    def test_get_courses_returns_consistent_data(self, test_client):
        """Test that courses endpoint returns consistent data on multiple calls."""
        response1 = test_client.get("/api/courses")
        response2 = test_client.get("/api/courses")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both responses should be identical
        assert response1.json() == response2.json()

    def test_get_courses_with_query_params(self, test_client):
        """Test that courses endpoint ignores unexpected query parameters."""
        response = test_client.get("/api/courses?limit=5&offset=10")

        # Should still work (ignores params)
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2


class TestAPIIntegration:
    """Integration tests for API endpoints."""

    def test_query_and_courses_workflow(self, test_client):
        """Test typical workflow: check courses, then query."""
        # First, get available courses
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()

        # Verify we have courses
        assert courses_data["total_courses"] > 0

        # Then, make a query
        query_response = test_client.post(
            "/api/query",
            json={"query": "Tell me about Course A"}
        )
        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify we got an answer
        assert len(query_data["answer"]) > 0
        assert len(query_data["sources"]) > 0

    def test_multiple_queries_same_session(self, test_client):
        """Test multiple queries with the same session ID."""
        # First query creates session
        response1 = test_client.post(
            "/api/query",
            json={"query": "First question"}
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Second query uses same session
        response2 = test_client.post(
            "/api/query",
            json={
                "query": "Follow-up question",
                "session_id": session_id
            }
        )
        assert response2.status_code == 200

        # Session ID should be preserved
        assert response2.json()["session_id"] == session_id

    def test_content_type_headers(self, test_client):
        """Test that API returns correct content type."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_api_error_response_format(self, test_client):
        """Test that API errors follow FastAPI error format."""
        response = test_client.post(
            "/api/query",
            json={"query": "trigger error in query"}
        )

        assert response.status_code == 500
        data = response.json()

        # FastAPI error format
        assert "detail" in data
        assert isinstance(data["detail"], str)
