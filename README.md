# Montaigne

Media processing toolkit for presentation localization using Google Gemini AI.

## Features

- **PDF Extraction**: Convert PDF pages to images
- **Script Generation**: Generate voiceover scripts from slides using AI
- **Image Translation**: Translate text in images to any language
- **Audio Generation**: Generate voiceover audio from scripts using TTS
- **Video Generation**: Combine slides and audio into a narrated video
- **Graphical Interface**: User-friendly GUI for all operations

## Installation

```bash
pip install montaigne
```

Or from source:
```bash
pip install -e .
```

## Setup

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
2. Create a `.env` file:
   ```
   GEMINI_API_KEY=your-api-key
   ```
3. Install ffmpeg for video generation:
   - Windows: `choco install ffmpeg` or `winget install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
4. Verify setup:
   ```bash
   essai setup
   ```

## Graphical Interface

Launch the GUI for a user-friendly experience:

```bash
essai gui
```

```
┌─────────────────────────────────────────┐
│             Montaigne                   │
│  Transform presentations into videos    │
├─────────────────────────────────────────┤
│ [Quick Video] [Individual Steps] [Settings]
│                                         │
│ PDF File:     [________________] [Browse]│
│ Script:       [________________] [Browse]│
│ Output:       [________________] [Browse]│
│ Voice:        [Orus ▼]                  │
│ Resolution:   [1920:1080 ▼]             │
├─────────────────────────────────────────┤
│ Output:                                 │
│ ┌─────────────────────────────────────┐ │
│ │ Starting video generation...       │ │
│ │ Extracting pages...                 │ │
│ └─────────────────────────────────────┘ │
│ [▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │
│ [Generate Video]  [Clear]  [Open Folder]│
└─────────────────────────────────────────┘
```

## Command Line Usage

### One-Command Video Generation

```bash
essai video --pdf presentation.pdf
```

This runs the full pipeline: PDF → Script → Audio → Video

### Extract PDF to Images

```bash
essai pdf presentation.pdf
essai pdf presentation.pdf --dpi 200 --format jpg
```

### Generate Voiceover Script from Slides

```bash
essai script --input presentation.pdf
essai script --input slides_images/ --context "AI workshop"
```

### Generate Audio from Script

```bash
essai audio --script voiceover.md
essai audio --script voiceover.md --voice Kore
```

Available voices: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Orus`

### Generate Video from Existing Assets

```bash
essai video --images slides_images/ --audio voiceover_audio/
essai video --images slides/ --audio audio/ --resolution 1280:720
```

### Translate Images

```bash
essai images --input slides/
essai images --input image.png --lang Spanish
```

### Full Localization Pipeline

```bash
essai localize --pdf presentation.pdf --script voiceover.md --lang French
```

This will:
1. Extract PDF pages to images
2. Translate all images to the target language
3. Generate audio for all slides

## Full Pipeline Example

```bash
# Step-by-step
essai pdf presentation.pdf            # Extract slides
essai script --input presentation.pdf # Generate script
essai audio --script voiceover.md     # Generate audio
essai video --images slides/ --audio audio/  # Create video

# Or one command
essai video --pdf presentation.pdf
```

## Voiceover Script Format

Scripts should follow this markdown format:

```markdown
## SLIDE 1: Title
**[Duration: ~45 seconds]**

Your narration text for slide 1 goes here.

---

## SLIDE 2: Next Topic
**[Duration: ~60 seconds]**

Narration for slide 2.
```

## Requirements

- Python 3.10+
- Google Gemini API key
- ffmpeg (for video generation)
- Dependencies: `google-genai`, `python-dotenv`, `pymupdf`
