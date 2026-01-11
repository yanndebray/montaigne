"""Tests for pdf.py - PDF extraction functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

from montaigne.pdf import extract_pdf_pages, get_pdf_info


class TestExtractPdfPages:
    """Tests for PDF page extraction."""

    def test_extract_nonexistent_pdf_raises_error(self, temp_dir):
        """Extracting from non-existent PDF should raise FileNotFoundError."""
        fake_pdf = temp_dir / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            extract_pdf_pages(fake_pdf)

        assert "PDF not found" in str(exc_info.value)

    def test_default_output_directory(self, temp_dir):
        """Default output directory should be {pdf_stem}_images/."""
        # Create a mock PDF file (just for path testing)
        pdf_path = temp_dir / "presentation.pdf"
        pdf_path.touch()

        # Mock fitz module
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            extract_pdf_pages(pdf_path)

        # Check output directory was created
        expected_dir = temp_dir / "presentation_images"
        assert expected_dir.exists()

    def test_custom_output_directory(self, temp_dir):
        """Custom output directory should be used when specified."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        custom_output = temp_dir / "custom_output"

        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            extract_pdf_pages(pdf_path, output_dir=custom_output)

        assert custom_output.exists()

    def test_dpi_zoom_calculation(self, temp_dir):
        """DPI should correctly affect zoom factor (72 DPI is 1:1)."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            # Extract with 150 DPI
            extract_pdf_pages(pdf_path, dpi=150)

        # Check Matrix was called with correct zoom
        # zoom = 150/72 ≈ 2.083
        mock_fitz.Matrix.assert_called()
        call_args = mock_fitz.Matrix.call_args[0]
        expected_zoom = 150 / 72
        assert abs(call_args[0] - expected_zoom) < 0.01

    def test_png_format_output(self, temp_dir):
        """PNG format should produce .png files."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        output_dir = temp_dir / "output"

        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=2)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            result = extract_pdf_pages(pdf_path, output_dir=output_dir, image_format="png")

        # Check save was called for PNG
        assert mock_pix.save.called
        call_path = str(mock_pix.save.call_args_list[0][0][0])
        assert call_path.endswith(".png")

    def test_jpg_format_output(self, temp_dir):
        """JPG format should produce .jpg files with quality setting."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        output_dir = temp_dir / "output"

        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            result = extract_pdf_pages(pdf_path, output_dir=output_dir, image_format="jpg")

        # Check save was called with jpg_quality
        mock_pix.save.assert_called()
        call_args = mock_pix.save.call_args
        assert "jpg_quality" in call_args.kwargs or len(call_args.args) > 1

    def test_page_numbering_format(self, temp_dir):
        """Pages should be numbered with 3-digit padding (001, 002, etc.)."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        output_dir = temp_dir / "output"

        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=3)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            result = extract_pdf_pages(pdf_path, output_dir=output_dir)

        # Check returned paths have correct naming
        assert len(result) == 3
        assert "page_001" in str(result[0])
        assert "page_002" in str(result[1])
        assert "page_003" in str(result[2])

    def test_document_closed_after_extraction(self, temp_dir):
        """PDF document should be closed after extraction."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            extract_pdf_pages(pdf_path)

        mock_doc.close.assert_called_once()


class TestGetPdfInfo:
    """Tests for PDF info extraction."""

    def test_get_basic_info(self, temp_dir):
        """Get basic PDF information."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_page = MagicMock()
        mock_page.rect.width = 612  # Letter width in points
        mock_page.rect.height = 792  # Letter height in points

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=10)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_doc.metadata = {
            "title": "Test Presentation",
            "author": "Test Author",
            "subject": "Testing",
            "creator": "Test Creator",
        }
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            info = get_pdf_info(pdf_path)

        assert info["page_count"] == 10
        assert info["title"] == "Test Presentation"
        assert info["author"] == "Test Author"
        assert info["width"] == 612
        assert info["height"] == 792

    def test_get_info_empty_metadata(self, temp_dir):
        """Handle PDF with empty metadata."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_page = MagicMock()
        mock_page.rect.width = 1920
        mock_page.rect.height = 1080

        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=5)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_doc.metadata = {}
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            info = get_pdf_info(pdf_path)

        assert info["page_count"] == 5
        assert info["title"] == ""
        assert info["author"] == ""

    def test_document_closed_after_info(self, temp_dir):
        """Document should be closed after getting info."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=MagicMock())
        mock_doc.metadata = {}
        mock_fitz.open.return_value = mock_doc

        with patch.dict(sys.modules, {'fitz': mock_fitz}):
            get_pdf_info(pdf_path)

        mock_doc.close.assert_called_once()
