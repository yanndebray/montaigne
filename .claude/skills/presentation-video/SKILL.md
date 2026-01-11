---
name: presentation-video
description: Generate narrated videos from presentation PDFs with AI voiceover scripts. Use when creating video presentations, generating voiceovers for slides, or localizing presentations to other languages.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Presentation Video Generator Skill

Generate narrated videos from presentation PDFs using contextual source documents to create rich, informed voiceover scripts.

## When This Skill Applies

Use this skill when the user wants to:
- Create a video from a PDF presentation
- Generate voiceover scripts for slides
- Add narration to a slide deck
- Localize a presentation to another language
- Create TTS audio from slides

## Workflow Overview

1. **Analyze Input** - Identify PDF and context documents
2. **Extract Context** - Read .docx, .pdf, .md files for narrative context
3. **Extract Slides** - Convert PDF to images using `essai pdf`
4. **Generate Script** - Create voiceover markdown with duration limits
5. **Generate Audio** - Use `essai audio` for TTS
6. **Create Video** - Combine slides + audio with `essai video`

## Configuration

Default settings (can be overridden by user):
- **Max Duration**: 60 seconds per slide
- **Voice**: Orus
- **Speaking Pace**: 130-150 words per minute

## Instructions

### Step 1: Identify Files

Locate the main presentation PDF and scan for context documents:
- `.docx` files - Book summaries, source text
- `.pdf` files - Related presentations, playbooks
- `.md` files - Additional context
- `.png/.jpg` - Infographics, visual references

### Step 2: Extract Context from Documents

For `.docx` files, extract text content. See [DOCX_EXTRACTION.md](DOCX_EXTRACTION.md) for the extraction script.

For `.pdf` files, use:
```bash
essai pdf <pdf_path>
```

### Step 3: Extract Presentation Slides

```bash
essai pdf <presentation.pdf>
```

Creates `{pdf_stem}_images/` with `page_001.png`, `page_002.png`, etc.

Read and analyze each slide image to understand content and flow.

### Step 4: Generate Voiceover Script

Create a markdown script following the format in [SCRIPT_FORMAT.md](SCRIPT_FORMAT.md).

Key requirements:
- Master prompt with duration limit at the top
- Each slide: Duration, Tone, Voice-Over text
- Incorporate examples and stories from context documents
- Maintain narrative flow between slides

Save as `{pdf_stem}_voiceover.md`

### Step 5: Generate Audio

```bash
essai audio --script {pdf_stem}_voiceover.md --voice Orus
```

Available voices: Orus, Kore, Charon, Fenrir, Aoede, Puck

Creates `{pdf_stem}_voiceover_audio/` with WAV files.

### Step 6: Create Video

```bash
essai video --pdf <presentation.pdf> --audio {pdf_stem}_voiceover_audio
```

### Step 7: Localization (Optional)

If user requests localization to another language:

```bash
# Translate slide images
essai images --input {pdf_stem}_images --lang <language>

# Generate translated audio
essai audio --script {pdf_stem}_voiceover_{lang}.md --voice Orus

# Create localized video
essai video --images {pdf_stem}_translated --audio {pdf_stem}_voiceover_{lang}_audio
```

## Output Files

| File | Description |
|------|-------------|
| `{pdf_stem}_images/` | Extracted slide images |
| `{pdf_stem}_voiceover.md` | Voiceover script |
| `{pdf_stem}_voiceover_audio/` | TTS audio files |
| `{pdf_stem}_video.mp4` | Final narrated video |

## References

- [SCRIPT_FORMAT.md](SCRIPT_FORMAT.md) - Voiceover script format specification
- [DOCX_EXTRACTION.md](DOCX_EXTRACTION.md) - How to extract text from .docx files
- [scripts/extract_docx.py](scripts/extract_docx.py) - Python script for .docx extraction
