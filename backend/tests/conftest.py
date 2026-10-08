"""Test fixtures for PromptLab"""

import pytest
from fastapi.testclient import TestClient
from app.api import app
from app.storage import storage


@pytest.fixture
def client():
    """Create a test client for the API.

    Returns:
        A FastAPI TestClient bound to the application, used to issue
        requests without running a live server.
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Reset the in-memory storage around each test.

    Autouse fixture that guarantees test isolation by emptying the store
    before and after every test.

    Yields:
        None. Control returns to the fixture after the test completes so
        the store can be cleared again.
    """
    storage.clear()
    yield
    storage.clear()


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing.

    Returns:
        A dict of valid prompt fields suitable for POST /prompts, including
        a {{code}} template variable in the content.
    """
    return {
        "title": "Code Review Prompt",
        "content": "Review the following code and provide feedback:\n\n{{code}}",
        "description": "A prompt for AI code review"
    }


@pytest.fixture
def sample_collection_data():
    """Sample collection data for testing.

    Returns:
        A dict of valid collection fields suitable for POST /collections.
    """
    return {
        "name": "Development",
        "description": "Prompts for development tasks"
    }
