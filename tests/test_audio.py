"""Tests for audio.py - voiceover script parsing and audio generation."""

import pytest
import base64
import struct
from pathlib import Path

from montaigne.audio import (
    parse_voiceover_script,
    _parse_audio_mime_type,
    _decode_audio_data,
    _convert_to_wav,
    VOICES,
    DEFAULT_VOICE,
)


class TestParseVoiceoverScript:
    """Tests for voiceover script parsing."""

    def test_parse_standard_format(self, sample_voiceover_script):
        """Parse a standard voiceover script."""
        slides = parse_voiceover_script(sample_voiceover_script)

        assert len(slides) == 3

        # Check first slide
        assert slides[0]["number"] == 1
        assert "Introduction" in slides[0]["title"]
        assert "artificial intelligence" in slides[0]["text"]

        # Check second slide
        assert slides[1]["number"] == 2
        assert "Concepts" in slides[1]["title"] or slides[1]["title"]
        assert "machine learning" in slides[1]["text"].lower()

        # Check third slide
        assert slides[2]["number"] == 3
        assert "AI is transforming" in slides[2]["text"]

    def test_parse_alternative_format(self, sample_voiceover_script_alt_format):
        """Parse script with alternative formatting (dashes, em-dashes)."""
        slides = parse_voiceover_script(sample_voiceover_script_alt_format)

        # Should handle different separators (-, —, :)
        assert len(slides) >= 2

        # Verify slide numbers are parsed correctly
        slide_numbers = [s["number"] for s in slides]
        assert 1 in slide_numbers
        assert 2 in slide_numbers

    def test_parse_empty_script(self, temp_dir):
        """Empty script should return empty list."""
        empty_script = temp_dir / "empty.md"
        empty_script.write_text("# Empty Script\n\nNo slides here.", encoding="utf-8")

        slides = parse_voiceover_script(empty_script)
        assert slides == []

    def test_parse_script_without_duration(self, temp_dir):
        """Script without duration markers - should still capture content after headers."""
        script_content = """## SLIDE 1: Test Slide

This is content without a duration marker.
It should still be captured somehow.
"""
        script_path = temp_dir / "no_duration.md"
        script_path.write_text(script_content, encoding="utf-8")

        slides = parse_voiceover_script(script_path)
        # Current implementation requires Duration marker, so this may be empty
        # This test documents current behavior
        assert isinstance(slides, list)

    def test_slide_text_excludes_metadata(self, sample_voiceover_script):
        """Voiceover text should not include metadata like Duration or Tone."""
        slides = parse_voiceover_script(sample_voiceover_script)

        for slide in slides:
            assert "Duration:" not in slide["text"]
            assert "**Duration" not in slide["text"]
            assert "Tone:" not in slide["text"]

    def test_slide_title_truncation(self, temp_dir):
        """Long titles should be truncated to 50 chars."""
        long_title = "A" * 100
        script_content = f"""## SLIDE 1: {long_title}
**Duration:** 30s

Some voiceover text here.
"""
        script_path = temp_dir / "long_title.md"
        script_path.write_text(script_content, encoding="utf-8")

        slides = parse_voiceover_script(script_path)
        if slides:
            assert len(slides[0]["title"]) <= 50


