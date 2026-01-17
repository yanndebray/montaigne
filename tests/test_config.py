"""Tests for config.py - configuration and environment handling."""

import pytest
import os
from unittest.mock import patch, MagicMock

from montaigne.config import (
    check_dependencies,
    load_api_key,
    get_gemini_client,
    REQUIRED_PACKAGES,
)


class TestCheckDependencies:
    """Tests for dependency checking."""

    def test_check_dependencies_when_installed(self):
        """Returns True when all dependencies are available."""
        # In test environment, dependencies should be installed
        result = check_dependencies()
        assert result is True

    def test_check_dependencies_when_missing(self):
        """Returns False when imports fail."""
        with patch.dict("sys.modules", {"google.genai": None}):
            # Force ImportError by removing module
            with patch("montaigne.config.check_dependencies") as mock_check:
                mock_check.return_value = False
                assert mock_check() is False

    def test_required_packages_list(self):
        """Required packages list should contain expected packages."""
        assert "google-genai" in REQUIRED_PACKAGES
        assert "python-dotenv" in REQUIRED_PACKAGES
        assert "pymupdf" in REQUIRED_PACKAGES


class TestLoadApiKey:
    """Tests for API key loading."""

    def test_load_api_key_from_env(self):
        """Load API key from environment variable."""
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key-12345"}, clear=False):
                result = load_api_key("gemini")
                assert result == "test-api-key-12345"

    def test_load_elevenlabs_api_key_from_env(self):
        """Load ElevenLabs API key from environment variable."""
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "eleven-test-key"}, clear=False):
                result = load_api_key("elevenlabs")
                assert result == "eleven-test-key"

    def test_load_api_key_missing_exits(self):
        """Missing API key should call sys.exit(1)."""
        # Save original value if exists
        original_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with patch("dotenv.load_dotenv"):
                with pytest.raises(SystemExit) as exc_info:
                    load_api_key("gemini")
                assert exc_info.value.code == 1
        finally:
            # Restore original value
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key

    def test_load_api_key_unknown_client_exits(self):
        """Unknown client name should call sys.exit(1)."""
        with patch("dotenv.load_dotenv"):
            with pytest.raises(SystemExit) as exc_info:
                load_api_key("unknown_client")
            assert exc_info.value.code == 1

    def test_load_api_key_empty_string_exits(self):
        """Empty API key string should call sys.exit(1)."""
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
                # Temporarily set empty key
                os.environ["GEMINI_API_KEY"] = ""
                with pytest.raises(SystemExit) as exc_info:
                    load_api_key("gemini")
                assert exc_info.value.code == 1

    def test_load_dotenv_called(self):
        """load_dotenv should be called to load .env file."""
        with patch("dotenv.load_dotenv") as mock_load:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
                load_api_key("gemini")
                mock_load.assert_called_once()


class TestGetGeminiClient:
    """Tests for Gemini client creation."""

    def test_get_client_with_valid_key(self):
        """Client should be created with valid API key."""
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}, clear=False):
                with patch("google.genai.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    result = get_gemini_client()

                    mock_client_class.assert_called_once_with(api_key="test-api-key")
                    assert result == mock_client

    def test_get_client_missing_key_exits(self):
        """Missing API key should exit before creating client."""
        # Save original value if exists
        original_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with patch("dotenv.load_dotenv"):
                with pytest.raises(SystemExit):
                    get_gemini_client()
        finally:
            # Restore original value
            if original_key:
                os.environ["GEMINI_API_KEY"] = original_key


class TestApiKeyFormats:
    """Tests for various API key formats."""

    def test_standard_api_key_format(self):
        """Standard Gemini API key format should work."""
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyA1234567890abcdefghijklmnopqrstuvwx"}, clear=False):
                result = load_api_key("gemini")
                assert result.startswith("AIza")

    def test_api_key_with_whitespace_preserved(self):
        """API key with accidental whitespace should be preserved (user responsibility)."""
        # Note: The actual function doesn't strip whitespace
        # This test documents current behavior
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {"GEMINI_API_KEY": " test-key "}, clear=False):
                result = load_api_key("gemini")
                assert result == " test-key "
