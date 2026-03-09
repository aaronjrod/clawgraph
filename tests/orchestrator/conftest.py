from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class MockGeminiClient:
    def __init__(self):
        self.models = MagicMock()
        self.models.generate_content.side_effect = self.generate_content
        self.expected_responses = []

    def add_expected_call(self, name, args, text=None):
        call = SimpleNamespace(name=name, args=args)
        resp = SimpleNamespace(function_calls=[call], text=text)
        self.expected_responses.append(resp)

    def generate_content(self, model, contents, config=None):
        if self.expected_responses:
            return self.expected_responses.pop(0)

        # Default fallback to complete if nothing queued
        call = SimpleNamespace(name="complete", args={"final_summary": "Mock auto-complete"})
        resp = SimpleNamespace(function_calls=[call], text="Thinking: No more tasks.")
        return resp


@pytest.fixture
def mock_gemini(monkeypatch):
    mock_client = MockGeminiClient()

    def mock_init(*args, **kwargs):
        return mock_client

    monkeypatch.setattr("google.genai.Client", mock_init)
    return mock_client