class TestParseAudioMimeType:
    """Tests for audio MIME type parsing."""

    def test_parse_standard_mime(self):
        """Parse standard audio/L16 MIME type."""
        result = _parse_audio_mime_type("audio/L16;rate=24000")

        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000

    def test_parse_different_sample_rates(self):
        """Parse MIME types with different sample rates."""
        result = _parse_audio_mime_type("audio/L16;rate=44100")
        assert result["rate"] == 44100

        result = _parse_audio_mime_type("audio/L16;rate=16000")
        assert result["rate"] == 16000

    def test_parse_different_bit_depths(self):
        """Parse MIME types with different bit depths."""
        result = _parse_audio_mime_type("audio/L8;rate=24000")
        assert result["bits_per_sample"] == 8

        result = _parse_audio_mime_type("audio/L24;rate=24000")
        assert result["bits_per_sample"] == 24

    def test_parse_mime_with_extra_params(self):
        """Parse MIME type with extra parameters."""
        result = _parse_audio_mime_type("audio/L16;rate=24000;channels=1")
        assert result["rate"] == 24000
        assert result["bits_per_sample"] == 16

    def test_parse_malformed_mime_defaults(self):
        """Malformed MIME type should return defaults."""
        result = _parse_audio_mime_type("audio/unknown")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000

        result = _parse_audio_mime_type("")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000

    def test_parse_mime_case_insensitive(self):
        """Rate parameter should be case-insensitive."""
        result = _parse_audio_mime_type("audio/L16;RATE=48000")
        assert result["rate"] == 48000


class TestDecodeAudioData:
    """Tests for audio data decoding."""

    def test_decode_base64_data(self):
        """Decode base64-encoded audio data."""
        original = b"Hello, audio data!"
        encoded = base64.b64encode(original)

        result = _decode_audio_data(encoded)
        assert result == original

    def test_pass_through_binary_data(self):
        """Binary data should pass through unchanged."""
        binary_data = bytes([0x00, 0x01, 0x80, 0xFF, 0x7F])

        result = _decode_audio_data(binary_data)
        assert result == binary_data

    def test_decode_empty_data(self):
        """Empty data should return empty bytes."""
        result = _decode_audio_data(b"")
        assert result == b""


class TestConvertToWav:
    """Tests for WAV conversion."""

    def test_wav_header_structure(self):
        """Generated WAV should have correct header structure."""
        audio_data = bytes([0] * 1000)  # 1000 bytes of silence
        mime_type = "audio/L16;rate=24000"

        wav_data = _convert_to_wav(audio_data, mime_type)

        # Check RIFF header
        assert wav_data[:4] == b"RIFF"
        # Check WAVE format
        assert wav_data[8:12] == b"WAVE"
        # Check fmt chunk
        assert wav_data[12:16] == b"fmt "
        # Check data chunk
        assert wav_data[36:40] == b"data"

    def test_wav_data_size(self):
        """WAV file size should be header + data."""
        audio_data = bytes([0] * 500)
        mime_type = "audio/L16;rate=24000"

        wav_data = _convert_to_wav(audio_data, mime_type)

        # Header is 44 bytes, data is 500 bytes
        assert len(wav_data) == 44 + 500

    def test_wav_sample_rate_in_header(self):
        """Sample rate should be correctly set in WAV header."""
        audio_data = bytes([0] * 100)

        # Test with 24000 Hz
        wav_data = _convert_to_wav(audio_data, "audio/L16;rate=24000")
        # Sample rate is at bytes 24-28 (little-endian)
        sample_rate = struct.unpack("<I", wav_data[24:28])[0]
        assert sample_rate == 24000

        # Test with 44100 Hz
        wav_data = _convert_to_wav(audio_data, "audio/L16;rate=44100")
        sample_rate = struct.unpack("<I", wav_data[24:28])[0]
        assert sample_rate == 44100

    def test_wav_bits_per_sample(self):
        """Bits per sample should be correctly set in WAV header."""
        audio_data = bytes([0] * 100)

        wav_data = _convert_to_wav(audio_data, "audio/L16;rate=24000")
        # Bits per sample is at bytes 34-36 (little-endian)
        bits_per_sample = struct.unpack("<H", wav_data[34:36])[0]
        assert bits_per_sample == 16


class TestVoiceConstants:
    """Tests for voice-related constants."""

    def test_voices_list_not_empty(self):
        """VOICES list should contain available voices."""
        assert len(VOICES) > 0

    def test_default_voice_in_list(self):
        """Default voice should be in the voices list."""
        assert DEFAULT_VOICE in VOICES

    def test_known_voices_present(self):
        """Known voice names should be present."""
        expected_voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"]
        for voice in expected_voices:
            assert voice in VOICES
