# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Montaigne is a media processing toolkit for presentation localization using Google Gemini AI. It provides a CLI tool (`essai`) that handles:
- PDF extraction to images
- AI-powered voiceover script generation from slides
- Image translation to different languages
- Text-to-speech audio generation
- Video creation from slides + audio
- PowerPoint generation from PDF/images
- **Video/Audio annotation** with frame-accurate timestamps

## Common Commands

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check montaigne/
black --check montaigne/

# Format code
black montaigne/

# Run the CLI
essai --help
essai setup              # Verify API key and dependencies
essai pdf input.pdf      # Extract PDF to images
essai script --input presentation.pdf --context "Topic description"
essai audio --script voiceover.md --voice Orus
essai audio --script voiceover.md --provider coqui --voice female  # Local TTS
essai translate --input slides/ --lang French
essai ppt --input presentation.pdf --script voiceover.md
essai video --pdf presentation.pdf
essai localize --pdf presentation.pdf --lang French

# Using custom models (override defaults)
essai script --input presentation.pdf --model gemini-2.5-flash
essai audio --script voiceover.md --model gemini-2.5-flash-preview-tts
essai translate --input slides/ --model gemini-2.0-flash-exp

# Video annotation tool
pip install -e ".[annotate]"   # Install annotation dependencies
essai annotate video.mp4       # Launch annotation UI
essai annotate                 # Auto-detect media in current dir
essai annotate video.mp4 --export srt   # Export annotations to SRT
essai annotate video.mp4 --export vtt   # Export annotations to WebVTT

# Local TTS with Coqui XTTS-v2
pip install -e ".[coqui]"      # Install Coqui TTS dependencies
essai audio --script voiceover.md --provider coqui
essai audio --script voiceover.md --provider coqui --voice male
essai audio --list-voices --provider coqui  # List available voices
```

## Architecture

### Module Structure

```
montaigne/
├── cli.py              # Main entry point, argparse command definitions
├── config.py           # API key loading, dependency checks, Gemini client factory
├── pdf.py              # PDF extraction using PyMuPDF (fitz)
├── scripts.py          # Two-pass voiceover script generation with Gemini
├── audio.py            # TTS audio generation (supports Gemini, ElevenLabs, Coqui)
├── elevenlabs_tts.py   # ElevenLabs TTS provider integration
├── coqui_tts.py        # Local Coqui XTTS-v2 TTS provider integration
├── images.py           # Image translation with Gemini
├── video.py            # Video generation with ffmpeg
├── ppt.py              # PowerPoint generation with python-pptx
├── annotation.py       # Annotation data models, SQLite storage, export (WebVTT/SRT)
└── annotation_server.py # Flask-based annotation web UI with waveform visualization
```

### Key Patterns

**Gemini Client**: All AI operations use `config.get_gemini_client()` which loads the API key from `.env` file (GEMINI_API_KEY).

**Two-Pass Script Generation** (`scripts.py`):
1. `analyze_presentation_overview()` - First pass analyzes all slides to extract topic, audience, tone, and slide summaries
2. `generate_slide_script()` - Second pass generates individual scripts with sliding window context (previous/next slide awareness)

**File Naming Conventions**:
- PDF extraction: `page_001.png`, `page_002.png`, ...
- Audio files: `slide_01.wav`, `slide_02.wav`, ...
- Output dirs: `{input_stem}_images/`, `{input_stem}_audio/`, `{input_stem}_translated/`

**CLI Auto-detection**: Most commands auto-detect inputs when not specified (finds PDFs, image folders, voiceover scripts in current directory).

### External Dependencies

- **Google Gemini API**: Required for all AI operations (scripts, audio, image translation)
  - Script generation: `gemini-3-pro-preview` (default, configurable via `--model`)
  - TTS: `gemini-2.5-pro-preview-tts` (default, configurable via `--model`)
  - Image translation: `gemini-3-pro-image-preview` (default, configurable via `--model`)
- **ElevenLabs API**: Optional TTS provider (`--provider elevenlabs`)
- **Coqui XTTS-v2**: Optional local TTS provider (`--provider coqui`, requires `pip install montaigne[coqui]`)
  - Runs entirely on local hardware (CPU/GPU)
  - No API key required
  - Supports multilingual voice synthesis
- **ffmpeg**: Required only for video generation (`essai video`)
- **PyMuPDF (fitz)**: PDF extraction
- **python-pptx + Pillow**: PowerPoint generation

### Model Configuration

Each AI command supports a `--model` / `-m` flag to override the default Gemini model:

| Command | Default Model | Flag |
|---------|---------------|------|
| `essai script` | `gemini-3-pro-preview` | `--model` / `-m` |
| `essai audio` | `gemini-2.5-pro-preview-tts` | `--model` / `-m` |
| `essai translate` | `gemini-3-pro-image-preview` | `--model` / `-m` |

Example: `essai script --input slides.pdf --model gemini-2.5-flash`

### TTS Provider Configuration

The `essai audio` command supports multiple TTS providers via the `--provider` flag:

| Provider | Description | Installation | Default Voice |
|----------|-------------|--------------|---------------|
| `gemini` | Google Gemini TTS API (default) | Included | Orus |
| `elevenlabs` | ElevenLabs TTS API | Included | george |
| `coqui` | Local Coqui XTTS-v2 | `pip install montaigne[coqui]` | female |

**Gemini TTS** (default):
- Cloud-based, requires GEMINI_API_KEY
- Voices: Puck, Charon, Kore, Fenrir, Aoede, Orus
- Model configurable via `--model` flag

**ElevenLabs TTS**:
- Cloud-based, requires ELEVENLABS_API_KEY
- Presets: adam, bob, william, george
- Supports custom voice IDs

**Coqui TTS** (local):
- Runs entirely on local hardware (no API key needed)
- Voices: female, male, neutral
- Supports voice cloning with reference audio
- Requires installation: `pip install montaigne[coqui]`

Examples:
```bash
essai audio --script voiceover.md --provider gemini --voice Orus
essai audio --script voiceover.md --provider elevenlabs --voice george
essai audio --script voiceover.md --provider coqui --voice female
```

### Voiceover Script Format

Scripts use markdown with this structure:
```markdown
## SLIDE 1: Title
**Duration:** 30-45 seconds
**Tone:** Inviting, setting the stage

### Voice-Over:
Narration text here...

---
## SLIDE 2: Next Topic
...
```

The `audio.py` parser expects `## SLIDE N:` headers and extracts text after `Duration:` markers.

### Annotation Module

The annotation tool (`essai annotate`) provides frame-accurate video/audio annotation:

**Architecture**:
- **Local-First**: Uses SQLite for zero-latency persistence (no server round-trips)
- **Frame-Accurate**: Uses `requestVideoFrameCallback` API for precise timing (when available)
- **Source-Agnostic**: Works with any video/audio file format

**Data Model** (`annotation.py`):
- Uses millisecond integers for timestamps (avoids floating-point drift)
- Normalized percentage coordinates for resolution-independent shape overlays
- Second-bucketing optimization for O(1) time lookups during playback

**UX Patterns**:
- **Frictionless Capture**: Auto-pauses on typing, captures timestamp automatically
- **Keyboard-First**: I/O for in/out points, brackets for frame stepping
- **Waveform-Native**: Visual audio representation with click-to-seek

**Export Formats**:
- WebVTT (native browser captions)
- SRT (Premiere, DaVinci Resolve compatibility)
- JSON (programmatic access)
