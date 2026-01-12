"""Tests for progress bar integration in long-running operations."""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestProgressBars:
    """Tests for tqdm progress bar integration."""

    def test_pdf_extraction_uses_tqdm_in_tty(self, temp_dir):
        """PDF extraction should use tqdm when in a TTY environment."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        # Mock fitz and tqdm
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=3)
        mock_fitz.open.return_value = mock_doc

        mock_tqdm = MagicMock()
        mock_tqdm_instance = MagicMock()
        mock_tqdm_instance.__iter__ = Mock(return_value=iter(range(3)))
        mock_tqdm.return_value = mock_tqdm_instance

        # Patch tqdm module correctly
        mock_tqdm_module = MagicMock()
        mock_tqdm_module.tqdm = mock_tqdm

        with patch.dict(sys.modules, {"fitz": mock_fitz, "tqdm": mock_tqdm_module}):
            with patch("sys.stderr.isatty", return_value=True):
                # Import the module after patches are in place
                import importlib
                import montaigne.pdf

                importlib.reload(montaigne.pdf)
                montaigne.pdf.extract_pdf_pages(pdf_path)

        # Verify tqdm was called with correct parameters
        assert mock_tqdm.called
        call_args = mock_tqdm.call_args
        assert call_args[1]["desc"] == "Extracting pages"
        assert call_args[1]["unit"] == "page"

    def test_pdf_extraction_fallback_without_tqdm(self, temp_dir):
        """PDF extraction should work without tqdm."""
        from montaigne.pdf import extract_pdf_pages

        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        # Mock fitz
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=2)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            # Should not raise ImportError
            result = extract_pdf_pages(pdf_path)
            assert len(result) == 2

    def test_tqdm_available_and_tty_enabled(self):
        """Verify tqdm is available when installed."""
        try:
            from tqdm import tqdm

            # If tqdm is available, it should be callable
            assert callable(tqdm)
        except ImportError:
            pytest.skip("tqdm not installed")

    def test_tqdm_integration_works_with_real_tqdm(self, temp_dir):
        """Test that the integration works with real tqdm (if available)."""
        try:
            from tqdm import tqdm
        except ImportError:
            pytest.skip("tqdm not installed")

        from montaigne.pdf import extract_pdf_pages

        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        # Mock fitz
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=2)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            # This should work whether or not we're in a TTY
            result = extract_pdf_pages(pdf_path)
            assert len(result) == 2

    def test_non_tty_environment_uses_fallback(self, temp_dir):
        """Operations should work in non-TTY environments without tqdm."""
        from montaigne.pdf import extract_pdf_pages

        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {"fitz": mock_fitz}):
            with patch("sys.stderr.isatty", return_value=False):
                # Should not use tqdm but still work
                result = extract_pdf_pages(pdf_path)
                assert len(result) == 1

