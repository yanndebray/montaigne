"""Tests for cli.py - command-line interface."""

import pytest
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from montaigne.cli import main


class TestMainArgParsing:
    """Tests for main CLI argument parsing."""

    def test_no_command_prints_help(self, capsys):
        """No command should print help."""
        with patch.object(sys, 'argv', ['essai']):
            main()

        captured = capsys.readouterr()
        assert "Montaigne" in captured.out or "usage" in captured.out.lower()

    def test_version_flag(self):
        """--version flag should print version and exit."""
        with patch.object(sys, 'argv', ['essai', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestSetupCommand:
    """Tests for the setup command."""

    def test_setup_checks_dependencies(self, capsys):
        """Setup command should check dependencies."""
        with patch.object(sys, 'argv', ['essai', 'setup']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('dotenv.load_dotenv'):
                    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                        main()

        captured = capsys.readouterr()
        assert "Setup" in captured.out or "dependencies" in captured.out.lower()


class TestPdfCommand:
    """Tests for the pdf command."""

    def test_pdf_requires_input(self):
        """PDF command requires input argument."""
        with patch.object(sys, 'argv', ['essai', 'pdf']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error

    def test_pdf_with_valid_args(self, temp_dir):
        """PDF command with valid arguments."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path)]):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
                    main()
                    mock_extract.assert_called_once()

    def test_pdf_dpi_option(self, temp_dir):
        """PDF command respects --dpi option."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path), '--dpi', '300']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
                    main()
                    call_kwargs = mock_extract.call_args
                    assert call_kwargs.kwargs['dpi'] == 300

    def test_pdf_format_option(self, temp_dir):
        """PDF command respects --format option."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path), '--format', 'jpg']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
                    main()
                    call_kwargs = mock_extract.call_args
                    assert call_kwargs.kwargs['image_format'] == 'jpg'


class TestScriptCommand:
    """Tests for the script command."""

    def test_script_auto_detects_pdf(self, temp_dir):
        """Script command auto-detects PDF in current directory."""
        pdf_path = temp_dir / "presentation.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'script']):
            with patch('montaigne.cli.Path.cwd', return_value=temp_dir):
                with patch('montaigne.config.check_dependencies', return_value=True):
                    with patch('montaigne.scripts.generate_scripts') as mock_gen:
                        main()
                        mock_gen.assert_called_once()
                        # First arg should be the detected PDF
                        assert mock_gen.call_args[0][0].name == "presentation.pdf"

    def test_script_with_context(self, temp_dir):
        """Script command passes context to generator."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'script', '--input', str(pdf_path), '--context', 'AI presentation']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.scripts.generate_scripts') as mock_gen:
                    main()
                    call_kwargs = mock_gen.call_args
                    assert call_kwargs.kwargs['context'] == 'AI presentation'


class TestAudioCommand:
    """Tests for the audio command."""

    def test_audio_auto_detects_script(self, temp_dir):
        """Audio command auto-detects voiceover script."""
        script_path = temp_dir / "presentation_voiceover.md"
        script_path.write_text("# Voiceover Script")

        with patch.object(sys, 'argv', ['essai', 'audio']):
            with patch('montaigne.cli.Path.cwd', return_value=temp_dir):
                with patch('montaigne.config.check_dependencies', return_value=True):
                    with patch('montaigne.audio.generate_audio') as mock_gen:
                        main()
                        mock_gen.assert_called_once()
                        assert "voiceover" in str(mock_gen.call_args[0][0])

    def test_audio_voice_option(self, temp_dir):
        """Audio command respects --voice option."""
        script_path = temp_dir / "script.md"
        script_path.touch()

        with patch.object(sys, 'argv', ['essai', 'audio', '--script', str(script_path), '--voice', 'Fenrir']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.audio.generate_audio') as mock_gen:
                    main()
                    call_kwargs = mock_gen.call_args
                    assert call_kwargs.kwargs['voice'] == 'Fenrir'


class TestImagesCommand:
    """Tests for the images command."""

    def test_images_default_language(self, temp_dir):
        """Images command defaults to French."""
        img_path = temp_dir / "slide.png"
        img_path.touch()

        with patch.object(sys, 'argv', ['essai', 'images', '--input', str(img_path)]):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.images.translate_images') as mock_trans:
                    main()
                    call_kwargs = mock_trans.call_args
                    assert call_kwargs.kwargs['target_lang'] == 'French'

    def test_images_custom_language(self, temp_dir):
        """Images command respects --lang option."""
        img_path = temp_dir / "slide.png"
        img_path.touch()

        with patch.object(sys, 'argv', ['essai', 'images', '--input', str(img_path), '--lang', 'Spanish']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.images.translate_images') as mock_trans:
                    main()
                    call_kwargs = mock_trans.call_args
                    assert call_kwargs.kwargs['target_lang'] == 'Spanish'


class TestVideoCommand:
    """Tests for the video command."""

    def test_video_checks_ffmpeg(self, capsys):
        """Video command should check for ffmpeg."""
        with patch.object(sys, 'argv', ['essai', 'video', '--pdf', 'test.pdf']):
            with patch('montaigne.video.check_ffmpeg', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "ffmpeg" in captured.out.lower()

    def test_video_with_pdf_runs_pipeline(self, temp_dir):
        """Video command with --pdf runs full pipeline."""
        pdf_path = temp_dir / "presentation.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'video', '--pdf', str(pdf_path)]):
            with patch('montaigne.video.check_ffmpeg', return_value=True):
                with patch('montaigne.video.generate_video_from_pdf') as mock_gen:
                    main()
                    mock_gen.assert_called_once()


class TestPptCommand:
    """Tests for the ppt command."""

    def test_ppt_auto_detects_pdf(self, temp_dir):
        """PPT command auto-detects PDF."""
        pdf_path = temp_dir / "slides.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'ppt']):
            with patch('montaigne.cli.Path.cwd', return_value=temp_dir):
                with patch('montaigne.config.check_dependencies', return_value=True):
                    with patch('montaigne.ppt.create_pptx') as mock_create:
                        main()
                        mock_create.assert_called_once()
                        assert mock_create.call_args[0][0].suffix == ".pdf"

    def test_ppt_with_script(self, temp_dir):
        """PPT command uses script for notes."""
        pdf_path = temp_dir / "slides.pdf"
        pdf_path.touch()
        script_path = temp_dir / "voiceover.md"
        script_path.touch()

        with patch.object(sys, 'argv', ['essai', 'ppt', '--input', str(pdf_path), '--script', str(script_path)]):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.ppt.create_pptx') as mock_create:
                    main()
                    call_kwargs = mock_create.call_args
                    assert call_kwargs.kwargs['script_path'] is not None


class TestLocalizeCommand:
    """Tests for the localize command."""

    def test_localize_with_pdf(self, temp_dir):
        """Localize command with PDF runs full pipeline."""
        pdf_path = temp_dir / "deck.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'localize', '--pdf', str(pdf_path), '--lang', 'German']):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.pdf.extract_pdf_pages', return_value=[temp_dir / "page_001.png"]):
                    with patch('montaigne.images.translate_images'):
                        main()
                        # Should complete without error


class TestDependencyChecks:
    """Tests for dependency checking behavior."""

    def test_pdf_requires_dependencies(self, temp_dir):
        """PDF command should exit if dependencies not installed."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path)]):
            with patch('montaigne.config.check_dependencies', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_script_requires_dependencies(self, temp_dir):
        """Script command should exit if dependencies not installed."""
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        with patch.object(sys, 'argv', ['essai', 'script', '--input', str(pdf_path)]):
            with patch('montaigne.config.check_dependencies', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_audio_requires_dependencies(self, temp_dir):
        """Audio command should exit if dependencies not installed."""
        script_path = temp_dir / "test.md"
        script_path.touch()

        with patch.object(sys, 'argv', ['essai', 'audio', '--script', str(script_path)]):
            with patch('montaigne.config.check_dependencies', return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
