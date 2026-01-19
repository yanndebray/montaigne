# Montaigne

Media processing toolkit for presentation localization using Google Gemini AI.

## Features

- **PDF Extraction**: Convert PDF pages to images
- **Script Generation**: Generate voiceover scripts from slides using AI
- **Image Translation**: Translate text in images to any language
- **Audio Generation**: Generate voiceover audio from scripts using TTS
- **PowerPoint Generation**: Create PPTX from PDF or images with speaker notes
- **Video Generation**: Combine slides and audio into MP4 videos
- **Video/Audio Annotation**: Frame-accurate annotation tool with waveform visualization
- **Web Editor**: Streamlit-based slide editor for managing presentations

## Installation

### Using pip

```bash
pip install montaigne
```

### With optional dependencies

```bash
# Install with web editor support
pip install "montaigne[edit]"

# Install with annotation tool support
pip install "montaigne[annotate]"

# Install all optional dependencies
pip install "montaigne[all]"
```

### Using uv

```bash
uv pip install montaigne
```

### Using uvx (no installation required)

```bash
uvx --from montaigne essai setup
uvx --from montaigne essai script --input presentation.pdf
```

## Setup

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
2. Create a `.env` file:
   ```
   GEMINI_API_KEY=your-api-key
   ```
3. Verify setup:
   ```bash
   essai setup
   ```

## Usage

### Extract PDF to Images

```bash
essai pdf presentation.pdf
essai pdf presentation.pdf --dpi 200 --format jpg
```

### Generate Voiceover Script from Slides

```bash
essai script --input presentation.pdf
essai script --input slides_images/ --context "AI workshop"
essai script --input presentation.pdf --output custom_script.md
essai script --input presentation.pdf --model gemini-2.5-flash
```

Options:
- `--input, -i`: PDF file or folder of slide images
- `--output, -o`: Output markdown file path
- `--context, -c`: Additional context to guide script generation
- `--model, -m`: Gemini model to use (default: `gemini-3-pro-preview`)

### Generate Audio from Script

```bash
essai audio --script voiceover.md
essai audio --script voiceover.md --voice Kore
essai audio --script voiceover.md --model gemini-2.5-flash-preview-tts
```

Available voices: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Orus`

Options:
- `--script, -s`: Path to voiceover markdown script
- `--voice, -v`: TTS voice to use (default: `Orus`)
- `--model, -m`: Gemini TTS model (default: `gemini-2.5-pro-preview-tts`)

### Translate Images

```bash
essai images --input slides/
essai images --input image.png --lang Spanish
essai images --input slides/ --model gemini-2.0-flash-exp
```

Options:
- `--input, -i`: Image file or folder of images
- `--lang, -l`: Target language (default: `French`)
- `--model, -m`: Gemini model (default: `gemini-3-pro-image-preview`)

### Create PowerPoint from PDF or Images

```bash
essai ppt --input presentation.pdf
essai ppt --input slides/ --script voiceover.md
essai ppt --input presentation.pdf --keep-images
```

This will create a `.pptx` file with each PDF page or image as a slide. If a voiceover script is provided, it will be added as speaker notes.

### Generate Video from Slides

```bash
essai video --pdf presentation.pdf
essai video --images slides/ --audio audio/
```

### Full Localization Pipeline

```bash
essai localize --pdf presentation.pdf --script voiceover.md --lang French
```

This will:
1. Extract PDF pages to images
2. Translate all images to the target language
3. Generate audio for all slides

### Video/Audio Annotation Tool

Launch an interactive web UI for annotating videos or audio files with frame-accurate timestamps:

```bash
# Install annotation dependencies first
pip install "montaigne[annotate]"

# Launch annotation UI
essai annotate video.mp4
essai annotate audio.wav
essai annotate                        # Auto-detect media in current dir
essai annotate video.mp4 --network    # Make accessible on local network

# Export annotations
essai annotate video.mp4 --export srt   # Export to SRT (Premiere, DaVinci)
essai annotate video.mp4 --export vtt   # Export to WebVTT (browsers)
essai annotate video.mp4 --export json  # Export to JSON
```

**Keyboard shortcuts:**
| Key | Action |
|-----|--------|
| Space | Play/Pause |
| I | Set In point for range |
| O | Set Out point for range |
| [ ] | Step frame backward/forward |
| Ctrl+Enter | Submit annotation |
| Escape | Clear range / exit input |

**Features:**
- Frame-accurate timing using `requestVideoFrameCallback` API
- Waveform visualization with click-to-seek
- Light/dark theme toggle
- Local-first SQLite storage (zero-latency)
- Export to WebVTT, SRT, JSON formats

### Web Editor

Launch a Streamlit-based web interface for managing slides and scripts:

```bash
# Install editor dependencies first
pip install "montaigne[edit]"

# Launch the editor
essai edit
essai edit --pdf presentation.pdf --script voiceover.md
```

## Model Configuration

Each AI command supports a `--model` / `-m` flag to override the default Gemini model:

| Command | Default Model | Purpose |
|---------|---------------|---------|
| `essai script` | `gemini-3-pro-preview` | Script generation |
| `essai audio` | `gemini-2.5-pro-preview-tts` | Text-to-speech |
| `essai images` | `gemini-3-pro-image-preview` | Image translation |

List available models:
```bash
essai models
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

## Demo

See the `demo/hamlet/` folder for a complete example with:
- Sample PDF presentation
- Voiceover script
- Image asset

```bash
cd demo/hamlet
essai localize --lang French
```

## Requirements

- Python 3.10+
- Google Gemini API key
- ffmpeg (for video generation)
- Dependencies: `google-genai`, `python-dotenv`, `pymupdf`, `python-pptx`, `Pillow`

### Optional Dependencies

- **edit**: `streamlit` - Web editor interface
- **annotate**: `flask` - Video/audio annotation tool
- **cloud**: `fastapi`, `uvicorn`, `google-cloud-storage` - Cloud API deployment
