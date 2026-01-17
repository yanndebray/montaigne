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
essai images --input slides/ --lang French
essai ppt --input presentation.pdf --script voiceover.md
essai video --pdf presentation.pdf
essai localize --pdf presentation.pdf --lang French

# Using custom models (override defaults)
essai script --input presentation.pdf --model gemini-2.5-flash
essai audio --script voiceover.md --model gemini-2.5-flash-preview-tts
essai images --input slides/ --model gemini-2.0-flash-exp
```

## Architecture

### Module Structure

```
montaigne/
├── cli.py      # Main entry point, argparse command definitions
├── config.py   # API key loading, dependency checks, Gemini client factory
├── pdf.py      # PDF extraction using PyMuPDF (fitz)
├── scripts.py  # Two-pass voiceover script generation with Gemini
├── audio.py    # TTS audio generation with Gemini
├── images.py   # Image translation with Gemini
├── video.py    # Video generation with ffmpeg
└── ppt.py      # PowerPoint generation with python-pptx
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
- **ffmpeg**: Required only for video generation (`essai video`)
- **PyMuPDF (fitz)**: PDF extraction
- **python-pptx + Pillow**: PowerPoint generation

### Model Configuration

Each AI command supports a `--model` / `-m` flag to override the default Gemini model:

| Command | Default Model | Flag |
|---------|---------------|------|
| `essai script` | `gemini-3-pro-preview` | `--model` / `-m` |
| `essai audio` | `gemini-2.5-pro-preview-tts` | `--model` / `-m` |
| `essai images` | `gemini-3-pro-image-preview` | `--model` / `-m` |

Example: `essai script --input slides.pdf --model gemini-2.5-flash`

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
